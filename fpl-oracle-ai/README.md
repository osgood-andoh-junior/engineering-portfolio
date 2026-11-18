# FPL Oracle AI

A runnable local research application with real FPL data, FastAPI, Next.js, PostgreSQL/Redis, trained tree/recurrent models and OR-Tools squad optimization. The full production specification is not complete.

## Run again on this Windows workstation

From PowerShell:

```powershell
Set-Location '<project-folder>'
npm run services:up
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.manage sync
.\.venv\Scripts\python.exe -m scripts.manage predict
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location '<project-folder>'
npm run dev
```

Open http://127.0.0.1:3000/dashboard. API docs: http://127.0.0.1:8000/docs; health: http://127.0.0.1:8000/api/v1/health.

Use the existing ignored .env. PostgreSQL runs in Compose on 127.0.0.1:55432 because an unrelated Windows PostgreSQL service already owns 5432. Redis uses 127.0.0.1:6379. `npm run services:up` uses Docker on Windows if available, otherwise the installed Docker Engine/Compose in Ubuntu WSL2, with a hidden keepalive process. `npm run services:status` reports health; `npm run services:stop` stops only these two containers. Stop existing app processes before starting a second backend/frontend on the same ports. Original SQLite data/oracle.db is preserved; the verified application now uses PostgreSQL through .env.

For continuous refresh, run ` .\.venv\Scripts\python.exe -m workers.run` in another terminal. Worker long-job lease recovery remains a production validation gap.

## Dependencies and checks

Node 24, Python 3.12 and uv are used locally. For a new checkout create the environment with `uv venv --python 3.12 .venv`, then install the locked dependencies:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements.lock
npm ci
npm run lint
.\.venv\Scripts\python.exe -m ruff check apps/api ml workers scripts tests
npm run typecheck
npm test
.\.venv\Scripts\python.exe -m pytest -q
```

Python Ruff checks critical syntax/name/control-flow errors; frontend ESLint uses Next.js core-web-vitals and TypeScript rules. Stop the frontend before `npm run build`, then restart it. Browser verification: `$env:ORACLE_CAPTURE_SCREENSHOT='true'; npm run e2e --workspace apps/web`. Real PostgreSQL/Redis integration-test environment commands are in docs/LOCAL_VERIFICATION.md. Tests use isolated synthetic records; those records are never used to claim real production data coverage.

## Data and models

The six completed seasons 2020/21–2025/26 are retained as original source snapshots, normalized records and Parquet. Stable provider codes link identities; names never establish identity. `scripts.manage sync` refreshes official bootstrap/fixtures. `scripts.manage matches --limit 669 --offset 0` refreshes the currently registered player histories at one request per second using pooled connections. Empty upstream histories remain empty.

Historical research import requires explicit permission review in DATA_SOURCES.md. It is opt-in through HISTORICAL_DATA_PERMITTED and is not permission to redistribute underlying football data. Cached archive imports do not establish historical observed-at times.

Training: `scripts.manage train --epochs 5`, `train-minutes`, `backtest`, then `predict` (all run with `.venv\Scripts\python.exe -m`). Strict `train --strict-point-in-time` rejects missing deadline/observation coverage. Implemented families have real trained artifacts; absent ensemble, starting-XI and full event-simulation capabilities are not fabricated.

## Verification and limitations

Read [docs/LOCAL_VERIFICATION.md](docs/LOCAL_VERIFICATION.md) for the current phase audit, actual service/test results, failures and exact restart commands. [MODEL_CARD.md](MODEL_CARD.md) records scientific limitations. Historical deadline/observed-time coverage, complete managerial/tactical feeds, rolling transfer/chip planning and production deployment acceptance remain incomplete. Existing structured analyst output needs no LLM key; open-ended LLM reasoning is not enabled. No paid provisioning, publishing or remote push was performed.

Public squad import resolves players for the selected season, shows submitted and final lineups, and supports lineup optimization.

The platform-wide visual upgrade replaces primary object dumps with typed player cards, forecast comparisons, official FDR matrices, historical charts, manager timelines and verified model evaluation charts. Read [UI_AUDIT.md](UI_AUDIT.md) for all page changes, integrity rules, current data counts and limitations. Imported squad summaries use tab memory only; reload clears them.

Transfer planning is now available on /transfers and /optimizer through additive /planning APIs. Latest public manager import, editable ownership, explicitly confirmed bank/free transfers/selling values, legal OR-Tools transfer caps, hit accounting, keep baseline, alternatives and five-GW fixed-ownership comparisons are implemented. See [docs/TRANSFER_PLANNING.md](docs/TRANSFER_PLANNING.md) for usage and limitations. The full sequential future-transfer/rollover and correlated bench simulation specification remains incomplete; current liquidation value is not predicted future value.
