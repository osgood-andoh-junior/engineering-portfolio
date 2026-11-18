# Circuit-breaker timing investigation

The saved Phase 5 evidence recorded 16 of 60 modeled successes and 34 of 60 measured successes. All 18 additional modeled failures occurred after the service recovered. The model rejected all 15 arrivals in windows 7–9 and three of five in window 10. The HTTP harness recovered on its first request in window 7.

Both runs use a threshold of three failures and a four-second cooldown. The model spaces arrivals across each second and records failures immediately at admission. The third latency failure occurs at 2.4 seconds, allowing a probe at 6.5 seconds. That probe sees the final HTTP error window and opens the breaker until 10.5 seconds. The first eligible healthy arrival is at 10.6 seconds.

The harness schedules the five latency requests between 2.00 and 2.24 seconds. All five are admitted before the first deadline expires. Failure completions arrive approximately 650 ms after the corresponding scheduled arrivals. The existing breaker extends the cooldown on additional in-flight failures recorded while open. This pushes eligibility past the last arrival in window 6. The probe in window 7 succeeds and closes the breaker.

The deterministic replay holds the fixture and breaker implementation fixed, assumes immediate outcomes for healthy and error requests, and varies only arrival spacing and when latency failures are recorded.

| Arrival span | Latency failure observation | First probe | Successes |
| --- | --- | ---: | ---: |
| 1.0 s | At admission | 6.50 s | 16 |
| 0.3 s | At admission | 6.15 s | 16 |
| 1.0 s | After 650 ms | 7.80 s | 30 |
| 0.3 s | After 650 ms | 7.00 s | 34 |

This isolates an event-timing mismatch for this fixture. Synthetic capacity is 12 requests per window, the HTTP harness allows four in flight, and healthy windows offer at most six requests. The fifth latency request waits for capacity in the harness and still reaches its deadline. The timing replay reproduces both totals without a capacity limit. The harness uses actual admission and completion times, while the saved per-request evidence retains elapsed time and window membership. Add monotonic admission, outcome, and breaker-transition timestamps before calibrating on a less controlled trace.

The shared breaker also lets outstanding failures extend an open interval. Treat the desired behavior for concurrent completions as a separate policy decision. The original benchmark and breaker implementation are preserved.
