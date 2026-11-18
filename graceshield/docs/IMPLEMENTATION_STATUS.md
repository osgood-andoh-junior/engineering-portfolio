# Full-stack implementation status

The full-stack brief supersedes the prior frontend-only scope. Existing frontend work was preserved under `frontend/`; backend code and managed-PostgreSQL setup were added under `backend/`. No cloud resource, deployment or remote repository was created.

## Implemented in code

- FastAPI modular monolith, Pydantic inputs/public contracts, SQLAlchemy 2/psycopg hosted TLS connections, configuration guards, explicit Alembic initial migration for 22 tables, idempotent development seed, safe operational CLI and OpenAPI.
- Argon2id customer registration/login/logout/me, server-managed hashed opaque sessions, CSRF/Origin validation, rate limits, email verification/reset token workflows, admin bootstrap/RBAC and safe customer data views.
- Published catalogue/category/search/filter/sort/pagination APIs, protected category/product/variant/image-reference management, inventory adjustments/movements/low-stock records and audit events.
- Persistent guest/customer carts, login merge and backend price calculation; idempotent checkout preparation with configured shipping, product/inventory locks, pending orders, immutable line snapshots, reservation expiration/cancellation and controlled fulfilment states.
- Payment Protocol, fail-closed initialization/webhook routes and internal verified-event transaction processing, duplicate/stale/replay-window/amount safeguards. Fake adapter exists only in tests; no live provider.
- Typed/Zod frontend API integration, working authentication forms and token pages, backend carts/checkout/account/order interfaces, protected admin UI and preserved storefront visuals. No runtime mock catalogue fallback.
- Backend/front-end tests, guarded cloud concurrency/integration/browser suites, CI and current documentation.

## Requires configuration and empirical verification

No development/test database URLs were provided. **No cloud database was created or connected, no migration was applied, and PostgreSQL integration/concurrency/full-stack customer/admin journeys have not been executed.** Those features cannot be called complete under the requested definition of done yet. Follow `docs/database/NEON_SETUP.md` and supply credentials locally, not in chat.

Email delivery, shipping coverage/fee, approved real inventory/assets/business content and payment provider are unconfigured. Shipping/verification block checkout when missing. Payments remain disabled. Reservation release needs an operational schedule, not merely a configured expiry timestamp.

## Deliberate limits / remaining work

Admin UI supports basic primary-image/product/variant creation and inventory adjustments; advanced multi-image/variant editing and uploaded image storage need further work. Payment initialization/refund/reconciliation/provider-specific signature wiring requires provider approval, implementation and tests. No commercial policies, tax rules or delivery promises are invented. Durable email outbox/retry, retention jobs, monitored scheduler, production proxy/security hardening, approved Figma/logo/photos, full manual accessibility and production-like performance measurements remain launch work.

See `docs/FULL_STACK_REPORT.md` for checks actually executed. Historical frontend-only documentation is labeled as such; its previous test/performance claims do not establish current full-stack correctness.
