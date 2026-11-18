# Security model

Provision the first named administrator from a trusted local terminal with `uv run python -m backend.identity <username>`. The command prompts twice for a password and never creates a default credential. Once an account exists, the API rejects the former shared token. Remove ADMIN_TOKEN from the API and dashboard environment after migration. Earlier audit records retain their legacy attribution.

Passwords use salted PBKDF2-HMAC-SHA256 at 600,000 iterations. Server-side sessions use hashed random bearer credentials with a 30-minute lifetime. The dashboard stores the bearer in a same-site HTTP-only cookie. The API checks the active account and role per authenticated request. Public Phase 1 health and synthetic telemetry reads remain available on loopback. Viewer has authenticated read access to reports, operator can run simulations and request interventions, and administrator can approve execution, manage topology and accounts, verify the audit chain, and operate the emergency stop. Administrator-only account changes cannot remove the last active administrator.

Recovery continues to use typed local actions, individual confirmation, cooldowns, bounded attempts, and a persistent stop. Approval and action are distinct operations. The requester and confirming administrator can be different people. Administrative operations are intended for local use. There is no remote identity provider, MFA, or distributed login rate limiter.

## Audit verification

New recovery and identity events are chained in PostgreSQL using SHA-256 over the record ID, previous digest, and canonical JSON payload. Recovery records include the approval reference and before/after state when available. Phase 3 history remains accessible separately. Export the new chain from Audit Verification. Verify it and save the displayed checkpoint to independent trusted storage. Later verify an export against that checkpoint.

```powershell
uv run python -m backend.audit_chain .\cloudrescue-audit.json --checkpoint .\cloudrescue-checkpoint.json
```

A checkpoint authenticates a prefix only if its storage is trusted. It detects rewrites or truncation of the anchored prefix. An unanchored chain can detect inconsistent records, but a privileged attacker can rewrite the entire chain. Records appended after the checkpoint have internal integrity only until independently anchored.
