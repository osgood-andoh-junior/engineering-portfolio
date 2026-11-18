import json
from dataclasses import dataclass
from random import Random
from statistics import mean
from typing import Any

from backend.diagnosis import Observation, diagnose
from backend.policies import Breaker, Bucket, Failover, Parameters, Retries
from backend.topology import DEFAULT_EDGES, Edges, upstream

POLICIES = {
    "baseline": (),
    "retry": ("retry",),
    "breaker": ("breaker",),
    "limit": ("limit",),
    "failover": ("failover",),
    "combined": ("limit", "failover", "breaker", "retry"),
}
SCENARIOS = ("primary", "upstream", "overload", "transient", "healthy_burst", "replay")
TICKS = 36


@dataclass(frozen=True)
class Frame:
    traffic: int
    primary: bool = True
    standby: bool = True
    upstream: bool = True
    transient: bool = False
    transient_probability: float = 0.32
    extra_latency_ms: int = 0
    primary_capacity: int = 12
    standby_capacity: int = 7
    cascade: bool = True
    independent: bool = False


def frames(scenario: str, edges: Edges, replay: dict[str, Any] | None = None) -> list[Frame]:
    if scenario == "replay":
        assert replay is not None
        source = replay["frames"]
        if not source:
            raise ValueError("Replay has no observations")
        origin = float(source[0]["time"])
        latest: dict[str, bool] = {}
        cursor = 0
        result = []
        for tick in range(TICKS):
            while cursor < len(source) and float(source[cursor]["time"]) - origin <= tick:
                for row in source[cursor]["observations"]:
                    # Explicitly blocked dependents do not imply a failed primary.
                    latest[row["service"]] = bool(row["available"] or row["blocked_by"])
                cursor += 1
            result.append(
                Frame(
                    8,
                    primary=latest.get("messaging", True),
                    upstream=all(
                        latest.get(parent, True) for parent in upstream(edges, "messaging")
                    ),
                )
            )
        return result
    rows = []
    for tick in range(TICKS):
        fault = 6 <= tick < 20
        rows.append(
            Frame(
                traffic=(22 if fault else 8)
                if scenario == "overload"
                else 11
                if scenario == "healthy_burst"
                else 8,
                primary=not (fault and scenario == "primary"),
                upstream=not (fault and scenario == "upstream"),
                transient=fault and scenario == "transient",
            )
        )
    return rows


