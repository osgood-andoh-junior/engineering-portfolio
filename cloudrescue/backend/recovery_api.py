from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select, text
from sqlalchemy.dialects.postgresql import insert

from backend.api_support import DB
from backend.audit_chain import append
from backend.config import settings
from backend.diagnosis_api import incident_diagnosis
from backend.identity import Admin, OperatorActor, Viewer, principal
from backend.models import ApplicationSetting, HealthCheck, Incident, ReplaySession
from backend.policies import Parameters
from backend.recovery_control import enabled, execute, recommendation, request_action, resume, stop
from backend.recovery_lab import SCENARIOS, benchmark, compare
from backend.recovery_models import (
    Approval,
    AuditEvent,
    Execution,
    ExperimentResult,
    PolicyVersion,
    Recommendation,
    RecoveryExperiment,
    RecoveryPolicy,
)
from backend.telemetry import event

router = APIRouter(prefix="/recovery", dependencies=[Depends(principal)])


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["primary", "upstream", "overload", "transient", "healthy_burst", "replay"]
    seed: Annotated[int, Field(ge=0, le=2_147_483_647)] = 42
    parameters: Parameters = Field(default_factory=Parameters)
    replay_id: Annotated[int, Field(gt=0)] | None = None


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: UUID
    incident_id: Annotated[int, Field(gt=0)]
    target: Literal["identity", "messaging", "storage"]
    action: Literal["reset_fault", "restart"]


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm: Literal[True]


@router.get("/policies")
def policies(db: DB):
    current = db.get(ApplicationSetting, "recovery_policy_defaults")
    return {
        "strategies": list(db.scalars(select(RecoveryPolicy.name).order_by(RecoveryPolicy.name))),
        "parameters": current.value if current else Parameters().model_dump(),
        "parameter_schema": Parameters.model_json_schema()["properties"],
        "scenarios": SCENARIOS,
    }


@router.put("/policies")
def publish_policy_defaults(payload: Parameters, db: DB, actor: Admin):
    db.execute(text("SELECT pg_advisory_xact_lock(726031028)"))
    current = db.get(ApplicationSetting, "recovery_policy_defaults")
    before = current.value if current else Parameters().model_dump()
    after = payload.model_dump()
    db.merge(ApplicationSetting(key="recovery_policy_defaults", value=after))
    version = PolicyVersion(policy="combined", parameters=after)
    db.add(version)
    db.flush()
    append(
        db,
        actor.username,
        "policy_defaults_updated",
        target="policy_lab",
        before=before,
        after=after,
        version=version.id,
    )
    db.commit()
    return {"version": version.id, "parameters": after}


