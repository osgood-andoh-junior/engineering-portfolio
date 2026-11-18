import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.v1 import admin, auth, cart, catalogue, orders, payments
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.db.session import get_engine

logger = logging.getLogger("graceshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.app_env == "test":
        settings.isolated_test_url()
    else:
        settings.connection_url()
    yield
    get_engine.cache_clear()


app = FastAPI(title="GraceShield API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        json.dumps(
            {"request_id": request_id, "method": request.method, "status": response.status_code}
        )
    )
    return response


def failure(request: Request, code: str, message: str, status: int):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": getattr(request.state, "request_id", ""),
            }
        },
    )


@app.exception_handler(DomainError)
async def domain_error(request: Request, error: DomainError):
    return failure(request, error.code, error.message, error.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    # Pydantic input/context can contain credentials; never serialize or log them.
    return failure(request, "validation_failed", "Check the supplied fields and try again.", 422)


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, error: IntegrityError):
    return failure(
        request,
        "record_conflict",
        "The record conflicts with an existing record or constraint.",
        409,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return failure(
        request,
        "database_unavailable",
        "The service is temporarily unavailable. Please try again later.",
        503,
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    logger.error(
        json.dumps(
            {"event": "unexpected_error", "request_id": getattr(request.state, "request_id", "")}
        )
    )
    return failure(
        request, "unexpected_error", "An unexpected error occurred. Please try again later.", 500
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/environment")
def environment():
    settings = get_settings()
    guarded = False
    if settings.app_env == "test":
        settings.isolated_test_url()
        guarded = True
    return {"environment": settings.app_env, "isolatedTesting": guarded}


@app.get("/ready")
def ready():
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


for router in (
    auth.router,
    catalogue.router,
    cart.router,
    orders.router,
    admin.router,
    payments.router,
):
    app.include_router(router, prefix="/api/v1")
