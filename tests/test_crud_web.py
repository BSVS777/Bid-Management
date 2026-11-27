"""Web delete forms and the users page."""
from tests.conftest import PASSWORD, USERNAME

CLOSING = "2026-12-01T10:00:00"


def seed(c):
    c.post("/api/suppliers", json={"name": "Proveedor Uno"})
    c.post("/api/tenders", json={"code": "LIC-1", "title": "Compra", "budget_crc": "1000",
                                 "closing_at": CLOSING})


def test_lists_render_delete_buttons_with_confirm(tclient):
    seed(tclient)
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500"})
    for path, action in (("/suppliers", "/suppliers/1/delete"), ("/tenders", "/tenders/1/delete"),
                         ("/exchange-rate", "/exchange-rate/1/delete")):
        html = tclient.get(path).text
        assert f'action="{action}"' in html and "confirm(" in html


def test_supplier_delete_web(tclient):
    seed(tclient)
    r = tclient.post("/suppliers/1/delete")
    assert r.status_code == 303 and r.headers["location"] == "/suppliers"
    assert "Proveedor Uno" not in tclient.get("/suppliers").text
    assert tclient.post("/suppliers/1/delete").status_code == 404


def test_supplier_delete_blocked_shows_error(tclient):
    seed(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/bids", json={"supplier_id": 1, "amount_crc": "10"})
    r = tclient.post("/suppliers/1/delete")
    assert r.status_code == 409 and "tiene ofertas" in r.text and "Proveedor Uno" in r.text


def test_tender_delete_web_and_blocked(tclient):
    seed(tclient)
    tclient.post("/api/tenders/1/publish")
    r = tclient.post("/tenders/1/delete")
    assert r.status_code == 409 and "Borrador" in r.text
    tclient.post("/api/tenders", json={"code": "LIC-2", "title": "Otra", "budget_crc": "5",
                                       "closing_at": CLOSING})
    r = tclient.post("/tenders/2/delete")
    assert r.status_code == 303
    assert "LIC-2" not in tclient.get("/tenders").text
    assert tclient.post("/tenders/9/delete").status_code == 404


def test_bid_delete_web(tclient):
    seed(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/bids", json={"supplier_id": 1, "amount_crc": "10"})
    assert 'action="/tenders/1/bids/1/delete"' in tclient.get("/tenders/1/bids").text
    r = tclient.post("/tenders/1/bids/1/delete")
    assert r.status_code == 303 and r.headers["location"] == "/tenders/1/bids"
    assert tclient.get("/api/tenders/1/bids").json() == []


def test_bid_delete_web_wrong_tender_or_unknown_404(tclient):
    seed(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/bids", json={"supplier_id": 1, "amount_crc": "10"})
    assert tclient.post("/tenders/2/bids/1/delete").status_code == 404
    assert tclient.post("/tenders/1/bids/9/delete").status_code == 404
    assert len(tclient.get("/api/tenders/1/bids").json()) == 1


def test_bid_delete_web_closed_tender_409(tclient):
    seed(tclient)
    tclient.post("/api/tenders/1/publish")
    tclient.post("/api/tenders/1/bids", json={"supplier_id": 1, "amount_crc": "10"})
    tclient.post("/api/tenders/1/close")
    r = tclient.post("/tenders/1/bids/1/delete")
    assert r.status_code == 409 and "Publicada" in r.text


def test_exchange_rate_history_and_delete_web(tclient):
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500"})
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "512.25"})
    assert "512.25" in tclient.get("/exchange-rate").text
    r = tclient.post("/exchange-rate/2/delete")
    assert r.status_code == 303
    assert "512.25" not in tclient.get("/exchange-rate").text
    assert tclient.post("/exchange-rate/2/delete").status_code == 404


def test_users_page_create_and_delete(authed):
    assert authed.post("/login", data={"username": USERNAME, "password": PASSWORD}).status_code == 303
    page = authed.get("/users")
    assert page.status_code == 200 and USERNAME in page.text
    assert "scrypt" not in page.text and PASSWORD not in page.text
    assert authed.post("/users", data={"username": "nuevo", "password": "Clave-Sintetica2"}
                       ).status_code == 303
    assert "nuevo" in authed.get("/users").text
    assert authed.post("/users/2/delete").status_code == 303
    assert "nuevo" not in authed.get("/users").text


def test_users_page_errors(authed):
    authed.post("/login", data={"username": USERNAME, "password": PASSWORD})
    r = authed.post("/users", data={"username": "ok-user", "password": "corta"})
    assert r.status_code == 422 and "contraseña" in r.text
    r = authed.post("/users", data={"username": USERNAME, "password": "Clave-Sintetica2"})
    assert r.status_code == 409 and "Ya existe" in r.text
    r = authed.post("/users/1/delete")  # self
    assert r.status_code == 409 and "propio" in r.text
    assert authed.post("/users/99/delete").status_code == 404
