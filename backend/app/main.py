from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints import (
    academic,
    assessment,
    auth,
    classes,
    curriculum,
    grading,
    reporting,
    teaching,
    users,
)
from app.core.config import Settings
from app.core.database import Database

SCHEMA_REVISION = "20261126_0002"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()

    app = FastAPI(title="PNL OBE API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=["Content-Disposition"],
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(status_code=503, content={"detail": "Layanan database belum tersedia"})

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["system"])
    def ready():
        try:
            with database.engine.connect() as connection:
                revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
                if revision != SCHEMA_REVISION:
                    return JSONResponse(status_code=503, content={"status": "not_ready"})
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(classes.router, prefix="/api/v1")
    app.include_router(curriculum.router, prefix="/api/v1")
    app.include_router(academic.router, prefix="/api/v1")
    app.include_router(teaching.router, prefix="/api/v1")
    app.include_router(assessment.router, prefix="/api/v1")
    app.include_router(grading.router, prefix="/api/v1")
    app.include_router(reporting.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    return app
