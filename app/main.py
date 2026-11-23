"""Application factory."""
import logging
from collections.abc import Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import sessionmaker

from app import database
from app.approval import DEFAULT_APPROVAL_RANGES, ApprovalRange, validate_ranges
from app.clock import Clock, system_clock
from app.routers import bids, bids_web, suppliers, suppliers_web, tenders, tenders_web

logger = logging.getLogger("bid_management")


def create_app(db_url: str | None = None, clock: Clock | None = None,
               approval_ranges: Sequence[ApprovalRange] | None = None) -> FastAPI:
    """Build the app; db_url overrides the default database, clock the system time,
    approval_ranges the default approver ranges (validated; ValueError if invalid)."""
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
        yield

    app = FastAPI(title="Bid-Management", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = factory
    app.state.clock = clock or system_clock
    app.state.approval_ranges = ranges

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, _exc: RequestValidationError):
        path = request.url.path
        if path.endswith("/bids") and request.method == "POST":
            detail = (
                "Solicitud inválida: revise los campos 'supplier_id' (entero) "
                "y 'amount_crc'."
            )
        elif path.endswith(("/bids", "/evaluation")):
            detail = "Solicitud inválida: el identificador debe ser un número entero."
        elif path.startswith("/api/tenders"):
            detail = (
                "Solicitud inválida: revise los campos 'code', 'title', "
                "'budget_crc' y 'closing_at'."
            )
        else:
            detail = "Solicitud inválida: se requiere un campo 'name' de tipo texto."
        return JSONResponse(status_code=422, content={"detail": detail})

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
    return app


app = create_app()
