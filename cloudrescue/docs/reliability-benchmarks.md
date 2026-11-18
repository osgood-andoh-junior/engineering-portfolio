# Reliability benchmarks

Run `uv run python -m backend.recovery_lab` from the repository root. The default seed is 42. The five workloads are a primary outage, shared upstream outage, overload, transient errors, and a healthy burst. Each runs for 36 one-second steps. Requests arrive at evenly spaced offsets. The primary and standby have budgets of 12 and 7 attempts per step. Requests and retries charge capacity to their arrival step. The model treats one in five operations as unsafe to retry. Instance and dependency health are exogenous, and the standby shares the upstream dependency.

Replay experiments use a bounded 36-second slice beginning at the first stored observation. Observations provide primary and upstream availability at the last known value. Traffic, standby capacity, retries, and other interventions remain modeled. The projection does not infer demand or derive causal production effects from historical checks.

- A modeled second is impaired below 90% request success. Detection requires three consecutive impaired seconds and recovery requires three consecutive acceptable seconds.
- MTTD, mean diagnosis delay, and MTTR average the elapsed time from the start of the first detected impaired streak to detection, first emitted diagnosis after detection, and confirmed recovery respectively. Means exclude runs without the corresponding event. Total downtime counts all impaired seconds across all runs.
- Recovery success divides recovered detected runs by all detected runs. Request success divides successful requests by original arrivals, including rejected requests in the denominator.
- Error-budget consumption divides unsuccessful arrivals by 1% of arrivals, based on a 99% success objective. Values can exceed 100%.
- Intervention attempts count sent retries and route changes. Upstream attempts include initial calls and retries. Retry overhead sums modeled backoff wait. Failed retry interventions count requests that retry but still fail. A harmful comparison has lower request success than the matched baseline.
- Observed dashboard metrics come from local simulator incidents and recorded health checks. They use the worker's existing detection and recovery rules. The dashboard labels modeled comparisons separately.

A lower-capacity standby can improve total successful requests while still leaving an impaired second. A breaker or rate limiter can reject traffic that the baseline serves. The seeded experiment results describe this model.

| Policy | Request success | Impaired seconds | Scenarios worse than baseline |
| --- | ---: | ---: | ---: |
| No intervention | 77.4% | 56 | 0 |
| Retry only | 78.1% | 51 | 0 |
| Circuit breaker | 65.3% | 66 | 4 |
| Rate limiting | 71.6% | 87 | 2 |
| Simulated failover | 83.0% | 57 | 0 |
| Combined | 72.0% | 89 | 4 |
