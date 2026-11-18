# Model card

Real local experiments have been executed. Generated artifacts contain dataset SHA256, feature schema, cutoff dates, calibration cutoff and out-of-time metrics. Random seed is 42. Training recency half-life is two years for tabular candidates. Default sequence lengths are 5/10/15/20; recurrent models carry each row's own historical context.

Baseline: five-observation mean, falling back to fitted position mean. CatBoost and LightGBM use median-imputed numerical player/fixture/context features with missingness indicators. Unavailable manager and tactical features have no learned influence until populated with dated observations. Small-sample player-manager starts/minutes estimates are regularized; cross-club coaching transfer is not treated as an invariant effect.

Calibration: empirical residual distribution on a separate chronological segment, with a 90% marginal interval. Baseline cold starts use fitted position priors. Cold starts and sparse managerial contexts use a 1.5 residual-scale precaution, explicitly an unvalidated conservatism policy. A temperature-calibrated minutes-band classifier is available; actual starting-XI probability is unavailable. No causal interpretation, guarantee or return-on-investment claim. Multi-gameweek errors currently use a square-root fixture-count approximation and must not be advertised as correlated team simulation.

Historical CSV observation timestamps are unavailable. Archive experiments are retrospective simulations using a conservative match completion lag, not proof that every record was observable at historical deadlines. Strict observed-at mode excludes unknown observations. Identity mapping uses stable player codes; unresolved identities are excluded from current forecasts.

Tabular promotion compares MAE on an identical single holdout. This is development model selection, not unbiased post-selection performance evidence. Recurrent lengths use different eligible cohorts; they are not automatically promoted or ensembled. Rolling-origin tabular A–E research tables and matched recurrent comparisons are persisted. Credible manager/new-signing/promoted-club evaluation, unbiased promotion evidence, Optuna/MLflow/SHAP and full scoring-event simulation remain required for production acceptance.

## Current research implementation

Real local training has run; artifact JSON files contain measured results. Stable provider codes join cross-season histories; unresolved seasonal IDs stay separate. The minutes-band classifier estimates zero and 60-plus minutes with temperature calibration. Actual starting-XI labels are not integrated, so starting probability remains unavailable.

Manager and sparse-history interval widening is an explicit unvalidated precaution. Exact historical deadlines and observation times remain missing; research proxy results must not be presented as production-valid backtests. The latest refresh must complete successfully before its artifacts are treated as a published release.

## Latest successful local experiment

Dataset prefix 4ea8f7697287; code snapshot 11e3ce75. Three-epoch recurrent runs cover all eight kind/length combinations. The shared tabular holdout has 30,563 observations: baseline MAE 1.05465, CatBoost 0.99948, LightGBM 0.99691. LightGBM was selected by this development holdout. These are retrospective research scores, not production accuracy claims: only 0.0196% of prepared rows have exact gameweek deadlines. Minutes classifier holdout Brier scores: zero minutes 0.09513, 60-plus 0.09069; log loss 0.49149. Full metrics/configurations are persisted with the artifacts.
