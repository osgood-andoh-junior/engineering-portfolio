import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url

from backend.api import app
from backend.config import Settings, settings
from backend.db import database_engine, sessions
from backend.detection import record
from backend.models import HealthCheck, Incident, ReplaySession
from backend.recovery_control import verify
from backend.recovery_models import Execution
from backend.replay import SCENARIOS
from backend.seed import seed
from backend.worker import probe
from simulator import main as simulator


def test_worker_connection_loss_releases_lock_without_duplicate_writes(database, monkeypatch):
    from backend import worker

    async def interrupt(client, slug, config):
        with database_engine().begin() as db:
            owner = db.scalar(
                text(
                    "SELECT pid FROM pg_locks WHERE locktype = 'advisory' "
                    "AND objid = 726031022 AND granted AND database = "
                    "(SELECT oid FROM pg_database WHERE datname = current_database())"
                )
            )
            assert owner is not None
            assert db.scalar(text("SELECT pg_terminate_backend(:pid, 2000)"), {"pid": owner})
        return HealthCheck(
            service_slug=slug, available=True, latency_ms=1, checked_at=datetime.now(UTC)
        )

    monkeypatch.setattr(worker, "probe", interrupt)
    with pytest.raises(ExceptionGroup):
        asyncio.run(worker.run(settings()))
    with database_engine().begin() as db:
        assert db.scalar(text("SELECT pg_try_advisory_xact_lock(726031022)"))
        assert db.scalar(select(func.count()).select_from(HealthCheck)) == 0


def test_named_operator_roles_and_audit(database):
    from backend.identity import password_hash
    from backend.security_models import Operator

    with sessions().begin() as db:
        db.add(
            Operator(
                username="admin-user",
                password=password_hash("test-admin-long-password"),
                role="administrator",
                active=True,
            )
        )
    with TestClient(app) as client:

        def login(username, password):
            result = client.post(
                "/identity/login", json={"username": username, "password": password}
            )
            assert result.status_code == 200
            return {"Authorization": "Bearer " + result.json()["token"]}

        assert (
            client.get(
                "/identity/me",
                headers={
                    "Authorization": "Bearer test-only-admin-token",
                },
            ).status_code
            == 401
        )
        admin = login("admin-user", "test-admin-long-password")
        for name, role in (("viewer-user", "viewer"), ("operator-user", "operator")):
            assert (
                client.post(
                    "/identity/accounts",
                    headers=admin,
                    json={
                        "username": name,
                        "password": "test-user-long-password",
                        "role": role,
                    },
                ).status_code
                == 201
            )
        viewer = login("viewer-user", "test-user-long-password")
        operator = login("operator-user", "test-user-long-password")
        assert (
            client.put("/recovery/policies", headers=operator, json={"rate": 14}).status_code == 403
        )
        assert client.put("/recovery/policies", headers=admin, json={"rate": 14}).status_code == 200
        assert client.get("/recovery/policies", headers=viewer).json()["parameters"]["rate"] == 14
        assert client.get("/recovery/center", headers=viewer).status_code == 200
        assert (
            client.post("/recovery/stop", headers=operator, json={"confirm": True}).status_code
            == 403
        )
        assert client.post("/scenarios/spike/run", headers=viewer).status_code == 403
        assert (
            client.put(
                "/identity/accounts/viewer-user",
                headers=viewer,
                json={
                    "active": True,
                    "role": "administrator",
                },
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/services/messaging/fault", headers=operator, json={"mode": "error"}
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/identity/accounts/operator-user",
                headers=admin,
                json={
                    "active": False,
                    "role": "operator",
                },
            ).status_code
            == 200
        )
        assert client.get("/identity/me", headers=operator).status_code == 401
        result = client.post("/audit-chain/verify", headers=admin, json=None)
        assert result.status_code == 200
        assert result.json()["valid"] and result.json()["count"] >= 8


