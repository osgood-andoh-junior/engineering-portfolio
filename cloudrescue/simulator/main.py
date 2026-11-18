import argparse
import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime

from sqlalchemy import select, true
from sqlalchemy.exc import SQLAlchemyError

from backend.config import SERVICES
from backend.db import sessions
from backend.models import DependencyGraph, FaultConfiguration
from backend.recovery_models import SimulatorRuntime
from backend.topology import graph_edges
from simulator.behavior import outcome

LOG = logging.getLogger("cloudrescue.simulator")


def fault_for(slug: str) -> tuple[str, int, str | None, int]:
    with sessions()() as db:
        graph_id = select(DependencyGraph.id).order_by(DependencyGraph.id.desc()).limit(1)
        rows = db.execute(
            select(FaultConfiguration, DependencyGraph, SimulatorRuntime)
            .select_from(FaultConfiguration)
            .join(DependencyGraph, true())
            .outerjoin(
                SimulatorRuntime, SimulatorRuntime.service_slug == FaultConfiguration.service_slug
            )
            .where(DependencyGraph.id == graph_id.scalar_subquery())
        ).all()
        now = datetime.now(UTC)
        faults = {
            fault.service_slug: ("error", 0)
            if runtime and runtime.restarting_until > now
            else ("healthy", 0)
            if fault.expires_at and fault.expires_at <= now
            else (fault.mode, fault.latency_ms)
            for fault, _, runtime in rows
        }
        if set(faults) != set(SERVICES):
            raise RuntimeError("Simulator service has not been seeded")
        graph = rows[0][1]
        return (*outcome(slug, graph_edges(graph), faults), graph.id)


async def respond(
    slug: str,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    provider: Callable[[str], tuple[str, int, str | None, int]] | None = None,
) -> None:
    try:
        metadata = ""
        headers = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=3)
        if headers.split(b"\r\n", 1)[0] not in {b"GET /health HTTP/1.1", b"GET /health HTTP/1.0"}:
            status, body = "404 Not Found", b'{"ok":false}'
        else:
            try:
                mode, latency, parent, graph_id = await asyncio.to_thread(
                    provider or fault_for, slug
                )
                metadata = f"X-CloudRescue-Graph: {graph_id}\r\n"
                if parent:
                    metadata += f"X-CloudRescue-Blocked-By: {parent}\r\n"
            except (RuntimeError, SQLAlchemyError):
                LOG.error('{"event":"fault_configuration_unavailable","service":"%s"}', slug)
                mode, latency = "unavailable", 0
            if mode == "disconnect":
                writer.transport.abort()
                return
            if mode == "latency":
                await asyncio.sleep(latency / 1000)
            if mode in {"unavailable", "dependency"}:
                status, body = "503 Service Unavailable", b'{"ok":false}'
            elif mode == "error":
                status, body = "500 Internal Server Error", b'{"ok":false}'
            else:
                status, body = "200 OK", b'{"ok":true}'
        writer.write(
            f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\n"
            f"{metadata}Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
            + body
        )
        await writer.drain()
    except (TimeoutError, OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        pass
    finally:
        writer.close()
        with suppress(OSError):
            await writer.wait_closed()


async def serve(slug: str, host: str) -> None:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await respond(slug, reader, writer)

    server = await asyncio.start_server(handle, host, SERVICES[slug][1], limit=8192)
    async with server:
        await server.serve_forever()


async def main(slug: str, host: str) -> None:
    await asyncio.gather(*(serve(key, host) for key in ([slug] if slug else SERVICES)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=SERVICES)
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "0.0.0.0"))
    args = parser.parse_args()
    asyncio.run(main(args.service, args.host))
