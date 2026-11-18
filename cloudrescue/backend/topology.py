from collections.abc import Iterable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.config import SERVICES
from backend.models import DependencyGraph

Edges = list[tuple[str, str]]
DEFAULT_EDGES: Edges = [("messaging", "identity"), ("storage", "identity")]


def upstream(edges: Edges, service: str) -> set[str]:
    found: set[str] = set()
    pending = [service]
    while pending:
        child = pending.pop()
        for dependent, parent in edges:
            if dependent == child and parent not in found:
                found.add(parent)
                pending.append(parent)
    return found


def validate(edges: Iterable[tuple[str, str]]) -> Edges:
    result = sorted(edges)
    if any(child not in SERVICES or parent not in SERVICES for child, parent in result):
        raise ValueError("Both endpoints must be local simulator services")
    if len(set(result)) != len(result):
        raise ValueError("Duplicate dependency")
    if any(service in upstream(result, service) for service in SERVICES):
        raise ValueError("Dependencies must be acyclic")
    return result


def latest(db: Session) -> DependencyGraph | None:
    return db.scalar(select(DependencyGraph).order_by(DependencyGraph.id.desc()).limit(1))


def publish(db: Session, edges: Iterable[tuple[str, str]], expected: int) -> DependencyGraph:
    normalized = validate(edges)
    db.execute(text("SELECT pg_advisory_xact_lock(726031023)"))
    current = latest(db)
    if (current.id if current else 0) != expected:
        raise LookupError("Graph changed. Refresh and retry.")
    if current and normalized == [tuple(edge) for edge in current.edges]:
        return current
    graph = DependencyGraph(edges=[list(edge) for edge in normalized])
    db.add(graph)
    db.flush()
    return graph


def graph_edges(graph: DependencyGraph | None) -> Edges:
    return [(child, parent) for child, parent in graph.edges] if graph else []