def test_recovery_auth_concurrency_audit_and_emergency_stop(database, monkeypatch):
    headers = {"Authorization": "Bearer test-only-admin-token"}
    origin = datetime.now(UTC) - timedelta(minutes=1)

    def observe(index, available):
        with sessions().begin() as db:
            check = HealthCheck(
                service_slug="messaging",
                checked_at=origin + timedelta(seconds=index),
                status_code=200 if available else 500,
                latency_ms=10,
                available=available,
            )
            record(db, check, settings())
            db.flush()
            verify(db, check)

    for index in range(3):
        observe(index, False)
    with TestClient(app) as client:
        incident = client.get("/incidents").json()[0]["id"]
        body = {
            "key": str(uuid.uuid4()),
            "incident_id": incident,
            "target": "messaging",
            "action": "restart",
        }
        assert client.get("/recovery/center").status_code == 401
        assert client.post("/recovery/approvals", json=body).status_code == 401
        assert client.post("/recovery/approvals", headers=headers, json=body).status_code == 409
        monkeypatch.setenv("RECOVERY_ENABLED", "true")
        settings.cache_clear()
        first = client.post("/recovery/approvals", headers=headers, json=body).json()["id"]
        assert client.post("/recovery/approvals", headers=headers, json=body).json()["id"] == first
        second = client.post(
            "/recovery/approvals", headers=headers, json={**body, "key": str(uuid.uuid4())}
        ).json()["id"]
        path = f"/recovery/approvals/{first}/execute"
        assert client.post(path, headers=headers, json={"confirm": False}).status_code == 422

        def submit(approval_id):
            return client.post(
                f"/recovery/approvals/{approval_id}/execute",
                headers=headers,
                json={"confirm": True},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(submit, [first, second])) == [200, 409]
        with sessions()() as db:
            execution = db.scalar(select(Execution))
            assert execution is not None
            winner = execution.approval_id
            origin = execution.deadline + timedelta(seconds=1)
        assert submit(winner) == 200
        assert simulator.fault_for("messaging")[0] == "error"
        observe(0, False)
        assert (
            client.post("/recovery/stop", headers=headers, json={"confirm": True}).status_code
            == 200
        )
        assert not client.get("/recovery/center", headers=headers).json()["enabled"]
        assert submit(second if winner == first else first) == 409
        events = client.get("/recovery/audit", headers=headers).json()
        assert sum(row["event"] == "executed" for row in events) == 1
        assert any(row["event"] == "failed" and row["evidence"]["check_id"] for row in events)
        assert any(row["event"] == "emergency_stop" for row in events)
        result = client.post(
            "/recovery/experiments", headers=headers, json={"scenario": "primary", "seed": 42}
        )
        assert result.status_code == 201
        assert len(result.json()["results"]) == 6
        assert (
            client.get(f"/recovery/experiments/{result.json()['id']}", headers=headers).json()
            == result.json()
        )


def test_versioned_topology_and_replay_are_authenticated_and_persistent(database):
    headers = {"Authorization": "Bearer test-only-admin-token"}
    with TestClient(app) as client:
        original = client.get("/dependencies").json()
        change = {"expected_version": original["version"], "edges": []}
        assert client.put("/dependencies", json=change).status_code == 401
        assert client.post("/replays", json={"source": "cascade"}).status_code == 401
        cycle = {**change, "edges": [["identity", "storage"], ["storage", "identity"]]}
        assert client.put("/dependencies", headers=headers, json=cycle).status_code == 422
        updated = client.put("/dependencies", headers=headers, json=change).json()
        assert updated["version"] > original["version"]
        assert client.put("/dependencies", headers=headers, json=change).status_code == 409
        assert client.get(f"/dependencies/{original['version']}").json() == original
        response = client.post("/replays", headers=headers, json={"source": "cascade"})
        assert response.status_code == 201
        saved = response.json()
        assert client.get(f"/replays/{saved['id']}").json() == saved
    with sessions()() as db:
        assert db.scalar(select(func.count()).select_from(ReplaySession)) == 1
        assert db.scalar(select(func.count()).select_from(Incident)) == 0
        assert db.scalar(select(func.count()).select_from(HealthCheck)) == 0


