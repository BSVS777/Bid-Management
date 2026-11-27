"""Exchange rate rules (REQ-010), shared by the API and the web UI.

Only CRC is ever persisted for amounts. The rate (CRC per 1 USD) is stored as
integer hundredths and USD values are computed at display time, rounded half-up
to 2 decimals using integer arithmetic only.
"""
import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExchangeRate

MAX_RATE_HUNDREDTHS = 10_000_000  # 100_000.00 CRC per USD
MAX_TEXT_LENGTH = 20
_PLAIN_RATE = re.compile(r"\d+(\.\d+)?", re.ASCII)

INVALID_RATE_MESSAGE = (
    "El tipo de cambio debe ser un número positivo con punto decimal, "
    "hasta 2 decimales y no mayor a 100000.00."
)
NO_RATE_MESSAGE = "No hay un tipo de cambio configurado."


class ExchangeRateError(Exception):
    """Base class for exchange rate domain errors."""


class InvalidRateError(ExchangeRateError):
    """The rate is not a valid positive amount (HTTP 422)."""


class RateNotFoundError(ExchangeRateError):
    """No rate exists with the requested id (HTTP 404)."""


class RateNotConfiguredError(ExchangeRateError):
    """No exchange rate has been configured yet."""


def parse_rate_hundredths(value: object) -> int:
    """Parse a CRC-per-USD rate into integer hundredths (500.00 -> 50000)."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise InvalidRateError(INVALID_RATE_MESSAGE)
    try:
        text = (repr(value) if isinstance(value, float) else str(value)).strip()
    except ValueError:  # absurdly large int
        raise InvalidRateError(INVALID_RATE_MESSAGE) from None
    if len(text) > MAX_TEXT_LENGTH or not _PLAIN_RATE.fullmatch(text):
        raise InvalidRateError(INVALID_RATE_MESSAGE)
    amount = Decimal(text)
    if amount.as_tuple().exponent < -2:
        raise InvalidRateError(INVALID_RATE_MESSAGE)
    hundredths = int(amount.scaleb(2))
    if not 0 < hundredths <= MAX_RATE_HUNDREDTHS:
        raise InvalidRateError(INVALID_RATE_MESSAGE)
    return hundredths


def set_rate(session: Session, now: datetime, value: object) -> ExchangeRate:
    """Validate and append a new rate; history is kept, the newest row is current."""
    row = ExchangeRate(rate_hundredths=parse_rate_hundredths(value), created_at=now)
    session.add(row)
    session.commit()
    return row


def get_current_rate(session: Session) -> ExchangeRate | None:
    """The newest rate, or None when none was configured."""
    return session.scalars(
        select(ExchangeRate).order_by(ExchangeRate.id.desc()).limit(1)
    ).first()


def require_rate(session: Session) -> ExchangeRate:
    rate = get_current_rate(session)
    if rate is None:
        raise RateNotConfiguredError(NO_RATE_MESSAGE)
    return rate


def format_rate(rate_hundredths: int) -> str:
    return f"{rate_hundredths // 100}.{rate_hundredths % 100:02d}"


def crc_to_usd(crc_cents: int, rate_hundredths: int) -> int:
    """CRC cents -> USD cents (= CRC cents * 100 / rate_hundredths), half-up."""
    if rate_hundredths <= 0:
        raise InvalidRateError(INVALID_RATE_MESSAGE)
    numerator = abs(crc_cents) * 100
    result = (2 * numerator + rate_hundredths) // (2 * rate_hundredths)
    return -result if crc_cents < 0 else result


def usd_to_crc(usd_cents: int, rate_hundredths: int) -> int:
    """USD cents -> CRC cents (= USD cents * rate_hundredths / 100), half-up."""
    if rate_hundredths <= 0:
        raise InvalidRateError(INVALID_RATE_MESSAGE)
    numerator = abs(usd_cents) * rate_hundredths
    result = (2 * numerator + 100) // 200
    return -result if usd_cents < 0 else result


def list_rates(session: Session) -> list[ExchangeRate]:
    """Full history, oldest first."""
    return list(session.scalars(select(ExchangeRate).order_by(ExchangeRate.id)))


def get_rate(session: Session, rate_id: int) -> ExchangeRate:
    row = session.get(ExchangeRate, rate_id)
    if row is None:
        raise RateNotFoundError("Tipo de cambio no encontrado.")
    return row


def delete_rate(session: Session, rate_id: int) -> None:
    """Remove one history entry; the newest remaining row becomes current."""
    session.delete(get_rate(session, rate_id))
    session.commit()
