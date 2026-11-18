# Architecture and security

The Next.js dashboard polls its own API routes every five seconds. Those routes forward allowlisted reads and authorized fault actions to FastAPI. FastAPI persists fault configuration in PostgreSQL. Three local simulators read their respective settings on every health request. The dedicated worker probes fixed targets over HTTP and writes measurements, service states, incident transitions, and evidence to PostgreSQL.

A PostgreSQL session advisory lock serializes worker ownership. The worker uses its lock-owning connection for all writes and exits if the connection fails. Per-check transactions lock the service row, and a partial unique index enforces one unresolved incident per service. HTTP probes run concurrently with a semaphore and a wall-clock timeout. Down services back off to the configured cap. A fast successful check begins a recovery streak, and a slow or failed check interrupts it.

The first failure in a consecutive sequence establishes the observed outage start. A successful but slow response degrades the service. Transient failed checks below the outage threshold also degrade it. An outage opens at the failure threshold and remains open through interrupted recoveries. Status and timestamps describe what the worker observed at sampling time.

Migration `0002` adds immutable `dependency_graphs`, append-only `fault_events`, and isolated `replay_sessions`. It also adds a graph version and optional upstream symptom marker to health checks, plus expiration for temporary fault configurations. Graph publication uses a transaction lock and expected version to prevent lost updates. Each simulator reads the active topology and fault configuration in one database statement. A failing ancestor produces a 503 on a healthy dependent, and an upstream latency fault contributes to dependent latency.

The worker stores the version reported by the simulator, with the graph sampled before the probe as a fallback for connections without HTTP headers. Diagnosis derives correlations from the recorded observations on demand, so a worker restart cannot duplicate correlation records. The API reports injection events separately from rule-based inference. Replay writes only to its own table and stores the ordered frames and computed findings. Existing Phase 1 observations have no graph version and cannot support historical topology inference.

## Trust boundaries

- Development endpoints bind to loopback by default. Compose publishes database, API, and dashboard ports on loopback and keeps simulator ports inside its network.
- Only the three compiled service identities and ports are probe targets. URLs never originate from a request or a database row. HTTP redirects and environment proxies are disabled for probes.
- The administrative API requires an environment-provided bearer token. The dashboard accepts the operator's token through a same-origin form and issues a signed, HTTP-only, same-site cookie with a 30-minute lifetime. Its server forwards the configured bearer token only on allowlisted write routes with a valid session and same-origin request. Tokens are never included in the client bundle.
- The default PostgreSQL credentials are for local development. Before hosting remotely, use a private network, HTTPS, managed secrets, database access controls, and identity-based administrative access.
- Database errors return generic messages. The worker logs service, state, and check result as structured JSON.

## Local experiment

Use the demonstration in the README. Observe how the recorded detection delay changes with polling cadence and the number of consecutive failures. Then compare recovery confirmation with and without an intervening fault. Set different thresholds in the environment and restart the API and worker to test another configuration. Run the idempotent seed command to refresh the stored configuration snapshot.

## Hosting boundaries

Compose is the supported integrated runtime. The backend and dashboard have separate build definitions. A future private Render environment could host PostgreSQL, the simulator containers, and the dedicated monitoring worker. A Vercel dashboard would require a securely reachable API and updated authorization and network controls. The current fixed Docker targets assume the local Compose network. The current release targets local operation.

The MVP retains health checks and incident evidence indefinitely. Operators should provision storage accordingly. The dashboard reports delayed checks after one minute. The API health endpoint confirms database connectivity and the worker's output records polling progress.

Phase 3 runs policy comparisons in an in-process traffic model. Its separate execution path serializes authenticated, individually confirmed local simulator changes with PostgreSQL. The monitoring worker records the verification outcome alongside its checks. See [recovery engine](recovery-engine.md) and [security](recovery-security.md).
