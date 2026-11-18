# Deployment readiness

> Historical frontend-only checklist. Current full-stack operational requirements are in `../deployment/DEPLOYMENT_PLAN.md`.

**Not approved for production. No deployment or GitHub publication is authorized.**

## Environments

- Local: `npm run dev`, local fixtures, no secrets.
- Test: deterministic fixtures, jsdom and production-build Playwright.
- Staging: future isolated HTTPS deployment with noindex, sandbox providers and test-only data, approval required.
- Production: future approved domain, secure backend, verified inventory, policies, payments and operational controls.

`NEXT_PUBLIC_SITE_URL` is optional and public: absolute HTTP(S) origin used for metadataBase. It contains no secret and does not enable indexing. No server-only configuration is consumed now. Add validated server-only configuration at the backend integration boundary, never expose private values to a client bundle.

## Release blockers

**High:** absent backend/auth/order/inventory/payment/shipping/notification services; unapproved business content, policies and inventory. **Medium:** pending approved Figma/logo/photo review, final accessibility/device validation, nonce CSP, field performance measurement and full visual regression baselines. Replace samples explicitly before enabling sales or search indexing.

Production needs scoped secrets, secure HTTP-only sessions, authorization, CSRF protection, request limits, idempotent orders/payments, authenticated webhooks and reconciliation. Verify rollback, backups/restore, migrations, support channels, incident ownership and domain/TLS before release. Run all CI gates and investigate any audit findings.

## Observability plan

Choose monitoring only when the backend architecture is approved. Capture safe frontend error identifiers and release versions, server structured logs with request correlation IDs, backend health/readiness, availability and real-user performance. Alert on payment failures/reconciliation mismatches, stuck orders, duplicate webhook patterns and fulfilment failures. Scrub personal data and secrets, define retention/access policies, and test alert routing and runbooks. No paid monitoring service is installed.

CI tests are prepared in `.github/workflows/quality.yml`; they have not been run on GitHub. Before public repository creation obtain explicit approval and use the requested private `graceshield-frontend` name. Never force-push. Before deployment obtain explicit approval independently.
