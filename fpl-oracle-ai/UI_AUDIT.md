# Platform UI audit — 1 November 2026

Scope: every existing navigation route plus player and manager detail routes. Existing backend JSON contracts and ML artifacts remain intact. Changes begin with transfers/forecast revisions, then extend through all routes.

| Page | Observed issue | Replacement | Status |
|---|---|---|---|
| /transfers | JSON.stringify of audit payloads; anonymous IDs; text-only comparison | Resolved player cards, before/after metrics, aggregate bars and true interval ranges, version/time provenance, no causal claim without evidence; financial-input warnings | Implemented |
| /transfers/live | Generic object dump | Human event timeline, participant/club labels, confirmation/source/date badges | Implemented |
| /predictions | 669-row unpaginated table; technical model IDs; no clubs, p6/p15/form/fixtures | Server-paginated searchable/sortable explorer, monogram avatars/badges, full probabilities, form and fixture outlook | Implemented |
| /players/:id | Player/context and forecast JSON | Player header, uncertainty cards, forecast revision and historical charts, named context; technical provenance in details | Implemented |
| /captaincy | Generic table | Captain comparison cards and probability/uncertainty comparisons with accessible table | Implemented |
| /optimizer | Result object dump, XI-only pitch without bench/captain markers | Preserve solver controls; named captain/vice/bench, budget breakdown, risk notes and intervals | Implemented |
| /squad | Working imported pitch and manual builder | Preserve interactions, captain/substitution semantics, privacy and transfer gates; share visual primitives/session-only summary | Preserved and improved |
| /historical | Numeric ID entry; one points chart | Named player/season selection, season summaries, points/minutes/goals/assists where recorded, match records and known club contributions | Implemented |
| /managers | Basic directory | Club-labelled coaching cards and measured record summaries | Implemented |
| /managers/:id | Entire manager JSON, unformatted tenures | Tenure timeline, W/D/L, goals/outcome trends, observed usage/formation coverage | Implemented |
| /tactics | Tactical object dumps | Observed/inferred labels, actual formation diagrams/frequencies, dated metrics/source timeline; explicit unavailable metrics | Implemented |
| /fixtures | 380-row schedule only | Official-source FDR matrix with GW columns, opponent monograms, H/A, blank/unassigned/double indicators, filters; schedule view retained | Implemented |
| /model-lab | Long artifact IDs, mixed cohort chart, sparse metric explanation | Latest-family leaderboard, MAE/RMSE, actual evaluated scatter/error/calibration/importance data where reproducible from saved runs; human labels and cohort warning | Implemented |
| /backtesting | Dense research table | Fold/ablation controls, measured MAE comparison plus accessible data table and missing-feature labels | Implemented |
| /dashboard | Decorative pitch, sparse context, technical model IDs | Executive metrics, upcoming fixtures, captain shortlist, session-only squad summary, availability/forecast changes, source/model status, no fabricated transfer plan | Implemented |
| /ai-analyst | Response object dump and numeric-only identities | Named selection, recommendation/evidence cards, intervals and timestamps, explicit structured-only mode | Implemented |
| /data-health | Raw source/coverage/job objects | Source freshness cards, season coverage chart, labelled job queue and limitations | Implemented |
| /settings | Simple preferences | Preserve settings with clear explanatory labels and persistence | Preserved and improved |
| Unknown routes | Next 404 | Preserve 404 behavior | Preserve |

## Integrity and performance rules

No synthetic content is inserted into production to populate charts. Null is never zero. Negative forecasts/intervals remain visible. Aggregate horizons are never split into invented gameweeks. Event-null comparisons have no verified event attribution. Model and feature changes remain explicit. Historical club/role fields are not inferred from current memberships. Heavy model visual data is prepared offline from saved fitted runs, not training inside requests. Historical responses are bounded/aggregated. Personal squad data is session-only and never enters shared Redis. Badge/portrait monograms are permitted placeholders, not unlicensed photos.

Technical identifiers remain available only in labelled expandable provenance where useful. JSON.stringify may remain for transport/storage/testing, never as a visible object dump. Final completion and test evidence will be appended.


## Implementation and real-data verification

