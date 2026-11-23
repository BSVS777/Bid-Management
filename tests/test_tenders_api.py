import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import NOW

CLOSING = (NOW + timedelta(hours=48)).isoformat()
REF = {"code": "LIC-2026-001", "title": "Adquisición de equipo",
       "budget_crc": "10000000.00", "closing_at": CLOSING}


def body(**overrides):
    return {**REF, **overrides}


def create(client, **overrides):
    return client.post("/api/tenders", json=body(**overrides))


# --- create --------------------------------------------------------------------

def test_create_reference_tender(tclient):
    r = create(tclient)
    assert r.status_code == 201
    assert r.json() == {
        "id": 1, "code": "LIC-2026-001", "title": "Adquisición de equipo",
        "budget_crc": "10000000.00", "closing_at": "2026-11-25T12:00:00",
        "status": "Borrador",
    }


@pytest.mark.parametrize("budget, expected", [(5, "5.00"), (12.5, "12.50"), ("0.01", "0.01")])
def test_budget_accepts_numbers_and_returns_two_decimals(tclient, budget, expected):
    assert create(tclient, budget_crc=budget).json()["budget_crc"] == expected


def test_closing_accepts_space_separator(tclient):
    r = create(tclient, closing_at="2026-12-31 10:00:00")
    assert r.status_code == 201
    assert r.json()["closing_at"] == "2026-12-31T10:00:00"


def test_closing_with_offset_is_converted(tclient):
    r = create(tclient, closing_at="2026-12-31T10:00:00+00:00")
    assert r.status_code == 201
    assert "+" not in r.json()["closing_at"] and "Z" not in r.json()["closing_at"]


@pytest.mark.parametrize("code", ["lic-2026-001", "  LIC-2026-001 ", "Lic-2026-001"])
def test_duplicate_code_409(tclient, code):
    create(tclient)
    r = create(tclient, code=code)
    assert r.status_code == 409
    assert "detail" in r.json()
    assert len(tclient.get("/api/tenders").json()) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"code": ""}, {"code": "   "}, {"code": "a b"}, {"code": "x" * 31},
        {"title": ""}, {"title": "   "}, {"title": "x" * 201},
        {"title": "<script>alert(1)</script>"},
        {"budget_crc": "0"}, {"budget_crc": "-1"}, {"budget_crc": "0.001"},
        {"budget_crc": "abc"}, {"budget_crc": "1e3"}, {"budget_crc": "NaN"},
        {"budget_crc": 0}, {"budget_crc": "10000000000000"},
        {"closing_at": "nope"}, {"closing_at": ""}, {"closing_at": "2026-12-31"},
        {"closing_at": "2026-11-23T11:59:59"},  # past
        {"closing_at": "2026-11-23T12:00:00"},  # exactly now
    ],
)
def test_invalid_fields_422(tclient, overrides):
    r = create(tclient, **overrides)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)
    assert "Traceback" not in r.text
    assert tclient.get("/api/tenders").json() == []


def test_script_title_not_echoed(tclient):
    r = create(tclient, title="<script>alert(1)</script>")
    assert "<script>" not in r.text


def test_closing_one_second_in_future_ok(tclient):
    assert create(tclient, closing_at="2026-11-23T12:00:01").status_code == 201


@pytest.mark.parametrize("field", ["code", "title", "budget_crc", "closing_at"])
def test_missing_field_422(tclient, field):
    payload = body()
    del payload[field]
    r = tclient.post("/api/tenders", json=payload)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


@pytest.mark.parametrize(
    "overrides",
    [{"code": 5}, {"title": None}, {"budget_crc": True}, {"budget_crc": None},
     {"budget_crc": [1]}, {"closing_at": 20261231}, {"closing_at": None}],
)
def test_wrong_types_422(tclient, overrides):
    assert create(tclient, **overrides).status_code == 422


def test_non_json_body_422(tclient):
    r = tclient.post("/api/tenders", content="not json",
                     headers={"content-type": "application/json"})
    assert r.status_code == 422


# --- read ----------------------------------------------------------------------

def test_list_get_and_filter(tclient):
    create(tclient, code="A")
    create(tclient, code="B")
    tclient.post("/api/tenders/2/publish")
    assert [t["code"] for t in tclient.get("/api/tenders").json()] == ["A", "B"]
    assert [t["code"] for t in tclient.get("/api/tenders?status=Borrador").json()] == ["A"]
    assert [t["code"] for t in tclient.get("/api/tenders?status=Publicada").json()] == ["B"]
    assert tclient.get("/api/tenders?status=Cerrada").json() == []
    assert tclient.get("/api/tenders/2").json()["status"] == "Publicada"


def test_invalid_status_filter_422(tclient):
    assert tclient.get("/api/tenders?status=Otra").status_code == 422


def test_not_found_404(tclient):
    assert tclient.get("/api/tenders/99").status_code == 404
    assert tclient.put("/api/tenders/99", json=body()).status_code == 404
    assert tclient.post("/api/tenders/99/publish").status_code == 404
    assert tclient.post("/api/tenders/99/close").status_code == 404
    assert tclient.get("/api/tenders/abc").status_code == 422


# --- update --------------------------------------------------------------------

