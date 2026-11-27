"""JSON API for the exchange rate (REQ-010) and USD evaluation views.

Status mapping: invalid rate -> 422; no rate configured -> 404 (GET rate) or
409 (USD evaluation); unknown tender -> 404. Stored CRC amounts are never changed.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StrictFloat, StrictInt, StrictStr
from sqlalchemy.orm import Session

from app.approval import ApprovalRange, get_approval_ranges
from app.clock import get_now
from app.database import get_db
from app.money import format_crc
from app.routers.bids import to_http_error as bid_http_error
from app.services import bids as bid_service
from app.services import exchange_rate as service

router = APIRouter(tags=["exchange-rate"])


class RateIn(BaseModel):
    crc_per_usd: StrictStr | StrictInt | StrictFloat


class RateOut(BaseModel):
    crc_per_usd: str
    set_at: str


class RateItemOut(BaseModel):
    id: int
    crc_per_usd: str
    set_at: str


class UsdBidOut(BaseModel):
    supplier_name: str
    amount_usd: str
    amount_crc: str


class UsdEvaluationOut(BaseModel):
    tender_id: int
    tender_code: str
    currency: str
    crc_per_usd: str
    rate_set_at: str
    budget_usd: str
    budget_crc: str
    best_bid: UsdBidOut | None
    message: str | None


def to_out(row) -> RateOut:
    return RateOut(crc_per_usd=service.format_rate(row.rate_hundredths),
                   set_at=row.created_at.isoformat(timespec="seconds"))


def usd_text(crc_cents: int, rate_hundredths: int) -> str:
    return format_crc(service.crc_to_usd(crc_cents, rate_hundredths))


@router.post("/api/exchange-rate", status_code=201, response_model=RateOut)
def create(payload: RateIn, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        return to_out(service.set_rate(db, now, payload.crc_per_usd))
    except service.InvalidRateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/api/exchange-rate", response_model=RateOut)
def current(db: Session = Depends(get_db)):
    try:
        return to_out(service.require_rate(db))
    except service.RateNotConfiguredError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


def to_item(row) -> RateItemOut:
    return RateItemOut(id=row.id, crc_per_usd=service.format_rate(row.rate_hundredths),
                       set_at=row.created_at.isoformat(timespec="seconds"))


@router.get("/api/exchange-rate/history", response_model=list[RateItemOut])
def history(db: Session = Depends(get_db)):
    return [to_item(r) for r in service.list_rates(db)]


@router.get("/api/exchange-rate/{rate_id}", response_model=RateItemOut)
def get_one(rate_id: int, db: Session = Depends(get_db)):
    try:
        return to_item(service.get_rate(db, rate_id))
    except service.RateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.delete("/api/exchange-rate/{rate_id}", status_code=204)
def delete(rate_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_rate(db, rate_id)
    except service.RateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/api/tenders/{tender_id}/evaluation/usd",
            response_model=UsdEvaluationOut)
def evaluation_usd(tender_id: int, db: Session = Depends(get_db),
                   ranges: tuple[ApprovalRange, ...] = Depends(get_approval_ranges)):
    try:
        result = bid_service.evaluate_tender(db, tender_id, ranges)
    except bid_service.BidError as exc:
        raise bid_http_error(exc) from None
    try:
        rate = service.require_rate(db)
    except service.RateNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    h = rate.rate_hundredths
    best = result.best_bid
    return UsdEvaluationOut(
        tender_id=result.tender.id,
        tender_code=result.tender.code,
        currency="USD",
        crc_per_usd=service.format_rate(h),
        rate_set_at=rate.created_at.isoformat(timespec="seconds"),
        budget_usd=usd_text(result.tender.budget_cents, h),
        budget_crc=format_crc(result.tender.budget_cents),
        best_bid=UsdBidOut(
            supplier_name=best.supplier.name,
            amount_usd=usd_text(best.amount_cents, h),
            amount_crc=format_crc(best.amount_cents),
        ) if best else None,
        message=result.message,
    )
