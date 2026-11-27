"""Unit tests for password hashing and signed tokens."""
import base64
import json
from datetime import timedelta

import pytest

from app import auth
from app.services import users as service
from tests.conftest import NOW

SECRET = b"unit-test-secret"


def test_hash_is_not_plaintext_and_salted():
    h1, h2 = auth.hash_password("Clave-Sintetica1"), auth.hash_password("Clave-Sintetica1")
    assert "Clave-Sintetica1" not in h1
    assert h1.startswith("scrypt$")
    assert h1 != h2  # random salt


def test_verify_password_ok_wrong_and_malformed():
    h = auth.hash_password("Clave-Sintetica1")
    assert auth.verify_password("Clave-Sintetica1", h)
    assert not auth.verify_password("clave-sintetica1", h)
    assert not auth.verify_password("", h)
    for bad in ("", "x", "scrypt$1$2", "md5$1$1$1$aa$bb", "scrypt$a$b$c$d$e"):
        assert not auth.verify_password("Clave-Sintetica1", bad)


def test_token_roundtrip_and_expiry_boundary():
    token = auth.issue_token(SECRET, 7, NOW)
    assert auth.verify_token(SECRET, token, NOW) == 7
    last_ok = NOW + auth.TOKEN_TTL - timedelta(seconds=1)
    assert auth.verify_token(SECRET, token, last_ok) == 7
    assert auth.verify_token(SECRET, token, NOW + auth.TOKEN_TTL) is None


def test_token_rejects_wrong_secret_and_garbage():
    token = auth.issue_token(SECRET, 7, NOW)
    assert auth.verify_token(b"other", token, NOW) is None
    for bad in (None, "", "abc", "a.b.c", ".", "a.b", token + "x", token[:-2]):
        assert auth.verify_token(SECRET, bad, NOW) is None


def test_token_payload_tampering_rejected():
    token = auth.issue_token(SECRET, 7, NOW)
    part, sig = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(part + "=="))
    payload["u"] = 1  # privilege swap keeping the old signature
    forged = base64.urlsafe_b64encode(
        json.dumps(payload).encode()).rstrip(b"=").decode()
    assert auth.verify_token(SECRET, f"{forged}.{sig}", NOW) is None


@pytest.mark.parametrize("name", ["abc", "a" * 50, "Ana.Maria-1_x"])
def test_username_valid_boundaries(name):
    assert service.validate_username(name) == name


@pytest.mark.parametrize("name", ["ab", "a" * 51, "", "  ", "con espacio", "ñandú", None, 5])
def test_username_invalid(name):
    with pytest.raises(service.InvalidUserError):
        service.validate_username(name)


@pytest.mark.parametrize("pwd", ["12345678", "x" * 128])
def test_password_valid_boundaries(pwd):
    assert service.validate_password(pwd) == pwd


@pytest.mark.parametrize("pwd", ["1234567", "x" * 129, "", None, 12345678])
def test_password_invalid(pwd):
    with pytest.raises(service.InvalidUserError):
        service.validate_password(pwd)


def test_service_stores_only_hash(session):
    user = service.create_user(session, NOW, "Ana", "Clave-Sintetica1")
    assert user.password_hash != "Clave-Sintetica1"
    assert "Clave-Sintetica1" not in user.password_hash
    assert service.authenticate(session, "ana", "Clave-Sintetica1").id == user.id  # casefold
    assert service.authenticate(session, "ana", "otra-clave-xx") is None
    assert service.authenticate(session, "nadie", "Clave-Sintetica1") is None
    assert service.authenticate(session, None, None) is None


def test_duplicate_username_casefolded(session):
    service.create_user(session, NOW, "Ana", "Clave-Sintetica1")
    with pytest.raises(service.DuplicateUserError):
        service.create_user(session, NOW, "ANA", "Clave-Sintetica1")
