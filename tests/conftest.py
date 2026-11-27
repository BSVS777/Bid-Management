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
    with TestClient(create_app(db_url, auth_enabled=False), follow_redirects=False) as c:
        yield c


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def tclient(db_url, clock):
    """Client whose app uses the fixed FakeClock."""
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock), follow_redirects=False) as c:
        yield c


@pytest.fixture
def session(db_url):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    database.init_db(engine)
    s = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield s
    s.close()
    engine.dispose()


USERNAME = "tester"
PASSWORD = "Sintetica-Clave1"  # synthetic test credential, not a real secret


@pytest.fixture
def auth_client(db_url, clock):
    """Client against an app with auth ENABLED and one synthetic user; no credentials."""
    from app.services.users import create_user

    app = create_app(db_url, clock=clock, secret_key="test-secret-key")
    with TestClient(app, follow_redirects=False) as c:
        with app.state.session_factory() as db:
            create_user(db, NOW, USERNAME, PASSWORD)
        yield c


@pytest.fixture
def authed(auth_client):
    """Same client, carrying a Bearer token obtained through the real login endpoint."""
    r = auth_client.post("/api/auth/login",
                         json={"username": USERNAME, "password": PASSWORD})
    auth_client.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return auth_client