All 16 navigation pages and both detail routes have been audited and updated. The shell loads page modules and Recharts lazily. Existing public API contracts, import resolution, solver, model artifacts and cache invalidation remain intact. Read-only /api/v1/presentation/* adapters supply bounded named records, source FDR, seasonal summaries, real forecast revisions and trusted evaluation exports. No migrations or retraining were needed for this UI work.

- Transfers: resolved identities, true before/after bars, signed deltas and intervals, timestamps, version/input-change warnings, explicit null-event attribution, filters/pagination and private-state affordability warnings. Missing selling/ownership/free-transfer state cannot produce an executable transfer.
- Predictions/captaincy: 25-row server-filtered pages (10 captain candidates), name/club/position/price controls, sorting, probabilities, last-five observed form, official next-fixture outlook and uncertainty. Profiles expose actual seasonal points, minutes, goals/assists where retained, historical source club labels and 1/3/5-GW aggregates.
- Squad/optimizer: preserved real import and manual builder; XI/bench/captain/vice, legal solver output and budget/risk explanation. Imported and recommended views remain separate. A memory-only squad summary/recommendation is available on the dashboard after import; browser reload clears it. Neither Redis nor local storage receives the squad.
- Historical/manager/tactics: season and named-player selection, observed series and club contribution charts, verified tenure/outcome timeline, usage minutes and observed 60-minute rates. A role diagram appears only for an actually supplied valid formation; source-inferred records remain labelled. No rotation or tactical-fit score is invented.
- Model lab/backtesting: latest-family leaderboard, real fold/ablation error chart/table, per-family saved training/version history, matched-cohort references, actual/predicted scatter, error histogram, empirical 10+ calibration and tree importance where available. Offline chart exports reproduced held-out count and MAE for all 11 saved latest points models. HTTP requests never train or deserialize models.
- Dashboard/analyst/data health/settings: measured executive cards, current GW/deadline, captain candidates, availability context, official fixtures, forecast revisions and data/model limitations; named structured evidence retrieval; source/season/cache/job visuals; existing preferences retained.

### Integrity checks

Primary UI components contain no JSON.stringify, JsonFacts, pre object dump or facts renderers. Remaining JSON serialization is transport/schema-validation code only. Long artifact IDs are confined to closed technical provenance. Nulls remain missing, percentages require a positive baseline, valid negatives remain on chart domains, seasonal IDs are scoped correctly, and aggregate horizons are never interpolated into gameweeks. Tests use isolated, explicitly synthetic fixtures; the live warehouse is not seeded from them.


### Coverage and feature limitations

- The prior full current-history request covered 669 players; the new 670th registration has not received a new full-history ingest in this UI task. Coverage messaging correctly reports that gap. Historical match warehouse and manager match facts can lag the freshly synchronized bootstrap/fixtures.
- Six completed seasons are present, but original historical observed-at/deadline snapshots and full past coaching memberships are incomplete. Current coaches/clubs are never projected backwards. Unknown club rows are excluded from club charts with a count.
- Production contains no licensed tactical observations or ingested football events. Those pages intentionally show meaningful empty states. Populated event/tactical read models and source/inferred distinctions are covered by isolated API regressions.
- Models are fitted research artifacts, not deadline-validated production models. Ensemble weighting, actual starting-XI classification and full correlated squad/automatic-substitution simulation remain absent. No per-epoch training loss history was retained; saved run/evaluation history is shown instead.
- Current private selling values, ownership, rollover, free transfers and chip eligibility are unavailable publicly. Transfer comparison remains research-only; unsupported transfer/chip optimization remains gated.
- Open-ended LLM analysis is not enabled. The analyst compares named stored evidence with explicit assumptions and intervals.
- Prediction/source freshness gates remain active. Expired forecasts were correctly rejected during a long test session; official sync plus inference restored eligibility. No freshness check was weakened.
- One non-fatal Starlette/httpx TestClient deprecation warning remains. The browser runner may emit the benign NO_COLOR/FORCE_COLOR warning.

### Validation record

Backend: 73 passed, including isolated PostgreSQL schema and Redis DB15 integration tests.
Frontend: 20 unit/component/adapter tests passed. ESLint (zero warnings), TypeScript, and configured Python Ruff checks passed.
Final browser and production-build results are recorded below after completion.

Screenshots are retained under data/screenshots/ and the ignored apps/web/test-results/ directory. Browser tests check actual services on desktop 1440, laptop 1280, tablet 768 and mobile 390 pixels, horizontal scrolling inside tables, usable charts, no primary object dumps, import/optimization, all tabs and named evidence selection.

### Repeat the visual verification

Use the restart commands in docs/LOCAL_VERIFICATION.md. Refresh scripts.manage sync before scripts.manage predict; source freshness is checked as well as prediction age. With both servers running:

~~~powershell
npm run lint
npm run typecheck
npm test
$env:ORACLE_CAPTURE_SCREENSHOT='1'
npm run e2e --workspace apps/web
~~~

Regenerate optional verified evaluation charts from existing trusted fitted runs (no retraining):

~~~powershell
.\.venv\Scripts\python.exe -m scripts.build_ui_evaluations
~~~

Stop the frontend before npm run build, then restart npm run dev. Application: http://127.0.0.1:3000/dashboard; squad: http://127.0.0.1:3000/squad; API docs: http://127.0.0.1:8000/docs.

### Final verification outcome

- **73 backend tests passed**, zero skipped, with PostgreSQL and Redis integration enabled; one known non-fatal Starlette/httpx deprecation warning.
- **20 frontend unit/component/adapter tests passed.**
- **24 browser/API tests passed**, zero skipped; screenshot capture was explicitly enabled. Every navigation tab, both detail views, filters, actual transfer comparison, structured analyst, manual validation, imported squad, lineup optimization and session clearing were exercised.
- Four viewport classes passed: desktop 1440, laptop 1280, tablet 768, mobile 390. Tables scroll within their containers and the document fits the viewport.
- ESLint with zero warnings, TypeScript checking, and configured Python Ruff checks passed.
- **Next.js production Webpack build passed**, including TypeScript, static generation and build tracing. Frontend restarted successfully on 127.0.0.1:3000; FastAPI remains on 127.0.0.1:8000.
- Screenshots were inspected for real transfer comparison, actual model evaluation, mobile FDR matrix and imported/recommended mobile squad.
- No credentials, paid provider, deployment, repository reset or remote push was required.

Resolved verification failures: a missing Vitest path alias; a test fixture missing required tenure evidence; a too-broad chart SVG count (legend also renders SVG); legacy raw-JSON selectors; selecting a genuinely unavailable transfer player; a duplicated brand/navigation selector; a gameweek-loading input race; stale source/forecast gates after the date changed; and newly added routes requiring API restart. A transient quoting typo was caught by the compile/type checks and corrected before the final all-green run. Sandbox TestClient socketpair creation hung; rerunning the tests with approved local socket access passed. These are recorded rather than hidden; no mocks or weakened validation were used to make live checks pass.
