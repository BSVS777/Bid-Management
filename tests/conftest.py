from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database
from app.main import create_app

NOW = datetime(2026, 11, 23, 12, 0, 0)


class FakeClock:
    """Mutable fixed clock injected into create_app and the services."""

    def __init__(self, now: datetime = NOW):
        self.current = now

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **kwargs) -> None:
        self.current += timedelta(**kwargs)


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def client(db_url):
    with TestClient(create_app(db_url), follow_redirects=False) as c:
        yield c


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def tclient(db_url, clock):
    """Client whose app uses the fixed FakeClock."""
    with TestClient(create_app(db_url, clock=clock), follow_redirects=False) as c:
        yield c


@pytest.fixture
def session(db_url):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    database.init_db(engine)
    s = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield s
    s.close()
    engine.dispose()
