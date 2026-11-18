# Current local performance observation — 2026-10-16

Production-built Next.js application, Windows host, Chromium 156, iPhone 13 viewport, cold browser context, 4× CPU throttle, 150ms latency and 1.6Mbps download. **The API/database were unavailable. This measures the unavailable-service storefront shell, not an operational full-stack shop.**

| Metric           |     Observed |
| ---------------- | -----------: |
| LCP              |     3,228 ms |
| CLS              | 0.0015219358 |
| FCP              |     1,532 ms |
| DOMContentLoaded |     2,660 ms |
| Resource bytes   |      321,477 |
| INP              | Not measured |

The LCP observation **misses the 2.5-second target**. CLS is below 0.1 in this one local run, but neither metric establishes production p75 performance. Missing API waits, dynamic server rendering, proxy overhead, fonts and current host conditions affect the observation. Repeat with the configured cloud development/test database and representative data/network/devices; profile server timing, catalogue caching/invalidation and image/font loading before making any release claim. No threshold was weakened and no older frontend-only result is substituted for this result.

Reproduce from `frontend/` with a production preview on port 3000: `node scripts/measure-preview.mjs`. It writes raw ignored measurements to `frontend/test-results/performance.json`; subsequent Playwright runs clear that directory. No field monitoring or representative Ghanaian device/network study has been performed.
