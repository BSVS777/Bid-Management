"""JSON API for bids and tender evaluation.

Status mapping: unknown tender in the path or unknown supplier in a supplier
path -> 404; invalid or unknown supplier_id / amount in the body -> 422;
tender not 'Publicada', deadline reached, or duplicate bid -> 409.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StrictFloat, StrictInt, StrictStr
from sqlalchemy.orm import Session

from app.approval import ApprovalRange, get_approval_ranges
from app.clock import get_now
from app.database import get_db
from app.models import Bid
from app.money import format_crc
from app.services import bids as service

router = APIRouter(tags=["bids"])


class BidIn(BaseModel):
    supplier_id: StrictInt
    amount_crc: StrictStr | StrictInt | StrictFloat


class BidOut(BaseModel):
    id: int
    tender_id: int
    tender_code: str
    supplier_id: int
    supplier_name: str
    amount_crc: str
    created_at: str


class BidUpdate(BaseModel):
    amount_crc: StrictStr | StrictInt | StrictFloat


class EvaluationOut(BaseModel):
    tender_id: int
    tender_code: str
    budget_crc: str
    bid_count: int
    best_bid: BidOut | None
    saving_percent: str | None
    classification: str | None
    approver: str | None
    message: str | None


def to_out(bid: Bid) -> BidOut:
    return BidOut(
        id=bid.id,
        tender_id=bid.tender_id,
        tender_code=bid.tender.code,
        supplier_id=bid.supplier_id,
        supplier_name=bid.supplier.name,
        amount_crc=format_crc(bid.amount_cents),
        created_at=bid.created_at.isoformat(timespec="seconds"),
    )


def to_http_error(exc: service.BidError) -> HTTPException:
    """Map a domain error to a safe HTTP error."""
    if isinstance(exc, service.InvalidBidError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, (service.DuplicateBidError, service.BidNotAllowedError)):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/api/tenders/{tender_id}/bids", status_code=201, response_model=BidOut)
def create(tender_id: int, payload: BidIn, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        return to_out(service.create_bid(
            db, now, tender_id, payload.supplier_id, payload.amount_crc))
    except service.BidError as exc:
        raise to_http_error(exc) from None


@router.get("/api/tenders/{tender_id}/bids", response_model=list[BidOut])
def list_by_tender(tender_id: int, db: Session = Depends(get_db)):
    try:
        return [to_out(b) for b in service.list_bids_by_tender(db, tender_id)]
    except service.BidError as exc:
        raise to_http_error(exc) from None


@router.get("/api/suppliers/{supplier_id}/bids", response_model=list[BidOut])
def list_by_supplier(supplier_id: int, db: Session = Depends(get_db)):
    try:
        return [to_out(b) for b in service.list_bids_by_supplier(db, supplier_id)]
    except service.BidError as exc:
        raise to_http_error(exc) from None


@router.get("/api/tenders/{tender_id}/evaluation", response_model=EvaluationOut)
def evaluation(tender_id: int, db: Session = Depends(get_db),
               ranges: tuple[ApprovalRange, ...] = Depends(get_approval_ranges)):
    try:
        result = service.evaluate_tender(db, tender_id, ranges)
    except service.BidError as exc:
        raise to_http_error(exc) from None
    return EvaluationOut(
        tender_id=result.tender.id,
        tender_code=result.tender.code,
        budget_crc=format_crc(result.tender.budget_cents),
        bid_count=result.bid_count,
        best_bid=to_out(result.best_bid) if result.best_bid else None,
        saving_percent=result.saving_percent,
        classification=result.classification,
        approver=result.approver,
        message=result.message,
    )


@router.get("/api/bids/{bid_id}", response_model=BidOut)
def get_one(bid_id: int, db: Session = Depends(get_db)):
    try:
        return to_out(service.get_bid(db, bid_id))
    except service.BidError as exc:
        raise to_http_error(exc) from None


@router.put("/api/bids/{bid_id}", response_model=BidOut)
def update(bid_id: int, payload: BidUpdate, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        return to_out(service.update_bid(db, now, bid_id, payload.amount_crc))
    except service.BidError as exc:
        raise to_http_error(exc) from None


@router.delete("/api/bids/{bid_id}", status_code=204)
def delete(bid_id: int, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        service.delete_bid(db, now, bid_id)
    except service.BidError as exc:
        raise to_http_error(exc) from None
