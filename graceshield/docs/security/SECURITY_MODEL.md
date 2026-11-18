# Security model and remaining launch requirements

## Implemented controls

- PostgreSQL/psycopg only, TLS-required hosted URL validation, small pool/pre-ping/timeouts, secret configuration redaction, no raw SQL string interpolation of user inputs.
- Argon2id via maintained pwdlib; opaque random session/account tokens hashed at rest, HTTP-only SameSite cookies, login rotation, fixed expiry, logout and reset revocation.
- Verification/reset links use URL fragments, read and removed by the browser before submission, so tokens are not placed in server URL/query access logs. No tokens are logged by application code.
- Exact Origin and CSRF checks on cookie-authenticated mutations; public registration forbids extra role fields; verified server-side admin authorization; customer order ownership filtering.
- Database rate limiting with independent committed transactions so failed logins still consume attempts. Proxy client identity is a production configuration dependency.
- Pydantic input constraints, Zod transport validation, controlled image references, safe React output, no raw HTML, no authentication localStorage or card data.
- Backend-authoritative pricing/stock/totals, transaction row locks, idempotency constraints, immutable order snapshots, reservation releases, controlled order transitions and internal-only verified payment event processing.
- Duplicate provider-event uniqueness, stale payment protection, amount/currency checks and late-payment reconciliation. No installed live/fake customer payment provider.
- No body/query/credential logging; generated request IDs and safe structured events; audit records for sensitive changes. Existing frontend security headers remain in place.
- Test database requires explicit test mode/acknowledgment/host/name and a `_test` database suffix, rejects known development/production identities. No SQLite, auto-reset or production migration fallback.

## Security-sensitive configuration

Use separate development, test and production credentials and roles. `.env` files are ignored recursively; example files contain no credentials. `DATABASE_URL` and email credentials are backend-only. `API_INTERNAL_URL` is server-only frontend configuration, not a database URL. The frontend public origin is nonsecret. Use unique development passwords and synthetic customer details.

Production must use HTTPS, `COOKIE_SECURE=true`, exact approved origin, trusted reverse-proxy configuration, least-privilege database access and controlled operator access. Cookie-authenticated requests must never blindly trust client-supplied forwarding headers. Current proxy behavior groups local requests under local upstream identities; rate-limit behavior must be verified against the real deployment proxy before launch.

## Unresolved risks / release gates

- **High:** No managed database credentials were supplied, so migrations and PostgreSQL integration/concurrency/full-stack tests have not run. Code alone is not proof of transaction/security correctness.
- **High:** Approved payment provider credentials, implementation/signature tests, reconciliation/alerting and real transactional email delivery are unconfigured. Live payments remain disabled; pending development orders cannot be fulfilled.
- **High:** Business identity/contact details, policies, approved stock/pricing, shipping/tax decisions and real assets require founder/legal review.
- **High development-tool finding:** the existing frontend full npm audit has a reported braces/ESLint chain advisory without an available compatible fix at the previous inspection. Recheck before release; the full CI audit remains enabled. Production runtime npm audit and backend pip audit results must be recorded separately, never conflated.
- **Medium:** CSP still allows inline framework scripts/styles; adopt and test nonce/hash policy. Plan HSTS only after HTTPS/domain readiness. Restrict or disable interactive API docs for production as appropriate.
- **Medium:** Email is currently a direct configured HTTP gateway contract; durable outbox/retry/delivery-state semantics and provider-specific response verification need review. Messages are not logged; disabled/unavailable delivery is reported honestly.
- **Medium:** No image uploads are enabled. Add scoped object storage, MIME/magic-byte/dimension/size checks, safe filenames, malware handling and approved SVG policy before uploads. Controlled asset references currently avoid this attack surface.
- **Medium:** Personal-data retention/deletion, session/token/rate-limit cleanup, privileged audit access, monitoring, backup/restore drills and full manual accessibility/security review remain required.

Use OWASP ASVS and applicable cheat sheets for a separately scoped production security review. Automated tests/audits are not a penetration test or compliance certification.
