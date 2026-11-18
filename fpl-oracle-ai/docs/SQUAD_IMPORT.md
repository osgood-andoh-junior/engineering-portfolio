# Public squad import: completed UI and safe lineup optimization


## Verified snapshot

Team: Xenons. GW8 points: 43. Total at that deadline: 329. Public GW8 value: £102.0m; bank: £1.0m. These are historical public deadline values, not verified current spendable funds or selling values.

Final XI returned by FPL: Raya; Thomas, Calafiori, Mukiele, Bogle; Rogers, Palmer, Tavernier, Groß; Haaland, Calvert-Lewin. Formation 4-4-2.

Substitutes in returned order: Tzolakis, João Pedro, Rudoni, De Cuyper. João Pedro retains the selected C flag. Haaland retains VC and has an applied ×2 multiplier. The response records Bogle in / João Pedro out. Reversing that automatic substitution reconstructs the submitted 3-4-3; both views are available without altering the source snapshot.

Player resolution joins FPL element IDs to current-season player_season_identities, then canonical players/clubs. For example FPL 411 resolves to internal 493 (Haaland), and FPL 165 resolves to 185 (João Pedro). Names are not used as identity keys. Unresolved players are flagged and cannot be optimized.

## Interactive controls

- Click a pitch/bench card for club, current buy price, position, forecast interval, availability, model timestamp and player-profile link.
- Switch final/submitted/recommended XIs. Starters and four substitutes are separate, with captain/vice and applied historical multiplier badges.
- Choose conservative, balanced or aggressive and 1, 3 or 5 gameweeks. Forecasts start at upcoming GW9; they are not hindsight forecasts of GW8.
- Optimize My Squad submits all 15 canonical imported player IDs to POST /api/v1/optimizer/imported, rechecks public snapshot membership and reuses the existing CP-SAT optimizer. All 15 are locked into the squad; composition, XI, captain, vice and bench are solved using current registered players, verified season rules and fresh stored forecasts. Returned cards use the optimizer's latest forecast values.
- Import and optimization errors are readable; missing forecasts/identities and stale batches are not replaced by invented points. UI settings cannot change while optimization is pending.

## Transfer boundary

The public endpoints do not reveal verified current ownership, individual selling prices, current free-transfer balance or unused chip state. The GW8 wildcard and public bank are not treated as current transfer authorization. No legally certified purchases/sales are fabricated. The recommendation explicitly says no transfers proposed, retains all 15 and reports transfer_status=unavailable_private_state. It is a conditional lineup recommendation for the imported snapshot, not a current ownership or transfer-legality guarantee. Private/current transfer planning remains incomplete in the wider application.

There is no FPL password prompt, private scraping or remote team mutation. Public responses and optimizer POSTs use no-store. Imports are not persisted as shared team data. The existing manual builder, general optimizer and public Entry/Picks API contract remain available.

## Regression evidence

- Backend: 65 tests passed, including 7 new public-import/optimizer cases, real PostgreSQL concurrency and Redis integration.
- Frontend unit: 8 passed, including parsing, 15 unique picks, zero bank, historical finance fallback, auto-sub reversal, distinct FPL/canonical IDs and latest recommendation points.
- Browser/API: 18 passed. The real-manager check confirmed all 15 cards, 11 starters, four substitutes, 4-4-2 / 3-4-3, selected/effective captaincy, £102m / £1m and all three strategy/horizon options. It verified canonical IDs in the optimizer request, zero invented transfers, no raw JSON UI, clickable player details and 390px layout without page overflow.
- ESLint, TypeScript and Python critical-error Ruff checks passed. Final production build result is appended after completion.


Start the API and frontend, open the squad page, and enter a public manager ID and gameweek.

Final production build passed after the complete UI changes. The rebuilt /squad page and FastAPI health both returned HTTP 200. Services are left running. The live-manager screenshot shows the original final 4-4-2 and separate substitutes; the second screenshot shows the model-recommended lineup. The in-app tab retained a cached connection-error document during server restarts, so the authoritative interaction verification used the native Playwright browser against the running localhost services; reopening /squad loads the current application.
