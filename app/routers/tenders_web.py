"""Server-rendered web UI for tenders."""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.clock import get_now
from app.database import get_db
from app.money import format_crc, format_crc_display
from app.routers.tenders import to_http_error
from app.services import tenders as service

router = APIRouter(tags=["tenders-web"], include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)
templates.env.filters["crc"] = format_crc_display

_INPUT_FORMAT = "%Y-%m-%dT%H:%M"


def _blank_form() -> dict[str, str]:
    return {"code": "", "title": "", "budget_crc": "", "closing_at": ""}


def _list_page(request: Request, db: Session, form: dict[str, str] | None = None,
               error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "tenders.html",
        {
            "tenders": service.list_tenders(db),
            "form": form or _blank_form(),
            "error": error,
            "DRAFT": service.TenderStatus.DRAFT,
            "PUBLISHED": service.TenderStatus.PUBLISHED,
        },
        status_code=status_code,
    )


def _edit_page(request: Request, tender_id: int, form: dict[str, str],
               editable: bool = True, error: str | None = None,
               status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "tender_form.html",
        {"tender_id": tender_id, "form": form, "editable": editable, "error": error},
        status_code=status_code,
    )


@router.get("/tenders", response_class=HTMLResponse)
def list_page(request: Request, db: Session = Depends(get_db)):
    return _list_page(request, db)


@router.post("/tenders", response_class=HTMLResponse)
def create(request: Request, code: str = Form(""), title: str = Form(""),
           budget_crc: str = Form(""), closing_at: str = Form(""),
           db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    try:
        service.create_tender(db, now, code, title, budget_crc, closing_at)
    except service.TenderError as exc:
        http_exc = to_http_error(exc)
        form = {"code": code, "title": title, "budget_crc": budget_crc,
                "closing_at": closing_at}
        return _list_page(request, db, form, http_exc.detail, http_exc.status_code)
    return RedirectResponse("/tenders", status_code=303)


@router.get("/tenders/{tender_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, tender_id: int, db: Session = Depends(get_db)):
    try:
        tender = service.get_tender(db, tender_id)
    except service.TenderError as exc:
        raise to_http_error(exc) from None
    form = {
        "code": tender.code,
        "title": tender.title,
        "budget_crc": format_crc(tender.budget_cents),
        "closing_at": tender.closing_at.strftime(_INPUT_FORMAT),
    }
    if tender.status != service.TenderStatus.DRAFT:
        return _edit_page(
            request, tender.id, form, editable=False,
            error="Solo se puede editar una licitación en estado Borrador.",
            status_code=409)
    return _edit_page(request, tender.id, form)


@router.post("/tenders/{tender_id}/edit", response_class=HTMLResponse)
def edit(request: Request, tender_id: int, code: str = Form(""),
         title: str = Form(""), budget_crc: str = Form(""),
         closing_at: str = Form(""), db: Session = Depends(get_db),
         now: datetime = Depends(get_now)):
    try:
        service.update_tender(db, now, tender_id, code, title, budget_crc, closing_at)
    except service.TenderError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        form = {"code": code, "title": title, "budget_crc": budget_crc,
                "closing_at": closing_at}
        editable = not isinstance(exc, service.InvalidTransitionError)
        return _edit_page(request, tender_id, form, editable, http_exc.detail,
                          http_exc.status_code)
    return RedirectResponse("/tenders", status_code=303)


@router.post("/tenders/{tender_id}/publish", response_class=HTMLResponse)
def publish(request: Request, tender_id: int, db: Session = Depends(get_db),
            now: datetime = Depends(get_now)):
    try:
        service.publish_tender(db, now, tender_id)
    except service.TenderError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        return _list_page(request, db, error=http_exc.detail,
                          status_code=http_exc.status_code)
    return RedirectResponse("/tenders", status_code=303)


@router.post("/tenders/{tender_id}/close", response_class=HTMLResponse)
def close(request: Request, tender_id: int, db: Session = Depends(get_db)):
    try:
        service.close_tender(db, tender_id)
    except service.TenderError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        return _list_page(request, db, error=http_exc.detail,
                          status_code=http_exc.status_code)
    return RedirectResponse("/tenders", status_code=303)
