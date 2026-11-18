from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.models import HealthCheck, Incident, IncidentEvent, Service


def record(db: Session, check: HealthCheck, config: Settings) -> str:
    service = db.get(Service, check.service_slug, with_for_update=True)
    if service is None:
        raise ValueError("Service has not been seeded")
    incident = db.scalar(
        select(Incident).where(Incident.service_slug == service.slug, Incident.closed_at.is_(None))
    )
    now = check.checked_at
    slow = check.available and check.latency_ms >= config.degraded_ms
    events: list[str] = []
    if check.available:
        service.last_success_at = now
        service.consecutive_failures = 0
        service.failure_started_at = None
    else:
        if not service.consecutive_failures:
            service.failure_started_at = now
        service.consecutive_failures += 1

    if incident is None:
        service.state = "degraded" if slow or not check.available else "healthy"
        if service.consecutive_failures >= config.down_after:
            assert service.failure_started_at is not None
            incident = Incident(
                service_slug=service.slug, started_at=service.failure_started_at, detected_at=now
            )
            db.add(incident)
            service.state = "down"
            events.append("outage_detected")
    elif not check.available or slow:
        if service.recovery_streak:
            events.append("recovery_interrupted")
        service.recovery_streak = 0
        incident.recovery_started_at = None
        service.state = "degraded" if slow else "down"
    else:
        if not service.recovery_streak:
            incident.recovery_started_at = now
            events.append("recovery_started")
        service.recovery_streak += 1
        service.state = "recovering"
        if service.recovery_streak >= config.recover_after:
            incident.closed_at = now
            service.state = "healthy"
            service.recovery_streak = 0
            events.append("recovery_confirmed")

    db.add(check)
    if events and incident is not None:
        db.flush()
        if events[0] == "outage_detected":
            first = db.scalar(
                select(HealthCheck.id)
                .where(
                    HealthCheck.service_slug == service.slug,
                    HealthCheck.checked_at == incident.started_at,
                    HealthCheck.available.is_(False),
                )
                .order_by(HealthCheck.id)
                .limit(1)
            )
            if first is not None:
                db.add(
                    IncidentEvent(
                        incident_id=incident.id,
                        check_id=first,
                        occurred_at=incident.started_at,
                        kind="outage_started",
                    )
                )
        for event in events:
            db.add(
                IncidentEvent(
                    incident_id=incident.id, check_id=check.id, occurred_at=now, kind=event
                )
            )
    return service.state
