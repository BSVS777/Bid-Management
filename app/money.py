"""Money helpers for Costa Rican colones (CRC). Amounts are stored as integer cents.

Never uses float arithmetic: all parsing goes through ``decimal.Decimal``.
"""
import re
from decimal import Decimal

MAX_CENTS = 999_999_999_999_999  # 9_999_999_999_999.99 CRC
MAX_TEXT_LENGTH = 40
_PLAIN_NUMBER = re.compile(r"-?\d+(\.\d+)?", re.ASCII)


class InvalidMoneyError(ValueError):
    """The value is not a valid CRC amount."""


def _to_text(value: object) -> str:
    if isinstance(value, bool):
        raise InvalidMoneyError("El monto debe ser un número.")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, Decimal)):
        try:
            return repr(value) if isinstance(value, float) else str(value)
        except ValueError:  # absurdly large int
            raise InvalidMoneyError("El monto es demasiado grande.") from None
    raise InvalidMoneyError("El monto debe ser un número.")


def parse_crc_to_cents(value: object) -> int:
    """Parse a CRC amount (str, int, float or Decimal) into integer cents.

    Accepted: plain decimal notation with at most 2 decimals ("10000000",
    "10000000.00", "-5.5"). Rejected: booleans, NaN/inf, exponent notation
    ("1e3"), thousands separators, comma decimals, more than 2 decimals and
    magnitudes above 9_999_999_999_999.99. The sign is preserved; callers
    decide whether zero or negative amounts are acceptable.
    """
    text = _to_text(value)
    if not text or len(text) > MAX_TEXT_LENGTH or not _PLAIN_NUMBER.fullmatch(text):
        raise InvalidMoneyError(
            "El monto debe ser un número con punto decimal y hasta 2 decimales."
        )
    amount = Decimal(text)
    if amount.as_tuple().exponent < -2:
        raise InvalidMoneyError("El monto admite como máximo 2 decimales.")
    cents = int(amount.scaleb(2))
    if abs(cents) > MAX_CENTS:
        raise InvalidMoneyError("El monto supera el máximo permitido.")
    return cents


def cents_to_decimal(cents: int) -> Decimal:
    """Convert integer cents to a Decimal with exactly 2 decimals."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise TypeError("cents must be an int")
    return Decimal(cents).scaleb(-2)


def format_crc(cents: int) -> str:
    """API representation: plain string with 2 decimals, e.g. "10000000.00"."""
    return str(cents_to_decimal(cents))


def format_crc_display(cents: int) -> str:
    """Human representation for the UI, e.g. "10 000 000,00"."""
    whole, frac = divmod(abs(cents), 100)
    sign = "-" if cents < 0 else ""
    return f"{sign}{whole:,}".replace(",", " ") + f",{frac:02d}"
