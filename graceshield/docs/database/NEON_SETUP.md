# Managed PostgreSQL setup — Windows, no PostgreSQL or Docker installation

No database or cloud resource has been created by this task. The user must create/configure approved resources or explicitly authorize a separate resource-creation action. Never use production for development/testing.

## 1. Account and environments

1. Visit the [Neon console](https://console.neon.tech/) and create/sign in to your account. Review provider terms and costs before selecting a plan.
2. Create an approved development project/branch and a database named `graceshield_dev` using the provider console. Choose an appropriate region for your application; no data residency promise is inferred.
3. Create a **separate test branch/project**, with a dedicated database named `graceshield_test` and a separate least-privilege role. Do not reuse the development database. Tests require explicit host/name allowlisting.
4. Keep production in a separately approved environment, preferably with separate project/access roles. Do not create, migrate or modify production as part of this task.

## 2. Connection strings and TLS

Use the console’s **Connect** control to obtain the PostgreSQL connection string for the correct branch/database/role. Copy it privately into `backend/.env` as `DATABASE_URL` (no quotes needed unless your editor requires them). Preserve the provider’s required TLS/query settings, including `sslmode=require` or stronger. Passwords containing reserved URL characters must be percent-encoded by the provider’s connection-string generator.

Use the **pooled** URL for application traffic where appropriate. Set `MIGRATION_DATABASE_URL` to the **direct/non-pooled** URL for the same development database for Alembic. Code uses psycopg, a small SQLAlchemy pool (3 + 2 overflow), pre-ping, 10s connect timeout and disabled prepared statements for pooled compatibility. Review limits for your selected plan. [Neon connection guide](https://neon.com/docs/get-started/connect-neon), [pooling](https://neon.com/docs/connect/connection-pooling).

No live URL is shown here. `.env.example` contains blank placeholders. The API accepts only complete hosted PostgreSQL URLs with TLS; localhost/SQLite are rejected. Configuration errors do not echo secret inputs. Public frontend variables must never contain database URLs.

## 3. Install, migrate and verify development

Follow README dependency/venv setup, then:

```powershell
Set-Location backend
.venv/Scripts/python.exe -m app.cli check-db
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic current
$env:ALLOW_DEMO_SEED='true'
.venv/Scripts/python.exe -m app.cli seed
.venv/Scripts/python.exe -m app.cli bootstrap-admin
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Seed is non-production, explicit and idempotent. It creates the eleven categories and eighteen labeled demonstration products only when absent; it never resets edited stock/prices. Bootstrap prompts for credentials without logging them, refuses existing admin/email collisions, uses an advisory transaction lock, and records an audit event. No default administrator password exists. Bootstrap confirms the privileged address through the operator procedure; do not expose this CLI to customers.

Visit `/health`, `/ready` and `/docs` on port 8000. `/ready` checks actual connectivity. Do not report a migration/connectivity success until these commands have run against your supplied database.

## 4. Isolated cloud testing

Privately configure `TEST_DATABASE_URL`, `TEST_DATABASE_HOST` (the exact hostname, with or without `-pooler`) and `TEST_DATABASE_NAME=graceshield_test`. Test URL must point to the explicitly allowlisted host/database and must differ from `DATABASE_URL`. A production guard URL can be supplied privately to the test runner only if needed for additional equality checks; production credentials are never required for tests.

```powershell
Set-Location backend
$env:APP_ENV='test'
$env:ALLOW_TEST_DATABASE='true'
$env:RUN_DB_TESTS='true'
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m pytest tests -q
```

The guard rejects missing acknowledgment, non-test mode, no host allowlist, database names not ending `_test`, mismatched host/name, SQLite/non-TLS and known development/production identities. No reset/truncate/drop command is used by tests. Most integration tests use outer rollback transactions; concurrency fixtures commit tagged records and delete only their own records afterwards. Rate-limit records may persist in this isolated database and require a controlled retention process. Never point these commands at development or production.

For isolated browser tests, start FastAPI with the test configuration, seed the test database explicitly, configure test-only verified customer/admin fixture accounts, and supply their credentials through environment variables. The test-only fixture helper refuses non-test configuration. Full-stack Playwright checks additionally verify `/api/v1/environment` reports guarded test mode before any workflow runs. Do not use real customer accounts.

## 5. Production preparation

No production migration is authorized. Current operational CLI and Alembic environment explicitly refuse `APP_ENV=production`. Before lifting that safeguard in a separately reviewed change: approve TLS/domain/session/cookie/proxy settings, least-privilege app and migration roles, connection budgets, backups/PITR availability and retention, restore drills, monitoring/alerts, credential rotation, expand/contract migrations, lock timeout planning, rollback/recovery procedures and operator approval. Provider features vary by plan; verify them rather than assuming retention or recovery guarantees.
