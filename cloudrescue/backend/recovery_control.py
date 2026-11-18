from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.api_support import update_fault
from backend.audit_chain import append
from backend.config import settings
from backend.models import ApplicationSetting, FaultConfiguration, HealthCheck, Incident, Service
from backend.recovery_models import Approval, AuditEvent, Execution, SimulatorRuntime
from backend.telemetry import event as telemetry_event
from backend.topology import graph_edges, latest, upstream

COOLDOWN = timedelta(seconds=10)
APPROVAL_TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 2
CONTROL_LOCK = 726031024


def audit(
    db: Session, operator: str, event: str, approval_id: int | None = None, **evidence: Any
) -> None:
    db.add(AuditEvent(approval_id=approval_id, operator=operator, event=event, evidence=evidence))
    append(db, operator, event, approval_id=approval_id, evidence=evidence)
    telemetry_event("recovery", event)


def lock(db: Session) -> None:
    db.execute(text("SET LOCAL lock_timeout = '2s'"))
    db.execute(text("SET LOCAL statement_timeout = '3s'"))
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": CONTROL_LOCK})


def enabled(db: Session) -> bool:
    switch = db.get(ApplicationSetting, "recovery_stop")
    return settings().recovery_enabled and not (switch and switch.value.get("stopped"))


def recommendation(diagnosis: dict, checks: list[HealthCheck]) -> dict:
    candidates = diagnosis["candidates"]
    if not candidates:
        return {
            "strategy": "investigate",
            "reason": "The incident lacks corroborating causal evidence.",
            "risk": "Changing local state may conceal the underlying cause.",
            "candidates": [],
        }
    symptoms = any(candidate["symptoms"] for candidate in candidates)
    network = any(check.error in {"timeout", "connection"} for check in checks)
    repeated_unavailable = sum(not check.available for check in checks) >= 3
    if symptoms:
        strategy, reason = "breaker", "Dependent probes corroborate an upstream failure."
        risk = "Open breakers reject requests until a controlled probe succeeds."
    elif network and repeated_unavailable:
        strategy, reason = "failover", "Repeated failed probes suggest an unavailable instance."
        risk = "A standby may share the fault or have lower capacity. Validate in the policy lab."
    elif network:
        strategy, reason = "retry", "Recent transport errors may be transient."
        risk = "Retry only safe operations within a deadline and budget."
    elif any(check.status_code == 429 for check in checks):
        strategy, reason = "limit", "HTTP 429 responses indicate traffic was rejected."
        risk = "Admission control can reject requests the service could have served."
    else:
        strategy, reason = (
            "investigate",
            "Direct failures are visible, but the mechanism is unclear.",
        )
        risk = "Inspect the simulator and its dependencies before intervening."
    return {"strategy": strategy, "reason": reason, "risk": risk, "candidates": candidates}


def request_action(
    db: Session, *, key: str, incident_id: int, target: str, action: str, operator: str
) -> Approval:
    if action not in {"reset_fault", "restart"}:
        raise HTTPException(422, "Unknown intervention")
    lock(db)
    existing = db.scalar(select(Approval).where(Approval.key == key))
    if existing:
        if (existing.incident_id, existing.target, existing.action, existing.operator) != (
            incident_id,
            target,
            action,
            operator,
        ):
            raise HTTPException(409, "Idempotency key already identifies another request")
        return existing
    if not enabled(db):
        raise HTTPException(409, "Local recovery is disabled or stopped")
    incident = db.get(Incident, incident_id)
    if not incident or incident.closed_at:
        raise HTTPException(409, "Select an active incident")
    allowed = upstream(graph_edges(latest(db)), incident.service_slug) | {incident.service_slug}
    if target not in allowed:
        raise HTTPException(422, "Target must be the incident service or a configured upstream")
    approval = Approval(
        key=key,
        incident_id=incident_id,
        target=target,
        action=action,
        operator=operator,
        requested_at=datetime.now(UTC),
    )
    db.add(approval)
    db.flush()
    audit(
        db,
        operator,
        "requested",
        approval.id,
        action=action,
        target=target,
        incident_id=incident_id,
    )
    db.commit()
    return approval


