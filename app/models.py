"""ORM models."""
from datetime import datetime, timezone

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Casefolded normalized name; the UNIQUE constraint enforces duplicates.
    name_key: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Tender(Base):
    __tablename__ = "tenders"
    __table_args__ = (
        CheckConstraint("budget_cents > 0", name="ck_tenders_budget_positive"),
        CheckConstraint(
            "status IN ('Borrador', 'Publicada', 'Cerrada')", name="ck_tenders_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    # Casefolded code; the UNIQUE constraint enforces case-insensitive uniqueness.
    code_key: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Budget in CRC as integer cents (never float).
    budget_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    # Naive local datetime.
    closing_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Bid(Base):
    """A supplier's offer on a tender; one per (tender, supplier)."""

    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint("tender_id", "supplier_id", name="uq_bids_tender_supplier"),
        CheckConstraint("amount_cents > 0", name="ck_bids_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenders.id"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False, index=True
    )
    # Offered amount in CRC as integer cents (never float).
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    # Registration instant from the injected clock (naive local datetime).
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Eagerly joined so rows stay usable after the session is closed.
    supplier: Mapped[Supplier] = relationship(lazy="joined")
    tender: Mapped[Tender] = relationship(lazy="joined")


class ExchangeRate(Base):
    """Exchange rate history (CRC per 1 USD); the newest row is the current rate."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint("rate_hundredths > 0", name="ck_exchange_rates_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # CRC per USD in hundredths (500.00 is stored as 50000); never float.
    rate_hundredths: Mapped[int] = mapped_column(Integer, nullable=False)
    # Registration instant from the injected clock (naive local datetime).
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
