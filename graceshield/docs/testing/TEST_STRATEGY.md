# Full-stack test strategy

## Executable layers

- Frontend Vitest/RTL: catalogue transforms/URL parsing, money, legacy cart pure invariants, API-backed cart restoration/CSRF/mutations, sample cards, local form validation and payment-disabled behavior. Test transports/fixtures live under tests; runtime code does not fall back to fixtures.
- Backend pytest unit/security: configuration/TLS/test-database guards, strict Pydantic contracts, Argon2id/token behavior, CSRF/origin/admin rules, inventory/totals/order transitions, PostgreSQL schema compilation and OpenAPI/safe-error contracts.
- Cloud PostgreSQL integration: registration/login/logout/authorization; category/product CRUD and publication; stock adjustments/audit; guest merge/cart/current backend prices; checkout/idempotency/cancellation/reservation release; simultaneous checkout contention; verified payment duplicate/stale handling. These are **not run without isolated cloud credentials**.
- Playwright shell (desktop/mobile Chromium): navigation, 404, local form errors, skip link/mobile focus return, authentication gates, axe A/AA and overflow checks under unavailable backend conditions.
- Full-stack Playwright (separate opt-in): registration/login/guest merge/admin denial, verified-customer pending order and authorized admin screens. Requires a running backend in guarded test mode, real cloud test DB, migrations, explicit demonstration seed and test-only account fixtures. No fake successful payment exists.

## Commands

From root: `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`. Backend: `backend/.venv/Scripts/ruff.exe check backend`, `backend/.venv/Scripts/python.exe -m pytest backend/tests -q`. Run mypy from `backend/` using `.venv/Scripts/mypy.exe` (selected security/config/rules/integration modules are configured). Dependencies are pinned in npm lockfiles and `backend/requirements.lock`.

Install Chromium with `npm --prefix frontend exec -- playwright install chromium`; run `npm run test:e2e`. Set `RUN_FULL_STACK_E2E=true` only after test setup; browser tests verify `/api/v1/environment` reports guarded test mode before mutations. `E2E_CUSTOMER_EMAIL/PASSWORD` and `E2E_ADMIN_EMAIL/PASSWORD` are synthetic account credentials stored in local environment/CI secrets, never committed. The helper `python tests/setup_e2e.py` refuses non-test DB configuration and provisions only example-domain test identities.

Cloud tests: follow `docs/database/NEON_SETUP.md`, set `APP_ENV=test`, `ALLOW_TEST_DATABASE=true`, explicit `TEST_DATABASE_URL/HOST/NAME`, `RUN_DB_TESTS=true`, then migrate and run pytest. If opt-in is set but configuration is unsafe, tests fail rather than skip. Most tests roll back an outer transaction; the concurrency case commits unique fixtures for real separate-connection contention and cleans only those tagged records. No database reset/truncate is used. Test mode cannot use the known development database.

## CI and review limits

GitHub Actions runs frontend/backend static/unit/build/security gates plus shell browsers. A separate cloud job requires configured isolated database/account secrets and runs real migrations/integration/full-stack smoke tests; absent secrets fail the setup check rather than fabricate a pass. No workflow has been executed on GitHub in this task.

Full manual keyboard/screen-reader/zoom/device coverage, production-like hosting/network performance and reviewed visual regression baselines remain outstanding. Prior frontend-only screenshots/performance are historical, not full-stack evidence. Current executed results belong in `docs/FULL_STACK_REPORT.md`. An axe pass is not WCAG certification, schema compilation is not migration execution, and a successful Next build is not end-to-end commerce verification.
