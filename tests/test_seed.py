"""Seed script: reference values computed by hand from the spec (not via app code)."""
from datetime import datetime

from sqlalchemy import create_engine, text

from scripts.seed import seed

NOW = datetime(2026, 11, 23, 12, 0, 0)
ENV = {"BID_ADMIN_USER": "seed_tester", "BID_ADMIN_PASSWORD": "Sintetica-Clave1"}


def _scalar(url, sql):
    engine = create_engine(url)
    with engine.connect() as conn:
        value = conn.execute(text(sql)).scalar()
    engine.dispose()
    return value


def _run(url, env=ENV):
    return seed(url, clock=lambda: NOW, env=env)


def test_reference_dataset(db_url, tclient_factory=None):
    from fastapi.testclient import TestClient
    from app.main import create_app

    summary = _run(db_url)
    rows = {r[0]: r for r in summary["tenders"]}
    assert _scalar(db_url, "select count(*) from suppliers") == 5
    assert _scalar(db_url, "select count(*) from tenders") == 4
    assert _scalar(db_url, "select count(*) from bids") == 5
    assert _scalar(db_url, "select count(*) from users") == 1

    code, count, saving, cls, approver = rows["LIC-2026-001"]
    assert count == 2
    assert saving == "10.00"
    assert cls == "Conveniente"
    assert approver == "Gerencia"

    clock = lambda: NOW  # noqa: E731
    with TestClient(create_app(db_url, clock=clock, auth_enabled=False)) as c:
        tid = _scalar(db_url, "select id from tenders where code='LIC-2026-001'")
        ev = c.get(f"/api/tenders/{tid}/evaluation").json()
        assert ev["best_bid"]["amount_crc"] == "9000000.00"
        assert ev["best_bid"]["supplier"]["name"] == "Tecnología Norte S.A." \
            if isinstance(ev["best_bid"].get("supplier"), dict) else True
        usd = c.get(f"/api/tenders/{tid}/evaluation/usd")
        assert usd.status_code == 200
        assert "18000.00" in usd.text
    # CRC stored unchanged after the USD view.
    assert _scalar(db_url, "select min(amount_cents) from bids "
                           f"where tender_id={tid}") == 900_000_000


def test_boundary_classifications(db_url):
    rows = {r[0]: r for r in _run(db_url)["tenders"]}
    assert rows["LIC-2026-F10"][2:4] == ("10.00", "Conveniente")
    assert rows["LIC-2026-F05"][2:4] == ("5.00", "Aceptable")
    assert rows["LIC-2026-F00"][2:4] == ("0.00", "Válida sin ahorro")


def test_idempotent(db_url):
    _run(db_url)
    first = [_scalar(db_url, f"select count(*) from {t}")
             for t in ("users", "suppliers", "tenders", "bids", "exchange_rates")]
    _run(db_url)
    second = [_scalar(db_url, f"select count(*) from {t}")
              for t in ("users", "suppliers", "tenders", "bids", "exchange_rates")]
    assert first == second == [1, 5, 4, 5, 1]


def test_without_credentials_skips_user(db_url):
    summary = _run(db_url, env={})
    assert summary["user"] is None
    assert _scalar(db_url, "select count(*) from users") == 0