@router.post("/experiments", status_code=201)
def experiment(payload: ExperimentRequest, db: DB, actor: OperatorActor):
    if (payload.scenario == "replay") != (payload.replay_id is not None):
        raise HTTPException(422, "Select a saved replay only for a replay experiment")
    saved = db.get(ReplaySession, payload.replay_id) if payload.replay_id else None
    if payload.replay_id and not saved:
        raise HTTPException(404, "Replay not found")
    try:
        results = compare(
            payload.scenario, payload.parameters, payload.seed, saved.payload if saved else None
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    version = PolicyVersion(policy="combined", parameters=payload.parameters.model_dump())
    db.add(version)
    db.flush()
    row = RecoveryExperiment(
        version_id=version.id,
        scenario=payload.scenario,
        seed=payload.seed,
        replay_id=payload.replay_id,
    )
    db.add(row)
    db.flush()
    for result in results:
        db.add(ExperimentResult(experiment_id=row.id, policy=result["policy"], metrics=result))
    db.commit()
    return experiment_detail(row.id, db)


@router.get("/experiments")
def experiments(db: DB):
    return [
        {"id": row.id, "scenario": row.scenario, "seed": row.seed}
        for row in db.scalars(
            select(RecoveryExperiment).order_by(RecoveryExperiment.id.desc()).limit(50)
        )
    ]


@router.get("/experiments/{experiment_id}")
def experiment_detail(experiment_id: int, db: DB):
    row = db.get(RecoveryExperiment, experiment_id)
    if row is None:
        raise HTTPException(404, "Experiment not found")
    version = db.get(PolicyVersion, row.version_id)
    results = list(
        db.scalars(select(ExperimentResult.metrics).where(ExperimentResult.experiment_id == row.id))
    )
    order = ("baseline", "retry", "breaker", "limit", "failover", "combined")
    return {
        "id": row.id,
        "scenario": row.scenario,
        "seed": row.seed,
        "modeled": True,
        "version": row.version_id,
        "replay_id": row.replay_id,
        "parameters": version.parameters if version else {},
        "results": sorted(results, key=lambda result: order.index(result["policy"])),
    }


@router.get("/center")
def center(db: DB, actor: Viewer):
    incidents = list(
        db.scalars(
            select(Incident)
            .where(Incident.closed_at.is_(None))
            .order_by(Incident.detected_at.desc())
        )
    )
    return {
        "enabled": enabled(db),
        "configured": settings().recovery_enabled,
        "operator": actor.username,
        "incidents": [
            {"id": row.id, "target": row.service_slug, "detected_at": row.detected_at}
            for row in incidents
        ],
    }


@router.post("/recommendations/{incident_id}")
def recommend(incident_id: int, db: DB, actor: OperatorActor):
    diagnosis = incident_diagnosis(incident_id, db)
    incident = db.get(Incident, incident_id)
    assert incident is not None
    checks = list(
        db.scalars(
            select(HealthCheck)
            .where(
                HealthCheck.service_slug == incident.service_slug,
                HealthCheck.checked_at >= incident.started_at,
                HealthCheck.checked_at <= (incident.closed_at or datetime.now(UTC)),
            )
            .order_by(HealthCheck.checked_at.desc())
            .limit(12)
        )
    )
    result = recommendation(diagnosis, checks)
    event("recommendation", result["strategy"])
    db.execute(
        insert(Recommendation)
        .values(incident_id=incident_id, evidence=result)
        .on_conflict_do_update(
            index_elements=[Recommendation.incident_id],
            set_={"evidence": result, "updated_at": func.now()},
        )
    )
    db.commit()
    return result


def approval_view(row: Approval, execution: Execution | None):
    now = datetime.now(UTC)
    status = execution.status if execution else "awaiting_approval"
    if execution and status == "verifying" and execution.deadline <= now:
        status = "verification_expired"
    return {
        "id": row.id,
        "incident_id": row.incident_id,
        "target": row.target,
        "action": row.action,
        "operator": row.operator,
        "requested_at": row.requested_at,
        "approved_at": row.approved_at,
        "status": status,
        "evidence": execution.evidence if execution else None,
    }


@router.get("/approvals")
def approvals(db: DB):
    rows = db.execute(
        select(Approval, Execution).outerjoin(Execution).order_by(Approval.id.desc()).limit(50)
    )
    return [approval_view(row, execution) for row, execution in rows]


@router.post("/approvals", status_code=201)
def create_approval(payload: ActionRequest, db: DB, actor: OperatorActor):
    row = request_action(
        db, operator=actor.username, **{**payload.model_dump(), "key": str(payload.key)}
    )
    return approval_view(row, db.get(Execution, row.id))


@router.post("/approvals/{approval_id}/execute")
def approve(approval_id: int, payload: Confirmation, db: DB, actor: Admin):
    result = execute(db, approval_id, actor.username)
    row = db.get(Approval, approval_id)
    assert row is not None
    return approval_view(row, result)


@router.post("/stop")
def emergency_stop(payload: Confirmation, db: DB, actor: Admin):
    stop(db, actor.username)
    return {"stopped": True}


@router.post("/resume")
def emergency_resume(payload: Confirmation, db: DB, actor: Admin):
    resume(db, actor.username)
    return {"stopped": False}


@router.get("/audit")
def history(db: DB):
    rows = db.execute(
        select(AuditEvent, Approval).outerjoin(Approval).order_by(AuditEvent.id.desc()).limit(100)
    )
    return [
        {
            "id": row.id,
            "approval_id": row.approval_id,
            "event": row.event,
            "operator": row.operator,
            "occurred_at": row.occurred_at,
            "evidence": row.evidence,
            "action": approval.action if approval else None,
            "target": approval.target if approval else None,
            "approved_at": approval.approved_at if approval else None,
        }
        for row, approval in rows
    ]


@router.get("/analytics")
def analytics(db: DB):
    cutoff = datetime.now(UTC) - timedelta(days=7)
    incidents = list(
        db.scalars(
            select(Incident)
            .where(Incident.detected_at >= cutoff)
            .order_by(Incident.detected_at.desc())
        )
    )
    rows = db.execute(select(Execution.status, func.count()).group_by(Execution.status))
    counts = {status: count for status, count in rows}
    terminal = counts.get("succeeded", 0) + counts.get("failed", 0)
    closed = [row for row in incidents if row.closed_at]
    hour = func.date_trunc("hour", HealthCheck.checked_at)
    trend = db.execute(
        select(hour, func.count(), func.sum(case((HealthCheck.available.is_(False), 1), else_=0)))
        .where(HealthCheck.checked_at >= datetime.now(UTC) - timedelta(hours=24))
        .group_by(hour)
        .order_by(hour)
    )
    return {
        "modeled": benchmark()["summary"],
        "observed": {
            "incidents": len(incidents),
            "closed": len(closed),
            "mttd_seconds": sum(
                (row.detected_at - row.started_at).total_seconds() for row in incidents
            )
            / len(incidents)
            if incidents
            else None,
            "mttr_seconds": sum(
                (row.closed_at - row.started_at).total_seconds() for row in closed if row.closed_at
            )
            / len(closed)
            if closed
            else None,
            "execution_success": counts.get("succeeded", 0) / terminal if terminal else None,
            "execution_samples": terminal,
            "error_trend": [
                {"hour": hour_at, "checks": total, "error_rate": failed / total}
                for hour_at, total, failed in trend
            ],
            "durations": [
                {
                    "id": row.id,
                    "target": row.service_slug,
                    "seconds": (row.closed_at - row.started_at).total_seconds(),
                }
                for row in closed[:20]
                if row.closed_at
            ],
        },
    }
