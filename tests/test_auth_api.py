"""Login, route protection and secret hygiene through the HTTP layer."""
import pytest

from app.main import create_app
from tests.conftest import PASSWORD, USERNAME

PROTECTED_API = [
    ("get", "/api/suppliers"), ("get", "/api/tenders"), ("get", "/api/exchange-rate"),
    ("get", "/api/exchange-rate/history"), ("get", "/api/users"),
    ("get", "/api/bids/1"), ("delete", "/api/suppliers/1"), ("delete", "/api/users/1"),
    ("post", "/api/suppliers"), ("put", "/api/bids/1"),
]
PROTECTED_WEB = ["/", "/suppliers", "/tenders", "/exchange-rate", "/users",
                 "/tenders/1/bids", "/suppliers/1/bids"]


@pytest.mark.parametrize("method,path", PROTECTED_API)
def test_api_requires_auth(auth_client, method, path):
    r = getattr(auth_client, method)(path)
    assert r.status_code == 401
    assert r.json() == {"detail": "No autenticado"}
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", PROTECTED_WEB)
def test_web_redirects_to_login(auth_client, path):
    r = auth_client.get(path)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_web_post_is_protected_too(auth_client):
    r = auth_client.post("/suppliers", data={"name": "X"})
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert auth_client.post("/api/auth/login",
                            json={"username": USERNAME, "password": PASSWORD}).status_code == 200


@pytest.mark.parametrize("path", ["/login", "/docs", "/openapi.json"])
def test_public_paths_open(auth_client, path):
    assert auth_client.get(path).status_code == 200


def test_login_ok_returns_token_and_no_secrets(auth_client):
    r = auth_client.post("/api/auth/login",
                         json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"token", "token_type", "expires_in"}
    assert body["token_type"] == "Bearer" and body["expires_in"] == 8 * 3600
    assert PASSWORD not in r.text and "scrypt" not in r.text
    ok = auth_client.get("/api/suppliers", headers={"Authorization": f"Bearer {body['token']}"})
    assert ok.status_code == 200


def test_login_username_is_case_insensitive(auth_client):
    r = auth_client.post("/api/auth/login",
                         json={"username": USERNAME.upper(), "password": PASSWORD})
    assert r.status_code == 200


@pytest.mark.parametrize("creds", [
    {"username": USERNAME, "password": "incorrecta-xx"},   # wrong password
    {"username": "nadie", "password": PASSWORD},           # unknown user
    {"username": "", "password": ""},
])
def test_login_failure_is_generic(auth_client, creds):
    r = auth_client.post("/api/auth/login", json=creds)
    assert r.status_code == 401
    assert r.json() == {"detail": "Credenciales inválidas"}
    assert PASSWORD not in r.text


def test_login_malformed_body_422(auth_client):
    r = auth_client.post("/api/auth/login", json={"username": 5})
    assert r.status_code == 422
    assert "username" in r.json()["detail"]


@pytest.mark.parametrize("header", [
    "Bearer", "Bearer ", "Bearer abc.def", "Basic dGVzdGVyOnB3", "Token xyz", "bearer x.y.z",
])
def test_bad_authorization_headers_rejected(auth_client, header):
    r = auth_client.get("/api/suppliers", headers={"Authorization": header})
    assert r.status_code == 401


def test_tampered_token_rejected(authed):
    token = authed.headers["Authorization"].split(" ")[1]
    flipped = token[:-1] + ("A" if token[-1] != "A" else "B")
    r = authed.get("/api/suppliers", headers={"Authorization": f"Bearer {flipped}"})
    assert r.status_code == 401


def test_token_from_another_secret_rejected(db_url, clock, authed):
    other = create_app(db_url, clock=clock, secret_key="a-different-secret")
    from fastapi.testclient import TestClient
    with TestClient(other) as c:
        r = c.get("/api/suppliers", headers={"Authorization": authed.headers["Authorization"]})
    assert r.status_code == 401


def test_token_expires(authed, clock):
    assert authed.get("/api/suppliers").status_code == 200
    clock.advance(hours=8, seconds=1)
    assert authed.get("/api/suppliers").status_code == 401


def test_token_of_deleted_user_rejected(authed):
    other = authed.post("/api/users", json={"username": "otro", "password": "Clave-Sintetica2"})
    tok = authed.post("/api/auth/login", json={"username": "otro",
                                               "password": "Clave-Sintetica2"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert authed.delete(f"/api/users/{other.json()['id']}").status_code == 204
    assert authed.get("/api/suppliers", headers=h).status_code == 401


def test_web_login_sets_httponly_cookie_and_grants_access(auth_client):
    r = auth_client.post("/login", data={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 303 and r.headers["location"] == "/"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert PASSWORD not in r.headers["set-cookie"]
    assert auth_client.get("/suppliers").status_code == 200
    assert auth_client.get("/api/suppliers").status_code == 200  # cookie also valid for API


def test_web_login_failure_401_generic(auth_client):
    r = auth_client.post("/login", data={"username": USERNAME, "password": "mala-clave-1"})
    assert r.status_code == 401
    assert "Credenciales inválidas" in r.text
    assert "mala-clave-1" not in r.text
    assert "set-cookie" not in r.headers


def test_logout_clears_session(auth_client):
    auth_client.post("/login", data={"username": USERNAME, "password": PASSWORD})
    r = auth_client.post("/logout")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    auth_client.cookies.clear()
    assert auth_client.get("/suppliers").status_code == 303


def test_user_endpoints_never_expose_hash(authed):
    r = authed.get("/api/users")
    assert r.status_code == 200
    for text in (r.text, authed.get("/api/users/1").text,
                 authed.post("/api/users", json={"username": "nuevo",
                                                 "password": "Clave-Sintetica3"}).text):
        assert "password" not in text and "scrypt" not in text and "hash" not in text


def test_errors_do_not_leak_internals(authed):
    r = authed.get("/api/users/abc")
    assert r.status_code == 422
    assert "Traceback" not in r.text and "sqlalchemy" not in r.text.lower()


def test_seed_user_from_env(db_url, clock, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("BID_ADMIN_USER", "semilla")
    monkeypatch.setenv("BID_ADMIN_PASSWORD", "Clave-De-Semilla1")
    with TestClient(create_app(db_url, clock=clock)) as c:
        r = c.post("/api/auth/login", json={"username": "semilla",
                                            "password": "Clave-De-Semilla1"})
        assert r.status_code == 200
    with TestClient(create_app(db_url, clock=clock)) as c:  # idempotent on restart
        assert c.post("/api/auth/login", json={"username": "semilla",
                                               "password": "Clave-De-Semilla1"}).status_code == 200


def test_seed_ignored_when_password_invalid(db_url, clock, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("BID_ADMIN_USER", "semilla")
    monkeypatch.setenv("BID_ADMIN_PASSWORD", "corta")
    with TestClient(create_app(db_url, clock=clock)) as c:
        assert c.post("/api/auth/login", json={"username": "semilla",
                                               "password": "corta"}).status_code == 401


def test_auth_disabled_leaves_routes_open(client):
    assert client.get("/api/suppliers").status_code == 200
