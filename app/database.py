"""Database configuration: engine, session factory and declarative base."""
import os

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DB_URL = "sqlite:///./bid_management.db"


class Base(DeclarativeBase):
    """Declarative base for all models."""


def make_engine(url: str) -> Engine:
    """Build an engine; SQLite needs check_same_thread disabled for FastAPI."""
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


DATABASE_URL = os.environ.get("BID_DB_URL", DEFAULT_DB_URL)
engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(bind: Engine | None = None) -> None:
    """Create all tables (idempotent)."""
    from app import models  # noqa: F401  (register models on Base.metadata)

    Base.metadata.create_all(bind=bind or engine)


def get_db(request: Request):
    """FastAPI dependency yielding a session from the app's own factory."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