def run_policy(
    trace: list[Frame], policy: str, params: Parameters, seed: int, edges: Edges
) -> dict:
    options = POLICIES[policy]
    retries = Retries(params.retry_budget, params.retry_limit, params.retry_base_ms, Random(seed))
    bucket = Bucket(params.rate, params.burst)
    failover = Failover(params.failover_cooldown, params.failover_health_ticks)
    breakers = [Breaker(params.failure_threshold, params.breaker_cooldown) for _ in range(2)]
    arrivals = successes = attempts = retries_sent = rejected = switches = 0
    overhead = 0.0
    failed_retries = 0
    bins = []
    observations: list[Observation] = []
    detected = diagnosed = onset = recovered = None
    bad_streak = good_streak = 0
    has_upstream = bool(upstream(edges, "messaging"))
    for tick, frame in enumerate(trace):
        dependency_ok = frame.upstream or not has_upstream
        capacity = [frame.primary_capacity, frame.standby_capacity]
        previous = failover.standby
        standby = int(
            "failover" in options
            and failover.route(
                tick, frame.primary and dependency_ok, frame.standby and dependency_ok
            )
        )
        switches += int(bool(standby) != previous)
        breaker = breakers[standby]
        tick_success = 0
        for request in range(frame.traffic):
            arrivals += 1
            at = tick + request / frame.traffic
            if ("limit" in options and not bucket.admit(at)) or (
                "breaker" in options and not breaker.admit(at)
            ):
                rejected += 1
                continue
            elapsed = 0.0
            used = 0
            rng = Random(seed * 1_000_003 + tick * 101 + request)
            while True:
                attempts += 1
                duration = min(
                    40 + frame.extra_latency_ms + 15 * max(0, 12 - capacity[standby]),
                    params.deadline_ms - elapsed,
                )
                elapsed += duration
                healthy = (frame.standby if standby else frame.primary) and dependency_ok
                ok = (
                    healthy
                    and capacity[standby] > 0
                    and elapsed < params.deadline_ms
                    and not (frame.transient and rng.random() < frame.transient_probability)
                )
                capacity[standby] -= 1
                if "breaker" in options:
                    breaker.record(at, ok)
                if ok:
                    successes += 1
                    tick_success += 1
                    break
                delay = (
                    retries.delay(
                        used,
                        params.deadline_ms
                        - elapsed
                        - (40 + frame.extra_latency_ms + 15 * max(0, 12 - capacity[standby])),
                        transient=healthy and frame.transient and capacity[standby] > 0,
                        safe=request % 5 != 0,
                    )
                    if "retry" in options
                    else None
                )
                if delay is None:
                    failed_retries += int(used > 0)
                    break
                if "breaker" in options and not breaker.admit(at):
                    retries.budget += 1
                    break
                used += 1
                retries_sent += 1
                elapsed += delay
                overhead += delay
        success_rate = tick_success / frame.traffic
        bad = success_rate < 0.9
        bad_streak = bad_streak + 1 if bad else 0
        good_streak = 0 if bad else good_streak + 1
        if bad and onset is None:
            onset = tick
        if not bad and detected is None:
            onset = None
        if bad_streak >= 3 and detected is None:
            detected = tick
        if detected is not None and good_streak >= 3 and recovered is None:
            recovered = tick
        parent = min(upstream(edges, "messaging")) if has_upstream and not dependency_ok else None
        observations.append(
            Observation(
                tick,
                "messaging",
                not bad,
                40 + frame.extra_latency_ms,
                503 if parent else None,
                parent if frame.cascade else None,
            )
        )
        if parent:
            observations.append(Observation(tick, parent, False, 40, None))
        if frame.independent:
            observations.append(Observation(tick, "storage", frame.standby, 40, None))
        if (
            detected is not None
            and diagnosed is None
            and diagnose(observations[-8:], edges, 500, 5, "messaging")["candidates"]
        ):
            diagnosed = tick
        bins.append({"second": tick, "success_rate": success_rate})
    errors = arrivals - successes
    return {
        "policy": policy,
        "requests": arrivals,
        "successful_requests": successes,
        "request_success": successes / arrivals,
        "downtime_seconds": sum(item["success_rate"] < 0.9 for item in bins),
        "mttd_seconds": detected - onset if detected is not None and onset is not None else None,
        "diagnosis_seconds": diagnosed - onset
        if diagnosed is not None and onset is not None
        else None,
        "mttr_seconds": recovered - onset if recovered is not None and onset is not None else None,
        "recovered": recovered is not None if detected is not None else None,
        "error_budget_consumption": errors / (arrivals * 0.01),
        "upstream_attempts": attempts,
        "intervention_attempts": retries_sent + switches,
        "retry_attempts": retries_sent,
        "switches": switches,
        "rejected": rejected,
        "overhead_ms": round(overhead, 3),
        "failed_interventions": failed_retries,
        "series": bins,
    }


def compare(
    scenario: str, params: Parameters, seed: int, replay: dict[str, Any] | None = None
) -> list[dict]:
    edges = (
        [tuple(edge) for edge in replay["parameters"]["edges"]]
        if (replay and "parameters" in replay)
        else DEFAULT_EDGES
    )
    trace = frames(scenario, edges, replay)
    results = [run_policy(trace, policy, params, seed, edges) for policy in POLICIES]
    baseline = results[0]["request_success"]
    for result in results:
        result["harmful"] = result["request_success"] < baseline
    return results


def benchmark(seed: int = 42) -> dict:
    suites = {scenario: compare(scenario, Parameters(), seed) for scenario in SCENARIOS[:-1]}
    summaries = {}
    for index, policy in enumerate(POLICIES):
        rows = [suite[index] for suite in suites.values()]
        summaries[policy] = {
            metric: mean(values)
            if (values := [row[metric] for row in rows if row[metric] is not None])
            else None
            for metric in ("mttd_seconds", "diagnosis_seconds", "mttr_seconds", "recovered")
        }
        summaries[policy].update(
            {
                "request_success": sum(row["successful_requests"] for row in rows)
                / sum(row["requests"] for row in rows),
                "downtime_seconds": sum(row["downtime_seconds"] for row in rows),
                "harmful_scenarios": sum(row["harmful"] for row in rows),
            }
        )
    return {"modeled": True, "seed": seed, "summary": summaries, "scenarios": suites}


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
