"""QA functional flows through the HTML forms (TestClient following redirects)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import NOW

CLOSING_DT = NOW + timedelta(hours=48)
CLOSING = CLOSING_DT.strftime("%Y-%m-%dT%H:%M")
P1, P2, P3 = "Tecnología Norte S.A.", "Servicios del Valle", "Constructora Central"


@pytest.fixture
def web(db_url, clock):
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock),
                    follow_redirects=True) as c:
        yield c


def _supplier(c, name):
    r = c.post("/suppliers", data={"name": name})
    assert r.status_code == 200
    return max(s["id"] for s in c.get("/api/suppliers").json())


def _tender(c, code="LIC-2026-001", publish=True, closing=CLOSING):
    r = c.post("/tenders", data={"code": code, "title": "Equipo de cómputo",
                                 "budget_crc": "10000000.00", "closing_at": closing})
    assert r.status_code == 200
    tid = max(t["id"] for t in c.get("/api/tenders").json())
    if publish:
        assert c.post(f"/tenders/{tid}/publish").status_code == 200
    return tid


def _bid(c, tid, sid, amount):
    return c.post(f"/tenders/{tid}/bids", data={"supplier_id": str(sid), "amount_crc": amount})


def test_cp011_register_supplier_and_reject_duplicate(web):
    """CP-011 | REQ-001 | Register a supplier from the web form; a duplicate with other
    casing/spacing is rejected with a visible error | oracle: duplicates by normalized name
    (trim, collapse spaces, case-insensitive)"""
    r = web.post("/suppliers", data={"name": P1})
    assert r.status_code == 200
    assert f"<td>{P1}</td>" in web.get("/suppliers").text
    r = web.post("/suppliers", data={"name": "  TECNOLOGÍA   norte   s.a.  "})
    assert r.status_code == 409
    assert "Ya existe un proveedor con ese nombre." in r.text
    assert 'role="alert"' in r.text
    page = web.get("/suppliers").text
    assert page.count(f"<td>{P1}</td>") == 1 and "TECNOLOGÍA" not in page.replace("<td>", "")
    assert len(web.get("/api/suppliers").json()) == 1


def test_cp012_create_and_publish_tender(web):
    """CP-012 | REQ-002, REQ-003 | Create tender L1 and publish it through the web UI; the list
    shows Publicada | oracle: Borrador -> Publicada is an allowed transition for a valid
    tender"""
    r = web.post("/tenders", data={"code": "LIC-2026-001", "title": "Equipo de cómputo",
                                   "budget_crc": "10000000.00", "closing_at": CLOSING})
    assert r.status_code == 200
    assert "LIC-2026-001" in r.text and "Borrador" in r.text and "10 000 000,00" in r.text
    tid = web.get("/api/tenders").json()[0]["id"]
    r = web.post(f"/tenders/{tid}/publish")
    assert r.status_code == 200
    assert "Publicada" in r.text and "Borrador" not in r.text
    assert web.get("/api/tenders").json()[0]["status"] == "Publicada"


def test_cp013_bids_and_evaluation_page(web):
    """CP-013 | REQ-007 | Register P1 and P2 bids on L1 and read the evaluation | oracle: best =
    lowest offer (P1 9 000 000,00); saving 10 % of 10 000 000,00 -> Conveniente; offer in
    1 000 000,00-9 999 999,99 -> Gerencia"""
    s1, s2 = _supplier(web, P1), _supplier(web, P2)
    tid = _tender(web)
    assert _bid(web, tid, s1, "9000000.00").status_code == 200
    assert _bid(web, tid, s2, "9500000.00").status_code == 200
    page = web.get(f"/tenders/{tid}/bids").text
    assert "9 000 000,00" in page and "9 500 000,00" in page
    assert f"Mejor oferta: <strong>{P1}</strong>" in page
    assert "Ahorro: 10.00%" in page
    assert "Clasificación: Conveniente" in page
    assert "Aprobador: Gerencia" in page
    assert "Sin ofertas válidas" not in page


def test_cp014_closing_instant_boundary(web, clock):
    """CP-014 | REQ-004 | Bids one second before, exactly at and one second after closing |
    oracle: bids accepted only before the closing time; exactly at closing is rejected"""
    s1, s2, s3 = _supplier(web, P1), _supplier(web, P2), _supplier(web, P3)
    tid = _tender(web)
    clock.current = CLOSING_DT - timedelta(seconds=1)
    assert _bid(web, tid, s1, "9000000.00").status_code == 200
    clock.current = CLOSING_DT
    at = _bid(web, tid, s2, "9000000.00")
    assert at.status_code == 409 and "ya cerró" in at.text
    clock.current = CLOSING_DT + timedelta(seconds=1)
    after = _bid(web, tid, s3, "9000000.00")
    assert after.status_code == 409 and "ya cerró" in after.text
    bids = web.get(f"/api/tenders/{tid}/bids").json()
    assert [b["supplier_name"] for b in bids] == [P1]


def test_cp019_bid_on_draft_and_closed_tender_rejected(web):
    """CP-019 | REQ-004 | Bids on Borrador and Cerrada tenders are rejected | oracle: offers
    only on Publicadas"""
    sid = _supplier(web, P1)
    draft = _tender(web, "LIC-DRAFT", publish=False)
    r = _bid(web, draft, sid, "9000000.00")
    assert r.status_code == 409 and "estado Publicada" in r.text
    closed = _tender(web, "LIC-CLOSED")
    assert web.post(f"/tenders/{closed}/close").status_code == 200
    assert web.get(f"/api/tenders/{closed}").json()["status"] == "Cerrada"
    r = _bid(web, closed, sid, "9000000.00")
    assert r.status_code == 409 and "estado Publicada" in r.text
    for tid in (draft, closed):
        assert web.get(f"/api/tenders/{tid}/bids").json() == []
