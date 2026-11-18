# Security review and requirements

> Historical frontend-only review. See `security/SECURITY_MODEL.md` for current full-stack controls and launch blockers.

## Current controls

No backend mutations, secrets, credential sessions, analytics or payment fields. Checkout never submits/persists personal data. React text rendering avoids raw HTML. URL filters are bounded; money is integer minor units; storage is parsed through a strict value schema, capped and reconciled with known sample products. Internal links are fixed or generated from controlled slugs. Invalid environment origins fail configuration validation. `.env` files are ignored except placeholder `.env.example`.

Headers: nosniff, deny framing, strict-origin referrer policy, restricted camera/microphone/location, self-only CSP default/connect/font/image sources with data images. No dynamic external image loader. No sensitive console logging. Error UI omits stack traces.

## Remaining production work

### Observed dependency advisory (2026-10-15)

The full audit reports five high-severity entries in a single **development-only** chain: `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces`. The underlying advisory is [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm), stack exhaustion on deeply nested glob patterns. Registry latest `braces` is 3.0.3, inside the affected range; current `eslint-config-next` is 16.4.2. No compatible upstream fix was available during implementation. The suggested automated downgrade to Next 14 lint configuration was not applied. The full audit CI gate deliberately remains failing until resolved. `npm audit --omit=dev` reports zero vulnerabilities. Do not feed untrusted glob patterns to development tooling.

- **High**: no authentication, authorization, order validation, payment processing, stock management or secure backend. Real commerce must stay disabled.
- **High**: approve privacy, terms, returns, business identity and actual inventory before launch.
- **Medium**: CSP currently permits inline scripts/styles for framework compatibility. Adopt per-request nonces or hashes, test framework hydration and remove script unsafe-inline before production. Evaluate report-only deployment first. HSTS belongs on HTTPS production hosting after domain readiness.
- **Medium**: define CSRF/origin protections, credential hashing/provider configuration, HTTP-only secure sessions, rate limiting, least-privilege backend roles and API validation before integration.
- **Low**: local cart is browser-controlled and may be modified by users or other scripts. It has no financial authority; backend reconciliation is mandatory.

Run `npm audit --audit-level=high` and review all dependency paths; lockfile/CI prevent silent resolution drift. Do not automatically apply breaking audit fixes. Review dependency lifecycle scripts and source changes before upgrading. CI has read-only repository permissions; review/pin action SHAs as part of supply-chain hardening. Do not log customer addresses, passwords, card data, cookies or access tokens. Store deployment/backend/payment credentials only in an approved secret manager, never `NEXT_PUBLIC_*`.

Use applicable OWASP ASVS/cheat sheets for the eventual backend security review. This frontend review is not a penetration test or compliance certification.
