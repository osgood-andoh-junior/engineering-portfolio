# GraceShield full-stack commerce

Next.js + FastAPI modular monolith for Ghana (GHS), developed locally against **managed cloud PostgreSQL**. No local PostgreSQL or Docker is required or used. Live payments are disabled. No cloud resources, deployment or GitHub publication have been created.

**Configuration is required:** no database URL was supplied during implementation. The schema, migrations and integrations are implemented in code, but cloud-backed operation and full-stack journeys are not yet verified. No SQLite fallback or fabricated test success is used.

## Repository

- `frontend/`: preserved storefront, typed API transport, account/cart/checkout/admin interfaces, tests and local artwork.
- `backend/`: FastAPI, SQLAlchemy/psycopg, Alembic, session authentication, RBAC, inventory/order services and pytest.
- `docs/`: current architecture, database setup, API/security/testing and release notes.

## Windows setup

Install Node.js 24 LTS and Python 3.12+ (Python 3.12 tested). From PowerShell in the repository:

```powershell
npm --prefix frontend ci
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install --upgrade pip
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
backend/.venv/Scripts/python.exe -m pip install --no-deps -e backend
Copy-Item .env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

Privately fill `backend/.env` with your Neon development connection. Follow [Neon setup](docs/database/NEON_SETUP.md) for separate development/test databases, TLS and migration URLs. Never paste credentials into chat or commit them. Empty `DATABASE_URL` produces an explicit setup error.

```powershell
Set-Location backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.cli check-db
# Optional, non-production sample inventory; explicit opt-in only:
$env:ALLOW_DEMO_SEED='true'
.venv/Scripts/python.exe -m app.cli seed
.venv/Scripts/python.exe -m app.cli bootstrap-admin
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal from the repository root: `npm run dev`, then open **http://127.0.0.1:3000**. The default CSRF/CORS origin is exactly that origin; configure `FRONTEND_ORIGIN` if you change it. API docs: http://127.0.0.1:8000/docs . Browser calls are proxied through Next.js; database credentials never go to the browser.

## Checks

```powershell
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
backend/.venv/Scripts/ruff.exe check backend
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
```

Backend mypy checks selected security/configuration/rule/integration modules: run from `backend/` with `.venv/Scripts/mypy.exe`. Cloud integration tests require explicit isolated test configuration and `RUN_DB_TESTS=true`; without it they report **skipped**, not passed. Browser shell checks run with `npm run test:e2e`; full-stack checks require a running test-mode backend, migrated/seeded isolated cloud test database and `RUN_FULL_STACK_E2E=true`. See [test strategy](docs/testing/TEST_STRATEGY.md).

Development checkout requires verified email, explicit `SHIPPING_FEE_MINOR` in integer pesewas and `SHIPPING_REGIONS` matching supported Ghana regions. No commercial shipping defaults are invented. Email requires a reviewed HTTP delivery gateway; unconfigured verification/reset requests report that no email was sent. Use only test customer details and unique development passwords.

See [system overview](docs/architecture/SYSTEM_OVERVIEW.md), [schema](docs/database/SCHEMA.md), [API reference](docs/api/API_REFERENCE.md), [security model](docs/security/SECURITY_MODEL.md), [status](docs/IMPLEMENTATION_STATUS.md) and [deployment plan](docs/deployment/DEPLOYMENT_PLAN.md). The previous frontend-only report is historical and does not describe this full-stack phase.
