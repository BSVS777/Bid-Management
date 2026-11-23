"""Bid business rules (REQ-004..009), shared by the API and the web UI.

Check order in ``create_bid`` (first failure wins): tender exists (404) ->
tender is 'Publicada' (409) -> strictly before closing (409) -> supplier is a
valid existing id (422) -> amount valid, > 0 and <= budget (422) -> no previous
bid of that supplier (409). Wrong state and deadline both use 409.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.approval import DEFAULT_APPROVAL_RANGES, ApprovalRange, approver_for
from app.models import Bid, Supplier, Tender
from app.money import InvalidMoneyError, format_crc_display, parse_crc_to_cents
from app.services.suppliers import SupplierNotFoundError, get_supplier
from app.services.tenders import TenderNotFoundError, TenderStatus, get_tender

NO_BIDS_MESSAGE = "Sin ofertas válidas"


class Classification:
    CONVENIENT = "Conveniente"
    ACCEPTABLE = "Aceptable"
    NO_SAVING = "Válida sin ahorro"


class BidError(Exception):
    """Base class for bid domain errors."""


class InvalidBidError(BidError):
    """Invalid supplier or amount (HTTP 422)."""


class DuplicateBidError(BidError):
    """The supplier already bid on this tender (HTTP 409)."""


class BidNotAllowedError(BidError):
    """The tender is not open for bids: wrong state or deadline passed (HTTP 409)."""


class BidTargetNotFoundError(BidError):
    """The tender (or supplier, for supplier listings) does not exist (HTTP 404)."""


def _duplicate_error() -> DuplicateBidError:
    return DuplicateBidError("Este proveedor ya registró una oferta para esta licitación.")


def _tender_or_404(session: Session, tender_id: int) -> Tender:
    try:
        return get_tender(session, tender_id)
    except TenderNotFoundError:
        raise BidTargetNotFoundError("Licitación no encontrada.") from None


def validate_amount(amount_crc: object, budget_cents: int) -> int:
    """Return cents; require 0 < amount <= budget (equal to budget is valid)."""
    try:
        cents = parse_crc_to_cents(amount_crc)
    except InvalidMoneyError as exc:
        raise InvalidBidError(f"Monto inválido: {exc}") from None
    if cents <= 0:
        raise InvalidBidError("El monto de la oferta debe ser mayor que cero.")
    if cents > budget_cents:
        raise InvalidBidError(
            "El monto de la oferta no puede superar el presupuesto de la licitación "
            f"({format_crc_display(budget_cents)} CRC)."
        )
    return cents


def _validate_supplier(session: Session, supplier_id: object) -> Supplier:
    if isinstance(supplier_id, bool) or not isinstance(supplier_id, int):
        raise InvalidBidError("Debe seleccionar un proveedor válido.")
    try:
        return get_supplier(session, supplier_id)
    except SupplierNotFoundError:
        raise InvalidBidError("El proveedor seleccionado no existe.") from None


def create_bid(session: Session, now: datetime, tender_id: int, supplier_id: object,
               amount_crc: object) -> Bid:
    tender = _tender_or_404(session, tender_id)
    if tender.status != TenderStatus.PUBLISHED:
        raise BidNotAllowedError(
            "Solo se aceptan ofertas en licitaciones en estado Publicada."
        )
    if now >= tender.closing_at:  # exactly at closing_at is already rejected
        raise BidNotAllowedError("La licitación ya cerró: no se aceptan más ofertas.")
    supplier = _validate_supplier(session, supplier_id)
    cents = validate_amount(amount_crc, tender.budget_cents)
    existing = session.scalars(
        select(Bid.id).where(Bid.tender_id == tender.id, Bid.supplier_id == supplier.id)
    ).first()
    if existing is not None:
        raise _duplicate_error()
    bid = Bid(tender_id=tender.id, supplier_id=supplier.id, amount_cents=cents,
              created_at=now)
    session.add(bid)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_error() from None
    return bid


def list_bids_by_tender(session: Session, tender_id: int) -> list[Bid]:
    """Bids of a tender in registration order."""
    tender = _tender_or_404(session, tender_id)
    return list(session.scalars(
        select(Bid).where(Bid.tender_id == tender.id).order_by(Bid.created_at, Bid.id)
    ).unique())


def list_bids_by_supplier(session: Session, supplier_id: int) -> list[Bid]:
    """Bids of a supplier in registration order."""
    try:
        supplier = get_supplier(session, supplier_id)
    except SupplierNotFoundError:
        raise BidTargetNotFoundError("Proveedor no encontrado.") from None
    return list(session.scalars(
        select(Bid).where(Bid.supplier_id == supplier.id).order_by(Bid.created_at, Bid.id)
    ).unique())


@dataclass(frozen=True)
class Evaluation:
    """Read-only evaluation result of a tender."""

    tender: Tender
    bid_count: int
    best_bid: Bid | None
    saving_percent: str | None
    classification: str | None
    approver: str | None
    message: str | None


def saving_percent_hundredths(budget_cents: int, best_cents: int) -> int:
    """Saving percent in hundredths of a percent, rounded half-up (integers only)."""
    numerator = (budget_cents - best_cents) * 10_000
    return (2 * numerator + budget_cents) // (2 * budget_cents)


def format_percent(hundredths: int) -> str:
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def classify(budget_cents: int, best_cents: int) -> str:
    """Classify on exact arithmetic (never on the rounded percentage)."""
    diff = budget_cents - best_cents
    if diff <= 0:
        return Classification.NO_SAVING
    if diff * 10 >= budget_cents:  # saving >= 10 %
        return Classification.CONVENIENT
    return Classification.ACCEPTABLE


def evaluate_tender(session: Session, tender_id: int,
                    ranges: tuple[ApprovalRange, ...] = DEFAULT_APPROVAL_RANGES
                    ) -> Evaluation:
    """Best bid = lowest amount; ties go to the earliest (created_at, then id)."""
    tender = _tender_or_404(session, tender_id)
    count = session.scalar(
        select(func.count(Bid.id)).where(Bid.tender_id == tender.id)
    ) or 0
    best = session.scalars(
        select(Bid).where(Bid.tender_id == tender.id)
        .order_by(Bid.amount_cents, Bid.created_at, Bid.id).limit(1)
    ).unique().first()
    if best is None:
        return Evaluation(tender, 0, None, None, None, None, NO_BIDS_MESSAGE)
    percent = format_percent(
        saving_percent_hundredths(tender.budget_cents, best.amount_cents))
    return Evaluation(
        tender=tender, bid_count=count, best_bid=best, saving_percent=percent,
        classification=classify(tender.budget_cents, best.amount_cents),
        approver=approver_for(ranges, best.amount_cents), message=None,
    )
