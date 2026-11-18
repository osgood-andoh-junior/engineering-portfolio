# Deployment and operations plan — not authorization to deploy

No deployment/push/cloud creation is authorized. Existing code is for local full-stack development against approved hosted databases. Publication target, once explicitly approved, is a private `graceshield` monorepo. Never force-push or publish secrets.

## Environment separation

Development: local Next/FastAPI, managed dev PostgreSQL, labeled seed inventory, test-only customer details, disabled payments. Testing: dedicated cloud branch/database and credentials, explicit host/name guard, synthetic identities and deterministic fixtures. Production: separately approved project/database/credentials with HTTPS, reviewed policies/inventory/providers and operator controls. No local PostgreSQL/Docker is required for ordinary development or CI.

## Production database requirements

Before any production migration: confirm backup schedule/retention, PITR availability for the chosen provider plan, restore procedure and drill results, recovery objectives, independent operator access, least-privilege application/migration roles, private access controls where available, TLS verification, credential rotation, provider connection limits and per-worker pool budgets. Monitor connection saturation/slow queries/storage and migration duration. Review expand/contract changes, lock/statement timeouts, rollback and forward-fix procedures; obtain explicit approval. Alembic/CLI currently refuse production operational changes.

## Services and reliability

Run supervised API/frontend processes with request/time/body limits, exact trusted proxy configuration, origin/cookie/CSRF verification, environment secrets injected by the hosting secret manager and no public customer caching. Schedule reservation expiry at least once per minute using a controlled worker/cron/task service invoking the operational CLI in the approved environment; the current development CLI blocks production until reviewed. Monitor scheduler lag; checkout’s opportunistic expiry is not a substitute for reliable unattended release.

Add retention jobs for expired sessions/account tokens/rate buckets, durable transactional notification outbox/retries and reconciliation jobs when providers are approved. Define idempotent webhook retry/late-payment/refund handling and human reconciliation runbooks. Do not enable live payments merely by setting a secret; provider implementation and verification are required.

## Observability and incident readiness

Backend liveness/readiness, generated request IDs, structured method/status logs and audit events exist. Select approved error tracking and metrics only after privacy/security review; redact personal data/tokens. Plan alerts for availability/readiness, DB failures/connections, checkout conflicts, reservation expiry lag, stuck orders, payment failures/reconciliation mismatches, duplicate/invalid webhooks and fulfilment errors. Define ownership, escalation, retention/access limits and restore/rollback drills. No paid monitoring product is installed or claimed active.

## Release gates

All cloud migrations/integration/concurrency/full-stack tests must pass against isolated test data; frontend/backend lint/type/unit/build/audit gates must be reviewed; no unresolved high security findings; approved logo/Figma/photos/content/policies/support channels; verified email and payments; shipping/tax rules; manual accessibility/device review; representative performance measurements; backups/restore/monitoring; explicit founder approval for repository publication and deployment separately.
