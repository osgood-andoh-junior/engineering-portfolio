# Local verification and restart commands

This report records actual local execution. The existing warehouse and trained artifacts contain real provider data; synthetic data is confined to isolated tests. No production data is seeded from mocks.

## Restart on this Windows workstation

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

The service helper uses Docker on Windows when available, otherwise Docker Engine installed in the existing Ubuntu WSL2 distribution. It starts only PostgreSQL and Redis through this project's Compose file. Local secrets are generated in ignored .env; do not replace that file or print its contents. SQLite data/oracle.db is preserved as the original local source. The one-time copy utility refuses nonempty PostgreSQL targets.

URLs:

- Application: http://127.0.0.1:3000/dashboard
- FastAPI docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/v1/health
- Real players: http://127.0.0.1:8000/api/v1/players?limit=10
- Real fixtures: http://127.0.0.1:8000/api/v1/fixtures?limit=10
- Data health: http://127.0.0.1:8000/api/v1/data-health
- PostgreSQL: 127.0.0.1:55432; Redis: 127.0.0.1:6379 (not web pages)

## Dependency and verification commands

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements.lock
npm ci
uv pip check --python .venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m ruff check apps/api ml workers scripts tests
npm run lint
npm run typecheck
npm test
npm run build
$env:ORACLE_CAPTURE_SCREENSHOT='true'
npm run e2e --workspace apps/web
```

Stop the frontend before its production build, then restart it with npm run dev. New setup requires Node 24, Python 3.12 and uv; create .venv with `uv venv --python 3.12 .venv` first. Use the existing .env on this machine. New installations must create .env with local database credentials before starting Compose.

Real service integration test configuration (secrets are read from settings, never written into this document):

```powershell
$env:TEST_DATABASE_URL=(& .\.venv\Scripts\python.exe -c 'from apps.api.config import settings; print(settings.database_url)')
$env:TEST_REDIS_URL='redis://127.0.0.1:6379/15'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=data/verification-tests
```

The PostgreSQL test creates/drops a unique isolated schema; the Redis integration test uses database 15. Normal unit tests use isolated temporary records. API cache tests may invalidate local application cache version; regenerate forecasts after testing. Isolated tests do not populate the production warehouse with synthetic players/events.

Optional continuous scheduler, in another terminal:

```powershell
.\.venv\Scripts\python.exe -m workers.run
```

Historical research import requires reviewing DATA_SOURCES.md and explicitly enabling permitted use. Six source archives are already present. Current match history can be resumed using `python -m scripts.manage matches --offset 0 --limit 50`; forecasts are regenerated separately. Upstream failures can leave partial coverage and must not be called a complete sync.

## Phase audit

The phase statuses and final execution results are appended after service verification finishes. Passing tests does not establish fully observed historical deadlines, production model quality or deployment readiness.

## Implementation phases: audited against the supplied specification

| Phase | Actual status | Evidence and outstanding work |
| --- | --- | --- |
| 1 — Foundation | Complete locally | Monorepo, schema, six migrations, healthy Compose PostgreSQL/Redis, backend health, real FPL bootstrap/fixtures. App-container deployment is a separate unverified path. |
| 2 — Historical intelligence | Partial | Six real seasons in relational storage/raw snapshots/Parquet; stable-code identity mapping, validation and feature snapshots work. Exact historical deadlines and observed-time coverage are missing. |
| 3 — Core ML | Complete as a research pipeline | Real baseline, CatBoost and LightGBM artifacts, chronological research evaluation, generated forecasts and APIs. Scores do not establish production-valid point-in-time performance. |
| 4 — Recurrent ML | Partial | LSTM/GRU weights verified for 5/10/15/20 lengths and matched comparisons persisted. No validated learned ensemble. |
| 5 — Football intelligence | Partial | Twenty current verified manager tenures, 160 manager match facts, authenticated event ingestion and context/cold-start code. Tactical observations and transfer-event tables are empty; complete historical coverage/feed integration is missing. |
| 6 — Prediction/optimization | Partial | Residual probabilities, calibrated minutes bands, legal squad/XI/captain and fixed 1/3/5-GW horizon work. Ownership/selling values/rollover, rolling transfers, validated chips, joint simulation and automatic substitutions are incomplete. |
| 7 — Frontend | Partial | Sixteen navigation tabs plus player/manager detail routes and real API connections work. Several advanced matrices/analyses from the full specification remain absent; empty-data sections are not completed intelligence features. |
| 8 — Automation | Partial | TanStack/BFF, real Redis caching/locks and durable job infrastructure work. Continuous scheduler operation and long-job lease renewal/recovery are not fully verified. |
| 9 — Analyst | Partial | Structured selected-player evidence retrieval/explanation works. Open-ended LLM reasoning is not implemented; no API key is required for the existing mode. |
| 10 — Production validation | Partial | Local tests/build/lint/types are executed. Strict historical validation, full decision backtests, load/security/deployment/backup-restoration acceptance remain outstanding. |

## Model audit

All 62 registered local artifacts were deserialized from the trusted training directory and checked for fitted estimators/priors or loadable recurrent weights. Families: baseline, CatBoost, LightGBM, LSTM, GRU and minutes. Recurrent lengths: 5, 10, 15, 20. No missing fitted artifacts were found among those implemented families. These checks are not new accuracy evaluation.

Missing or unvalidated capabilities: learned ensemble, starting-XI classifier, validated manager/tactics/transfer lift and full joint scoring-event simulation. Advanced experiment tooling (Optuna/MLflow/SHAP) is not implemented. Registered models were not retrained during this verification; expanding current-season inference history does not alter their saved training/evaluation claims.

The latest completed tabular development experiment used 30,563 held-out observations: baseline MAE 1.05465, CatBoost 0.99948, LightGBM 0.99691. Only approximately 0.0196% of that prepared dataset has exact gameweek deadlines. Historical results remain retrospective research, with no causal or production accuracy claim.

## Historical archive coverage

| Season | Stored fixture records |
| --- | ---: |
| 2020/21 | 24,365 |
| 2021/22 | 25,447 |
| 2022/23 | 26,505 |
| 2023/24 | 29,725 |
| 2024/25 | 27,605 |
| 2025/26 | 29,747 |

Total completed-season records: 163,394. Ten exact duplicate source rows were removed from the final season; the original archive remains preserved. No whole requested season is missing. Exact historical gameweek deadlines, original observation times, complete manager/tactical history and actual starting-XI labels are missing. Source rights still require deployment-specific review. Current-season completion is recorded with the final ingestion result below.

## Failures encountered and resolved

- Docker was absent on Windows: installed Docker Engine 29.1.3 and Compose 2.40.3 in existing Ubuntu WSL2.
- Docker Hub image transfer stalled: pulled the official PostgreSQL image via public.ecr.aws/docker/library; retained it locally under the Compose image name. PostgreSQL image manifest digest: sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b.
- WSL service-only lifetime interrupted container availability: added a hidden project-owned keepalive and container restart policies.
- Port 5432 belonged to an existing Windows PostgreSQL service; initial password authentication reached that service. Kept it untouched and moved this project's container to 55432.
- No lint command existed: installed supported ESLint 10/Next config and Ruff; fixed React countdown effect, unused imports and anonymous config export. Python lint checks critical syntax/name/control-flow errors; it is not a full formatting/style audit.
- Deprecated Redis SETEX warning: replaced with SET plus expiry.
- Current match ingestion rebuilt HTTP clients for every request: added scoped connection reuse while preserving retries and the one-request-per-second limit. Connection reuse/rate/cleanup has a dedicated isolated test.
- Sandbox execution blocked Python async socket-pair initialization/package-cache writes; verification commands were rerun with the required local execution permission.

Remaining non-fatal framework warning: Starlette warns that its HTTPX TestClient compatibility path is deprecated. Tests pass; the production FPL adapter still uses its declared HTTPX dependency. No warning is presented as a passing test for an unavailable feature.

## Final measured outcome — PostgreSQL/Redis verification

- Docker Compose: PostgreSQL 17 and Redis 7 healthy in Ubuntu WSL2; Windows Python reaches the actual containers. Existing Windows PostgreSQL on 5432 was not modified. Application PostgreSQL port: 55432.
- Migrations: 0006 (head) on PostgreSQL. One-time source-preserving copy matched all table counts; data/postgres-copy-report.json records the result.
- Official FPL bootstrap/fixtures refreshed successfully: 669 players, 380 fixtures.
- Full current-season history request completed for all 669 players: 5,220 stored player-fixture records. No fixed eight-row-per-player assumption is made. Empty/missing upstream values were not fabricated. The former four-player coverage gap is resolved for the current registered request set.
- Six historical archives were revalidated from retained real snapshots: 163,394 completed-season records. Total fixture records: 168,614. This does not resolve absent historical deadlines/observation times or establish freshness against a newly downloaded archive revision.
- Forecast refresh succeeded: 2,007 outputs across 1/3/5-GW horizons. Local registry: 62 fitted artifacts, all validated; no retraining or new accuracy claim was made during verification.
- Final backend tests: 58 passed, zero skipped; both PostgreSQL concurrency and Redis integration were executed. A non-fatal Starlette/HTTPX compatibility deprecation warning remains.
- Browser/API suite: 17 passed against the real PostgreSQL/Redis-backed app, including actual public import, full manual squad, legal optimization and all tabs. One additional isolated player-picker test uses a clearly labelled intercepted test fixture; it is not evidence of real-data coverage and does not seed the warehouse. Real-data counts and flows were verified separately.
- Frontend unit tests: 2 passed. ESLint/Next/TypeScript lint, Python critical-error Ruff lint, TypeScript checking and final Webpack build passed. Dependency checker: 68 compatible installed Python packages; npm install audit reported zero vulnerabilities.
- Final fixes also include same-name player disambiguation via club labels/stable IDs, FPL footer source selection by ID rather than database row order, accurate history-completion messaging and archive import success metadata. Archive success records local cached ingestion, not newly observed historical timestamps.
- Ordinary unit tests now isolate application caches from .env Redis; the explicit Redis integration test uses DB 15. The app cache version was rotated after tests. Synthetic records stay in temporary SQLite or a unique PostgreSQL test schema and are not published as production coverage.
- API and frontend remain running. Background scheduler is not started by this verification; use the optional worker command above for continuous updates. Long-job lease recovery and production automation remain partially validated.

Raw evidence: data/local-audit.json, data/ingestion-full-verification.json, data/model-artifact-verification.json, data/coverage.json and data/screenshots/dashboard.png. This report supersedes earlier SQLite-only/service-skipped verification results. No remote deployment, paid provisioning or Git push occurred.

Final smoke checks returned HTTP 200 for health, players, fixtures, default 100-row predictions and data health through the frontend proxy. PostgreSQL reports server version 17.11; no isolated oracle_test_ schemas remain. Application Redis reports real mode and the current-history completion message reflects the successful full batch. Local .env and audit data are Git-ignored. API/frontend and both database containers remain running; the optional scheduler is not running.

## Platform visual UI verification — 1 November 2026

The latest UI work is documented in UI_AUDIT.md at the repository root and supersedes older test counts above: **73 backend**, **20 frontend unit/component/adapter**, and **24 browser/API** checks passed with no skips; lint, types, configured Python Ruff and the production build passed. Four viewport classes and all pages were exercised against real services. Synthetic fixture tests remain explicitly isolated and do not establish production data coverage.

The latest official bootstrap/fixture refresh returned **670 players / 380 fixtures**; inference generated **2,010 actual saved model outputs** for the upcoming GW10, across 1/3/5-GW horizons. No model retraining was necessary. The previous full current-history batch covered 669 registered players, so it has not been rerun against the expanded registration set. Tactical observations, verified football-event ingestion, original historical observation/deadline snapshots, private transfer/chip state, open-ended LLM reasoning and absent production ensemble/starting-XI/joint simulation models retain the limitations explained in UI_AUDIT.md.


The read-only evaluation chart exports can be reproduced from existing trusted saved artifacts without training:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.build_ui_evaluations
~~~

After a source refresh, regenerate predictions immediately; both source age and forecast age are checked by the solver. Continuous background refresh was not started by this UI task. Existing restart commands and port assignments above remain valid.

## Transfer planning — 5 November 2026

Implemented additive /api/v1/planning/latest-squad/{id} and /api/v1/planning/transfers routes with no-store manager responses, exact selling-value cash constraints, OR-Tools squad/XI/captain selection, keep baseline and capped alternatives. Existing imported-lineup and legacy transfer API contracts remain unchanged. New settings panels appear on /transfers and /optimizer. Read docs/TRANSFER_PLANNING.md and the latest IMPLEMENTATION_PLAN.md section for exact scope and remaining work.


Real keep-squad solver checks returned OPTIMAL at 1/3/5-GW horizons: **49.4146 / 146.5199 / 242.2627** expected net points, zero transfers/hits and unchanged £1.0m bank. Unknown liquidation value stays null. A browser regression then exercised the actual manager's keep-squad plans through the new API for all three horizons, using those user-confirmed inputs and no selling values. Evidence: data/transfer-real-keep-verification.json. These are stored model forecasts, not claimed actual scores.

Checks completed: **83 backend tests passed** with PostgreSQL and Redis integration enabled; **22 frontend unit tests passed**; **25-test complete browser suite passed**, followed by **both transfer-specific browser tests passing**, including the additional real keep-plan test. This represents 26 distinct browser tests across the full and targeted runs, not a claimed single 26-test run. ESLint, TypeScript and configured Python Ruff passed. The production-build result is recorded below when finished.

The first full browser run exposed a duplicate risk-control label and initial hydration input races. Labels/loading gates were fixed. Browser feature flows now pace requests within the real 120/minute quota; API rate limits were not weakened. One known non-fatal Starlette/httpx deprecation warning remains.

Actual one-/two-/paid-transfer and chip recommendations for this manager remain gated until exact selling prices are entered. Isolated synthetic regression fixtures cover those solver paths, selling-profit rounding/losses, cash constraints, transfer hits, multiple free transfers, club/formation limits and infeasibility. They do not establish the manager's unknown finances.

This is single-deadline planning over aggregate 1/3/5-GW forecasts. Sequential future transfer/rollover optimization, learned future prices, correlated bench/automatic-substitution contribution and exact individual attribution of whole-XI/captain gains remain incomplete. Current liquidation value is not a prediction of future appreciation. Free Hit is temporary and restricted to 1 GW; GW20 has a conservative eligibility gate. No production-completeness claim is made for the entire transfer-engine specification.

The production Webpack build passed and the frontend restarted on port 3000. The new manager settings additionally clear ownership/financial confirmations when the manager ID changes, and owned-player club labels resolve through the actual club directory. These final presentation safeguards are rechecked by TypeScript/lint and the transfer-specific browser checks; final build restart is repeated below.
Final production Webpack build passed after the manager-state and club-label safeguards; frontend restarted on 127.0.0.1:3000 and FastAPI remains on 127.0.0.1:8000. Both transfer-specific browser checks passed again after those safeguards. Real-manager nonzero transfers remain deliberately gated on exact selling prices.
