import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict, replace
from pathlib import Path
from random import Random
from statistics import mean, median

from backend.policies import Parameters
from backend.recovery_lab import POLICIES, Frame, run_policy
from backend.topology import DEFAULT_EDGES

FAMILIES = (
    "network",
    "upstream",
    "cascade",
    "overload",
    "latency",
    "intermittent",
    "independent",
    "slow_recovery",
    "flapping",
    "partial_replicas",
)
PARTITIONS = {"development": 12, "validation": 6, "held_out": 6}
VERSION = "cloudrescue-phase4-model-1"
METRICS = (
    "request_success",
    "downtime_seconds",
    "mttd_seconds",
    "diagnosis_seconds",
    "mttr_seconds",
    "overhead_ms",
    "intervention_attempts",
    "failed_interventions",
    "harmful",
    "false_positive",
    "false_negative",
)


def workloads(master: int):
    for partition, count in PARTITIONS.items():
        for family in FAMILIES:
            for index in range(count):
                key = f"{VERSION}:{master}:{partition}:{family}:{index}"
                seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
                rng = Random(seed)
                start = rng.randint(4, 9)
                duration = rng.randint(5, 18)
                traffic = rng.randint(3, 11)
                primary, standby = rng.randint(9, 16), rng.randint(4, 10)
                burst = rng.randint(5, 17)
                latency = rng.randint(480, 930)
                chance = rng.uniform(0.15, 0.65)
                trace = []
                for tick in range(36):
                    age = tick - start
                    active = 0 <= age < duration
                    frame = Frame(
                        max(1, traffic + rng.randint(-2, 2)),
                        primary_capacity=primary,
                        standby_capacity=standby,
                    )
                    if family == "overload":
                        frame = replace(
                            frame,
                            traffic=frame.traffic + burst if active and age % 3 else frame.traffic,
                        )
                    elif active:
                        if family == "network":
                            frame = replace(frame, transient=True, transient_probability=chance)
                        elif family in {"upstream", "cascade"}:
                            frame = replace(frame, upstream=False, cascade=family == "cascade")
                        elif family == "latency":
                            frame = replace(frame, extra_latency_ms=latency)
                        elif family == "intermittent":
                            frame = replace(frame, primary=rng.random() > chance)
                        elif family == "independent":
                            frame = replace(
                                frame, primary=age % 4 < 2, standby=age % 5 < 2, independent=True
                            )
                        elif family == "slow_recovery":
                            frame = replace(
                                frame,
                                primary=age >= duration // 2,
                                primary_capacity=max(2, primary * age // duration),
                            )
                        elif family == "flapping":
                            frame = replace(frame, primary=age % 2 == 0)
                        elif family == "partial_replicas":
                            frame = replace(
                                frame,
                                primary_capacity=max(2, primary // 2),
                                standby_capacity=max(1, standby // 2),
                                standby=age % 3 != 0,
                                primary=age % 4 != 0,
                            )
                    trace.append(frame)
                yield partition, family, seed, trace


def measure(
    partition: str,
    family: str,
    seed: int,
    trace: list[Frame],
    policy: str,
    params: Parameters,
    baseline: dict | None = None,
) -> dict:
    result = run_policy(trace, policy, params, seed, DEFAULT_EDGES)
    reference = result if baseline is None else baseline
    impaired = 0
    expected = False
    for frame in trace:
        exogenous = (
            not frame.primary
            or not frame.upstream
            or frame.extra_latency_ms >= 500
            or frame.primary_capacity / frame.traffic < 0.9
            or (frame.transient and frame.transient_probability > 0.1)
        )
        impaired = impaired + 1 if exogenous else 0
        expected = expected or impaired >= 3
    detected = result["mttd_seconds"] is not None
    return {
        "partition": partition,
        "family": family,
        "seed": seed,
        **result,
        "harmful": result["request_success"] < reference["request_success"],
        "false_positive": detected if not expected else None,
        "false_negative": not detected if expected else None,
    }


def tune(data: list[tuple[str, str, int, list[Frame]]]) -> tuple[Parameters, list[dict]]:
    if any(partition == "held_out" for partition, *_ in data):
        raise ValueError("Held-out data cannot be used for tuning")
    default = Parameters()
    rng = Random(410)
    candidates = [default] + [
        Parameters(
            failure_threshold=rng.choice((2, 4, 8)),
            retry_budget=rng.choice((8, 20, 40)),
            retry_base_ms=rng.choice((30, 80, 160)),
            rate=rng.choice((9, 12, 16, 20)),
            failover_health_ticks=rng.choice((1, 2, 3)),
        )
        for _ in range(10)
    ]
    scores = []
    for index, params in enumerate(candidates):
        dev = [
            run_policy(trace, "combined", params, seed, DEFAULT_EDGES)["request_success"]
            for part, _, seed, trace in data
            if part == "development"
        ]
        scores.append({"index": index, "development": mean(dev), "parameters": params.model_dump()})
    finalists = sorted(scores, key=lambda row: (-row["development"], row["index"]))[:3]
    for row in finalists:
        params = candidates[row["index"]]
        row["validation"] = mean(
            run_policy(trace, "combined", params, seed, DEFAULT_EDGES)["request_success"]
            for part, _, seed, trace in data
            if part == "validation"
        )
    winner = max(finalists, key=lambda row: (row["validation"], -row["index"]))
    return candidates[winner["index"]], scores


def statistics(values: list[float], seed: int = 151, groups: list[str] | None = None) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    rng = Random(seed)
    strata: dict[str, list[float]] = {}
    for group, value in zip(groups or ["all"] * len(values), values, strict=True):
        strata.setdefault(group, []).append(value)
    samples = sorted(
        sum(sum(rng.choices(group, k=len(group))) for group in strata.values()) / len(values)
        for _ in range(600)
    )
    return {
        "n": len(values),
        "mean": mean(values),
        "median": median(values),
        "p05": ordered[int(0.05 * (len(values) - 1))],
        "p95": ordered[int(0.95 * (len(values) - 1))],
        "ci95": [samples[15], samples[584]],
    }


def benchmark(master: int = 42) -> dict:
    data = list(workloads(master))
    tuned, tuning = tune([item for item in data if item[0] != "held_out"])
    raw = []
    for part, family, seed, trace in data:
        baseline = measure(part, family, seed, trace, "baseline", Parameters())
        raw.append(baseline)
        for policy in (*tuple(POLICIES)[1:], "tuned"):
            row = measure(
                part,
                family,
                seed,
                trace,
                "combined" if policy == "tuned" else policy,
                tuned if policy == "tuned" else Parameters(),
                baseline,
            )
            raw.append(
                {
                    **row,
                    "policy": policy,
                    "paired_success_delta": row["request_success"] - baseline["request_success"],
                }
            )
    summary = {}
    for policy in (*POLICIES, "tuned"):
        rows = [row for row in raw if row["partition"] == "held_out" and row["policy"] == policy]
        summary[policy] = {
            metric: statistics(
                [float(row[metric]) for row in rows if row.get(metric) is not None],
                groups=[row["family"] for row in rows if row.get(metric) is not None],
            )
            for metric in (*METRICS, "paired_success_delta")
        }
    return {
        "version": VERSION,
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "architecture": platform.machine(),
        },
        "master_seed": master,
        "distribution_per_family": PARTITIONS,
        "families": FAMILIES,
        "trial_count": len(data),
        "configuration": {"duration_seconds": 36, "bootstrap_resamples": 600},
        "policy_versions": {"default": Parameters().model_dump(), "tuned": tuned.model_dump()},
        "tuning": tuning,
        "held_out": summary,
        "raw": raw,
        "workloads": [
            {
                "partition": part,
                "family": family,
                "seed": str(seed),
                "frames": [asdict(frame) for frame in trace],
            }
            for part, family, seed, trace in data
        ],
    }


def csv_rows(result: dict):
    return [
        {
            **{key: value for key, value in row.items() if key != "series"},
            "series": json.dumps(row["series"], separators=(",", ":")),
        }
        for row in result["raw"]
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    rows = csv_rows(result)
    with (args.output / "benchmark.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"trials": result["trial_count"], "held_out": result["held_out"]}, indent=2))
