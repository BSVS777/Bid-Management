from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.approval import ApprovalRange
from app.database import make_engine
from app.main import create_app
from app.models import Bid
from tests.conftest import NOW, FakeClock

CLOSING = NOW + timedelta(hours=48)
P1_NAME, P2_NAME = "Tecnología Norte S.A.", "Servicios del Valle"


def add_tender(client, code="LIC-2026-001", budget="10000000.00", publish=True):
    r = client.post("/api/tenders", json={
        "code": code, "title": "Equipo", "budget_crc": budget,
        "closing_at": CLOSING.isoformat()})
    assert r.status_code == 201
    tid = r.json()["id"]
    if publish:
        assert client.post(f"/api/tenders/{tid}/publish").status_code == 200
    return tid


def add_supplier(client, name):
    r = client.post("/api/suppliers", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def post_bid(client, tender_id, supplier_id, amount):
    return client.post(f"/api/tenders/{tender_id}/bids",
                       json={"supplier_id": supplier_id, "amount_crc": amount})


@pytest.fixture
def world(tclient):
    return add_tender(tclient), add_supplier(tclient, P1_NAME), add_supplier(tclient, P2_NAME)


def test_create_bid_201_shape(tclient, world):
    t, p1, _ = world
    r = post_bid(tclient, t, p1, "9000000.00")
    assert r.status_code == 201
    assert r.json() == {
        "id": 1, "tender_id": t, "tender_code": "LIC-2026-001", "supplier_id": p1,
        "supplier_name": P1_NAME, "amount_crc": "9000000.00",
        "created_at": "2026-11-23T12:00:00"}


@pytest.mark.parametrize("amount, expected", [(5, "5.00"), (12.5, "12.50"), ("0.01", "0.01"),
                                              ("10000000", "10000000.00")])
def test_amount_formats_and_budget_equal(tclient, world, amount, expected):
    t, p1, _ = world
    r = post_bid(tclient, t, p1, amount)
    assert r.status_code == 201
    assert r.json()["amount_crc"] == expected


@pytest.mark.parametrize("amount", [0, "0", "0.00", -1, "-5.5", "10000000.01", 10000000.01,
                                    "1.234", "abc", "", "1e3", "1,5",
                                    "<script>alert(1)</script>", "<b>x</b>"])
def test_invalid_amounts_422(tclient, world, amount):
    t, p1, _ = world
    r = post_bid(tclient, t, p1, amount)
    assert r.status_code == 422
    assert "detail" in r.json() and "Traceback" not in r.text
    assert "<script>" not in r.text
    assert tclient.get(f"/api/tenders/{t}/bids").json() == []


@pytest.mark.parametrize("payload", [
    {}, {"supplier_id": 1}, {"amount_crc": "5"},
    {"supplier_id": "1", "amount_crc": "5"}, {"supplier_id": True, "amount_crc": "5"},
    {"supplier_id": 1, "amount_crc": True}, {"supplier_id": 1, "amount_crc": None},
    {"supplier_id": 1, "amount_crc": [1]}, {"supplier_id": 1.5, "amount_crc": "5"},
])
def test_malformed_body_safe_422(tclient, world, payload):
    t, _, _ = world
    r = tclient.post(f"/api/tenders/{t}/bids", json=payload)
    assert r.status_code == 422
    assert r.json() == {"detail": "Solicitud inválida: revise los campos "
                        "'supplier_id' (entero) y 'amount_crc'."}


def test_non_json_body_safe_422(tclient, world):
    r = tclient.post(f"/api/tenders/{world[0]}/bids", content="not json",
                     headers={"content-type": "application/json"})
    assert r.status_code == 422 and "Traceback" not in r.text


def test_non_integer_path_ids_safe_422(tclient):
    for path in ("/api/tenders/abc/bids", "/api/tenders/abc/evaluation",
                 "/api/suppliers/abc/bids"):
        r = tclient.get(path)
        assert r.status_code == 422 and "Traceback" not in r.text
        assert "identificador" in r.json()["detail"]


def test_unknown_supplier_422_unknown_tender_404(tclient, world):
    t, p1, _ = world
    assert post_bid(tclient, t, 999, "100").status_code == 422
    assert post_bid(tclient, 999, p1, "100").status_code == 404
    assert tclient.get("/api/tenders/999/bids").status_code == 404
    assert tclient.get("/api/tenders/999/evaluation").status_code == 404
    assert tclient.get("/api/suppliers/999/bids").status_code == 404


# --- time and state -----------------------------------------------------------------

def test_before_at_after_closing(tclient, clock, world):
    t, p1, p2 = world
    clock.current = CLOSING - timedelta(seconds=1)
    assert post_bid(tclient, t, p1, "100").status_code == 201
    clock.current = CLOSING
    r = post_bid(tclient, t, p2, "100")
    assert r.status_code == 409 and "cerró" in r.json()["detail"]
    clock.current = CLOSING + timedelta(seconds=1)
    assert post_bid(tclient, t, p2, "100").status_code == 409
    assert len(tclient.get(f"/api/tenders/{t}/bids").json()) == 1


def test_draft_and_closed_tenders_409(tclient):
    p = add_supplier(tclient, P1_NAME)
    draft = add_tender(tclient, publish=False)
    r = post_bid(tclient, draft, p, "100")
    assert r.status_code == 409 and "Publicada" in r.json()["detail"]
    closed = add_tender(tclient, code="LIC-2")
    tclient.post(f"/api/tenders/{closed}/close")
    assert post_bid(tclient, closed, p, "100").status_code == 409


def test_duplicate_409(tclient, world):
    t, p1, _ = world
    assert post_bid(tclient, t, p1, "100").status_code == 201
    r = post_bid(tclient, t, p1, "50")
    assert r.status_code == 409 and "ya registró" in r.json()["detail"]
    assert len(tclient.get(f"/api/tenders/{t}/bids").json()) == 1


def test_db_unique_constraint_via_direct_insert(tclient, world, db_url):
    t, p1, _ = world
    post_bid(tclient, t, p1, "100")
    engine = make_engine(db_url)
    with sessionmaker(bind=engine)() as s:
        s.add(Bid(tender_id=t, supplier_id=p1, amount_cents=1, created_at=NOW))
        with pytest.raises(IntegrityError):
            s.commit()
    engine.dispose()


# --- listings -------------------------------------------------------------------------

def test_listings_by_tender_and_supplier(tclient, world):
    t, p1, p2 = world
    t2 = add_tender(tclient, code="LIC-2")
    post_bid(tclient, t, p1, "300")
    post_bid(tclient, t, p2, "200")
    post_bid(tclient, t2, p1, "400")
    by_tender = tclient.get(f"/api/tenders/{t}/bids").json()
    assert [b["supplier_name"] for b in by_tender] == [P1_NAME, P2_NAME]
    by_supplier = tclient.get(f"/api/suppliers/{p1}/bids").json()
    assert [b["tender_code"] for b in by_supplier] == ["LIC-2026-001", "LIC-2"]
    assert tclient.get(f"/api/suppliers/{p2}/bids").json()[0]["amount_crc"] == "200.00"


# --- evaluation -------------------------------------------------------------------------

def test_evaluation_reference_scenario(tclient, world):
    t, p1, p2 = world
    post_bid(tclient, t, p1, "9000000.00")
    clock_bid = post_bid(tclient, t, p2, "9500000.00")
    assert clock_bid.status_code == 201
    ev = tclient.get(f"/api/tenders/{t}/evaluation").json()
    assert ev["best_bid"]["supplier_name"] == P1_NAME
    assert ev["best_bid"]["amount_crc"] == "9000000.00"
    assert ev["saving_percent"] == "10.00"
    assert ev["classification"] == "Conveniente"
    assert ev["approver"] == "Gerencia"
    assert ev["bid_count"] == 2 and ev["budget_crc"] == "10000000.00"
    assert ev["tender_code"] == "LIC-2026-001" and ev["message"] is None


def test_evaluation_without_bids(tclient, world):
    ev = tclient.get(f"/api/tenders/{world[0]}/evaluation").json()
    assert ev["best_bid"] is None and ev["approver"] is None
    assert ev["saving_percent"] is None and ev["classification"] is None
    assert ev["message"] == "Sin ofertas válidas" and ev["bid_count"] == 0


def test_evaluation_tie_first_registered_wins(tclient, clock, world):
    t, p1, p2 = world
    post_bid(tclient, t, p2, "9000000")
    clock.advance(minutes=5)
    post_bid(tclient, t, p1, "9000000")
    ev = tclient.get(f"/api/tenders/{t}/evaluation").json()
    assert ev["best_bid"]["supplier_id"] == p2


@pytest.mark.parametrize("best, percent, cls", [
    ("900000", "10.00", "Conveniente"), ("950000", "5.00", "Aceptable"),
    ("1000000", "0.00", "Válida sin ahorro"), ("900005", "10.00", "Aceptable"),
])
def test_evaluation_classifications(tclient, best, percent, cls):
    t = add_tender(tclient, budget="1000000.00")
    p = add_supplier(tclient, P1_NAME)
    post_bid(tclient, t, p, best)
    ev = tclient.get(f"/api/tenders/{t}/evaluation").json()
    assert (ev["saving_percent"], ev["classification"]) == (percent, cls)


@pytest.mark.parametrize("best, approver", [
    ("0.01", "Encargado de Área"), ("999999.99", "Encargado de Área"),
    ("1000000.00", "Gerencia"), ("9999999.99", "Gerencia"),
    ("10000000.00", "Junta Directiva"),
])
def test_evaluation_approver_boundaries(tclient, world, best, approver):
    t, p1, _ = world
    post_bid(tclient, t, p1, best)
    assert tclient.get(f"/api/tenders/{t}/evaluation").json()["approver"] == approver


def test_evaluation_uses_configured_ranges(db_url, clock):
    ranges = [ApprovalRange(1, 100, "Jefe"), ApprovalRange(100, None, "Director")]
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock, approval_ranges=ranges)) as c:
        t = add_tender(c)
        p = add_supplier(c, P1_NAME)
        post_bid(c, t, p, "5")
        assert c.get(f"/api/tenders/{t}/evaluation").json()["approver"] == "Director"


