"""QA security cases: input whitelist, HTML escaping, hidden internal errors."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import suppliers as supplier_service
from tests.conftest import NOW

CLOSING = (NOW + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")
SCRIPT = "<script>alert(1)</script>"


@pytest.fixture
def web(db_url, clock):
    with TestClient(create_app(db_url, auth_enabled=False, clock=clock),
                    follow_redirects=True) as c:
        yield c


def test_cp015_supplier_name_character_whitelist(web):
    """CP-015 | REQ-012 | Supplier names with disallowed symbols are rejected via API and web;
    allowed characters accepted | oracle: only letters, digits, spaces, dot, comma and
    parentheses are allowed in a supplier name"""
    bad = ["Proveedor@Norte", "A#B", "X;DROP TABLE", "Y$", "<b>", "Proveedor 😀",
           "A/B", "A'B", 'A"B', "A&B", "A-B", "A_B"]
    for name in bad:
        api = web.post("/api/suppliers", json={"name": name})
        assert api.status_code == 422, name
        assert "letras, números, espacios, punto, coma y paréntesis" in api.json()["detail"]
        ui = web.post("/suppliers", data={"name": name})
        assert ui.status_code == 422, name
        assert 'role="alert"' in ui.text and "El nombre solo puede contener" in ui.text
    assert web.get("/api/suppliers").json() == []
    good = ["Tecnología Norte S.A.", "Servicios del Valle", "Ñandú (Costa Rica), S.A.",
            "José Pérez 123.", "Compañía, Ltda (CR)"]
    for i, name in enumerate(good):
        if i % 2:
            r = web.post("/suppliers", data={"name": name})
            assert r.status_code == 200 and name in r.text
        else:
            r = web.post("/api/suppliers", json={"name": name})
            assert r.status_code == 201 and r.json()["name"] == name
    assert [s["name"] for s in web.get("/api/suppliers").json()] == good


def test_cp016_no_script_execution_and_hidden_internal_errors(db_url, clock, monkeypatch):
    """CP-016 | REQ-012 | HTML/script input is rejected or escaped and internal errors are
    hidden | oracle: no HTML/script execution from user input; internal errors show a generic
    message without stack trace, exception text, paths or credentials"""
    app = create_app(db_url, auth_enabled=False, clock=clock)
    with TestClient(app, follow_redirects=True, raise_server_exceptions=False) as c:
        responses = [
            c.post("/suppliers", data={"name": SCRIPT}),
            c.post("/api/suppliers", json={"name": SCRIPT}),
            c.post("/tenders", data={"code": "LIC-X", "title": SCRIPT,
                                     "budget_crc": "100.00", "closing_at": CLOSING}),
            c.post("/tenders", data={"code": SCRIPT, "title": "t",
                                     "budget_crc": "100.00", "closing_at": CLOSING}),
        ]
        assert c.post("/suppliers", data={"name": "Proveedor Uno"}).status_code == 200
        assert c.post("/tenders", data={"code": "LIC-1", "title": "Titulo",
                                        "budget_crc": "100.00",
                                        "closing_at": CLOSING}).status_code == 200
        c.post("/tenders/1/publish")
        responses += [
            c.post("/tenders/1/bids", data={"supplier_id": "1",
                                            "amount_crc": '"><script>alert(1)</script>'}),
            c.post("/tenders/1/bids", data={"supplier_id": SCRIPT, "amount_crc": "10"}),
            c.get("/suppliers"), c.get("/tenders"), c.get("/tenders/1/bids"),
            c.get("/tenders/1/bids?currency=%3Cscript%3Ealert(1)%3C/script%3E"),
        ]
        for r in responses:
            assert r.status_code < 500
            assert SCRIPT not in r.text and "<script" not in r.text.lower()
        assert responses[0].status_code == 422 and "&lt;script&gt;" in responses[0].text
        assert c.get("/api/suppliers").json()[0]["name"] == "Proveedor Uno"

        def boom(*_a, **_k):
            raise RuntimeError("secret-db-path C:\\x")

        monkeypatch.setattr(supplier_service, "list_suppliers", boom)
        for url in ("/api/suppliers", "/suppliers"):
            r = c.get(url)
            assert r.status_code == 500, url
            assert r.json() == {"detail": "Error interno"}
            low = r.text.lower()
            for leak in ("traceback", "runtimeerror", "secret-db-path", "c:\\\\x",
                         "c:\\x", "file \"", ".py", "sqlalchemy"):
                assert leak not in low, (url, leak)
