import json
import logging
from collections import Counter
from threading import Lock

from opentelemetry import metrics

log = logging.getLogger("cloudrescue.pipeline")
meter = metrics.get_meter("cloudrescue")
counter = meter.create_counter("cloudrescue.pipeline.events")
totals: Counter[tuple[str, str]] = Counter()
lock = Lock()


def event(stage: str, outcome: str) -> None:
    with lock:
        totals[stage, outcome] += 1
    counter.add(1, {"stage": stage, "outcome": outcome})
    log.info(json.dumps({"event": "pipeline", "stage": stage, "outcome": outcome}))


def snapshot():
    with lock:
        return [
            {"stage": stage, "outcome": outcome, "count": count}
            for (stage, outcome), count in sorted(totals.items())
        ]
