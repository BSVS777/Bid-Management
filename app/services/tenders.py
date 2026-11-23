"""Tender business rules (REQ-002 fields, REQ-003 states), shared by API and UI."""
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Tender
from app.money import InvalidMoneyError, parse_crc_to_cents

MAX_CODE_LENGTH = 30
MAX_TITLE_LENGTH = 200
_CODE_PATTERN = re.compile(r"[A-Za-z0-9_-]+", re.ASCII)
_FORBIDDEN_TITLE_CHARS = "<>"


class TenderStatus:
    """Tender states, stored as plain strings."""

    DRAFT = "Borrador"
    PUBLISHED = "Publicada"
    CLOSED = "Cerrada"
    ALL = (DRAFT, PUBLISHED, CLOSED)


class TenderError(Exception):
    """Base class for tender domain errors."""


class InvalidTenderError(TenderError):
    """The supplied data violates a validation rule (HTTP 422)."""


class DuplicateTenderError(TenderError):
    """Another tender already has an equivalent code (HTTP 409)."""


class InvalidTransitionError(TenderError):
    """The requested state change or edit is not allowed (HTTP 409)."""


class TenderNotFoundError(TenderError):
    """No tender exists with the requested id (HTTP 404)."""


def normalize_code(code: object) -> str:
    """Return the trimmed code or raise InvalidTenderError."""
    if not isinstance(code, str):
        raise InvalidTenderError("El código de la licitación debe ser texto.")
    stripped = code.strip()
    if not stripped:
        raise InvalidTenderError("El código de la licitación es obligatorio.")
    if len(stripped) > MAX_CODE_LENGTH:
        raise InvalidTenderError(
            f"El código no puede superar {MAX_CODE_LENGTH} caracteres."
        )
    if not _CODE_PATTERN.fullmatch(stripped):
        raise InvalidTenderError(
            "El código solo puede contener letras, números, guion y guion bajo."
        )
    return stripped


def code_key(code: str) -> str:
    """Comparison key for case-insensitive duplicate detection."""
    return code.casefold()


def validate_title(title: object) -> str:
    """Return the trimmed title or raise InvalidTenderError."""
    if not isinstance(title, str):
        raise InvalidTenderError("El título de la licitación debe ser texto.")
    stripped = title.strip()
    if not stripped:
        raise InvalidTenderError("El título de la licitación es obligatorio.")
    if len(stripped) > MAX_TITLE_LENGTH:
        raise InvalidTenderError(
            f"El título no puede superar {MAX_TITLE_LENGTH} caracteres."
        )
    if any(ch in _FORBIDDEN_TITLE_CHARS or not ch.isprintable() for ch in stripped):
        raise InvalidTenderError(
            "El título contiene caracteres no permitidos (por ejemplo < o >)."
        )
    return stripped


def validate_budget(budget_crc: object) -> int:
    """Return the budget in cents; it must be a valid CRC amount greater than zero."""
    try:
        cents = parse_crc_to_cents(budget_crc)
    except InvalidMoneyError as exc:
        raise InvalidTenderError(f"Presupuesto inválido: {exc}") from None
    if cents <= 0:
        raise InvalidTenderError("El presupuesto debe ser mayor que cero.")
    return cents


