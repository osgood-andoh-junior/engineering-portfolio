# Recovery security

Phase 4 adds named accounts and separates the requester from the approving administrator. The [current identity and audit model](security-model.md) describes the migration from the shared token.

Recovery execution defaults to disabled. Set `RECOVERY_ENABLED=true` only for a local simulator stack. The existing administrator credential authenticates the API and dashboard. `RECOVERY_OPERATOR` labels that shared local principal in the audit trail. A deployment with multiple humans needs separate identities to attribute approvals individually.

An intervention request binds the incident, target, action, operator, and idempotency key. The operator confirms that specific request within five minutes. A PostgreSQL transaction lock serializes execution and emergency stop. Only the incident service and configured local upstream services are eligible. The two supported actions use typed database updates. Each incident permits two execution attempts, and each target has a ten-second cooldown and one verification in flight.

Approval, action, audit records, and resulting simulator state commit together. A repeated execute request returns the existing execution. Database lock and statement timeouts bound each operation. The monitoring deadline is capped at five minutes. With monitoring offline, the UI shows expired verification until a worker records evidence. On recovery, incident closure plus a post-action healthy probe supplies verification. This establishes observed recovery after an action without attributing causality.

Emergency stop blocks further execution and leaves completed changes and ongoing verification intact. An explicit resume invalidates pending approvals from before the resume. Both operations are audited. Only the fixed local simulator configuration and runtime tables are mutated. Policy experiments have no path to live execution.
