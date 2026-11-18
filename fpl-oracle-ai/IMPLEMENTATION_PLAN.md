# Implementation status — 29 October 2026

Working local research implementation. The complete production specification is not yet satisfied. No deployment, paid provisioning or remote push occurred.

## Executed

- FastAPI/Next.js monorepo, six migrations, provenance, stable identities, temporal memberships, confirmed-event transactions, audit logs and durable jobs.
- Official 2026/27 bootstrap: 669 players, 380 fixtures. Six completed historical seasons: 163,394 deduplicated records retained as raw snapshots and Parquet. Current match history: only 32 records after provider failures.
- Real baseline, CatBoost, LightGBM and LSTM/GRU experiments at lengths 5/10/15/20; chronological calibration, persisted artifacts and forecasts. Consult successful artifact leaderboards; a failed refresh is not a release.
- Twenty current manager tenures from reviewed official sources, 160 manager match facts, authenticated event and tactical-observation ingestion. Missing tactical values remain missing.
- Minutes-band classifier, empirical intervals/haul probabilities, basic legal squad/XI/captain optimizer, manual squad validation and evidence-grounded comparisons.
- Eighteen frontend views, live API integration, public FPL-ID import, manual builder and model/source health views.
- Verification: 54 backend tests passed, 2 PostgreSQL/Redis integration tests skipped; 2 frontend unit tests and 4 browser tests passed. Screenshot: data/screenshots/dashboard.png.

## Partial or outstanding

- Exact historical gameweek deadlines and observation times are missing. Research evaluations use labelled retrospective fixture-boundary proxies. Strict point-in-time mode rejects this coverage.
- Complete manager histories, licensed tactics, actual lineup labels and continuous event feeds are missing. Manager/tactical predictive lift is unproven.
- Current-season player histories need a complete successful synchronization.
- Full joint scoring-event simulation, automatic substitutions, ownership/selling-price/rollover state, rolling transfer planning and validated chip decisions remain unimplemented. Relevant optimizer routes explicitly return unavailable.
- Learned ensemble promotion, comprehensive ablations/cohort evaluation, MLflow/Optuna/SHAP, optional LLM integration and advanced frontend analyses remain outstanding.
- PostgreSQL/Redis concurrency, long-job lease renewal, containers, shared artifact storage, production secrets and deployment require verification. Docker is absent. CI/hosting files are templates, not execution evidence.

## Operation

Use one writer at a time with local SQLite; stop API/worker before schema changes or model publication. Production requires PostgreSQL. Historical research permission was enabled for this local import; source-code licensing does not grant underlying data redistribution rights. Review DATA_SOURCES.md before deployment.

Final verification: current-schema health returned 200; refreshed real-data optimizer returned OPTIMAL with 15 players, 11 starters and cost 999 (£99.9m). The new refresh-job regression plus optimizer/migration smoke tests passed (5 tests). The final production-bundle browser suite passed all 4 tests. A later full-suite rerun was interrupted after stalling; the recorded 54-test full-suite pass predates the final invalidation fix, which has targeted coverage. Temporary local servers were stopped after verification.

## Follow-up feature verification

The subsequent request to run the app and test every tab is recorded in docs/FEATURE_TEST_REPORT.md. Latest results: 55 backend tests passed, 2 external-service tests skipped; all 17 browser/API tests passed; 2 frontend unit tests passed; TypeScript and production build passed. This supersedes the earlier interrupted full-suite result. Pagination, public-ID error presentation and manual-validation invalidation were fixed. Local API/frontend were left running for the user; the background scheduler is not running.

## Latest verification supersedes earlier service limitations

See docs/LOCAL_VERIFICATION.md for the audited phase table and exact restart commands. Docker Engine/Compose are installed in Ubuntu WSL2; PostgreSQL (55432) and Redis (6379) are healthy, migrations reached 0006, and the existing real-data warehouse was copied without altering SQLite. Official ingestion now covers all 669 current players with 5,220 current-season records, alongside 163,394 completed-season records. There are 62 verified fitted artifacts and 2,007 latest horizon outputs. Backend: 58 passed with real services and no skips. Browser/API: 17 passed. Frontend unit: 2 passed. Lint, type check and build passed. This verifies local research functionality; it does not complete the remaining production/model/data requirements.

## Public squad interface follow-up

The raw Entry/Picks primary display was replaced by the verified interactive squad interface. Source API compatibility is preserved through additive season-scoped resolution. Imported lineup optimization retains all 15 players and explicitly does not invent private transfer state. See docs/SQUAD_IMPORT.md. Latest checks: backend 65 passed; frontend unit 8 passed; browser/API 18 passed; lint, types and build passed.

## Transfer planning implementation — 5 November 2026

Implemented an additive manager-state-gated transfer planner; existing /optimizer/transfers and imported-lineup contracts remain unchanged. New /planning/transfers accepts explicitly confirmed integer-tenth bank/selling values, current ownership, free transfers, locks/exclusions, chip eligibility and current GW. OR-Tools selects a legal affordable squad/XI/captain and independent checks verify composition, positions, club limits and cash. Alternatives and a keep-squad baseline are included.


Completed scope: zero/up-to-one/up-to-two/up-to-fifteen transfer caps; 0–5 free transfers; four-point paid-transfer deductions; permanent Wildcard and single-GW Free Hit scenarios with explicit eligibility gates; 1/3/5-GW fixed-ownership aggregate scoring; position-matched transfers; remaining bank/current liquidation value; individual differences and plan-level net gain; captain/vice/bench; manual ownership and purchase/selling price inputs; source evidence and no-store manager endpoints.

Remaining scope: a true sequential multi-deadline transfer/rollover engine, learned future prices, correlated squad/bench automatic-substitution contribution, exact per-transfer attribution of captaincy/lineup gains, and full real-manager executable-plan validation after the missing selling prices are supplied. Free Hit is restricted to 1 GW; GW20 needs special previous-half eligibility verification and is conservatively gated. Current liquidation value is never presented as predicted future appreciation. These limitations prevent calling this the complete production transfer engine.

See docs/TRANSFER_PLANNING.md for contracts, user workflow and validation results. No historical records, trained artifacts or existing API contracts were removed.


Final validation: 83 backend tests (PostgreSQL/Redis enabled), 22 frontend tests, all 25 preexisting/new browser tests plus the additional actual-manager keep-plan browser scenario passed across full and targeted runs. Actual manager zero-transfer checks now cover all three horizons without invented selling prices. Unknown liquidation value remains null. Final selling-input gates continue to prevent real-manager nonzero-transfer recommendations until values are supplied.
