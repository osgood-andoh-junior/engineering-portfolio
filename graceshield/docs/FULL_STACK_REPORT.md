# GraceShield full-stack engineering report

Date: 2026-10-16. **Local implementation prepared; database-backed completion remains blocked on private cloud database configuration. Not production-ready.** No cloud resource, production migration, deployment, GitHub repository or push was performed.

## 1. Frontend features

Preserved the Next.js storefront under `frontend/`: homepage, catalogue/category/product pages, gallery, search/filter/sort/pagination, cart, checkout, auth/account/order-history and information routes. Added verification/reset pages and protected admin overview/products/categories/inventory/orders/customers. Replaced runtime catalogue/cart fixtures with validated FastAPI transport. No unavailable service is replaced by fake inventory or a fake authenticated session. Existing colors/fonts/layout/illustrations remain; no approved Figma/PRD/logo asset was supplied.

## 2. Backend modules

FastAPI modular monolith with Pydantic contracts, SQLAlchemy/psycopg session management, hosted TLS configuration guards, Argon2id/opaque session security, authorization/CSRF/rate limiting, catalogue repository, cart/order/inventory/payment services, safe errors/request IDs, audit records, liveness/readiness and operational CLI. Source is implemented and unit-tested where feasible; actual PostgreSQL-backed behavior is **not yet empirically verified**.

## 3. Database tables and migrations

22 normalized PostgreSQL tables cover the requested identity/catalogue/inventory/cart/order/payment/shipment/audit entities plus sessions/account tokens/rate limits. UUIDs, FKs, unique/check constraints, indexes, UTC timestamps and integer pesewa money are defined. Initial Alembic revision `0001` is frozen explicit DDL. Offline migration rendering passed; **no migration has been applied to a cloud database**. Seed is explicit, non-production and idempotent. Test guards reject unsafe environment/host/name/identity configurations. No local PostgreSQL, Docker or SQLite is used.

## 4. API endpoints

Versioned auth/session/me/verification/reset, public categories/products, cart operations, checkout preparation, owned orders/cancellation, admin catalogue/inventory/orders/customers/metrics, fail-closed payments/webhook and environment endpoints. OpenAPI snapshot and route details: `api/openapi.json` and `api/API_REFERENCE.md`. All protected operations enforce backend permissions; client-supplied prices/roles/stock/payment status are not trusted.

## 5. Authentication status

Registration/login/logout/current user, secure password hashing, hashed random session tokens, login rotation, expiry/revocation, exact Origin/CSRF checks and database-coordinated rate limits are implemented. Email verification/reset use expiring single-use tokens; fragment-based links avoid placing tokens in server URL logs. Public registration cannot assign admin roles. Bootstrap is explicit, prompted and audited, with no default password. **Real session/email workflows await cloud verification and configured delivery.** Disabled delivery reports no email sent; it does not fabricate success.

## 6. Products and inventory

Published-only public queries, category archiving, protected product/category CRUD, variants, controlled existing image references, stock adjustments, movement history and low-stock counts are implemented. Uploads are deliberately absent; the image storage Protocol currently validates approved repository assets. Ordered row locks and stock constraints are designed to prevent overselling; a two-connection contention test exists but is **unexecuted without cloud test credentials**. Seeded products remain labeled demonstration content, not approved real stock.

## 7. Cart and checkout

Server-persisted guest/customer carts, quantity/availability checks, login merging and current server prices are implemented. Browser storage has no authentication authority. Checkout validates customer/address, requires verified email and explicit delivery configuration, serializes cart/idempotency checks, snapshots prices, reserves inventory and creates a pending-payment order. Retries with conflicting details fail safely. Missing shipping configuration blocks preparation rather than inventing charges. Frontend validation/transport tests pass; cloud cart/checkout transactions still require verification.

## 8. Order lifecycle

Pending payment → verified paid → processing → shipped → delivered, with controlled cancellation/refund paths. Unpaid fulfilment and public/admin “mark paid” are rejected. Pending cancellation/expiration releases reservations; operational expiry command and opportunistic checkout expiry exist. **A supervised expiration schedule is still required for unattended release.** Immutable order-line snapshots have no mutation endpoint. Owner filtering and server-admin roles protect access; these database-backed guarantees require the isolated integration run.

## 9. Payment readiness

Provider Protocol covers initialization, verification, authenticated webhook parsing, refund and reconciliation. Internal verified-event handling uses transactional order/payment locks, amount/currency checks, event uniqueness, stale/duplicate protection, inventory consumption and late-payment reconciliation. Timestamp replay-window enforcement is prepared. No approved provider/credentials were supplied, so live initialization/webhooks fail closed. Test-only adapter code is confined to tests. **Provider-specific initialization/refund/reconciliation/signature wiring is incomplete until provider approval and integration work. No payment success has been exposed to customers.**

## 10. Admin dashboard

