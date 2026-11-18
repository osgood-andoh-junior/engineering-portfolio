# Phase 4 results

Seed 42 generated 240 workloads and 1,680 policy evaluations. The held-out set contained 60 workloads, six per family.

| Policy | Mean success | 95% interval | Mean impaired seconds | Worse than baseline |
| --- | ---: | ---: | ---: | ---: |
| No intervention | 80.67% | 78.64–82.65% | 8.42 | 0.0% |
| Retry only | 81.12% | 79.04–83.09% | 8.23 | 0.0% |
| Circuit breaker | 68.36% | 65.68–70.81% | 12.22 | 93.3% |
| Rate limiting | 78.38% | 76.16–80.60% | 11.27 | 33.3% |
| Failover | 84.40% | 82.42–86.35% | 7.60 | 1.7% |
| Default combined | 74.83% | 72.09–77.73% | 12.20 | 71.7% |
| Tuned combined | 80.98% | 78.34–83.36% | 8.58 | 45.0% |

Failover had the highest mean success and fewest impaired seconds. Its paired improvement was 3.72 percentage points with a 95% interval of 2.87 to 4.40. The tuned combined policy improved on the default combined configuration. Its paired improvement over no intervention was 0.31 points with a 95% interval of −0.99 to 1.53, and it regressed on 45% of individual traces.

See [benchmark methodology](benchmark-methodology.md) for scope and denominators. The runner produces conditional delay, tail, overhead, and detection-error distributions for each policy.

Retry-only had the shortest conditional mean recovery time at 12.66 seconds. All policies had two-second conditional mean detection and diagnosis delays under the modeled thresholds. Recovery means have different sample counts because the policies change which episodes are detected and recovered.

PostgreSQL 17 verification exercised upgrades from Phase 3 and from an empty database. The backend tests checked named roles, session deactivation, policy authorization, duplicate approval handling, concurrent execution, emergency stop, and loss of the worker database connection. The browser suite exercised the benchmark, CSV export, chain verification, and prior outage and recovery flows.
