# Local performance observation

> Historical frontend-only measurement. This is not a measurement of the API-backed full-stack implementation.

Measured 2026-10-15 using the production build (Next.js 16.4.2), local Windows host, Chromium 156, iPhone 13 viewport, cold browser context, 4× CPU throttle, 150ms network latency and 1.6Mbps download. One navigation, no field data.

| Metric                   |      Observed |
| ------------------------ | ------------: |
| Largest contentful paint |      1,624 ms |
| Cumulative layout shift  |  0.0030817211 |
| First contentful paint   |        864 ms |
| DOM content loaded       |        926 ms |
| Resource transfer total  | 349,458 bytes |
| INP                      |  Not measured |

These are local lab observations, not demonstrated production p75 Core Web Vitals. Real devices, representative Ghanaian connectivity, hosting latency, catalogue integration and field monitoring are still required. The 2.5s LCP / 200ms INP / 0.1 CLS targets are goals rather than a launch certification.

To reproduce: build and start the application on port 3000, install Playwright Chromium, then run `node scripts/measure-preview.mjs`. The helper writes ignored raw data to `test-results/performance.json`; Playwright clears that folder on the next test run, so approved measurements should be recorded here. Do not measure while running parallel browser tests.
