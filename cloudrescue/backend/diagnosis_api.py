from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api_support import DB, update_fault
from backend.config import SERVICES, settings
from backend.diagnosis import Observation, diagnose
from backend.evaluation import evaluate
from backend.identity import require_admin, require_operator
from backend.models import (
    DependencyGraph,
    FaultConfiguration,
    FaultEvent,
    HealthCheck,
    Incident,
    ReplaySession,
)
from backend.replay import SCENARIOS, replay, scenario_result
from backend.telemetry import event
from backend.topology import DEFAULT_EDGES, graph_edges, latest, publish

router = APIRouter()
Slug = Literal["identity", "messaging", "storage"]


class GraphChange(BaseModel):
    expected_version: Annotated[int, Field(ge=0)]
    edges: Annotated[list[tuple[Slug, Slug]], Field(max_length=6)]


class ReplayRequest(BaseModel):
    source: Literal["single", "latency", "cascade", "independent", "spike", "incident"]
    incident_id: Annotated[int, Field(gt=0)] | None = None


def graph_view(graph: DependencyGraph):
    return {
        "version": graph.id,
        "created_at": graph.created_at,
        "edges": graph.edges,
        "services": list(SERVICES),
    }


@router.get("/dependencies")
def dependencies(db: DB):
    graph = latest(db)
    if graph is None:
        raise HTTPException(404, "Graph unavailable")
    return graph_view(graph)


@router.get("/dependencies/{version}")
def graph_version(version: int, db: DB):
    graph = db.get(DependencyGraph, version)
    if graph is None:
        raise HTTPException(404, "Graph version not found")
    return graph_view(graph)


