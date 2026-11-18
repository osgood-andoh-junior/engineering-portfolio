# FPL Oracle AI

Local-first monorepo: Next.js App Router is a presentation/BFF layer. FastAPI owns validation and read APIs; SQLAlchemy owns relational state. PostgreSQL is the deployment database; SQLite is an explicitly limited local/test fallback. Redis caches public versioned resources. PostgreSQL durable jobs drive ingestion, targeted inference and invalidation. Training never runs inside HTTP requests.

Raw immutable responses and CSV downloads live in data/raw with SHA256 manifests. Analytical snapshots use Parquet. Historical FPL IDs are scoped by season, and cross-season links require stable provider codes or reviewed mappings; names alone do not establish identity. Feature cutoffs require both match completion and observed-at before the deadline. Missing manager/tactical observations remain missing.

Model candidates: recent-form baseline, CatBoost, LightGBM, LSTM and GRU. Training/calibration/test partitions are chronological. Artifacts include schema, training cutoffs, residual calibration, dataset digest and metrics. Promotion requires measured improvement. Live inference refuses season/source mismatches and missing artifacts. Cold starts use learned position priors with wider intervals, never invented prior-league equivalence.

Confirmed events are submitted by authenticated ingestion operators from registered official sources. Transactions close/open temporal memberships or tenures, create regime identifiers and durable refresh jobs. Unconfirmed evidence is stored but never changes authoritative records. Corrections must be reviewed; ambiguous identities are quarantined. Provider-independent event ingestion is implemented before enabling a source-specific feed whose terms and schema can be verified.

Incremental migrations: 0001 core identities, facts, provenance and analytical outputs; 0002 football intelligence, temporal state, events and jobs. Apply migrations before starting services; back up before changes. No automatic destructive migration on API startup. Frontend polling picks up published batches without redeployment.

Security: no FPL credentials; public manager IDs only. Same-origin BFF allowlist, strict backend CORS, internal bearer token, bounded inputs, request IDs, rate limits, no shared caching of manager imports. No publishing or paid services without approval.

Migrations now extend through 0006: observations, external mappings, bitemporal end boundaries and registration verification. Early migrations use a frozen schema. Later-confirmed departures do not alter earlier known contexts. Confirmed transfers await matching FPL registration; upstream conflicts cannot silently revert authoritative moves or enter optimization.

Stop API/worker before migrations and model publication on single-writer SQLite. Production requires PostgreSQL. Historical research evaluations use labelled deadline proxies; strict point-in-time mode rejects missing observed-time coverage.
