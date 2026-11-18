# GraceShield system overview

## Boundaries and structure

`frontend/` is the preserved Next.js App Router interface. `backend/app` is a FastAPI modular monolith, with core config/security/errors, SQLAlchemy database/models, Pydantic contracts, catalogue repositories, transaction-oriented cart/order/payment services, API modules and external integration boundaries. `backend/alembic` contains a frozen initial PostgreSQL migration, not runtime `create_all`. `backend/tests` separates pure/security checks and credential-dependent PostgreSQL integration tests. Root CI/docs coordinate both applications.

Browser `/api/v1` requests proxy through Next to a private FastAPI origin. Server-rendered catalogue pages call the private origin directly. A Zod adapter validates external responses and maps image contracts into existing components. Runtime catalogue/cart/account/order flows have no fixture fallback; seed data is explicitly imported into the development database. Old local-cart pure helpers remain regression-test material, not persistence authority.

## Authentication and authorization

Argon2id credential hashes, random opaque tokens stored as SHA-256 hashes, HTTP-only SameSite=Lax session cookies, configurable Secure attribute and fixed expiry. Login rotates token/CSRF values, logout deletes the session, password reset invalidates all sessions. CSRF requires both the stored session token and exact allowed Origin on cookie-authenticated mutations. Roles are normalized; public registration rejects extra fields and cannot assign roles. Verified admin authorization runs on every admin endpoint. Email token workflows use expiring single-use records and configured gateway delivery only.

## Commerce transaction model

Backend catalogue exposes only published products in active categories. Carts store variant IDs/quantities and calculate current server prices; authenticated carts are shared across sessions and merge guest lines up to quantity bounds, surfacing unavailable stock. User/session row locks serialize cart mutations. Cart content does not reserve inventory.

Checkout requires a verified account and explicit shipping configuration. It locks the customer/cart, replays existing idempotency keys safely, validates current publication/variants/stock, locks products/inventory consistently, snapshots prices in immutable order lines and reserves inventory. Pending orders expire after configured minutes (default 15); cancellation/expiration releases reservations. Execute `python -m app.cli expire-reservations` regularly using a supervised scheduler; checkout also opportunistically expires pending reservations. The application does not install a scheduler or claim automatic background execution without one.

Only internal verified payment-event processing can mark an order paid and consume reserved physical inventory. Public/admin order transitions cannot forge payment status or fulfil unpaid orders. Payment provider selection/initialization/refund/reconciliation and authenticated webhook adapters remain approval/configuration work; no live provider is installed. Test-only adapter code exists solely under tests.

## Reliability and limits

PostgreSQL/psycopg only, small pre-ping pool, TLS validation, safe errors and no sensitive parameter logging. A readiness endpoint queries connectivity; schema migration/version checking remains an operational check. Structured logs carry generated request IDs/method/status, not bodies/query strings or exception SQL. Audit logs record actor/action/resource, with no secrets.

Catalogue reads currently use `no-store` for correctness during integration; no customer data is publicly cached. Revisit public catalogue caching with explicit invalidation before high-volume launch. Synchronous FastAPI endpoints use the worker thread pool; connection budgets must match workers/provider limits. Database rate limits coordinate processes; production reverse-proxy client identity must be configured and verified before real traffic.

No Figma/PRD/approved logo assets, shipping policy, real catalogue, payment provider, email provider or database credentials were supplied. Existing visual design is preserved; the provisional logo and illustrations still require approval. See implementation status and full-stack report for verification boundaries.
