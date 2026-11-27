"""Stdlib-only authentication primitives: scrypt password hashes and signed tokens.

Token format: ``base64url(payload_json).base64url(hmac_sha256(secret, payload_part))``
with payload ``{"u": user_id, "exp": epoch_seconds}``. Expiry is evaluated with the
app's injected clock. Nothing here logs or returns secrets.
"""
import base64
import binascii
import functools
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
SALT_BYTES = 16
TOKEN_TTL = timedelta(hours=8)
COOKIE_NAME = "session"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          maxmem=64 * 1024 * 1024, dklen=32)


def hash_password(password: str) -> str:
    """Return ``scrypt$n$r$p$salt$hash`` with a fresh random salt."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check; any malformed stored hash simply fails."""
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = _b64d(digest)
        actual = _scrypt(password, _b64d(salt), int(n), int(r), int(p))
    except (ValueError, binascii.Error):
        return False
    return hmac.compare_digest(actual, expected)


@functools.cache
def dummy_hash() -> str:
    """Hash verified when the user does not exist, to equalize response timing."""
    return hash_password(secrets.token_urlsafe(16))


def new_secret() -> bytes:
    return secrets.token_bytes(32)


def _sign(secret: bytes, payload_part: str) -> str:
    return _b64e(hmac.new(secret, payload_part.encode("ascii"), hashlib.sha256).digest())


def issue_token(secret: bytes, user_id: int, now: datetime,
                ttl: timedelta = TOKEN_TTL) -> str:
    payload = json.dumps({"u": user_id, "exp": int((now + ttl).timestamp())},
                         separators=(",", ":"))
    part = _b64e(payload.encode("utf-8"))
    return f"{part}.{_sign(secret, part)}"


def verify_token(secret: bytes, token: str | None, now: datetime) -> int | None:
    """Return the user id for a valid, unexpired token; otherwise None."""
    if not token or token.count(".") != 1:
        return None
    part, signature = token.split(".")
    try:
        if not hmac.compare_digest(_sign(secret, part), signature):
            return None
        data = json.loads(_b64d(part))
        user_id, exp = data["u"], data["exp"]
    except (ValueError, KeyError, TypeError, binascii.Error):
        return None
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        return None
    if isinstance(exp, bool) or not isinstance(exp, int) or int(now.timestamp()) >= exp:
        return None
    return user_id
