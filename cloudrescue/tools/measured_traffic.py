"""Collect bounded HTTP evidence from a privately started CloudRescue listener."""

import argparse
import asyncio
import json
import platform
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from random import Random
from statistics import mean, stdev
from time import perf_counter

import httpx
from cloudrescue_traces import Frame as TraceFrame
from cloudrescue_traces import load

from backend.policies import Breaker, Bucket, Parameters, Retries
from backend.recovery_lab import Frame, run_policy
from simulator.main import respond

POLICIES = ("baseline", "retry", "breaker", "limit")
LATENCY_MS = 750
MAX_CONCURRENCY = 4


async def measure(trace: list[TraceFrame], seed: int, policy: str) -> dict:
    params = Parameters()
    breaker = Breaker(params.failure_threshold, params.breaker_cooldown)
    bucket = Bucket(params.rate, params.burst)
    retry = Retries(params.retry_budget, params.retry_limit, params.retry_base_ms, Random(seed))
    mode = "healthy"

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await respond(
            "messaging",
            reader,
            writer,
            lambda _: (mode, LATENCY_MS if mode == "latency" else 0, None, 1),
        )

    rows: list[dict] = []
    limiter = asyncio.Semaphore(MAX_CONCURRENCY)
    started_at = datetime.now(UTC).isoformat()
    async with await asyncio.start_server(handler, "127.0.0.1", 0) as server:
        assert server.sockets is not None
        port = server.sockets[0].getsockname()[1]
        async with httpx.AsyncClient(
            trust_env=False,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=MAX_CONCURRENCY),
        ) as client:
            origin = perf_counter()

            async def request(tick: int, index: int, traffic: int) -> dict:
                scheduled = origin + tick + 0.3 * index / traffic
                await asyncio.sleep(max(0, scheduled - perf_counter()))
                now = perf_counter()
                if policy == "limit" and not bucket.admit(now - origin):
                    return {
                        "success": False,
                        "latency_ms": 0,
                        "attempts": 0,
                        "error": "rate_limited",
                    }
                if policy == "breaker" and not breaker.admit(now - origin):
                    return {
                        "success": False,
                        "latency_ms": 0,
                        "attempts": 0,
                        "error": "breaker_open",
                    }
                deadline = scheduled + params.deadline_ms / 1000
                attempts = 0
                status = None
                error = None
                try:
                    async with asyncio.timeout(max(0, deadline - perf_counter())):
                        while True:
                            async with limiter:
                                attempts += 1
                                try:
                                    response = await client.get(
                                        f"http://127.0.0.1:{port}/health", timeout=None
                                    )
                                    status = response.status_code
                                    error = None if response.is_success else "http_status"
                                except httpx.TransportError:
                                    error = "connection"
                            if policy != "retry":
                                break
                            delay = retry.delay(
                                attempts - 1,
                                (deadline - perf_counter()) * 1000,
                                error == "connection",
                                index % 5 != 0,
                            )
                            if delay is None:
                                break
                            await asyncio.sleep(delay / 1000)
                except TimeoutError:
                    error = "deadline"
                elapsed = (perf_counter() - now) * 1000
                if policy == "breaker":
                    breaker.record(perf_counter() - origin, error is None)
                return {
                    "success": error is None,
                    "latency_ms": elapsed,
                    "status": status,
                    "attempts": attempts,
                    "error": error,
                }

            for tick, frame in enumerate(trace):
                await asyncio.sleep(max(0, origin + tick - perf_counter()))
                mode = frame.fault
                responses = await asyncio.gather(
                    *(request(tick, index, frame.requests) for index in range(frame.requests))
                )
                success = sum(row["success"] for row in responses)
                rows.append(
                    {
                        "second": tick,
                        "observed_at": datetime.now(UTC).isoformat(),
                        "fault": mode,
                        "success": success,
                        "requests": frame.requests,
                        "responses": responses,
                    }
                )
            await asyncio.sleep(max(0, origin + len(trace) - perf_counter()))

    successes = sum(row["success"] for row in rows)
    requests = sum(row["requests"] for row in rows)
    responses = [item for row in rows for item in row["responses"]]
    latency = sorted(item["latency_ms"] for item in responses if item["attempts"])
    impaired = [row["second"] for row in rows if row["success"] / row["requests"] < 0.9]
    recovery = next(
        (
            row["second"]
            for row in rows
            if impaired and row["second"] > impaired[-1] and row["success"] == row["requests"]
        ),
        None,
    )
    return {
        "started_at": started_at,
        "request_success": successes / requests,
        "error_rate": 1 - successes / requests,
        "throughput_success_per_second": successes / len(rows),
        "p95_latency_ms": latency[int(0.95 * (len(latency) - 1))] if latency else None,
        "downtime_seconds": len(impaired),
        "first_impaired_second": impaired[0] if impaired else None,
        "recovered_second": recovery,
        "series": rows,
    }


def summarize(rows: list[dict], metric: str) -> dict:
    predicted = [row["modeled"][metric] for row in rows]
    observed = [row["measured"][metric] for row in rows]
    errors = [guess - actual for guess, actual in zip(predicted, observed, strict=True)]
    absolute_percent = [
        abs(error) / actual * 100 for error, actual in zip(errors, observed, strict=True) if actual
    ]
    return {
        "predicted_mean": mean(predicted),
        "observed_mean": mean(observed),
        "bias": mean(errors),
        "mean_absolute_error": mean(map(abs, errors)),
        "mean_absolute_percentage_error": mean(absolute_percent) if absolute_percent else None,
        "percentage_samples": len(absolute_percent),
        "observed_sd": stdev(observed),
        "paired_error_sd": stdev(errors),
    }


def ranking_agreement(summary: dict) -> dict[str, int]:
    counts = {"agree": 0, "opposite": 0, "tie_mismatch": 0}
    for left, right in combinations(summary, 2):
        a = summary[left]["request_success"]
        b = summary[right]["request_success"]
        predicted = a["predicted_mean"] - b["predicted_mean"]
        observed = a["observed_mean"] - b["observed_mean"]
        signs = tuple(
            0 if abs(value) < 1e-12 else (1 if value > 0 else -1) for value in (predicted, observed)
        )
        key = "agree" if signs[0] == signs[1] else "tie_mismatch" if 0 in signs else "opposite"
        counts[key] += 1
    return counts


async def experiment(trace: list[TraceFrame], seeds: tuple[int, ...]) -> dict:
    rows = []
    for seed in seeds:
        for policy in POLICIES:
            measured = await asyncio.wait_for(measure(trace, seed, policy), timeout=len(trace) + 3)
            model = [
                Frame(
                    frame.requests,
                    primary=frame.fault not in {"error", "disconnect"},
                    extra_latency_ms=LATENCY_MS if frame.fault == "latency" else 0,
                )
                for frame in trace
            ]
            modeled = run_policy(model, policy, Parameters(), seed, [])
            rows.append({"seed": seed, "policy": policy, "measured": measured, "modeled": modeled})
    summary = {
        policy: {
            metric: summarize([row for row in rows if row["policy"] == policy], metric)
            for metric in ("request_success", "downtime_seconds")
        }
        for policy in POLICIES
    }
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "policies": list(POLICIES),
        "seeds": seeds,
        "summary": summary,
        "success_ranking_pairs": ranking_agreement(summary),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace = load(args.trace)
    result = asyncio.run(experiment(trace, (42, 77, 103)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
