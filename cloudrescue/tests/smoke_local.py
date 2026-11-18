"""Exercise the isolated native stack without a browser."""

import json
import os
import socket
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from time import monotonic, sleep

import httpx
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def wait_for(read, timeout=30):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        try:
            result = read()
            if result:
                return result
        except httpx.TransportError:
            pass
        sleep(0.25)
    raise TimeoutError("Local smoke-test condition did not arrive")


def main():
    database = make_url(os.environ["DATABASE_URL"])
    if database.host not in {"127.0.0.1", "localhost"} or not (
        database.database == "cloudrescue_e2e"
        or (database.database or "").startswith("cloudrescue_e2e_")
    ):
        raise ValueError("Use a dedicated local cloudrescue_e2e database")
    for port in (8101, 8102, 8103, 18000):
        with socket.socket() as listener:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", port))
    with ExitStack() as cleanup:
        env = dict(os.environ, POLL_SECONDS="1", MAX_BACKOFF_SECONDS="2", SIM_NETWORK="loopback")
        token = env["ADMIN_TOKEN"]
        logs = ROOT / ".local-run"
        logs.mkdir(exist_ok=True)

        def start(name, *args):
            logfile = cleanup.enter_context((logs / f"smoke-{name}.log").open("w"))
            process = subprocess.Popen(
                [sys.executable, "-m", *args],
                cwd=ROOT,
                env=env,
                stdout=logfile,
                stderr=subprocess.STDOUT,
            )
            cleanup.callback(process.wait, timeout=10)
            cleanup.callback(process.terminate)

        start("simulator", "simulator.main")
        start("api", "uvicorn", "backend.api:app", "--port", "18000")
        client = cleanup.enter_context(
            httpx.Client(base_url="http://127.0.0.1:18000", trust_env=False)
        )
        wait_for(lambda: client.get("/health").is_success)
        for port in (8101, 8102, 8103):
            wait_for(lambda port=port: client.get(f"http://127.0.0.1:{port}/health").is_success)
        start("worker", "backend.worker")
        wait_for(lambda: client.get("/metrics").json()["checks"] >= 3)
        duplicate = subprocess.run(
            [sys.executable, "-m", "backend.worker"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=True,
            timeout=10,
        )
        assert b"worker_skipped" in duplicate.stderr

        path = "/services/messaging"
        headers = {"Authorization": f"Bearer {token}"}
        assert client.put(path + "/fault", json={"mode": "disconnect"}).status_code == 401

        def has_state(state):
            return client.get(path).json()["state"] == state

        try:
            client.put(
                path + "/fault",
                headers=headers,
                json={
                    "mode": "latency",
                    "latency_ms": 1200,
                },
            ).raise_for_status()
            wait_for(lambda: has_state("degraded"))
            client.put(
                path + "/fault",
                headers=headers,
                json={
                    "mode": "disconnect",
                },
            ).raise_for_status()
            wait_for(lambda: has_state("down"))
            active = [item for item in client.get("/incidents").json() if not item["closed_at"]]
            assert len(active) == 1
        finally:
            client.delete(path + "/fault", headers=headers).raise_for_status()

        wait_for(lambda: has_state("healthy"))
        incident = client.get(f"/incidents/{active[0]['id']}").json()
        assert incident["closed_at"]
        assert incident["events"][-1]["kind"] == "recovery_confirmed"
        print(
            json.dumps(
                {
                    "checks": client.get("/metrics").json()["checks"],
                    "incident": incident["id"],
                    "detection_seconds": incident["detection_seconds"],
                    "recovery_seconds": incident["recovery_seconds"],
                }
            )
        )


if __name__ == "__main__":
    main()
