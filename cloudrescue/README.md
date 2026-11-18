# CloudRescue

CloudRescue monitors three local simulated cloud services, detects outages, and shows how they recover. All observations are synthetic, measured from real local HTTP requests. This independent project has no affiliation with Microsoft.

CloudRescue is released under the [MIT license](LICENSE).

The [external validation report](docs/external-validation-report.md) compares bounded HTTP measurements with modeled policy results. The [trace package](packages/reliability-traces) validates local JSON and CSV workloads without a database or frontend. See the [release checklist](docs/release-checklist.md) before publishing.

[Architecture overview](docs/architecture-overview.md) · [Benchmark Lab screenshot](docs/images/benchmark-lab.png)

## Start on Windows with Docker Compose

Run these commands in PowerShell from the repository root with Docker Desktop running.

```powershell
Copy-Item .env.example .env
$adminToken = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
(Get-Content .env) -replace '^ADMIN_TOKEN=$', "ADMIN_TOKEN=$adminToken" | Set-Content .env -Encoding ascii
docker compose up --build -d
docker compose ps
docker compose logs -f worker
```

Save the generated token securely or copy it from your local `.env` when signing in. Press Ctrl+C to leave the log view. Open [the dashboard](http://127.0.0.1:3000) or [API documentation](http://127.0.0.1:8000/docs). The one-shot migration service applies Alembic and seeds the three services before the API, worker, and simulators start. `docker compose down` stops the stack and preserves the named database volume.

## Run locally with uv and npm

Install uv, Node.js 24, and PostgreSQL 17. Start PostgreSQL locally, or run only the Compose database using `docker compose up -d db`. For a native PostgreSQL installation, create a login and database using psql as your local database administrator.

```sql
CREATE ROLE cloudrescue LOGIN PASSWORD 'cloudrescue';
CREATE DATABASE cloudrescue OWNER cloudrescue;
```

Create `.env` and generate the token as shown above. If using a different database password, update `DATABASE_URL` and URL-encode reserved characters. Use the same project root for all Python commands.

```powershell
uv sync --locked --python 3.12
uv run alembic upgrade head
uv run python -m backend.seed
```

Run these commands in **three separate PowerShell terminals** from the root. Start the simulators before the worker.

```powershell
uv run python -m simulator.main
```

```powershell
uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

```powershell
uv run python -m backend.worker
```

Start the dashboard in a fourth terminal. The token stays in the dashboard server process environment.

```powershell
$env:ADMIN_TOKEN = (Get-Content .env | Where-Object { $_ -match '^ADMIN_TOKEN=' }) -replace '^ADMIN_TOKEN=', ''
Set-Location frontend
Copy-Item .env.example .env.local
npm.cmd ci
npm.cmd run dev
```

| Local interface | URL |
| --- | --- |
| Dashboard | http://127.0.0.1:3000 |
| FastAPI documentation | http://127.0.0.1:8000/docs |
| Identity health | http://127.0.0.1:8101/health |
| Messaging health | http://127.0.0.1:8102/health |
| Storage health | http://127.0.0.1:8103/health |

Simulator ports are internal to Docker Compose. Native PowerShell runs expose them only on loopback.

## Reproduce an outage

1. Wait for the overview to show three healthy services and collected measurements.
2. Open **Fault Simulation**, sign in with the development admin token, and select **Messaging Service**.
3. Apply **Increased latency** at 1,200 ms. Within a polling cycle plus dashboard refresh, Messaging becomes **Degraded**. In **Monitoring Metrics**, filter to Messaging to see the increase.
4. Apply **Connection failure**. The simulator closes the HTTP connection before sending a response. The third consecutive failed observation opens an incident and marks Messaging **Down**. The **HTTP 500** mode also produces failed checks.
5. Select **Restore service**. Down services back off to at most 20 seconds by default. The first fast, successful check moves Messaging to **Recovering**. Three consecutive fast, successful checks resolve the incident.
6. Open **Incidents**, then the Messaging incident. Review the first observed failure, detection delay, recovery confirmation time, and the recorded evidence for each milestone.

Availability is the percentage of checks that received a successful HTTP response in the selected period. Response latency is the mean for successful checks. Down services are sampled less often during backoff, so availability is a sample ratio. Incident duration runs from the first failed check until recovery is confirmed.

## Diagnose and replay a cascade

1. Open **Service Dependencies**. The default graph shows Messaging and Storage depending on Identity. Sign in through **Fault Simulation** to publish graph changes. Each publication preserves the previous version.
2. Open **Incident Replay**, select **Identity failure cascades to both dependents**, and choose **Run on local simulators**. The API applies the faults together and they expire automatically. The five scenario recipes use the default graph and require existing faults to be cleared.
3. Under **Incidents**, open the Messaging or Storage incident while the fault is active or after it resolves. Its analysis shows the Identity hypothesis, reported downstream failures, check evidence, and the separate fault-injection record.
4. In **Incident Replay**, select **Recorded incident**, enter its ID, and save. Step through the stored frames. **Preview scenario** runs the same diagnosis on deterministic seeded observations without touching the running simulators.
5. Open **Diagnostic Evaluation**, or run the following from the repository root.

```powershell
uv run python -m backend.evaluation
```

Existing Phase 1 installations must run `uv run alembic upgrade head` before restarting the API, worker, and simulators. Phase 1 incident history remains available. Recorded diagnosis and replay require versioned observations from Phase 2.

## Recovery engineering

Phase 4 adds Benchmark Lab, Security Administration, Audit Verification, and Reliability Report. After migrating, bootstrap a named administrator and sign in with the account password. The first account disables the shared token. See [security model](docs/security-model.md), [benchmark methodology](docs/benchmark-methodology.md), and [held-out results](docs/phase-4-results.md).

```powershell
uv run alembic upgrade head
uv run python -m backend.identity my-admin
uv run python -m backend.benchmark --seed 42 --output benchmark-output
```

Apply `uv run alembic upgrade head` and restart the native stack with the PowerShell commands above. Sign in through **Fault Simulation** to use **Recovery Center**, **Policy Lab**, **Reliability Analytics**, and **Audit History**. Policy Lab and recommendations are available while live recovery is disabled.

For authorized local simulator actions, set `RECOVERY_ENABLED=true` in the root `.env` and restart the API. Open an incident in Recovery Center, review the recommendation, request a local fault reset or simulated restart, then confirm the individual approval. Monitoring determines the final result. The emergency stop is persistent and an explicit resume requires fresh approvals.

```powershell
uv run python -m backend.recovery_lab
```

[Recovery architecture](docs/recovery-engine.md) · [Recovery security](docs/recovery-security.md) · [Benchmarks](docs/reliability-benchmarks.md) · [Phase 4](docs/phase-4.md)

## Test and build

Use a **local test PostgreSQL instance** and a database role with permission to create databases. The backend tests create and remove their own uniquely named databases. The browser workflow mutates fault configuration and creates an incident, so point it at a separate local stack or a fresh test database.

```powershell
$env:CLOUDRESCUE_TEST_DATABASE = 'postgresql+psycopg://cloudrescue:cloudrescue@127.0.0.1:5432/postgres'
uv run ruff check backend simulator tests
uv run mypy backend simulator
uv run pytest -q
Set-Location frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test -- --run
npm.cmd run build
npm.cmd exec playwright install chromium
$env:CLOUDRESCUE_E2E_ADMIN_TOKEN = (Get-Content ../.env | Where-Object { $_ -match '^ADMIN_TOKEN=' }) -replace '^ADMIN_TOKEN=', ''
npm.cmd run e2e
```

With Microsoft Edge installed, set `$env:CLOUDRESCUE_BROWSER_CHANNEL = 'msedge'` to use Edge for Playwright. Set `CLOUDRESCUE_E2E_URL` if the isolated dashboard uses a different port.

The Windows test runner starts and stops an isolated stack against a fresh PostgreSQL database you supply. It uses ports 8101–8103, 13000, and 18000. Run from the root after building the dashboard, with those ports free.

```powershell
.\tests\run-local-e2e.ps1 -DatabaseUrl 'postgresql+psycopg://cloudrescue:cloudrescue@127.0.0.1:5432/cloudrescue_e2e'
```

## Project map

- `backend/` contains configuration, models, persistence, API, worker, state transitions, and Alembic migrations.
- `simulator/` serves deterministic HTTP responses on three separate local ports.
- `frontend/` contains the Next.js dashboard, server-side API routes, Vitest checks, and Playwright workflows.
- `tests/` contains Python checks covering the API, persistence, simulator, and incident lifecycle.
- `infra/` contains container build definitions.
- `docs/` documents architecture, deployment boundaries, and Phase 2.

[Architecture and security](docs/architecture.md) · [Phase 2 measurements](docs/phase-2.md) · [Phase 3 proposal](docs/phase-3.md)