def test_edit_draft(tclient):
    create(tclient)
    r = tclient.put("/api/tenders/1", json=body(
        code="LIC-2026-002", title="Nuevo", budget_crc="7.5",
        closing_at="2026-12-31T10:00:00"))
    assert r.status_code == 200
    assert r.json() == {
        "id": 1, "code": "LIC-2026-002", "title": "Nuevo", "budget_crc": "7.50",
        "closing_at": "2026-12-31T10:00:00", "status": "Borrador",
    }
    assert tclient.get("/api/tenders/1").json()["code"] == "LIC-2026-002"


def test_edit_own_code_case_variant_ok(tclient):
    create(tclient)
    assert tclient.put("/api/tenders/1", json=body(code="lic-2026-001")).status_code == 200


def test_edit_duplicate_code_409(tclient):
    create(tclient, code="A")
    create(tclient, code="B")
    assert tclient.put("/api/tenders/2", json=body(code=" a ")).status_code == 409


def test_edit_invalid_422(tclient):
    create(tclient)
    assert tclient.put("/api/tenders/1", json=body(budget_crc="0")).status_code == 422
    assert tclient.put("/api/tenders/1", json=body(title="<b>")).status_code == 422


def test_edit_blocked_after_publish_409(tclient):
    create(tclient)
    tclient.post("/api/tenders/1/publish")
    r = tclient.put("/api/tenders/1", json=body(title="Otro"))
    assert r.status_code == 409
    assert "Borrador" in r.json()["detail"]
    assert tclient.get("/api/tenders/1").json()["title"] == REF["title"]


def test_edit_blocked_after_close_409(tclient):
    create(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/close")
    assert tclient.put("/api/tenders/1", json=body(title="Otro")).status_code == 409


# --- state machine ---------------------------------------------------------------

def test_full_lifecycle(tclient):
    create(tclient)
    r = tclient.post("/api/tenders/1/publish")
    assert (r.status_code, r.json()["status"]) == (200, "Publicada")
    r = tclient.post("/api/tenders/1/close")
    assert (r.status_code, r.json()["status"]) == (200, "Cerrada")


def test_draft_to_closed_directly_409(tclient):
    create(tclient)
    r = tclient.post("/api/tenders/1/close")
    assert r.status_code == 409
    assert tclient.get("/api/tenders/1").json()["status"] == "Borrador"


def test_publish_twice_409(tclient):
    create(tclient)
    tclient.post("/api/tenders/1/publish")
    assert tclient.post("/api/tenders/1/publish").status_code == 409


def test_close_twice_409(tclient):
    create(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/close")
    assert tclient.post("/api/tenders/1/close").status_code == 409


def test_closed_cannot_be_reopened_409(tclient):
    create(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/close")
    assert tclient.post("/api/tenders/1/publish").status_code == 409
    assert tclient.get("/api/tenders/1").json()["status"] == "Cerrada"


def test_publish_after_closing_date_passed_rejected(tclient, clock):
    create(tclient)
    clock.advance(hours=48, seconds=1)
    r = tclient.post("/api/tenders/1/publish")
    assert r.status_code == 422
    assert "fecha de cierre" in r.json()["detail"]
    assert tclient.get("/api/tenders/1").json()["status"] == "Borrador"


def test_publish_exactly_at_closing_rejected(tclient, clock):
    create(tclient)
    clock.advance(hours=48)
    assert tclient.post("/api/tenders/1/publish").status_code == 422


def test_publish_just_before_closing_ok(tclient, clock):
    create(tclient)
    clock.advance(hours=47, minutes=59)
    assert tclient.post("/api/tenders/1/publish").status_code == 200


def test_published_tender_can_be_closed_after_deadline(tclient, clock):
    create(tclient)
    tclient.post("/api/tenders/1/publish")
    clock.advance(days=10)
    assert tclient.post("/api/tenders/1/close").status_code == 200


# --- app-level behavior ----------------------------------------------------------

def test_persistence_across_app_instances(db_url, clock):
    with TestClient(create_app(db_url, clock=clock)) as c1:
        assert c1.post("/api/tenders", json=REF).status_code == 201
        c1.post("/api/tenders/1/publish")
    with TestClient(create_app(db_url, clock=clock)) as c2:
        data = c2.get("/api/tenders/1").json()
        assert data["code"] == "LIC-2026-001"
        assert data["status"] == "Publicada"
        assert data["budget_crc"] == "10000000.00"
        assert c2.post("/api/tenders", json=REF).status_code == 409


def test_default_clock_is_system_time(db_url):
    from datetime import datetime
    future = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
    past = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    with TestClient(create_app(db_url)) as c:
        assert c.post("/api/tenders", json=body(closing_at=future)).status_code == 201
        assert c.post("/api/tenders", json=body(code="B", closing_at=past)).status_code == 422


def test_supplier_validation_message_unchanged(client):
    r = client.post("/api/suppliers", json={})
    assert r.status_code == 422
    assert "'name'" in r.json()["detail"]


def test_tender_validation_message_mentions_tender_fields(tclient):
    r = tclient.post("/api/tenders", json={})
    assert "'closing_at'" in r.json()["detail"]
    assert re.search(r"Traceback", r.text) is None
