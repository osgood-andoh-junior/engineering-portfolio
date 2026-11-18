# Feature verification — 29 October 2026

Local program: http://127.0.0.1:3000/dashboard. API documentation: http://127.0.0.1:8000/docs.

The API and frontend are running locally. This is a research build; passing navigation and interaction checks does not make the unfinished production features available.

## Coverage

| Tab / feature | What was exercised |
| --- | --- |
| Overview | Live counts, forecasts, source health, links and rendered dashboard |
| Player predictions | Complete 669-player pagination; search, position, price, horizon, sort and optional context columns |
| Player profile | Real identity, historical chart and stored forecasts |
| My squad | Real public manager-ID import; input errors; add/remove players; starters; captain/vice; complete 15-player validation; budget changes clear old results |
| Squad optimizer | Three strategies; legal squad and XI; budget; locked/excluded players; infeasible/overlapping constraints; unsupported chips |
| Captaincy | Ten-player forecast shortlist and captain API |
| Fixture planner | 380 fixtures, club names, kickoff/result rendering |
| Transfer planner | Real forecast comparison, supplied point cost and explicit legality limitations |
| Live transfers | Source-backed feed route and truthful empty state |
| Managers | Twenty records and a manager's tenure/statistics detail |
| Tactical intelligence | Route and explicit missing-observation state |
| AI analyst | Selected-player evidence comparison without an LLM |
| Historical explorer | Player selection and resolved history |
| Backtesting | All three rolling windows and ablation tables |
| Model lab | Registered artifacts, measured metrics and promoted status |
| Data health | Source registry, counts, research warnings, coverage/cache/jobs |
| Settings | Manager ID, strategy/horizon persistence after reload |
| Mobile | Navigation and no horizontal page overflow at 390px |
| API protections | Missing records, invalid inputs, public-proxy allowlist and internal authentication rejection |
| Forecast outputs | All horizons, complete pagination, probability ranges/order and intervals |

## Fixes made during verification

- Prediction and transfer lists now fetch subsequent pages; the old 500-row limit hid 169 players.
- Invalid public manager IDs show a readable instruction instead of raw validation JSON.
- Manual squad validation clears when budget, captain or vice-captain changes.

The API test permits one transport retry for ECONNRESET on large paginated reads after idle keep-alive closure. HTTP status and data assertions remain unchanged; full test retries are not enabled.

## Boundaries

Tactical observations, a continuous verified transfer-event feed, historical exact deadline coverage, rolling transfer planning and validated chip decisions remain unavailable/incomplete. Their empty/error states were tested, not their unavailable calculations. Real PostgreSQL and Redis integration tests require services absent on this machine. No paid infrastructure was provisioned and nothing was published.

Backend verification: 55 passed, 2 service-integration tests skipped. Frontend unit verification: 2 passed. TypeScript validation and Webpack production build passed. Final browser/API result is recorded below after completion.

## Final result

The complete browser/API run passed **17/17 tests** (2.5 minutes). All 16 navigation tabs loaded without recorded runtime/API failures in the navigation check; player and manager detail routes were exercised separately. The API probability check permits the documented single closed-socket retry. During the combined high-volume suite the API also returned temporary 429 responses, confirming the rate limit remained active; the suite completed successfully without relaxing that limit.

Final fixes passed TypeScript validation, the Webpack production build and both frontend unit tests. The full backend suite passed 55 tests with only the two real-service tests skipped. Dashboard screenshot: data/screenshots/dashboard.png; per-tab screenshots: apps/web/test-results/features-All-tabs-against--2fb68-out-runtime-or-API-failures/.

Services were left running for this request. The background scheduler was not started as part of this feature verification; source/forecast freshness limits still apply. Continuous refresh requires the documented worker process. No claim is made that unavailable tactical, transfer-planning or chip functionality has been completed.

The subsequent PostgreSQL/Redis-backed verification supersedes the earlier skipped-service results: see LOCAL_VERIFICATION.md. Current history requests cover all 669 players; backend tests 58 passed with no skips, and browser/API tests 17 passed. Same-name player handling and footer freshness-source selection were also fixed. The full production specification remains incomplete.