def execute(db: Session, approval_id: int, operator: str) -> Execution:
    lock(db)
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    previous = db.get(Execution, approval.id)
    if previous:
        return previous
    now = datetime.now(UTC)
    resumed = db.get(ApplicationSetting, "recovery_resumed")
    incident = db.get(Incident, approval.incident_id)
    allowed = (
        upstream(graph_edges(latest(db)), incident.service_slug) | {incident.service_slug}
        if incident
        else set()
    )
    checks = [
        (not enabled(db), "Local recovery is disabled or stopped"),
        (now - approval.requested_at > APPROVAL_TTL, "Approval expired"),
        (
            bool(resumed and approval.requested_at < datetime.fromisoformat(resumed.value["at"])),
            "Approval predates the last emergency resume",
        ),
        (not incident or bool(incident.closed_at), "Incident already closed"),
        (approval.target not in allowed, "Target is no longer related to this incident"),
    ]
    for invalid, reason in checks:
        if invalid:
            audit(db, operator, "blocked", approval.id, reason=reason)
            db.commit()
            raise HTTPException(409, reason)
    executions = select(Execution).join(Approval).where(Approval.target == approval.target)
    active = db.scalar(
        executions.where(Execution.status == "verifying", Execution.deadline > now).limit(1)
    )
    recent = db.scalar(executions.where(Execution.started_at > now - COOLDOWN).limit(1))
    count = (
        db.scalar(
            select(func.count())
            .select_from(Execution)
            .join(Approval)
            .where(Approval.incident_id == approval.incident_id)
        )
        or 0
    )
    if active or recent or count >= MAX_ATTEMPTS:
        reason = "Target busy or cooling down, or incident attempt limit reached"
        audit(db, operator, "blocked", approval.id, reason=reason)
        db.commit()
        raise HTTPException(409, reason)
    fault = db.get(FaultConfiguration, approval.target, with_for_update=True)
    if fault is None:
        raise HTTPException(409, "Simulator fault state unavailable")
    approval.approved_at = now
    before = {"fault_mode": fault.mode, "latency_ms": fault.latency_ms}
    config = settings()
    timeout = min(
        300,
        max(
            10,
            config.max_backoff_seconds
            + (config.poll_seconds + config.timeout_seconds) * (config.recover_after + 1),
        ),
    )
    result = Execution(
        approval_id=approval.id,
        status="verifying",
        started_at=now,
        deadline=now + timedelta(seconds=timeout),
        evidence={"previous_fault": fault.mode},
    )
    db.add(result)
    audit(db, operator, "approved", approval.id, requested_by=approval.operator)
    if approval.action == "reset_fault":
        update_fault(db, fault, "healthy", 0, now)
    else:
        runtime = db.get(SimulatorRuntime, approval.target)
        restart_until = now + timedelta(seconds=2)
        if runtime:
            runtime.restarting_until = restart_until
        else:
            db.add(SimulatorRuntime(service_slug=approval.target, restarting_until=restart_until))
    audit(
        db,
        operator,
        "executed",
        approval.id,
        action=approval.action,
        target=approval.target,
        before=before,
        after={
            "fault_mode": fault.mode,
            "latency_ms": fault.latency_ms,
            "restart_seconds": 2 if approval.action == "restart" else 0,
        },
        deadline=result.deadline.isoformat(),
        previous_fault=fault.mode
        if approval.action == "restart"
        else result.evidence["previous_fault"],
    )
    db.commit()
    return result


def stop(db: Session, operator: str) -> None:
    lock(db)
    db.merge(ApplicationSetting(key="recovery_stop", value={"stopped": True}))
    audit(db, operator, "emergency_stop")
    db.commit()


def resume(db: Session, operator: str) -> None:
    lock(db)
    if not settings().recovery_enabled:
        raise HTTPException(409, "Local recovery is disabled by configuration")
    db.merge(ApplicationSetting(key="recovery_stop", value={"stopped": False}))
    # Pending pre-stop approvals cannot execute after an explicit resume.
    db.merge(
        ApplicationSetting(key="recovery_resumed", value={"at": datetime.now(UTC).isoformat()})
    )
    audit(db, operator, "emergency_resume")
    db.commit()


def verify(db: Session, check: HealthCheck) -> None:
    """Called in the same transaction as the monitoring observation."""
    rows = db.execute(
        select(Execution, Approval, Incident)
        .select_from(Execution)
        .join(Approval, Approval.id == Execution.approval_id)
        .join(Incident, Incident.id == Approval.incident_id)
        .where(
            Execution.status == "verifying",
            (Incident.service_slug == check.service_slug)
            | (Execution.deadline <= check.checked_at),
        )
        .with_for_update(of=Execution)
    ).all()
    for execution, approval, incident in rows:
        if check.checked_at <= execution.started_at:
            continue
        service = db.get(Service, approval.target)
        good = check.available and check.latency_ms < settings().degraded_ms
        status = (
            "failed"
            if check.checked_at >= execution.deadline
            else "succeeded"
            if good
            and service
            and service.state == "healthy"
            and incident.closed_at
            and incident.closed_at > execution.started_at
            else None
        )
        if status:
            execution.status = status
            execution.evidence = {
                **execution.evidence,
                "reason": "Verification deadline elapsed"
                if status == "failed"
                else "Incident closed and post-action health was confirmed",
                "check_id": check.id,
                "check_service": check.service_slug,
                "available": check.available,
                "status_code": check.status_code,
                "latency_ms": check.latency_ms,
                "verified_at": check.checked_at.isoformat(),
                "incident_closed_at": incident.closed_at.isoformat()
                if incident.closed_at
                else None,
            }
            audit(db, "monitoring-worker", status, approval.id, **execution.evidence)
