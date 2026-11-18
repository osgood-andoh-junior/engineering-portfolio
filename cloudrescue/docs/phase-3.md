# Phase 3 proposal: recovery policy evaluation

The implemented Phase 3 behavior is documented in [Recovery engine](recovery-engine.md).

Start with a dry-run policy evaluator. Feed it saved replay frames and compare simulated decisions with the observed baseline. Version policies, graph snapshots, input evidence, and evaluation thresholds so another operator can reproduce the result.

- Model circuit breakers with closed, open, and half-open states. Measure error exposure and retry load.
- Model token-bucket rate limiting. Track deliberate rejections separately from service failures.
- Model replica failover with promotion delay, readiness, replication lag, and failback conditions.
- Score recovery time, errors, dropped work, and resource cost. Use both scripted faults and counterexamples where intervention would make things worse.

An execution layer would require separately authorized targets, action allowlists, scoped credentials, human approval, idempotency keys, and explicit rollback plans. Validate policies inside the simulator before considering execution. Confidence from Phase 2 should never act as the sole trigger.

OpenTelemetry can add trace and metric evidence to later versions. Optional AI assistance could summarize redacted evidence with source references after deterministic replay provides a baseline. Keep control decisions in versioned policies.
