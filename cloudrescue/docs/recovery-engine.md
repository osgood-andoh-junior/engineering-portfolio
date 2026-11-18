# Recovery engine

Policy Lab compares six variants against a shared traffic trace. Circuit breakers allow one half-open probe after cooldown. A token bucket controls admission. The failover router selects between a modeled primary and a lower-capacity standby, with health checks, cooldown, and two healthy primary ticks for routine failback. Retries use seeded exponential jitter, a per-run budget, a per-request attempt limit, and the remaining deadline. Only modeled safe requests with transient failures qualify.

The combined policy selects an instance each second, applies rate limiting before breaker admission, and lets the breaker veto retries. Retries consume the selected instance's capacity. Breaker state is separate for each instance. Live intervention supports a fault reset and a two-second simulated restart. A restart preserves the injected fault so monitoring can record an unsuccessful intervention.

Recommendations consume Phase 2 candidates and health checks. A corroborated cascade suggests a breaker, repeated transport failures suggest testing failover, and sparse transport evidence suggests bounded retries. HTTP 429 can suggest rate limiting. Insufficient or inconclusive evidence calls for investigation. Operators review risks and choose the intervention independently.

Migration 0003 adds recovery policies, policy versions, experiments, results, recommendations, approvals, executions, audit events, and simulator runtime. Each experiment persists its parameter version, seed, replay reference, and calculated results. The worker verifies executions using newly persisted checks and incident closure. Replay and experiments keep their own records.

Authenticated endpoints under `/recovery` expose `GET /policies`, `GET /center`, `POST /recommendations/{incident_id}`, `GET|POST /experiments`, `GET /experiments/{id}`, `GET|POST /approvals`, `POST /approvals/{id}/execute`, `POST /stop`, `POST /resume`, `GET /analytics`, and `GET /audit`.
