"""Server-rendered web UI: login, logout and user management."""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import auth
from app.clock import get_now
from app.database import get_db
from app.routers.users import INVALID_CREDENTIALS, to_http_error
from app.services import users as service

router = APIRouter(tags=["users-web"], include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def _login_page(request: Request, username: str = "", error: str | None = None,
                status_code: int = 200):
    return templates.TemplateResponse(
        request, "login.html", {"username": username, "error": error},
        status_code=status_code)


def _users_page(request: Request, db: Session, username: str = "",
                error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request, "users.html",
        {"users": service.list_users(db), "username": username, "error": error,
         "current_id": getattr(request.state, "user_id", None)},
        status_code=status_code)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _login_page(request)


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(""), password: str = Form(""),
          db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    user = service.authenticate(db, username, password)
    if user is None:
        return _login_page(request, username, INVALID_CREDENTIALS, 401)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        auth.COOKIE_NAME, auth.issue_token(request.app.state.secret_key, user.id, now),
        max_age=int(auth.TOKEN_TTL.total_seconds()), httponly=True, samesite="lax")
    return response


@router.api_route("/logout", methods=["GET", "POST"], response_class=HTMLResponse)
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    return _users_page(request, db)


@router.post("/users", response_class=HTMLResponse)
def create(request: Request, username: str = Form(""), password: str = Form(""),
           db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    try:
        service.create_user(db, now, username, password)
    except service.UserError as exc:
        http_exc = to_http_error(exc)
        return _users_page(request, db, username, http_exc.detail, http_exc.status_code)
    return RedirectResponse("/users", status_code=303)


@router.post("/users/{user_id}/delete", response_class=HTMLResponse)
def delete(request: Request, user_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_user(db, user_id, getattr(request.state, "user_id", None))
    except service.UserError as exc:
        http_exc = to_http_error(exc)
        if http_exc.status_code == 404:
            raise http_exc from None
        return _users_page(request, db, error=http_exc.detail,
                           status_code=http_exc.status_code)
    return RedirectResponse("/users", status_code=303)
