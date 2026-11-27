"""Server-rendered web UI for bids and tender evaluation."""
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.approval import ApprovalRange, get_approval_ranges
from app.clock import get_now
from app.database import get_db
from app.money import format_crc_display
from app.routers.bids import to_http_error
from app.services import bids as service
from app.services import exchange_rate as rate_service
from app.services import suppliers as supplier_service

router = APIRouter(tags=["bids-web"], include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)
templates.env.filters["crc"] = format_crc_display

_ID_PATTERN = re.compile(r"[0-9]{1,18}", re.ASCII)


def _parse_supplier_id(raw: str) -> int | str:
    """Convert the select value to int; anything else is left for the service to reject."""
    text = raw.strip()
    return int(text) if _ID_PATTERN.fullmatch(text) else raw


def _page(request: Request, db: Session, tender_id: int,
          ranges: tuple[ApprovalRange, ...], form: dict[str, str] | None = None,
          error: str | None = None, status_code: int = 200,
          currency: str = "CRC"):
    try:
        result = service.evaluate_tender(db, tender_id, ranges)
        bids = service.list_bids_by_tender(db, tender_id)
    except service.BidError as exc:
        raise to_http_error(exc) from None
    rate = rate_service.get_current_rate(db) if currency == "USD" else None
    if rate is not None:
        hundredths = rate.rate_hundredths

        def fmt(cents: int) -> str:
            return format_crc_display(rate_service.crc_to_usd(cents, hundredths))
    else:
        fmt = format_crc_display
    return templates.TemplateResponse(
        request,
        "bids.html",
        {
            "fmt": fmt,
            "unit": "USD" if rate is not None else "CRC",
            "rate": rate_service.format_rate(rate.rate_hundredths) if rate else None,
            "rate_at": rate.created_at.strftime("%Y-%m-%d %H:%M:%S") if rate else None,
            "usd_missing": currency == "USD" and rate is None,
            "tender": result.tender,
            "evaluation": result,
            "bids": bids,
            "suppliers": supplier_service.list_suppliers(db),
            "form": form or {"supplier_id": "", "amount_crc": ""},
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/tenders/{tender_id}/bids", response_class=HTMLResponse)
def bids_page(request: Request, tender_id: int, currency: str = "CRC",
              db: Session = Depends(get_db),
              ranges: tuple[ApprovalRange, ...] = Depends(get_approval_ranges)):
    # Display-only toggle: anything other than USD falls back to CRC.
    return _page(request, db, tender_id, ranges,
                 currency="USD" if currency.upper() == "USD" else "CRC")


@router.post("/tenders/{tender_id}/bids", response_class=HTMLResponse)
def create(request: Request, tender_id: int, supplier_id: str = Form(""),
           amount_crc: str = Form(""), db: Session = Depends(get_db),
           now: datetime = Depends(get_now),
           ranges: tuple[ApprovalRange, ...] = Depends(get_approval_ranges)):
    try:
        service.create_bid(db, now, tender_id, _parse_supplier_id(supplier_id),
                           amount_crc)
    except service.BidError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        form = {"supplier_id": supplier_id, "amount_crc": amount_crc}
        return _page(request, db, tender_id, ranges, form, http_exc.detail,
                     http_exc.status_code)
    return RedirectResponse(f"/tenders/{tender_id}/bids", status_code=303)


@router.get("/suppliers/{supplier_id}/bids", response_class=HTMLResponse)
def supplier_bids_page(request: Request, supplier_id: int,
                       db: Session = Depends(get_db)):
    try:
        supplier = supplier_service.get_supplier(db, supplier_id)
    except supplier_service.SupplierError as exc:
        from app.routers.suppliers import to_http_error as supplier_http_error
        raise supplier_http_error(exc) from None
    return templates.TemplateResponse(
        request,
        "supplier_bids.html",
        {"supplier": supplier, "bids": service.list_bids_by_supplier(db, supplier_id)},
    )


@router.post("/tenders/{tender_id}/bids/{bid_id}/delete", response_class=HTMLResponse)
def delete(request: Request, tender_id: int, bid_id: int,
           db: Session = Depends(get_db), now: datetime = Depends(get_now),
           ranges: tuple[ApprovalRange, ...] = Depends(get_approval_ranges)):
    try:
        bid = service.get_bid(db, bid_id)
        if bid.tender_id != tender_id:  # the bid must belong to the tender in the URL
            raise service.BidTargetNotFoundError("Oferta no encontrada.")
        service.delete_bid(db, now, bid_id)
    except service.BidError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        return _page(request, db, tender_id, ranges, error=http_exc.detail,
                     status_code=http_exc.status_code)
    return RedirectResponse(f"/tenders/{tender_id}/bids", status_code=303)
