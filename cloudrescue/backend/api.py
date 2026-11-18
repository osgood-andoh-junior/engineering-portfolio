import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api_support import DB, update_fault
from backend.audit_chain import append
from backend.config import SERVICES, settings
from backend.diagnosis_api import router
from backend.identity import OperatorActor
from backend.models import (
    FaultConfiguration,
    HealthCheck,
    Incident,
    IncidentEvent,
    Service,
)
from backend.recovery_api import router as recovery_router
from backend.seed import monitoring_settings
from backend.validation_api import router as validation_router

app = FastAPI(title="CloudRescue", version="0.1.0")
app.include_router(router)
app.include_router(recovery_router)
app.include_router(validation_router)


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logging.getLogger("cloudrescue.api").error('{"event":"database_operation_failed"}')
    return JSONResponse({"detail": "Database temporarily unavailable"}, status_code=503)


def get_service(db: Session, slug: str) -> Service:
    service = db.get(Service, slug)
    if service is None:
        raise HTTPException(404, "Service not found")
    return service


def service_view(service: Service):
    return {
        "slug": service.slug,
        "name": service.name,
        "state": service.state,
        "last_success_at": service.last_success_at,
        "consecutive_failures": service.consecutive_failures,
        "failure_started_at": service.failure_started_at,
        "synthetic": True,
    }


def check_view(check: HealthCheck):
    return {
        "id": check.id,
        "checked_at": check.checked_at,
        "status_code": check.status_code,
        "latency_ms": check.latency_ms,
        "available": check.available,
        "error": check.error,
    }


def incident_view(incident: Incident):
    end = incident.closed_at or datetime.now(UTC)
    return {
        "id": incident.id,
        "service_slug": incident.service_slug,
        "started_at": incident.started_at,
        "detected_at": incident.detected_at,
        "recovery_started_at": incident.recovery_started_at,
        "closed_at": incident.closed_at,
        "duration_seconds": (end - incident.started_at).total_seconds(),
        "detection_seconds": (incident.detected_at - incident.started_at).total_seconds(),
        "recovery_seconds": (
            (end - incident.recovery_started_at).total_seconds()
            if incident.recovery_started_at
            else None
        ),
    }


@app.get("/health")
def health(db: DB):
    db.execute(select(1))
    return {"status": "ok"}


@app.get("/services")
def list_services(db: DB):
    return [service_view(service) for service in db.scalars(select(Service).order_by(Service.slug))]


@app.get("/services/{slug}")
def service_detail(slug: str, db: DB):
    service = get_service(db, slug)
    fault = db.get(FaultConfiguration, slug)
    expired = bool(fault and fault.expires_at and fault.expires_at <= datetime.now(UTC))
    return {
        **service_view(service),
        "fault": {
            "mode": "healthy" if expired else fault.mode,
            "latency_ms": 0 if expired else fault.latency_ms,
            "updated_at": fault.updated_at,
            "expires_at": fault.expires_at,
        }
        if fault
        else None,
    }


@app.get("/services/{slug}/checks")
def checks(slug: str, db: DB, limit: Annotated[int, Query(ge=1, le=500)] = 50):
    get_service(db, slug)
    query = (
        select(HealthCheck)
        .where(HealthCheck.service_slug == slug)
        .order_by(HealthCheck.checked_at.desc(), HealthCheck.id.desc())
        .limit(limit)
    )
    return [check_view(check) for check in db.scalars(query)]


@app.get("/incidents")
def incidents(
    db: DB, limit: Annotated[int, Query(ge=1, le=500)] = 30, offset: int = Query(0, ge=0)
):
    query = select(Incident).order_by(Incident.detected_at.desc()).offset(offset).limit(limit)
    return [incident_view(incident) for incident in db.scalars(query)]


@app.get("/incidents/{incident_id}")
def incident_detail(incident_id: int, db: DB):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    query = (
        select(IncidentEvent, HealthCheck)
        .join(HealthCheck, HealthCheck.id == IncidentEvent.check_id)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.id)
    )
    return {
        **incident_view(incident),
        "events": [
            {"kind": event.kind, "occurred_at": event.occurred_at, "check": check_view(check)}
            for event, check in db.execute(query)
        ],
    }


