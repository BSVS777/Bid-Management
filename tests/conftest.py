import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database
from app.main import create_app


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def client(db_url):
    with TestClient(create_app(db_url), follow_redirects=False) as c:
        yield c


@pytest.fixture
def session(db_url):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    database.init_db(engine)
    s = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield s
    s.close()
    engine.dispose()
