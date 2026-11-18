# Full-stack implementation plan

The 2026-10-15 full-stack brief replaces the prior frontend-only scope. Inspection found a clean committed Next.js frontend, 18 demonstration products, localStorage cart and deliberately disabled auth/checkout; no Figma/PRD/approved assets, Python on PATH or managed database credentials were supplied.

## Architecture and structure

Preserve the existing interface under `frontend/`. Add `backend/` as a synchronous FastAPI modular monolith: SQLAlchemy 2/psycopg repositories, explicit service transactions, Pydantic contracts, Alembic migrations, database-backed sessions/rate limits and operational CLI. Root documentation/CI spans both. Next proxies browser `/api/v1` calls to FastAPI so HTTP-only cookies remain same-origin; server catalogue requests use a private API origin. No database secrets enter frontend configuration.

## Database design

PostgreSQL only, UUID primary keys, UTC timestamps, explicit foreign keys/uniqueness/checks/indexes. Users/roles/user_roles/profiles/addresses; categories/products/variants/images; inventory/movements; carts/items; orders/immutable lines; payments/events; shipments; audit logs. Additional sessions, single-use account tokens and rate-limit buckets support security. Money uses integer pesewas. Order inventory is reserved transactionally using ordered row locks, with expiration/cancellation release. Paid state is accessible only through verified payment integration, not customer/admin request bodies.

## API modules and frontend integration

Versioned `/api/v1`: auth and current user; categories/products (public published records only); cart and merge; checkout preparation/orders; protected admin categories/products/inventory/orders/customers. Backend owns pricing, quantities, stock and all totals. Payment provider interface remains unavailable without approved provider configuration. Auth/email status never fabricates delivery. Replace runtime fixture imports with validated API data and reuse existing presentation components. Keep original fixtures only for isolated tests and explicit development seed input.

## Testing strategy

Pure pytest tests for security, validation, money, transitions and test-database guards; PostgreSQL integration tests require an explicitly named/isolated cloud test URL and guard marker. No SQLite substitute. Never auto-reset a database. Browser full-stack tests require configured API and isolated seeded test DB; absent credentials are reported as unexecuted, not passed. Retain frontend unit coverage, build/type/lint checks, add backend Ruff/mypy and isolated CI database secrets. No cloud resource creation or production migration is authorized.

## Milestones

1. Monorepo/configuration, schema/migration and Windows/Neon setup.
2. Secure sessions/CSRF, roles, account token workflows and bootstrap.
3. Catalogue/admin and inventory transactions/audit.
4. Guest/customer carts, merge, idempotent checkout, reservations/order lifecycle.
5. Payment contracts with no live/fake customer success.
6. Frontend API/auth/cart/checkout/admin integration.
7. Available local checks, credential-dependent integration checks, review/documentation.

## Decisions requiring business input

No approved shipping fees/coverage/policies, tax rules, email service, payment provider, production inventory or Figma assets exist here. Checkout preparation must fail closed until an explicit development shipping configuration is supplied; seed products remain visibly demonstration content. Cloud creation requires separate approval. Work proceeds on code and non-database tests while configuration is pending.