@pytest.mark.parametrize("name", SCENARIOS)
def test_authorized_scenarios_change_actual_http_responses(name, database):
    scenario = SCENARIOS[name]
    headers = {"Authorization": "Bearer test-only-admin-token"}
    with TestClient(app) as api:
        path = f"/scenarios/{name}/run"
        assert api.post(path).status_code == 401
        assert api.post(path, headers=headers).status_code == 201
        assert api.post(path, headers=headers).status_code == 409

        async def scenario_http():
            from contextlib import AsyncExitStack
            from functools import partial

            async with AsyncExitStack() as stack:
                client = await stack.enter_async_context(httpx.AsyncClient(trust_env=False))
                for slug in ("messaging", "storage", "identity"):
                    server = await stack.enter_async_context(
                        await asyncio.start_server(
                            partial(simulator.respond, slug),
                            "127.0.0.1",
                            0,
                        )
                    )
                    url = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}/health"
                    mode, latency = scenario.faults.get(slug, ("healthy", 0))
                    start = asyncio.get_running_loop().time()
                    if mode == "disconnect":
                        with pytest.raises(httpx.RemoteProtocolError):
                            await client.get(url)
                    else:
                        response = await client.get(url)
                        if name == "cascade":
                            assert response.status_code == 503
                            assert response.headers["X-CloudRescue-Blocked-By"] == "identity"
                        else:
                            assert response.status_code == (500 if mode == "error" else 200)
                        if latency:
                            assert asyncio.get_running_loop().time() - start >= latency / 1000
                    if name == "spike" and slug == "messaging":
                        await asyncio.sleep(2)
                        assert api.get("/services/messaging").json()["fault"]["mode"] == "healthy"
                        assert (await client.get(url)).status_code == 200
                    if slug in scenario.faults:
                        assert (
                            api.delete(f"/services/{slug}/fault", headers=headers).status_code
                            == 200
                        )
                        assert (await client.get(url)).status_code == 200

        asyncio.run(scenario_http())


@pytest.fixture
def database(monkeypatch):
    base = os.environ.get("CLOUDRESCUE_TEST_DATABASE")
    if not base:
        pytest.skip("Set CLOUDRESCUE_TEST_DATABASE to run PostgreSQL integration tests")
    url = make_url(base)
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("The integration database must be local")
    database_name = f"cloudrescue_test_{uuid.uuid4().hex}"
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{database_name}"'))
    monkeypatch.setenv("DATABASE_URL", url.set(database=database_name).render_as_string(False))
    monkeypatch.setenv("ADMIN_TOKEN", "test-only-admin-token")
    settings.cache_clear()
    database_engine.cache_clear()
    sessions.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        seed()
        seed()
        yield
    finally:
        database_engine().dispose()
        database_engine.cache_clear()
        sessions.cache_clear()
        settings.cache_clear()
        with engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{database_name}"'))
        engine.dispose()


def test_probe_records_status_and_transport_failure():
    async def scenario():
        def handle(request):
            assert request.url == "http://127.0.0.1:8102/health"
            return httpx.Response(500)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await probe(client, "messaging", Settings())
            assert (result.available, result.status_code, result.error) == (
                False,
                500,
                "http_status",
            )

        def disconnect(request):
            raise httpx.RemoteProtocolError("disconnected")

        async with httpx.AsyncClient(transport=httpx.MockTransport(disconnect)) as client:
            result = await probe(client, "messaging", Settings())
            assert (result.available, result.status_code, result.error) == (
                False,
                None,
                "connection",
            )

    asyncio.run(scenario())