@router.put("/dependencies", dependencies=[Depends(require_admin)])
def change_graph(payload: GraphChange, db: DB):
    try:
        graph = publish(db, payload.edges, payload.expected_version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return graph_view(graph)


def incident_evidence(db: DB, incident_id: int, *, include_recovery: bool = False):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    config = settings()
    window = (
        max(config.max_backoff_seconds, config.poll_seconds * config.down_after)
        + config.poll_seconds
    )
    start = incident.started_at - timedelta(seconds=window)
    end = incident.detected_at + timedelta(seconds=window)
    if include_recovery:
        end = min(
            incident.closed_at + timedelta(microseconds=1)
            if incident.closed_at
            else datetime.now(UTC),
            incident.detected_at + timedelta(minutes=15),
        )
    elif incident.recovery_started_at:
        end = min(end, incident.recovery_started_at)
    first = db.scalar(
        select(HealthCheck)
        .where(
            HealthCheck.service_slug == incident.service_slug,
            HealthCheck.checked_at == incident.started_at,
            HealthCheck.available.is_(False),
        )
        .order_by(HealthCheck.id)
        .limit(1)
    )
    graph = db.get(DependencyGraph, first.graph_id) if first and first.graph_id else None
    rows = db.scalars(
        select(HealthCheck)
        .where(
            HealthCheck.graph_id == (graph.id if graph else None),
            HealthCheck.checked_at >= start,
            HealthCheck.checked_at < end,
        )
        .order_by(HealthCheck.checked_at, HealthCheck.id)
    )
    observations = [
        Observation(
            (row.checked_at - incident.started_at).total_seconds(),
            row.service_slug,
            row.available,
            row.latency_ms,
            row.status_code,
            row.blocked_by,
            row.id,
        )
        for row in rows
    ]
    events = db.scalars(
        select(FaultEvent)
        .where(FaultEvent.occurred_at <= incident.started_at)
        .distinct(FaultEvent.service_slug)
        .order_by(FaultEvent.service_slug, FaultEvent.occurred_at.desc(), FaultEvent.id.desc())
    )
    ground_truth = [
        {
            "service": event.service_slug,
            "mode": event.mode,
            "occurred_at": event.occurred_at.isoformat(),
        }
        for event in events
        if event.mode != "healthy"
        and (event.expires_at is None or event.expires_at > incident.started_at)
    ]
    metadata = {
        "incident_id": incident.id,
        "origin": incident.started_at.isoformat(),
        "graph_version": graph.id if graph else None,
        "ground_truth": ground_truth,
        "title": f"Recorded incident #{incident.id}",
    }
    return incident, observations, graph_edges(graph), window, metadata


@router.get("/incidents/{incident_id}/diagnosis")
def incident_diagnosis(incident_id: int, db: DB):
    incident, observations, edges, window, metadata = incident_evidence(db, incident_id)
    # Select the last frame in the opening episode where the incident service was down.
    # The versioned input and deterministic computation require no duplicate correlation rows.
    if metadata["graph_version"] is None:
        event("diagnosis", "insufficient_evidence")
        return {**metadata, "status": "insufficient_evidence", "candidates": [], "affected": []}
    for at in sorted(
        {
            item.time
            for item in observations
            if item.service == incident.service_slug and not item.available and item.time >= 0
        },
        reverse=True,
    ):
        result = diagnose(
            [row for row in observations if row.time <= at],
            edges,
            settings().degraded_ms,
            window,
            incident.service_slug,
        )
        if result["candidates"]:
            event("diagnosis", "suspected")
            return {**metadata, **result}
    return {
        **metadata,
        "status": "insufficient_evidence",
        "candidates": [],
        "affected": [incident.service_slug],
    }


@router.get("/scenarios")
def list_scenarios():
    return [{"id": name, "title": scenario.title} for name, scenario in SCENARIOS.items()]


@router.get("/scenarios/{scenario}")
def scenario_preview(scenario: str):
    if scenario not in SCENARIOS:
        raise HTTPException(404, "Scenario not found")
    return scenario_result(scenario)


@router.get("/evaluation")
def diagnostic_evaluation():
    return evaluate()


@router.post("/scenarios/{scenario}/run", dependencies=[Depends(require_operator)], status_code=201)
def run_scenario(scenario: str, db: DB):
    definition = SCENARIOS.get(scenario)
    if definition is None:
        raise HTTPException(404, "Scenario not found")
    if graph_edges(latest(db)) != DEFAULT_EDGES:
        raise HTTPException(409, "Restore the default dependency graph before running scenarios")
    config = settings()
    period = config.poll_seconds
    duration = (
        min(period / 2, 2)
        if scenario == "spike"
        else period * max(definition.rounds, config.down_after + 1)
    )
    if duration > 300:
        raise HTTPException(409, "Scenario duration exceeds the five-minute local limit")
    rows = list(
        db.scalars(
            select(FaultConfiguration).order_by(FaultConfiguration.service_slug).with_for_update()
        )
    )
    now = datetime.now(UTC)
    if len(rows) != len(SERVICES) or any(
        row.mode != "healthy" and (row.expires_at is None or row.expires_at > now) for row in rows
    ):
        raise HTTPException(409, "Restore existing faults before running a scenario")
    if any(
        mode == "latency" and not config.degraded_ms <= latency < config.timeout_seconds * 1000
        for mode, latency in definition.faults.values()
    ):
        raise HTTPException(409, "Monitoring thresholds do not support this scenario's latency")
    expires_at = now + timedelta(seconds=duration)
    for row in rows:
        if row.service_slug in definition.faults:
            mode, latency = definition.faults[row.service_slug]
            update_fault(db, row, mode, latency, now, expires_at)
    db.commit()
    return {
        "id": scenario,
        "started_at": now,
        "expires_at": expires_at,
        "injected_faults": definition.faults,
    }


@router.get("/replays")
def replay_list(db: DB):
    return [
        {
            "id": row.id,
            "source": row.source,
            "title": row.payload["title"],
            "created_at": row.created_at,
        }
        for row in db.scalars(select(ReplaySession).order_by(ReplaySession.id.desc()).limit(100))
    ]


@router.get("/replays/{replay_id}")
def replay_detail(replay_id: int, db: DB):
    row = db.get(ReplaySession, replay_id)
    if row is None:
        raise HTTPException(404, "Replay not found")
    return {"id": row.id, "source": row.source, **row.payload}


@router.post("/replays", dependencies=[Depends(require_operator)], status_code=201)
def create_replay(payload: ReplayRequest, db: DB):
    if (payload.source == "incident") != (payload.incident_id is not None):
        raise HTTPException(422, "Provide an incident ID only for recorded replay")
    if payload.incident_id is not None:
        _, observations, edges, window, metadata = incident_evidence(
            db, payload.incident_id, include_recovery=True
        )
        if metadata["graph_version"] is None:
            raise HTTPException(409, "Incident predates versioned observations")
        config = settings()
        result = {
            **metadata,
            **replay(observations, edges, config.degraded_ms, config.down_after, window),
        }
    else:
        result = scenario_result(payload.source)
    row = ReplaySession(source=payload.source, payload=result)
    db.add(row)
    db.commit()
    return {"id": row.id, "source": row.source, **row.payload}
