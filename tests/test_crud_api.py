"""CRUD gaps: DELETE / PUT / GET-by-id rules for every table (auth disabled here)."""
import pytest

CLOSING = "2026-12-01T10:00:00"


def supplier(c, name="Proveedor Uno"):
    return c.post("/api/suppliers", json={"name": name}).json()["id"]


def tender(c, code="LIC-1", budget="1000.00", publish=False):
    tid = c.post("/api/tenders", json={"code": code, "title": "Compra", "budget_crc": budget,
                                       "closing_at": CLOSING}).json()["id"]
    if publish:
        assert c.post(f"/api/tenders/{tid}/publish").status_code == 200
    return tid


def bid(c, tid, sid, amount="500.00"):
    r = c.post(f"/api/tenders/{tid}/bids", json={"supplier_id": sid, "amount_crc": amount})
    assert r.status_code == 201
    return r.json()["id"]


# ---- suppliers -------------------------------------------------------------
def test_delete_supplier_ok_then_404(tclient):
    sid = supplier(tclient)
    assert tclient.delete(f"/api/suppliers/{sid}").status_code == 204
    assert tclient.get(f"/api/suppliers/{sid}").status_code == 404
    r = tclient.delete(f"/api/suppliers/{sid}")
    assert r.status_code == 404 and r.json() == {"detail": "Proveedor no encontrado."}


def test_delete_supplier_with_bids_409_and_kept(tclient):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid(tclient, tid, sid)
    r = tclient.delete(f"/api/suppliers/{sid}")
    assert r.status_code == 409 and "ofertas" in r.json()["detail"]
    assert tclient.get(f"/api/suppliers/{sid}").status_code == 200


def test_delete_supplier_bad_id_422(tclient):
    r = tclient.delete("/api/suppliers/abc")
    assert r.status_code == 422 and "identificador" in r.json()["detail"]


def test_supplier_name_reusable_after_delete(tclient):
    sid = supplier(tclient, "Reusable")
    tclient.delete(f"/api/suppliers/{sid}")
    assert tclient.post("/api/suppliers", json={"name": "Reusable"}).status_code == 201


# ---- tenders ---------------------------------------------------------------
def test_delete_draft_tender_ok(tclient):
    tid = tender(tclient)
    assert tclient.delete(f"/api/tenders/{tid}").status_code == 204
    assert tclient.get(f"/api/tenders/{tid}").status_code == 404


@pytest.mark.parametrize("close", [False, True])
def test_delete_non_draft_tender_409(tclient, close):
    tid = tender(tclient, publish=True)
    if close:
        tclient.post(f"/api/tenders/{tid}/close")
    r = tclient.delete(f"/api/tenders/{tid}")
    assert r.status_code == 409 and "Borrador" in r.json()["detail"]
    assert tclient.get(f"/api/tenders/{tid}").status_code == 200


def test_delete_tender_404_and_422(tclient):
    assert tclient.delete("/api/tenders/999").status_code == 404
    assert tclient.delete("/api/tenders/x").status_code == 422


# ---- bids ------------------------------------------------------------------
def test_get_bid_and_404(tclient):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid_id = bid(tclient, tid, sid)
    r = tclient.get(f"/api/bids/{bid_id}")
    assert r.status_code == 200 and r.json()["amount_crc"] == "500.00"
    assert tclient.get("/api/bids/999").json() == {"detail": "Oferta no encontrada."}
    assert tclient.get("/api/bids/abc").status_code == 422


def test_update_bid_amount_ok_and_boundaries(tclient):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid_id = bid(tclient, tid, sid)
    r = tclient.put(f"/api/bids/{bid_id}", json={"amount_crc": "1000.00"})  # == budget
    assert r.status_code == 200 and r.json()["amount_crc"] == "1000.00"
    r = tclient.put(f"/api/bids/{bid_id}", json={"amount_crc": "0.01"})
    assert r.status_code == 200 and r.json()["amount_crc"] == "0.01"


@pytest.mark.parametrize("amount", ["1000.01", "0", "-5", "abc", "1e3"])
def test_update_bid_invalid_amount_422_unchanged(tclient, amount):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid_id = bid(tclient, tid, sid)
    assert tclient.put(f"/api/bids/{bid_id}", json={"amount_crc": amount}).status_code == 422
    assert tclient.get(f"/api/bids/{bid_id}").json()["amount_crc"] == "500.00"


def test_update_bid_missing_field_and_unknown_id(tclient):
    assert tclient.put("/api/bids/1", json={}).status_code == 422
    assert tclient.put("/api/bids/999", json={"amount_crc": "1.00"}).status_code == 404


def test_bid_change_blocked_when_tender_closed_state(tclient):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid_id = bid(tclient, tid, sid)
    tclient.post(f"/api/tenders/{tid}/close")
    assert tclient.put(f"/api/bids/{bid_id}", json={"amount_crc": "1.00"}).status_code == 409
    assert tclient.delete(f"/api/bids/{bid_id}").status_code == 409


def test_bid_change_blocked_at_deadline_exact(tclient, clock):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid_id = bid(tclient, tid, sid)
    clock.current = clock.current.replace(year=2026, month=12, day=1, hour=9, minute=59,
                                          second=59)
    assert tclient.put(f"/api/bids/{bid_id}", json={"amount_crc": "2.00"}).status_code == 200
    clock.advance(seconds=1)  # exactly closing_at: already closed
    assert tclient.put(f"/api/bids/{bid_id}", json={"amount_crc": "3.00"}).status_code == 409
    assert tclient.delete(f"/api/bids/{bid_id}").status_code == 409