def test_evaluation_is_read_only(tclient, world):
    t, p1, p2 = world
    post_bid(tclient, t, p1, "9000000")
    post_bid(tclient, t, p2, "9500000")
    before = tclient.get(f"/api/tenders/{t}/bids").json()
    tender_before = tclient.get(f"/api/tenders/{t}").json()
    for _ in range(3):
        tclient.get(f"/api/tenders/{t}/evaluation")
    assert tclient.get(f"/api/tenders/{t}/bids").json() == before
    assert tclient.get(f"/api/tenders/{t}").json() == tender_before


def test_evaluation_available_on_closed_tender(tclient, world):
    t, p1, _ = world
    post_bid(tclient, t, p1, "9000000")
    tclient.post(f"/api/tenders/{t}/close")
    assert tclient.get(f"/api/tenders/{t}/evaluation").json()["classification"] == "Conveniente"


# --- persistence ---------------------------------------------------------------------------

def test_persistence_across_app_instances(db_url):
    clock = FakeClock()
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock)) as first:
        t = add_tender(first)
        p1 = add_supplier(first, P1_NAME)
        p2 = add_supplier(first, P2_NAME)
        post_bid(first, t, p1, "9000000.00")
        post_bid(first, t, p2, "9500000.00")
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock)) as second:
        bids = second.get(f"/api/tenders/{t}/bids").json()
        assert [b["amount_crc"] for b in bids] == ["9000000.00", "9500000.00"]
        ev = second.get(f"/api/tenders/{t}/evaluation").json()
        assert ev["approver"] == "Gerencia" and ev["classification"] == "Conveniente"
        assert post_bid(second, t, p1, "1").status_code == 409


def test_error_responses_never_leak_tracebacks(tclient, world):
    t, p1, _ = world
    responses = [
        post_bid(tclient, t, p1, "x"), post_bid(tclient, 999, p1, "1"),
        post_bid(tclient, t, 999, "1"), tclient.get("/api/tenders/999/evaluation"),
    ]
    for r in responses:
        assert "Traceback" not in r.text and "detail" in r.json()
