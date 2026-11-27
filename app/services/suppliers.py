"""Supplier business rules, shared by the API and the web UI."""
import unicodedata

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Bid, Supplier

MAX_NAME_LENGTH = 120
ALLOWED_PUNCTUATION = " .,()"


class SupplierError(Exception):
    """Base class for supplier domain errors."""


class InvalidSupplierError(SupplierError):
    """The supplied data violates a validation rule."""


class DuplicateSupplierError(SupplierError):
    """Another supplier already has an equivalent name."""


class SupplierInUseError(SupplierError):
    """The supplier has bids and cannot be deleted (HTTP 409)."""


class SupplierNotFoundError(SupplierError):
    """No supplier exists with the requested id."""


def normalize_name(name: str) -> str:
    """Trim, collapse whitespace runs into one space and compose accents (NFC)."""
    return " ".join(unicodedata.normalize("NFC", name).split())


def name_key(normalized: str) -> str:
    """Comparison key used for case-insensitive duplicate detection."""
    return normalized.casefold()


def _is_allowed_char(ch: str) -> bool:
    return ch.isalpha() or ch.isdecimal() or ch in ALLOWED_PUNCTUATION


def validate_name(name: object) -> str:
    """Return the normalized name or raise InvalidSupplierError."""
    if not isinstance(name, str):
        raise InvalidSupplierError("El nombre del proveedor debe ser texto.")
    normalized = normalize_name(name)
    if not normalized:
        raise InvalidSupplierError("El nombre del proveedor es obligatorio.")
    if len(normalized) > MAX_NAME_LENGTH:
        raise InvalidSupplierError(
            f"El nombre no puede superar {MAX_NAME_LENGTH} caracteres."
        )
    if not all(_is_allowed_char(ch) for ch in normalized):
        raise InvalidSupplierError(
            "El nombre solo puede contener letras, números, espacios, "
            "punto, coma y paréntesis."
        )
    return normalized


def _duplicate_error() -> DuplicateSupplierError:
    return DuplicateSupplierError("Ya existe un proveedor con ese nombre.")


def _find_by_key(session: Session, key: str) -> Supplier | None:
    return session.scalars(select(Supplier).where(Supplier.name_key == key)).first()


def create_supplier(session: Session, name: object) -> Supplier:
    normalized = validate_name(name)
    key = name_key(normalized)
    if _find_by_key(session, key) is not None:
        raise _duplicate_error()
    supplier = Supplier(name=normalized, name_key=key)
    session.add(supplier)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_error() from None
    return supplier


def get_supplier(session: Session, supplier_id: int) -> Supplier:
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:
        raise SupplierNotFoundError("Proveedor no encontrado.")
    return supplier


def update_supplier(session: Session, supplier_id: int, name: object) -> Supplier:
    supplier = get_supplier(session, supplier_id)
    normalized = validate_name(name)
    key = name_key(normalized)
    other = _find_by_key(session, key)
    if other is not None and other.id != supplier.id:
        raise _duplicate_error()
    supplier.name = normalized
    supplier.name_key = key
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_error() from None
    return supplier


def list_suppliers(session: Session) -> list[Supplier]:
    return list(session.scalars(select(Supplier).order_by(Supplier.id)))


def delete_supplier(session: Session, supplier_id: int) -> None:
    """Delete a supplier; refused while it has bids (keeps bid history intact)."""
    supplier = get_supplier(session, supplier_id)
    if session.scalars(select(Bid.id).where(Bid.supplier_id == supplier.id)).first():
        raise SupplierInUseError(
            "No se puede eliminar el proveedor porque tiene ofertas registradas.")
    session.delete(supplier)
    session.commit()