def parse_closing_at(value: object) -> datetime:
    """Parse an ISO-8601 date-time into a naive local datetime.

    Accepts "T" or space separators. A value carrying a UTC offset is converted
    to the machine's local time. Date-only values are rejected.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if "T" not in text and " " not in text:
            raise InvalidTenderError(
                "La fecha de cierre debe incluir fecha y hora (ISO-8601)."
            )
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise InvalidTenderError(
                "La fecha de cierre no es válida; use el formato AAAA-MM-DDTHH:MM."
            ) from None
    else:
        raise InvalidTenderError("La fecha de cierre debe ser texto ISO-8601.")
    if parsed.tzinfo is not None:
        try:
            parsed = parsed.astimezone().replace(tzinfo=None)
        except (OverflowError, ValueError, OSError):
            raise InvalidTenderError("La fecha de cierre está fuera de rango.") from None
    return parsed


def _require_future(closing_at: datetime, now: datetime) -> None:
    if closing_at <= now:
        raise InvalidTenderError(
            "La fecha de cierre debe ser posterior al momento actual."
        )


def _duplicate_error() -> DuplicateTenderError:
    return DuplicateTenderError("Ya existe una licitación con ese código.")


def _find_by_key(session: Session, key: str) -> Tender | None:
    return session.scalars(select(Tender).where(Tender.code_key == key)).first()


def create_tender(session: Session, now: datetime, code: object, title: object,
                  budget_crc: object, closing_at: object) -> Tender:
    clean_code = normalize_code(code)
    clean_title = validate_title(title)
    cents = validate_budget(budget_crc)
    closing = parse_closing_at(closing_at)
    _require_future(closing, now)
    key = code_key(clean_code)
    if _find_by_key(session, key) is not None:
        raise _duplicate_error()
    tender = Tender(
        code=clean_code, code_key=key, title=clean_title, budget_cents=cents,
        closing_at=closing, status=TenderStatus.DRAFT, created_at=now,
    )
    session.add(tender)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_error() from None
    return tender


def get_tender(session: Session, tender_id: int) -> Tender:
    tender = session.get(Tender, tender_id)
    if tender is None:
        raise TenderNotFoundError("Licitación no encontrada.")
    return tender


def list_tenders(session: Session, status: str | None = None) -> list[Tender]:
    """List tenders ordered by id; optionally filtered by status."""
    if status is not None and status not in TenderStatus.ALL:
        raise InvalidTenderError("Estado inválido; use Borrador, Publicada o Cerrada.")
    query = select(Tender).order_by(Tender.id)
    if status is not None:
        query = query.where(Tender.status == status)
    return list(session.scalars(query))


def update_tender(session: Session, now: datetime, tender_id: int, code: object,
                  title: object, budget_crc: object, closing_at: object) -> Tender:
    """Edit a tender; only allowed while it is a draft.

    The closing date must be in the future only when it changes, so a draft
    whose date already passed can still have other fields corrected.
    """
    tender = get_tender(session, tender_id)
    if tender.status != TenderStatus.DRAFT:
        raise InvalidTransitionError(
            "Solo se puede editar una licitación en estado Borrador."
        )
    clean_code = normalize_code(code)
    clean_title = validate_title(title)
    cents = validate_budget(budget_crc)
    closing = parse_closing_at(closing_at)
    if closing != tender.closing_at:
        _require_future(closing, now)
    key = code_key(clean_code)
    other = _find_by_key(session, key)
    if other is not None and other.id != tender.id:
        raise _duplicate_error()
    tender.code, tender.code_key = clean_code, key
    tender.title, tender.budget_cents, tender.closing_at = clean_title, cents, closing
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_error() from None
    return tender


def publish_tender(session: Session, now: datetime, tender_id: int) -> Tender:
    """Borrador -> Publicada; the closing date must still be in the future."""
    tender = get_tender(session, tender_id)
    if tender.status != TenderStatus.DRAFT:
        raise InvalidTransitionError(
            "Solo se puede publicar una licitación en estado Borrador."
        )
    _require_future(tender.closing_at, now)
    tender.status = TenderStatus.PUBLISHED
    session.commit()
    return tender


def close_tender(session: Session, tender_id: int) -> Tender:
    """Publicada -> Cerrada."""
    tender = get_tender(session, tender_id)
    if tender.status != TenderStatus.PUBLISHED:
        raise InvalidTransitionError(
            "Solo se puede cerrar una licitación en estado Publicada."
        )
    tender.status = TenderStatus.CLOSED
    session.commit()
    return tender
