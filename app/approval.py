"""Configurable approval ranges (REQ-009).

Ranges are expressed in integer cents and are half-open intervals
``[min_cents, max_cents)``. Half-open intervals leave no gap between
999 999,99 (99_999_999 cents) and 1 000 000,00 (100_000_000 cents): the first
range ends *before* 100_000_000 and the next one starts *at* it. The last range
is unbounded (``max_cents=None``) so every positive amount maps to one approver.
"""
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class ApprovalRange:
    """Approver for amounts in ``[min_cents, max_cents)``; ``None`` = unbounded."""

    min_cents: int
    max_cents: int | None
    approver: str


DEFAULT_APPROVAL_RANGES: tuple[ApprovalRange, ...] = (
    ApprovalRange(1, 100_000_000, "Encargado de área"),     # 0,01 - 999 999,99
    ApprovalRange(100_000_000, 1_000_000_000, "Gerencia"),  # 1 000 000,00 - 9 999 999,99
    ApprovalRange(1_000_000_000, None, "Junta Directiva"),  # >= 10 000 000,00
)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_ranges(ranges) -> tuple[ApprovalRange, ...]:
    """Return the ranges as a tuple or raise ValueError if the config is invalid.

    Rules: non-empty; first range starts at 1 cent; every range has a positive
    ``min`` strictly below its ``max``; ranges sorted by ``min``; consecutive
    ranges are contiguous (no overlap, no gap); only the last range is
    unbounded, and it must be; approver names are non-empty.
    """
    items = tuple(ranges)
    if not items:
        raise ValueError("La configuración de rangos de aprobación no puede estar vacía.")
    for r in items:
        if not isinstance(r, ApprovalRange):
            raise ValueError("Cada rango debe ser un ApprovalRange.")
        if not isinstance(r.approver, str) or not r.approver.strip():
            raise ValueError("Cada rango debe indicar un aprobador.")
        if not _is_int(r.min_cents) or r.min_cents <= 0:
            raise ValueError(
                "El mínimo de cada rango debe ser un entero positivo (centavos)."
            )
        if r.max_cents is not None:
            if not _is_int(r.max_cents) or r.max_cents <= 0:
                raise ValueError(
                    "El máximo de cada rango debe ser un entero positivo (centavos)."
                )
            if r.max_cents <= r.min_cents:
                raise ValueError("El máximo de un rango debe ser mayor que su mínimo.")
    if items[0].min_cents != 1:
        raise ValueError("El primer rango debe comenzar en 1 centavo (sin huecos).")
    for prev, nxt in zip(items, items[1:]):
        if nxt.min_cents < prev.min_cents:
            raise ValueError("Los rangos deben estar ordenados de menor a mayor.")
        if prev.max_cents is None:
            raise ValueError("Solo el último rango puede ser ilimitado.")
        if nxt.min_cents < prev.max_cents:
            raise ValueError("Los rangos de aprobación se traslapan.")
        if nxt.min_cents > prev.max_cents:
            raise ValueError("Los rangos de aprobación tienen un hueco entre ellos.")
    if items[-1].max_cents is not None:
        raise ValueError("El último rango debe ser ilimitado (sin máximo).")
    return items


def approver_for(ranges: tuple[ApprovalRange, ...], amount_cents: int) -> str:
    """Return the approver for an amount (> 0; covered by a validated config)."""
    for r in ranges:
        if amount_cents >= r.min_cents and (
            r.max_cents is None or amount_cents < r.max_cents
        ):
            return r.approver
    raise ValueError("El monto no está cubierto por los rangos de aprobación.")


def get_approval_ranges(request: Request) -> tuple[ApprovalRange, ...]:
    """FastAPI dependency: ranges configured on the app."""
    return request.app.state.approval_ranges