def test_delete_bid_ok_then_supplier_deletable(tclient):
    sid, tid = supplier(tclient), tender(tclient, publish=True)
    bid_id = bid(tclient, tid, sid)
    assert tclient.delete(f"/api/bids/{bid_id}").status_code == 204
    assert tclient.get(f"/api/tenders/{tid}/bids").json() == []
    assert tclient.delete(f"/api/bids/{bid_id}").status_code == 404
    assert tclient.delete(f"/api/suppliers/{sid}").status_code == 204


# ---- exchange rates --------------------------------------------------------
def test_rate_history_get_and_delete(tclient, clock):
    for v in ("500.00", "510.50"):
        tclient.post("/api/exchange-rate", json={"crc_per_usd": v})
    hist = tclient.get("/api/exchange-rate/history").json()
    assert [(h["id"], h["crc_per_usd"]) for h in hist] == [(1, "500.00"), (2, "510.50")]
    assert tclient.get("/api/exchange-rate/2").json()["crc_per_usd"] == "510.50"
    assert tclient.delete("/api/exchange-rate/2").status_code == 204
    assert tclient.get("/api/exchange-rate").json()["crc_per_usd"] == "500.00"  # falls back
    assert tclient.get("/api/exchange-rate/2").status_code == 404
    assert tclient.delete("/api/exchange-rate/2").status_code == 404


def test_rate_history_empty_and_bad_id(tclient):
    assert tclient.get("/api/exchange-rate/history").json() == []
    assert tclient.get("/api/exchange-rate/abc").status_code == 422
    assert tclient.delete("/api/exchange-rate/abc").status_code == 422


def test_delete_only_rate_makes_current_404(tclient):
    tclient.post("/api/exchange-rate", json={"crc_per_usd": "500"})
    tclient.delete("/api/exchange-rate/1")
    assert tclient.get("/api/exchange-rate").status_code == 404


# ---- users -----------------------------------------------------------------
PWD = "Clave-Sintetica1"


def test_user_crud_cycle(tclient):
    r = tclient.post("/api/users", json={"username": "Ana", "password": PWD})
    assert r.status_code == 201
    uid = r.json()["id"]
    assert set(r.json()) == {"id", "username", "created_at"}
    assert tclient.get(f"/api/users/{uid}").json()["username"] == "Ana"
    assert tclient.put(f"/api/users/{uid}", json={"username": "Ana2"}).json()["username"] == "Ana2"
    assert tclient.put(f"/api/users/{uid}", json={"password": "Otra-Clave-22"}).status_code == 200
    tclient.post("/api/users", json={"username": "Beto", "password": PWD})
    assert tclient.delete(f"/api/users/{uid}").status_code == 204
    assert tclient.get(f"/api/users/{uid}").status_code == 404
    assert [u["username"] for u in tclient.get("/api/users").json()] == ["Beto"]


def test_user_update_password_takes_effect(tclient):
    uid = tclient.post("/api/users", json={"username": "Ana", "password": PWD}).json()["id"]
    tclient.put(f"/api/users/{uid}", json={"password": "Otra-Clave-22"})
    ok = tclient.post("/api/auth/login", json={"username": "Ana", "password": "Otra-Clave-22"})
    old = tclient.post("/api/auth/login", json={"username": "Ana", "password": PWD})
    assert (ok.status_code, old.status_code) == (200, 401)


@pytest.mark.parametrize("body", [
    {"username": "ab", "password": PWD}, {"username": "ok-user", "password": "short"},
    {"username": "con espacio", "password": PWD}, {"username": "ok-user"},
    {"username": 1, "password": PWD}, {},
])
def test_user_create_invalid_422(tclient, body):
    assert tclient.post("/api/users", json=body).status_code == 422


def test_user_duplicate_409_casefold_and_update_collision(tclient):
    tclient.post("/api/users", json={"username": "Ana", "password": PWD})
    assert tclient.post("/api/users", json={"username": "ANA", "password": PWD}).status_code == 409
    uid = tclient.post("/api/users", json={"username": "Beto", "password": PWD}).json()["id"]
    assert tclient.put(f"/api/users/{uid}", json={"username": "ana"}).status_code == 409
    assert tclient.put(f"/api/users/{uid}", json={"username": "BETO"}).status_code == 200  # self


def test_user_put_empty_body_422_and_404(tclient):
    uid = tclient.post("/api/users", json={"username": "Ana", "password": PWD}).json()["id"]
    assert tclient.put(f"/api/users/{uid}", json={}).status_code == 422
    assert tclient.put("/api/users/999", json={"username": "xxx"}).status_code == 404
    assert tclient.get("/api/users/999").status_code == 404
    assert tclient.delete("/api/users/999").status_code == 404


def test_cannot_delete_last_user(tclient):
    uid = tclient.post("/api/users", json={"username": "Ana", "password": PWD}).json()["id"]
    r = tclient.delete(f"/api/users/{uid}")
    assert r.status_code == 409 and "último" in r.json()["detail"]
    assert tclient.get(f"/api/users/{uid}").status_code == 200


def test_cannot_delete_self_but_can_delete_other(authed):
    me = next(u for u in authed.get("/api/users").json() if u["username"] == "tester")
    r = authed.delete(f"/api/users/{me['id']}")
    assert r.status_code == 409 and "propio" in r.json()["detail"]
    other = authed.post("/api/users", json={"username": "otro", "password": PWD}).json()["id"]
    assert authed.delete(f"/api/users/{other}").status_code == 204
