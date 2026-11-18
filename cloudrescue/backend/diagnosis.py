from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, TypedDict

from backend.topology import Edges, upstream


@dataclass(frozen=True)
class Observation:
    time: float
    service: str
    available: bool
    latency_ms: float
    status_code: int | None = None
    blocked_by: str | None = None
    check_id: int | None = None


class Candidate(TypedDict):
    service: str
    confidence: float
    symptoms: list[str]
    reason: str
    evidence: list[dict[str, Any]]
    possible_cascade: list[str]


def diagnose(
    observations: list[Observation],
    edges: Edges,
    threshold: int,
    window: float,
    anchor: str | None = None,
) -> dict:
    latest: dict[str, Observation] = {}
    onset: dict[str, float] = {}
    for item in sorted(observations, key=lambda item: item.time):
        latest[item.service] = item
        if not item.available or item.latency_ms >= threshold:
            onset.setdefault(item.service, item.time)
        else:
            onset.pop(item.service, None)
    if not onset or (anchor is not None and anchor not in onset):
        return {"status": "insufficient_evidence", "candidates": [], "affected": sorted(onset)}
    if anchor is not None:
        onset = {name: at for name, at in onset.items() if abs(at - onset[anchor]) <= window}

    links: dict[str, list[str]] = defaultdict(list)
    unresolved: set[str] = set()
    for name in sorted(onset):
        parent = latest[name].blocked_by
        ancestors = upstream(edges, name)
        if parent:
            if (
                parent in onset
                and parent in ancestors
                and abs(onset[parent] - onset[name]) <= window
            ):
                links[parent].append(name)
            else:
                unresolved.add(name)
    candidates: list[Candidate] = []
    for name in sorted(onset):
        item = latest[name]
        if name in unresolved or item.blocked_by:
            continue
        symptoms = links[name]
        # A lone slow sample cannot distinguish a spike from sustained degradation.
        evidence = [
            sample
            for sample in observations
            if sample.service == name
            and sample.time >= onset[name]
            and (not sample.available or sample.latency_ms >= threshold)
        ]
        if item.available and len(evidence) < 2:
            continue
        # A generic 503 with no causal marker may be shared infrastructure failure.
        if item.status_code == 503:
            continue
        confidence = 0.95 if symptoms else 0.75 if len(evidence) >= 2 else 0.60
        candidates.append(
            {
                "service": name,
                "confidence": confidence,
                "symptoms": symptoms,
                "reason": (
                    "Dependent probes reported this upstream service as blocking their responses."
                    if symptoms
                    else "Repeated abnormal probes at this service."
                    if len(evidence) >= 2
                    else "A direct failure was observed at this service."
                ),
                "evidence": [asdict(latest[key]) for key in [name, *symptoms]],
                "possible_cascade": sorted(
                    {child for child, _ in edges if name in upstream(edges, child)}
                ),
            }
        )
    candidates.sort(key=lambda candidate: (-candidate["confidence"], candidate["service"]))
    return {
        "status": "suspected" if candidates else "insufficient_evidence",
        "candidates": candidates,
        "affected": sorted(onset),
    }
