from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text

from tests.conftest import NOW

CLOSING = NOW + timedelta(hours=48)


def add_tender(client, budget="10000000.00"):
    r = client.post("/api/tenders", json={
        "code": "LIC-2026-001", "title": "Equipo", "budget_crc": budget,
        "closing_at": CLOSING.isoformat()})
    tid = r.json()["id"]
    assert client.post(f"/api/tenders/{tid}/publish").status_code == 200
    return tid


def add_bid(client, tid, amount, name="Tecnología Norte S.A."):
    sid = client.post("/api/suppliers", json={"name": name}).json()["id"]
    r = client.post(f"/api/tenders/{tid}/bids",
                    json={"supplier_id": sid, "amount_crc": amount})
    assert r.status_code == 201


def test_post_rate_ok(tclient):
    r = tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"})
    assert r.status_code == 201
    assert r.json() == {"crc_per_usd": "500.00", "set_at": "2026-11-23T12:00:00"}


def test_get_rate_ok_returns_latest(tclient, clock):
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"})
    clock.advance(hours=1)
    tclient.post("/api/exchange-rate", json={"crc_per_usd": 512.5})
    r = tclient.get("/api/exchange-rate")
    assert r.status_code == 200
    assert r.json() == {"crc_per_usd": "512.50", "set_at": "2026-11-23T13:00:00"}


def test_get_rate_unset_is_404_with_clear_message(tclient):
    r = tclient.get("/api/exchange-rate")
    assert r.status_code == 404
    assert r.json() == {"detail": "No hay un tipo de cambio configurado."}


@pytest.mark.parametrize("bad", ["0", "0.00", "-500", "abc", "1e3", "", "500.001",
                                 "99999999999999999999", 0, -1, True, None, [], {}])
def test_post_rate_invalid_is_422_without_internals(tclient, bad):
    r = tclient.post("/api/exchange-rate", json={"crc_per_usd": bad})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert isinstance(detail, str) and "Traceback" not in detail
    assert "pydantic" not in detail.lower()
    assert tclient.get("/api/exchange-rate").status_code == 404  # nothing stored


def test_post_rate_missing_field_or_bad_json(tclient):
    assert tclient.post("/api/exchange-rate", json={}).status_code == 422
    r = tclient.post("/api/exchange-rate", content="not json",
                     headers={"content-type": "application/json"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_boundary_minimum_accepted(tclient):
    assert tclient.post("/api/exchange-rate",
                        json={"crc_per_usd": "0.01"}).status_code == 201


def test_usd_evaluation_reference_case(tclient):
    tid = add_tender(tclient)
    add_bid(tclient, tid, "9000000.00")
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"})
    r = tclient.get(f"/api/tenders/{tid}/evaluation/usd")
    assert r.status_code == 200
    body = r.json()
    assert body["best_bid"]["amount_usd"] == "18000.00"
    assert body["best_bid"]["amount_crc"] == "9000000.00"
    assert body["budget_usd"] == "20000.00"
    assert body["crc_per_usd"] == "500.00"
    assert body["rate_set_at"] == "2026-11-23T12:00:00"
    assert body["currency"] == "USD"


def test_usd_evaluation_without_rate_is_409(tclient):
    tid = add_tender(tclient)
    r = tclient.get(f"/api/tenders/{tid}/evaluation/usd")
    assert r.status_code == 409
    assert r.json()["detail"] == "No hay un tipo de cambio configurado."


def test_usd_evaluation_unknown_tender_404_and_bad_id_422(tclient):
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"})
    assert tclient.get("/api/tenders/999/evaluation/usd").status_code == 404
    r = tclient.get("/api/tenders/abc/evaluation/usd")
    assert r.status_code == 422 and "entero" in r.json()["detail"]


def test_usd_evaluation_no_bids(tclient):
    tid = add_tender(tclient)
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"})
    body = tclient.get(f"/api/tenders/{tid}/evaluation/usd").json()
    assert body["best_bid"] is None and body["message"] == "Sin ofertas válidas"


def test_usd_view_and_rate_change_do_not_alter_stored_crc(tclient, db_url):
    tid = add_tender(tclient)
    add_bid(tclient, tid, "9000000.00")
    eng = create_engine(db_url)

    def snapshot():
        with eng.connect() as c:
            return (c.execute(text("select id, budget_cents from tenders")).all(),
                    c.execute(text("select id, amount_cents from bids")).all())

    before = snapshot()
    assert before[1][0][1] == 900_000_000
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"})
    tclient.get(f"/api/tenders/{tid}/evaluation/usd")
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "777.77"})
    tclient.get(f"/api/tenders/{tid}/evaluation/usd")
    assert snapshot() == before
    eng.dispose()
    best = tclient.get(f"/api/tenders/{tid}/evaluation").json()["best_bid"]
    assert best["amount_crc"] == "9000000.00"
