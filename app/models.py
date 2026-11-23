"""ORM models."""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

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
