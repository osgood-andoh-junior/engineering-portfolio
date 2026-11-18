from dataclasses import asdict, dataclass
from itertools import groupby

from backend.config import SERVICES
from backend.diagnosis import Observation, diagnose
from backend.topology import DEFAULT_EDGES, Edges
from simulator.behavior import Faults, outcome

POLL = 5
THRESHOLD = 500
DOWN_AFTER = 3
WINDOW = 25


@dataclass(frozen=True)
class Scenario:
    title: str
    faults: Faults
    rounds: int
    expected: tuple[str, ...]


SCENARIOS = {
    "single": Scenario(
        "Single Storage connection failure", {"storage": ("disconnect", 0)}, 4, ("storage",)
    ),
    "latency": Scenario(
        "Sustained Messaging latency", {"messaging": ("latency", 1200)}, 4, ("messaging",)
    ),
    "cascade": Scenario(
        "Identity failure cascades to both dependents",
        {"identity": ("disconnect", 0)},
        4,
        ("identity",),
    ),
    "independent": Scenario(
        "Independent Messaging and Storage failures",
        {"messaging": ("error", 0), "storage": ("disconnect", 0)},
        4,
        ("messaging", "storage"),
    ),
    "spike": Scenario(
        "One temporary Messaging latency spike", {"messaging": ("latency", 800)}, 1, ()
    ),
}


def seeded(name: str) -> list[Observation]:
    scenario = SCENARIOS[name]
    normal = dict.fromkeys(SERVICES, ("healthy", 0))
    rows = []
    for step in range(7):
        faults = normal | scenario.faults if 1 <= step <= scenario.rounds else normal
        for service in SERVICES:
            mode, latency, parent = outcome(service, DEFAULT_EDGES, faults)
            code = {"disconnect": None, "dependency": 503, "error": 500}.get(mode, 200)
            rows.append(Observation(step * POLL, service, code == 200, latency + 10, code, parent))
    return rows


def replay(
    observations: list[Observation],
    edges: Edges,
    threshold: int = THRESHOLD,
    down_after: int = DOWN_AFTER,
    window: float = WINDOW,
) -> dict:
    ordered = sorted(observations, key=lambda item: item.time)
    seen: list[Observation] = []
    streaks: dict[str, int] = {}
    first_detection: dict[str, float] = {}
    first_diagnosis: dict[str, float] = {}
    predictions: dict[str, float] = {}
    frames = []
    for at, batch in groupby(ordered, key=lambda item: item.time):
        current = list(batch)
        for item in current:
            streaks[item.service] = 0 if item.available else streaks.get(item.service, 0) + 1
            if streaks[item.service] >= down_after:
                first_detection.setdefault(item.service, at)
        seen.extend(current)
        seen = [item for item in seen if item.time >= at - window]
        result = diagnose(seen, edges, threshold, window)
        for candidate in result["candidates"]:
            name = candidate["service"]
            first_diagnosis.setdefault(name, at)
            predictions[name] = max(predictions.get(name, 0), candidate["confidence"])
        frames.append({"time": at, "observations": [asdict(row) for row in current], **result})
    return {
        "frames": frames,
        "parameters": {
            "edges": edges,
            "degraded_ms": threshold,
            "down_after": down_after,
            "correlation_seconds": window,
        },
        "first_detection": first_detection,
        "first_diagnosis": first_diagnosis,
        "predictions": predictions,
    }


def scenario_result(name: str) -> dict:
    scenario = SCENARIOS[name]
    return {
        "title": scenario.title,
        "ground_truth": list(scenario.expected),
        "injected_faults": scenario.faults,
        "fault_started": POLL,
        **replay(seeded(name), DEFAULT_EDGES),
    }