Interfaces and authorized APIs cover stored overview counts/sales, category/product creation/edit/archive, basic variant creation, inventory adjustments, order transitions and customer overview. Changes are audited; no business analytics are invented. Advanced multi-image/variant editing, stock history presentation and uploads need further UI/storage work. Current APIs expose movement history. Authenticated database-backed admin journeys are **not yet run**.

## 11. Automated checks

| Check                                      | Observed result                                                                                 |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Backend Ruff                               | Passed                                                                                          |
| Backend configured mypy modules            | Passed (9 source files)                                                                         |
| Backend pytest                             | **54 passed, 6 cloud integration cases skipped**                                                |
| PostgreSQL DDL/migration offline rendering | Passed; no connection or migration execution implied                                            |
| Missing DATABASE_URL startup behavior      | Confirmed clear setup failure; no fallback                                                      |
| Frontend lint/types/build                  | Passed after fixes                                                                              |
| Frontend Vitest/RTL                        | 28/28 passed, including fragment-token safety                                                   |
| Playwright shell desktop/mobile            | **8 passed**; strict HTTP 404, keyboard/focus, unavailable-service/auth gates, axe and overflow |
| Full-stack Playwright                      | **6 skipped**; requires configured guarded test backend/database/accounts                       |
| Backend dependency audit                   | No known vulnerabilities after updating project-local pip to 26.2.1                             |
| Frontend production npm audit              | Zero vulnerabilities                                                                            |
| Full frontend npm audit                    | **Failed: 5 high development-tool entries** in one braces/ESLint chain                          |
| GitHub Actions                             | Prepared; not executed on GitHub                                                                |

Discovered/fixed: checkout label/error association retained from prior phase, CSRF transport integration, root script argument forwarding, monorepo build root, server/client admin constant boundary, strict pre-stream 404 routing, login touch-target spacing and reset/verification token URL exposure. No failing assertion was disabled. The current HTTPX/Starlette test client emits a deprecation warning; tests still pass, and a reviewed future dependency update is warranted.

## 12. Security findings

- **High:** Missing development/test database credentials block migration, integration/concurrency and true full-stack verification; do not infer correctness from code/HTTP schema alone.
- **High development-tool finding:** full npm audit still reports the `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces` chain, [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm). Full audit CI remains enabled. Runtime npm and backend audits are clear; these are separate results.
- **High launch blockers:** provider/email configuration, approved business/legal/inventory/shipping/tax decisions and real credentials/operations are absent.
- **Medium:** CSP nonce/hash hardening, production trusted-proxy/client-IP behavior, durable email delivery/outbox, retention/expiry monitoring, image upload storage, backup/restore and privileged audit procedures require review.
- No critical exploit was identified in the available local checks; no penetration test or compliance claim is made.

## 13. Accessibility and performance

Shell axe A/AA checks and overflow tests pass across seven routes at desktop/mobile sizes; keyboard skip link and mobile dialog focus return pass. Authenticated catalogue/checkout/admin accessibility, full manual keyboard/screen-reader/zoom/device coverage and reviewed visual baselines remain unverified.

Current unavailable-API mobile shell lab run: **LCP 3,228ms (misses 2.5s target), CLS 0.001522, FCP 1,532ms, 321,477 resource bytes, DOMContentLoaded 2,660ms**. INP is unmeasured. This is one cold local Chromium run with 4× CPU throttle, 150ms latency and 1.6Mbps download, not full-stack/field performance. See `testing/FULL_STACK_PERFORMANCE.md`; previous frontend-only metrics are explicitly historical.

## 14. Known limits and configuration blockers

No cloud URLs or approved Figma/PRD/assets/provider/business policies were supplied. No migration, database seed, admin bootstrap or cloud test operation was executed. No actual email/payment/shipping promise exists. Operational expiry scheduling, cleanup/outbox/monitoring and advanced admin/UI/storage/provider work remain incomplete. Local shell behavior is verified; commerce transaction behavior is not yet verified against PostgreSQL.

## 15. Startup and Git

See root README and `database/NEON_SETUP.md` for Windows venv/dependencies, private `.env` setup, separate Neon development/test databases, TLS/direct migration URLs, migrations, explicit seed/admin bootstrap and two local processes. Root `npm run dev` starts the preserved frontend; run FastAPI from `backend/`. Use http://127.0.0.1:3000 to match the default Origin. No local database/Docker is required.

Work is on `feat/full-stack-commerce`; prior work is preserved in Git history. Local commits/status are reported in the handoff. No remote/push/publication/deployment is performed; intended private monorepo name is `graceshield` only when publication is explicitly approved.

## 16. Next requirements before completion or launch

Configure isolated managed development/test connections privately, run migrations/connectivity/seed and all cloud integration/concurrency/full-stack tests, fix any failures, then verify real email and approved shipping settings. Resolve the development audit finding, approve design/content/policies/stock, finish provider/storage/advanced admin/operations work, measure configured performance, perform full security/accessibility review and staging/backup/restore verification. Obtain explicit approval separately before any cloud resource creation, production operation, GitHub publication or deployment.
