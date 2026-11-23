"""Application factory."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import sessionmaker

from app import database
from app.routers import suppliers, suppliers_web

logger = logging.getLogger("bid_management")


def create_app(db_url: str | None = None) -> FastAPI:
    """Build the app; db_url overrides the default module-level database."""
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

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, _exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Solicitud inválida: se requiere un campo 'name' de tipo texto."
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception):
        logger.error("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Error interno"})

    @app.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/suppliers", status_code=307)

    app.include_router(suppliers.router)
    app.include_router(suppliers_web.router)
    return app


app = create_app()
