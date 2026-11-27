"""User rules: CRUD, credential checks and the last-user / self-delete guards."""
import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import dummy_hash, hash_password, verify_password
from app.models import User

MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH = 3, 50
MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH = 8, 128
_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]+", re.ASCII)


class UserError(Exception):
    """Base class for user domain errors."""


class InvalidUserError(UserError):
    """Invalid input (HTTP 422)."""


class DuplicateUserError(UserError):
    """Username already taken (HTTP 409)."""


class UserConflictError(UserError):
    """Operation not allowed: deleting yourself or the last user (HTTP 409)."""


class UserNotFoundError(UserError):
    """No user with that id (HTTP 404)."""


def validate_username(username: object) -> str:
    if not isinstance(username, str):
        raise InvalidUserError("El nombre de usuario debe ser texto.")
    text = username.strip()
    if not MIN_USERNAME_LENGTH <= len(text) <= MAX_USERNAME_LENGTH:
        raise InvalidUserError(
            f"El nombre de usuario debe tener entre {MIN_USERNAME_LENGTH} y "
            f"{MAX_USERNAME_LENGTH} caracteres.")
    if not _USERNAME_PATTERN.fullmatch(text):
        raise InvalidUserError(
            "El nombre de usuario solo puede contener letras, números, punto, "
            "guion y guion bajo.")
    return text


def validate_password(password: object) -> str:
    if not isinstance(password, str):
        raise InvalidUserError("La contraseña debe ser texto.")
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise InvalidUserError(
            f"La contraseña debe tener entre {MIN_PASSWORD_LENGTH} y "
            f"{MAX_PASSWORD_LENGTH} caracteres.")
    return password


def _duplicate() -> DuplicateUserError:
    return DuplicateUserError("Ya existe un usuario con ese nombre.")


def _find_by_key(session: Session, key: str) -> User | None:
    return session.scalars(select(User).where(User.username_key == key)).first()


def create_user(session: Session, now: datetime, username: object,
                password: object) -> User:
    name = validate_username(username)
    secret = validate_password(password)
    key = name.casefold()
    if _find_by_key(session, key) is not None:
        raise _duplicate()
    user = User(username=name, username_key=key, password_hash=hash_password(secret),
                created_at=now)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate() from None
    return user


def get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise UserNotFoundError("Usuario no encontrado.")
    return user


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.id)))


def update_user(session: Session, user_id: int, username: object = None,
                password: object = None) -> User:
    """Change username and/or password; at least one must be supplied."""
    user = get_user(session, user_id)
    if username is None and password is None:
        raise InvalidUserError("Debe indicar 'username' o 'password'.")
    if username is not None:
        name = validate_username(username)
        other = _find_by_key(session, name.casefold())
        if other is not None and other.id != user.id:
            raise _duplicate()
    if password is not None:
        new_hash = hash_password(validate_password(password))
    if username is not None:
        user.username, user.username_key = name, name.casefold()
    if password is not None:
        user.password_hash = new_hash
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate() from None
    return user


def delete_user(session: Session, user_id: int, acting_user_id: int | None = None) -> None:
    user = get_user(session, user_id)
    if acting_user_id is not None and user.id == acting_user_id:
        raise UserConflictError("No puede eliminar su propio usuario.")
    if (session.scalar(select(func.count(User.id))) or 0) <= 1:
        raise UserConflictError("No se puede eliminar el último usuario.")
    session.delete(user)
    session.commit()


def authenticate(session: Session, username: object, password: object) -> User | None:
    """Return the user for valid credentials, else None (no distinction why)."""
    user = None
    if isinstance(username, str) and isinstance(password, str):
        user = _find_by_key(session, username.strip().casefold())
    stored = user.password_hash if user else dummy_hash()
    ok = verify_password(password if isinstance(password, str) else "", stored)
    return user if (user is not None and ok) else None
