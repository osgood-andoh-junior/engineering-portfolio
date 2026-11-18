# Transfer planning — implemented scope and verification

## How to use

Open http://127.0.0.1:3000/transfers or /optimizer and find Manager transfer planning.

2. Confirm/edit current ownership with Remove and Add current owned player. Historical GW8 import remains on /squad; Use imported snapshot as draft explicitly copies that ownership.
3. Enter current bank **1.0** and free transfers **2**, as confirmed by the user. No transfers since GW9 were reported. These are user-confirmed values, not inferred public values.
4. Enter each exact FPL selling price. Optional purchase inputs can calculate half-profit selling values with floor rounding in integer tenths. Publicly recorded purchase costs populate only when known; they are not a substitute for checking current selling prices. Seven initial GW4 purchase costs remain unknown.
5. Select risk preference, 1/3/5 GW horizon and maximum transfers. Maximum 0 is keep; 1/2 permit up to that many changes. Maximum 3 with two free transfers permits a hit, but the solver may prefer fewer changes.
6. Lock retained players or exclude players from the result. Confirm all manager inputs. Generate recommendations stays disabled until the required fields are filled.
7. Inspect the keep baseline, recommended net/gross points, actual sale/buy values, plan hit, remaining bank, current liquidation value, captain/vice, XI, bench and alternatives. Five-GW comparison evaluates fixed ownership against keeping the old squad, using stored five-GW models.
8. Wildcard was used in GW8, so it is not eligible again in the first half. Free Hit eligibility must be confirmed; it is limited to one GW and original ownership returns afterwards. No action submits transfers to FPL.

## Contracts and integrity

POST /api/v1/planning/transfers is additive. Financial values are integer £0.1m units; no default bank/free-transfer/selling-price assumptions are supplied. confirmed must be true. Optional manager_id permits checking publicly used chips. Missing/unconfirmed state is rejected. The solver also rejects absent/stale forecasts, wrong GW, conflicting constraints and infeasible budgets.


Selling price: current price for a loss; otherwise purchase price plus floor((current minus purchase)/2), in integer tenths. Retaining a player costs no repurchase; only sold players release their manager selling value. Only incoming players consume current buy prices. Independent validation checks final cash, fifteen distinct players, 2/5/5/3 positions, club cap, eleven-player formation and position-matched transfers.

Official rules reviewed:
- https://www.premierleague.com/en/news/2174907 — 20 July 2026 guide: five saved free transfers, four-point hits, selling-profit rounding and full loss.
- https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627 — two chip sets, half-season expiry, one chip/GW, permanent Wildcard and temporary Free Hit, GW19→20 Free Hit restriction.

## Limits

This is a single-deadline transfer engine over aggregate forecast horizons, not sequential future-GW scheduling. It does not forecast future price changes or optimize rollover over several deadlines. Liquidation value uses current prices only.

Expected points already reflect the existing model's availability/minutes inputs and actual fixture horizons, including blanks/doubles where represented in the forecast. The transfer layer prohibits unavailable/unregistered incoming players. It does not multiply model points again by minutes probabilities.

Bench is shown and ordered by expected points, but automatic substitutions, captain fallback and correlated joint uncertainty are not simulated. Individual player differences are not additive explanations of plan gain when XI/captaincy changes. Hit cost and net gain are reported once at plan level.

Real-manager executable plans remain unverified until exact selling prices are confirmed. No invented values were inserted to make that check pass. Synthetic solver fixtures are isolated tests, not evidence of the manager's finances.

Zero-transfer plans can run without selling prices; cash remains unchanged and liquidation value is explicitly unknown. Actual manager GW9 keep plans solved OPTIMAL for 1/3/5 GW: 49.4146 / 146.5199 / 242.2627 model points with £1.0m unchanged bank and zero hits. These are research model aggregates, not guaranteed scores.

## Regression results

83 backend tests passed including actual isolated PostgreSQL/Redis integration; 22 frontend tests passed; all 25 browser tests passed before the additional real keep-plan scenario was added, then both transfer-specific browser tests passed. Thus 26 distinct browser tests have passing coverage across those runs. ESLint, TypeScript and configured Python Ruff passed. Build status is in docs/LOCAL_VERIFICATION.md.

User bank/free-transfer/ownership confirmations support genuine zero-transfer checks. Real one-/two-transfer and paid/chip execution remains dependent on exact selling prices. Synthetic tests prove solver accounting and constraint paths only, not the manager's private values.
