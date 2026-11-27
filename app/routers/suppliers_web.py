"""Server-rendered web UI for suppliers."""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.suppliers import to_http_error
from app.services import suppliers as service

router = APIRouter(tags=["suppliers-web"], include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def _list_page(request: Request, db: Session, name: str = "",
               error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "suppliers.html",
        {"suppliers": service.list_suppliers(db), "name": name, "error": error},
        status_code=status_code,
    )


def _edit_page(request: Request, supplier_id: int, name: str,
               error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "supplier_form.html",
        {"supplier_id": supplier_id, "name": name, "error": error},
        status_code=status_code,
    )


@router.get("/suppliers", response_class=HTMLResponse)
def list_page(request: Request, db: Session = Depends(get_db)):
    return _list_page(request, db)


@router.post("/suppliers", response_class=HTMLResponse)
def create(request: Request, name: str = Form(""), db: Session = Depends(get_db)):
    try:
        service.create_supplier(db, name)
    except service.SupplierError as exc:
        http_exc = to_http_error(exc)
        return _list_page(request, db, name, http_exc.detail, http_exc.status_code)
    return RedirectResponse("/suppliers", status_code=303)


@router.get("/suppliers/{supplier_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, supplier_id: int, db: Session = Depends(get_db)):
    try:
        supplier = service.get_supplier(db, supplier_id)
    except service.SupplierError as exc:
        raise to_http_error(exc) from None
    return _edit_page(request, supplier.id, supplier.name)


@router.post("/suppliers/{supplier_id}/edit", response_class=HTMLResponse)
def edit(request: Request, supplier_id: int, name: str = Form(""),
         db: Session = Depends(get_db)):
    try:
        service.update_supplier(db, supplier_id, name)
    except service.SupplierError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        return _edit_page(request, supplier_id, name, http_exc.detail,
                          http_exc.status_code)
    return RedirectResponse("/suppliers", status_code=303)


@router.post("/suppliers/{supplier_id}/delete", response_class=HTMLResponse)
def delete(request: Request, supplier_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_supplier(db, supplier_id)
    except service.SupplierError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        return _list_page(request, db, error=http_exc.detail,
                          status_code=http_exc.status_code)
    return RedirectResponse("/suppliers", status_code=303)
