# Architecture decisions

## Full-stack phase (2026-10-16)

The new brief supersedes the frontend-only boundaries below. Preserve the storefront under `frontend/`; add a PostgreSQL-only FastAPI modular monolith under `backend/`. Use managed TLS database connections with separate guarded tests, no SQLite/Docker fallback, explicit frozen Alembic migrations, hashed opaque sessions with cookie/CSRF controls, backend-authoritative pricing and transaction locks, real account/cart/order APIs, and fail-closed payment/email/shipping configuration. See `SYSTEM_OVERVIEW.md` and `FULL_STACK_PLAN.md`. Prior decisions below describe the earlier phase and are retained as history.

1. **Next.js 16 / React 19 / Tailwind 4**: use current compatible package families and npm lockfile. Separate lint from builds as required by current Next.js. See official Next.js installation and Tailwind Next.js installation documentation, reviewed during setup: https://nextjs.org/docs/app/getting-started/installation and https://tailwindcss.com/docs/installation/framework-guides/nextjs . Exact installed versions are in the lockfile.
2. **Server catalogue with native GET forms**: accessible, shareable URL state and predictable history without a new state-management dependency. Filters apply explicitly rather than on every keystroke.
3. **Small cart React context and pure reducer**: sufficient for a single local cart; no global store dependency. Versioned Zod parsing contains untrusted storage.
4. **No authentication simulation**: disabled credential inputs and clear service status avoid suggesting account protection that does not exist.
5. **No fake order state**: checkout only validates in memory. Confirmation describes validation, not order creation. Payment fields are absent.
6. **Demo indexing disabled**: root metadata noindex/nofollow, robots disallow, empty sitemap. An origin alone cannot enable indexing.
7. **Local SVG and fonts**: deterministic, self-contained preview with stable dimensions. Product views are illustrations rather than falsely attributed photographs. Two gallery views demonstrate local interaction; real distinct product views require supplied assets.
8. **CSP baseline**: deny framing, plugins and foreign origins. Inline script/style allowances support current framework rendering; nonce/hash hardening remains a release requirement. No claim of complete XSS mitigation.
9. **Information pages report missing policy decisions**: avoids inventing commercial terms, delivery promises or contact information.
