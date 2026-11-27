"""Application factory."""
import logging
import os
from collections.abc import Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import sessionmaker

from app import auth, database
from app.approval import DEFAULT_APPROVAL_RANGES, ApprovalRange, validate_ranges
from app.clock import Clock, system_clock
from app.models import User
from app.routers import (bids, bids_web, exchange_rate, exchange_rate_web, suppliers,
                         suppliers_web, tenders, tenders_web, users, users_web)
from app.services import users as user_service

logger = logging.getLogger("bid_management")

# Reachable without a session: login (web + API), logout, API docs.
PUBLIC_PATHS = frozenset({"/login", "/logout", "/api/auth/login", "/docs", "/redoc",
                          "/openapi.json"})
NOT_AUTHENTICATED = "No autenticado"
ID_MESSAGE = "Solicitud inválida: el identificador debe ser un número entero."


def _bearer_or_cookie(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return request.cookies.get(auth.COOKIE_NAME)


def _seed_initial_user(factory, clock: Clock) -> None:
    """Create the first user from BID_ADMIN_USER / BID_ADMIN_PASSWORD when both are
    set and that user does not exist. Invalid values are skipped with a warning
    (the password is never logged)."""
    username = os.environ.get("BID_ADMIN_USER")
    password = os.environ.get("BID_ADMIN_PASSWORD")
    if not username or not password:
        return
    with factory() as db:
        try:
            user_service.create_user(db, clock(), username, password)
        except user_service.DuplicateUserError:
            pass
        except user_service.UserError as exc:
            logger.warning("BID_ADMIN_USER/BID_ADMIN_PASSWORD ignored: %s", exc)


def _validation_detail(request: Request) -> str:
    path, method = request.url.path, request.method
    if path == "/api/auth/login":
        return "Solicitud inválida: se requieren 'username' y 'password' de tipo texto."
    if path.startswith("/api/users") and method in ("POST", "PUT"):
        return "Solicitud inválida: revise los campos 'username' y 'password'."
    if method == "DELETE" or path.startswith(("/api/users/", "/api/exchange-rate/")) \
            or (path.startswith("/api/bids/") and method == "GET"):
        return ID_MESSAGE
    if path.startswith("/api/bids/"):
        return "Solicitud inválida: revise el campo 'amount_crc'."
    if path == "/api/exchange-rate":
        return "Solicitud inválida: se requiere el campo 'crc_per_usd'."
    if path.endswith("/bids") and method == "POST":
        return ("Solicitud inválida: revise los campos 'supplier_id' (entero) "
                "y 'amount_crc'.")
    if path.endswith(("/bids", "/evaluation", "/evaluation/usd")):
        return ID_MESSAGE
    if path.startswith("/api/tenders"):
        return ("Solicitud inválida: revise los campos 'code', 'title', "
                "'budget_crc' y 'closing_at'.")
    return "Solicitud inválida: se requiere un campo 'name' de tipo texto."


def create_app(db_url: str | None = None, clock: Clock | None = None,
               approval_ranges: Sequence[ApprovalRange] | None = None,
               auth_enabled: bool = True, secret_key: str | bytes | None = None
               ) -> FastAPI:
    """Build the app; db_url overrides the default database, clock the system time,
    approval_ranges the default approver ranges (validated; ValueError if invalid).

    auth_enabled=False disables login enforcement (tests/tools only). The token
    secret comes from secret_key, else env BID_SECRET_KEY, else a random per-process
    value (sessions then do not survive restarts)."""
    ranges = validate_ranges(
        DEFAULT_APPROVAL_RANGES if approval_ranges is None else approval_ranges)
    if db_url is None:
        engine, factory = database.engine, database.SessionLocal
    else:
        engine = database.make_engine(db_url)
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        database.init_db(engine)
        _seed_initial_user(factory, app.state.clock)
        yield

    app = FastAPI(title="Bid-Management", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = factory
    app.state.clock = clock or system_clock
    app.state.approval_ranges = ranges
    app.state.auth_enabled = auth_enabled
    raw_secret = secret_key or os.environ.get("BID_SECRET_KEY")
    if isinstance(raw_secret, str):
        raw_secret = raw_secret.encode("utf-8")
    app.state.secret_key = raw_secret or auth.new_secret()

    if auth_enabled:
        @app.middleware("http")
        async def require_login(request: Request, call_next):
            path = request.url.path
            if path in PUBLIC_PATHS:
                return await call_next(request)
            user_id = auth.verify_token(
                app.state.secret_key, _bearer_or_cookie(request), app.state.clock())
            if user_id is not None:
                with factory() as db:
                    if db.get(User, user_id) is None:  # deleted users lose access
                        user_id = None
            if user_id is None:
                if path.startswith("/api/"):
                    return JSONResponse(status_code=401,
                                        content={"detail": NOT_AUTHENTICATED},
                                        headers={"WWW-Authenticate": "Bearer"})
                return RedirectResponse("/login", status_code=303)
            request.state.user_id = user_id
            return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, _exc: RequestValidationError):
        return JSONResponse(status_code=422,
                            content={"detail": _validation_detail(request)})

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception):
        logger.error("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Error interno"})

    @app.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/suppliers", status_code=307)

    app.include_router(suppliers.router)
    app.include_router(suppliers_web.router)
    app.include_router(tenders.router)
    app.include_router(tenders_web.router)
    app.include_router(bids.router)
    app.include_router(bids_web.router)
    app.include_router(exchange_rate.router)
    app.include_router(exchange_rate_web.router)
    app.include_router(users.router)
    app.include_router(users_web.router)
    return app


app = create_app()
