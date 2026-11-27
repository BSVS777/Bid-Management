"""JSON API for users and token login.

Auth choice: ``POST /api/auth/login`` returns a signed Bearer token; send it as
``Authorization: Bearer <token>``. The web UI uses the same token in an HttpOnly cookie.
Password hashes are never serialized.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, StrictStr
from sqlalchemy.orm import Session

from app import auth
from app.clock import get_now
from app.database import get_db
from app.models import User
from app.services import users as service

router = APIRouter(tags=["users"])

INVALID_CREDENTIALS = "Credenciales inválidas"


class LoginIn(BaseModel):
    username: StrictStr
    password: StrictStr


class TokenOut(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int


class UserCreate(BaseModel):
    username: StrictStr
    password: StrictStr


class UserUpdate(BaseModel):
    username: StrictStr | None = None
    password: StrictStr | None = None


class UserOut(BaseModel):
    id: int
    username: str
    created_at: str


def to_out(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username,
                   created_at=user.created_at.isoformat(timespec="seconds"))


def to_http_error(exc: service.UserError) -> HTTPException:
    """Map a domain error to a safe HTTP error."""
    if isinstance(exc, service.InvalidUserError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, (service.DuplicateUserError, service.UserConflictError)):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/api/auth/login", response_model=TokenOut)
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db),
          now: datetime = Depends(get_now)):
    user = service.authenticate(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    token = auth.issue_token(request.app.state.secret_key, user.id, now)
    return TokenOut(token=token, expires_in=int(auth.TOKEN_TTL.total_seconds()))


@router.post("/api/users", status_code=201, response_model=UserOut)
def create(payload: UserCreate, db: Session = Depends(get_db),
           now: datetime = Depends(get_now)):
    try:
        return to_out(service.create_user(db, now, payload.username, payload.password))
    except service.UserError as exc:
        raise to_http_error(exc) from None


@router.get("/api/users", response_model=list[UserOut])
def list_all(db: Session = Depends(get_db)):
    return [to_out(u) for u in service.list_users(db)]


@router.get("/api/users/{user_id}", response_model=UserOut)
def get_one(user_id: int, db: Session = Depends(get_db)):
    try:
        return to_out(service.get_user(db, user_id))
    except service.UserError as exc:
        raise to_http_error(exc) from None


@router.put("/api/users/{user_id}", response_model=UserOut)
def update(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    try:
        return to_out(service.update_user(db, user_id, payload.username,
                                          payload.password))
    except service.UserError as exc:
        raise to_http_error(exc) from None


@router.delete("/api/users/{user_id}", status_code=204)
def delete(request: Request, user_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_user(db, user_id, getattr(request.state, "user_id", None))
    except service.UserError as exc:
        raise to_http_error(exc) from None