BUCKET_SECONDS = {1: 30, 6: 180, 24: 900, 168: 3600}


def aggregates(db: Session, hours: int, slug: str | None = None):
    since = datetime.now(UTC) - timedelta(hours=hours)
    bucket_seconds = BUCKET_SECONDS[hours]
    bucket = func.floor(func.extract("epoch", HealthCheck.checked_at) / bucket_seconds)
    query = select(
        bucket,
        func.count(),
        func.sum(case((HealthCheck.available, 1), else_=0)),
        func.avg(HealthCheck.latency_ms).filter(HealthCheck.available),
    ).where(HealthCheck.checked_at >= since)
    if slug is not None:
        get_service(db, slug)
        query = query.where(HealthCheck.service_slug == slug)
    return db.execute(query.group_by(bucket).order_by(bucket)).all(), bucket_seconds


@app.get("/metrics")
def metrics(db: DB, hours: int = 1, service: str | None = None):
    if hours not in BUCKET_SECONDS:
        raise HTTPException(422, "Choose a period of 1, 6, 24, or 168 hours")
    rows, seconds = aggregates(db, hours, service)
    checks = sum(row[1] for row in rows)
    successes = sum(row[2] for row in rows)
    return {
        "synthetic": True,
        "hours": hours,
        "checks": checks,
        "availability": 100 * successes / checks if checks else None,
        "points": [
            {
                "time": datetime.fromtimestamp(int(bucket) * seconds, UTC),
                "latency_ms": round(latency, 2) if latency is not None else None,
                "error_rate": round(100 * (count - good) / count, 2),
                "checks": count,
            }
            for bucket, count, good, latency in rows
        ],
    }


@app.get("/summary")
def summary(db: DB):
    counts = dict.fromkeys(("healthy", "degraded", "down", "recovering"), 0)
    for state, count in db.execute(select(Service.state, func.count()).group_by(Service.state)):
        counts[state] = count
    active = db.scalar(
        select(func.count()).select_from(Incident).where(Incident.closed_at.is_(None))
    )
    last = db.scalar(select(func.max(HealthCheck.checked_at)))
    return {
        "total": sum(counts.values()),
        **counts,
        "active_incidents": active,
        "last_check_at": last,
    }


@app.get("/settings")
def read_settings():
    return monitoring_settings()


class FaultRequest(BaseModel):
    model_config = {"extra": "forbid"}

    mode: Literal["latency", "error", "disconnect"]
    latency_ms: int | None = Field(None, ge=1, le=10000, strict=True)

    @model_validator(mode="after")
    def validate_latency(self) -> "FaultRequest":
        if self.mode == "latency":
            config = settings()
            if self.latency_ms is None or not (
                config.degraded_ms <= self.latency_ms < config.timeout_seconds * 1000
            ):
                raise ValueError(
                    "Latency must meet the degradation threshold and stay below timeout"
                )
        elif self.latency_ms is not None:
            raise ValueError("Latency is only allowed in latency mode")
        return self


def set_fault(db: Session, slug: str, mode: str, latency_ms: int, operator: str):
    if slug not in SERVICES:
        raise HTTPException(404, "Service not found")
    fault = db.get(FaultConfiguration, slug, with_for_update=True)
    if fault is None:
        raise HTTPException(404, "Service not found")
    before = {"mode": fault.mode, "latency_ms": fault.latency_ms}
    update_fault(db, fault, mode, latency_ms)
    append(
        db,
        operator,
        "fault_changed",
        target=slug,
        before=before,
        after={"mode": mode, "latency_ms": latency_ms},
    )
    db.commit()
    return {"mode": fault.mode, "latency_ms": fault.latency_ms, "updated_at": fault.updated_at}


@app.put("/services/{slug}/fault")
def start_fault(slug: str, fault: FaultRequest, db: DB, actor: OperatorActor):
    return set_fault(db, slug, fault.mode, fault.latency_ms or 0, actor.username)


@app.delete("/services/{slug}/fault")
def stop_fault(slug: str, db: DB, actor: OperatorActor):
    return set_fault(db, slug, "healthy", 0, actor.username)