def test_admin_requires_token_even_without_database():
    with TestClient(app) as client:
        assert client.put("/services/messaging/fault", json={"mode": "error"}).status_code == 401
        assert client.delete("/services/messaging/fault").status_code == 401
        assert client.get("/openapi.json").status_code == 200


def test_persistence_incident_lifecycle_and_api(database):
    origin = datetime.now(UTC) - timedelta(minutes=5)
    config = settings()

    def observation(index, code=200, latency=10):
        with sessions().begin() as db:
            return record(
                db,
                HealthCheck(
                    service_slug="messaging",
                    checked_at=origin + timedelta(seconds=index * 5),
                    status_code=code,
                    latency_ms=latency,
                    available=code == 200,
                    error=None if code == 200 else "http_status",
                ),
                config,
            )

    assert observation(0) == "healthy"
    assert observation(1, latency=1200) == "degraded"
    assert observation(2, 500) == "degraded"
    assert observation(3, 500) == "degraded"
    assert observation(4, 500) == "down"
    assert observation(5, 500) == "down"
    assert observation(6) == "recovering"
    assert observation(7, 500) == "down"
    assert observation(8) == "recovering"
    assert observation(9) == "recovering"
    assert observation(10) == "healthy"
    with sessions()() as db:
        assert db.scalar(select(func.count()).select_from(Incident)) == 1
        assert db.scalar(select(func.count()).select_from(HealthCheck)) == 11

    with TestClient(app) as client:
        assert len(client.get("/services").json()) == 3
        assert client.get("/services/messaging/checks?limit=2").json()[0]["available"]
        assert client.get("/services/not-local").status_code == 404
        assert client.get("/summary").json()["active_incidents"] == 0
        metrics = client.get("/metrics?hours=1&service=messaging").json()
        assert metrics["checks"] == 11
        assert metrics["availability"] == pytest.approx(600 / 11)
        (incident,) = client.get("/incidents").json()
        assert incident["detection_seconds"] == 10
        assert incident["recovery_seconds"] == 10
        detail = client.get(f"/incidents/{incident['id']}").json()
        assert [event["kind"] for event in detail["events"]] == [
            "outage_started",
            "outage_detected",
            "recovery_started",
            "recovery_interrupted",
            "recovery_started",
            "recovery_confirmed",
        ]


def test_fault_api_changes_real_http_responses(database, monkeypatch):
    with TestClient(app) as api:
        headers = {"Authorization": "Bearer test-only-admin-token"}
        path = "/services/messaging/fault"
        assert (
            api.put(path, headers=headers, json={"mode": "latency", "latency_ms": 1}).status_code
            == 422
        )
        assert (
            api.put(path, headers=headers, json={"mode": "error", "url": "invalid"}).status_code
            == 422
        )

        async def scenario():
            async def respond(reader, writer):
                await simulator.respond("messaging", reader, writer)

            async with await asyncio.start_server(respond, "127.0.0.1", 0) as server:
                port = server.sockets[0].getsockname()[1]
                monkeypatch.setattr(
                    Settings, "target", lambda self, slug: f"http://127.0.0.1:{port}/health"
                )
                async with httpx.AsyncClient(trust_env=False) as client:
                    assert (await probe(client, "messaging", settings())).available
                    assert (
                        api.put(
                            path, headers=headers, json={"mode": "latency", "latency_ms": 550}
                        ).status_code
                        == 200
                    )
                    slow = await probe(client, "messaging", settings())
                    assert slow.available and slow.latency_ms >= 550
                    assert api.put(path, headers=headers, json={"mode": "error"}).status_code == 200
                    assert (await probe(client, "messaging", settings())).status_code == 500
                    assert (
                        api.put(path, headers=headers, json={"mode": "disconnect"}).status_code
                        == 200
                    )
                    assert (await probe(client, "messaging", settings())).error == "connection"
                    assert api.delete(path, headers=headers).status_code == 200
                    assert (await probe(client, "messaging", settings())).available

        asyncio.run(scenario())
