"""JSON API for suppliers."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StrictStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Supplier
from app.services import suppliers as service

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


class SupplierIn(BaseModel):
    name: StrictStr


class SupplierOut(BaseModel):
    id: int
    name: str


def to_out(supplier: Supplier) -> SupplierOut:
    return SupplierOut(id=supplier.id, name=supplier.name)


def to_http_error(exc: service.SupplierError) -> HTTPException:
    """Map a domain error to a safe HTTP error."""
    if isinstance(exc, service.InvalidSupplierError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, service.DuplicateSupplierError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=404, detail=str(exc))


@router.post("", status_code=201, response_model=SupplierOut)
def create(payload: SupplierIn, db: Session = Depends(get_db)):
    try:
        return to_out(service.create_supplier(db, payload.name))
    except service.SupplierError as exc:
        raise to_http_error(exc) from None


@router.get("", response_model=list[SupplierOut])
def list_all(db: Session = Depends(get_db)):
    return [to_out(s) for s in service.list_suppliers(db)]


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_one(supplier_id: int, db: Session = Depends(get_db)):
    try:
        return to_out(service.get_supplier(db, supplier_id))
    except service.SupplierError as exc:
        raise to_http_error(exc) from None


@router.put("/{supplier_id}", response_model=SupplierOut)
def update(supplier_id: int, payload: SupplierIn, db: Session = Depends(get_db)):
    try:
        return to_out(service.update_supplier(db, supplier_id, payload.name))
    except service.SupplierError as exc:
        raise to_http_error(exc) from None
