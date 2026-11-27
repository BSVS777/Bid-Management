"""JSON API for tenders."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StrictFloat, StrictInt, StrictStr
from sqlalchemy.orm import Session

from app.clock import get_now
from app.database import get_db
from app.models import Tender
from app.money import format_crc
from app.services import tenders as service

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


class TenderIn(BaseModel):
    code: StrictStr
    title: StrictStr
    budget_crc: StrictStr | StrictInt | StrictFloat
    closing_at: StrictStr


class TenderOut(BaseModel):
    id: int
    code: str
    title: str
    budget_crc: str
    closing_at: str
    status: str


def to_out(tender: Tender) -> TenderOut:
    return TenderOut(
        id=tender.id,
        code=tender.code,
        title=tender.title,
        budget_crc=format_crc(tender.budget_cents),
        closing_at=tender.closing_at.isoformat(timespec="seconds"),
        status=tender.status,
    )


def to_http_error(exc: service.TenderError) -> HTTPException:
    """Map a domain error to a safe HTTP error."""
    if isinstance(exc, service.InvalidTenderError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, (service.DuplicateTenderError, service.InvalidTransitionError)):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=404, detail=str(exc))


@router.post("", status_code=201, response_model=TenderOut)
def create(payload: TenderIn, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        return to_out(service.create_tender(
            db, now, payload.code, payload.title, payload.budget_crc,
            payload.closing_at))
    except service.TenderError as exc:
        raise to_http_error(exc) from None


@router.get("", response_model=list[TenderOut])
def list_all(status: str | None = None, db: Session = Depends(get_db)):
    try:
        return [to_out(t) for t in service.list_tenders(db, status)]
    except service.TenderError as exc:
        raise to_http_error(exc) from None


@router.get("/{tender_id}", response_model=TenderOut)
def get_one(tender_id: int, db: Session = Depends(get_db)):
    try:
        return to_out(service.get_tender(db, tender_id))
    except service.TenderError as exc:
        raise to_http_error(exc) from None


@router.put("/{tender_id}", response_model=TenderOut)
def update(tender_id: int, payload: TenderIn, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        return to_out(service.update_tender(
            db, now, tender_id, payload.code, payload.title, payload.budget_crc,
            payload.closing_at))
    except service.TenderError as exc:
        raise to_http_error(exc) from None


@router.post("/{tender_id}/publish", response_model=TenderOut)
def publish(tender_id: int, db: Session = Depends(get_db),
            now: datetime = Depends(get_now)):
    try:
        return to_out(service.publish_tender(db, now, tender_id))
    except service.TenderError as exc:
        raise to_http_error(exc) from None


@router.post("/{tender_id}/close", response_model=TenderOut)
def close(tender_id: int, db: Session = Depends(get_db)):
    try:
        return to_out(service.close_tender(db, tender_id))
    except service.TenderError as exc:
        raise to_http_error(exc) from None


@router.delete("/{tender_id}", status_code=204)
def delete(tender_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_tender(db, tender_id)
    except service.TenderError as exc:
        raise to_http_error(exc) from None
