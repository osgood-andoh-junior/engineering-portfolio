import asyncio
import json
import logging
from datetime import UTC, datetime
from time import perf_counter

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import SERVICES, Settings, settings
from backend.db import database_engine
from backend.detection import record
from backend.models import HealthCheck
from backend.recovery_control import verify
from backend.telemetry import event
from backend.topology import latest

LOG = logging.getLogger("cloudrescue.worker")
LOCK_ID = 726031022


async def probe(client: httpx.AsyncClient, slug: str, config: Settings) -> HealthCheck:
    started = perf_counter()
    checked_at = datetime.now(UTC)
    code = None
    error = None
    graph_id = None
    blocked_by = None
    try:
        async with asyncio.timeout(config.timeout_seconds):
            response = await client.get(config.target(slug))
        code = response.status_code
        version = response.headers.get("X-CloudRescue-Graph", "")
        if version.isascii() and version.isdecimal() and len(version) <= 9:
            graph_id = int(version)
        parent = response.headers.get("X-CloudRescue-Blocked-By")
        if code == 503 and parent in SERVICES:
            blocked_by = parent
        if not response.is_success:
            error = "http_status"
    except (TimeoutError, httpx.TimeoutException):
        error = "timeout"
    except httpx.RequestError:
        error = "connection"
    return HealthCheck(
        service_slug=slug,
        checked_at=checked_at,
        status_code=code,
        latency_ms=(perf_counter() - started) * 1000,
        available=error is None,
        error=error,
        graph_id=graph_id,
        blocked_by=blocked_by,
    )


async def run(config: Settings) -> None:
    # The physical connection owns the advisory lock and performs every write.
    with database_engine().connect() as connection:
        if not connection.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": LOCK_ID}):
            LOG.warning('{"event":"worker_skipped","reason":"database lock already held"}')
            return
        connection.commit()
        try:
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
                semaphore = asyncio.Semaphore(config.max_concurrency)

                async def poll(slug: str) -> None:
                    delay = config.poll_seconds
                    while True:
                        started = perf_counter()
                        with Session(bind=connection) as db:
                            graph = latest(db)
                            fallback = graph.id if graph else None
                        async with semaphore:
                            check = await probe(client, slug, config)
                        # Run the short database transaction without an await so each
                        # task uses the lock-owning connection serially.
                        with Session(bind=connection) as db, db.begin():
                            if check.graph_id is None:
                                check.graph_id = fallback
                            state = record(db, check, config)
                            db.flush()
                            verify(db, check)
                            available = check.available
                        event("monitoring", state)
                        LOG.info(
                            json.dumps(
                                {
                                    "event": "health_check",
                                    "service": slug,
                                    "state": state,
                                    "available": available,
                                }
                            )
                        )
                        delay = (
                            min(delay * 2, config.max_backoff_seconds)
                            if state == "down"
                            else config.poll_seconds
                        )
                        await asyncio.sleep(max(0, delay - (perf_counter() - started)))

                async with asyncio.TaskGroup() as group:
                    for slug in SERVICES:
                        group.create_task(poll(slug))
        finally:
            if not connection.invalidated:
                try:
                    connection.rollback()
                    connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
                    connection.commit()
                except SQLAlchemyError:
                    connection.invalidate()
                    raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        asyncio.run(run(settings()))
    except (SQLAlchemyError, ExceptionGroup):
        LOG.error('{"event":"worker_stopped","reason":"monitoring transaction failed"}')
        raise SystemExit(1) from None
