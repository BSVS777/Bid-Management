"""Server-rendered page to configure and view the exchange rate."""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.clock import get_now
from app.database import get_db
from app.services import exchange_rate as service

router = APIRouter(tags=["exchange-rate-web"], include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def _page(request: Request, db: Session, value: str = "",
          error: str | None = None, status_code: int = 200):
    rate = service.get_current_rate(db)
    return templates.TemplateResponse(
        request,
        "exchange_rate.html",
        {
            "rate_text": service.format_rate(rate.rate_hundredths) if rate else None,
            "rate_at": rate.created_at.strftime("%Y-%m-%d %H:%M:%S") if rate else None,
            "history": [(r.id, service.format_rate(r.rate_hundredths),
                         r.created_at.strftime("%Y-%m-%d %H:%M:%S"))
                        for r in reversed(service.list_rates(db))],
            "value": value,
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/exchange-rate", response_class=HTMLResponse)
def page(request: Request, db: Session = Depends(get_db)):
    return _page(request, db)


@router.post("/exchange-rate", response_class=HTMLResponse)
def update(request: Request, crc_per_usd: str = Form(""),
           db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    try:
        service.set_rate(db, now, crc_per_usd)
    except service.InvalidRateError as exc:
        return _page(request, db, crc_per_usd, str(exc), 422)
    return RedirectResponse("/exchange-rate", status_code=303)


@router.post("/exchange-rate/{rate_id}/delete", response_class=HTMLResponse)
def delete(rate_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_rate(db, rate_id)
    except service.RateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return RedirectResponse("/exchange-rate", status_code=303)
