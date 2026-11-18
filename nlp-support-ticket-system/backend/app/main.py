import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import models, predictions, tickets, training
from backend.app.config import Settings
from backend.app.database.repository import Repository
from backend.app.database.session import Database
from backend.app.services.intelligence import IntelligenceService
from backend.app.services.registry import FACTORIES
from ml.src.interfaces import StudentMLNotImplemented


def create_app(settings: Settings | None = None, factories=None):
    settings = settings or Settings.from_env()
    database = Database(settings.database_path)

    @asynccontextmanager
    async def lifespan(app):
        database.initialize()
        settings.artifact_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title="NLP Support-Ticket Intelligence", lifespan=lifespan)
    app.state.repository = Repository(database)
    app.state.intelligence = IntelligenceService(
        app.state.repository,
        FACTORIES if factories is None else factories,
        settings.artifact_dir,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(StudentMLNotImplemented)
    async def student_missing(request: Request, error: StudentMLNotImplemented):
        return JSONResponse(
            status_code=501,
            content={
                "error": "STUDENT_ML_NOT_IMPLEMENTED",
                "component": error.component,
                "message": "Complete TODO(STUDENT-ML) in the ML module.",
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logging.getLogger(__name__).exception("Request failed", exc_info=error)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "Request failed. Check the backend logs.",
            },
        )

    @app.get("/health")
    def health():
        with database.connect() as connection:
            connection.execute("SELECT 1 FROM tickets LIMIT 1")
        return {"status": "ok", "database": "sqlite"}

    for router in (tickets.router, predictions.router, training.router, models.router):
        app.include_router(router)
    return app


app = create_app()
