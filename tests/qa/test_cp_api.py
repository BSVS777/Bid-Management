"""QA API-level cases (HTTP through TestClient)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from app.models import Bid
from tests.conftest import NOW

CLOSING = (NOW + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
P1, P2 = "Tecnología Norte S.A.", "Servicios del Valle"


def _supplier(c, name):
    r = c.post("/api/suppliers", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def _tender(c, code="LIC-2026-001", budget="10000000.00", publish=True):
    r = c.post("/api/tenders", json={"code": code, "title": "Equipo de cómputo",
                                     "budget_crc": budget, "closing_at": CLOSING})
    assert r.status_code == 201
    tid = r.json()["id"]
    if publish:
        assert c.post(f"/api/tenders/{tid}/publish").status_code == 200
    return tid


def _bid(c, tid, sid, amount):
    return c.post(f"/api/tenders/{tid}/bids", json={"supplier_id": sid, "amount_crc": amount})


def test_cp008_duplicate_bid_rejected_by_api_and_db(tclient):
    """CP-008 | REQ-006 | A supplier cannot bid twice on one tender, also enforced by the DB |
    oracle: one bid per supplier per tender; duplicates rejected by API (409) and by the
    database UNIQUE constraint"""
    tid, sid = _tender(tclient), _supplier(tclient, P1)
    assert _bid(tclient, tid, sid, "9000000.00").status_code == 201
    dup = _bid(tclient, tid, sid, "8500000.00")
    assert dup.status_code == 409
    assert len(tclient.get(f"/api/tenders/{tid}/bids").json()) == 1
    with tclient.app.state.session_factory() as db:
        db.add(Bid(tender_id=tid, supplier_id=sid, amount_cents=1, created_at=NOW))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    assert len(tclient.get(f"/api/tenders/{tid}/bids").json()) == 1


def test_cp009_persistence_after_restart_and_api_validation(db_url, clock):
    """CP-009 | REQ-011 | Data survives an application restart and the API rejects what the UI
    rejects with controlled messages | oracle: data persists on restart; API returns success
    and error responses and does not accept invalid input"""
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock)) as c1:
        sid, tid = _supplier(c1, P1), _tender(c1)
        assert _bid(c1, tid, sid, "9000000.00").status_code == 201
    # simulated restart: brand new app instance over the same SQLite file
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock),
                    follow_redirects=False) as c2:
        assert [s["name"] for s in c2.get("/api/suppliers").json()] == [P1]
        assert [t["code"] for t in c2.get("/api/tenders").json()] == ["LIC-2026-001"]
        bids = c2.get(f"/api/tenders/{tid}/bids").json()
        assert [(b["supplier_name"], b["amount_crc"]) for b in bids] == [(P1, "9000000.00")]
        # same invalid inputs the UI rejects -> controlled 4xx, no internals
        empty = c2.post("/api/suppliers", json={"name": "   "})
        over = _bid(c2, tid, _supplier(c2, P2), "10000000.01")
        ui_empty = c2.post("/suppliers", data={"name": "   "})
        ui_over = c2.post(f"/tenders/{tid}/bids",
                          data={"supplier_id": "2", "amount_crc": "10000000.01"})
        assert (empty.status_code, over.status_code) == (422, 422)
        assert (ui_empty.status_code, ui_over.status_code) == (422, 422)
        assert "obligatorio" in empty.json()["detail"]
        assert "no puede superar el presupuesto" in over.json()["detail"]
        for r in (empty, over):
            assert "Traceback" not in r.text and "sqlalchemy" not in r.text.lower()
        assert len(c2.get(f"/api/tenders/{tid}/bids").json()) == 1


def test_cp010_usd_view_does_not_change_stored_crc(tclient):
    """CP-010 | REQ-010 | USD view uses the rate, shows rate and date, and leaves CRC data
    untouched | oracle: USD = CRC / rate (9 000 000,00 / 500,00 = 18 000,00); only CRC is
    persisted; the view toggle does not modify the database"""
    tid, sid = _tender(tclient), _supplier(tclient, P1)
    assert _bid(tclient, tid, sid, "9000000.00").status_code == 201

    def stored():
        with tclient.app.state.session_factory() as db:
            return [b.amount_cents for b in db.query(Bid).all()]

    assert stored() == [900_000_000]
    assert tclient.post("/api/exchange-rate", json={"crc_per_usd": "500.00"}).status_code == 201
    r = tclient.get(f"/api/tenders/{tid}/evaluation/usd")
    assert r.status_code == 200
    body = r.json()
    assert body["best_bid"]["amount_usd"] == "18000.00"
    assert body["best_bid"]["amount_crc"] == "9000000.00"
    assert body["budget_usd"] == "20000.00"
    assert body["crc_per_usd"] == "500.00" and body["rate_set_at"].startswith("2026-11-23")
    page = tclient.get(f"/tenders/{tid}/bids?currency=USD")
    assert page.status_code == 200
    assert "18 000,00" in page.text
    assert "500.00 CRC por USD" in page.text and "2026-11-23" in page.text
    assert stored() == [900_000_000]
    assert tclient.get(f"/api/tenders/{tid}/bids").json()[0]["amount_crc"] == "9000000.00"
    assert "9 000 000,00" in tclient.get(f"/tenders/{tid}/bids").text


def test_cp020_bid_amount_edges_rejected_by_api(tclient):
    """CP-020 | REQ-005 | Negative edge cases for bid amounts through the API | oracle: amount
    must be > 0 and <= budget; budget + 0,01, zero and negative amounts are rejected"""
    tid, sid = _tender(tclient), _supplier(tclient, P1)
    for bad in ["10000000.01", "0", "0.00", "-0.01", "-5", 0, -1, 10000000.01]:
        r = _bid(tclient, tid, sid, bad)
        assert r.status_code == 422, bad
        assert isinstance(r.json()["detail"], str) and "Traceback" not in r.text
    assert tclient.get(f"/api/tenders/{tid}/bids").json() == []
    assert _bid(tclient, tid, sid, "10000000.00").status_code == 201
