# Phase 2 diagnosis and evaluation

## Evidence and scoring

The simulator treats dependency edges as dependent → upstream. The diagnosis engine considers abnormal observations near incident onset and checks whether downstream HTTP 503 responses name an abnormal ancestor. A graph edge or simultaneous failures alone do not establish causality. Direct failures remain independent hypotheses when there is no corroborating dependency evidence.

Scores are 0.95 for a corroborated upstream failure, 0.75 for repeated direct abnormal checks, and 0.60 for a single direct failed check. A lone slow sample, a generic 503, or a blocked-dependent response without corroborating upstream evidence can yield insufficient evidence. Scores express rule strength and have no probability calibration. The fault ledger is presented separately and never enters scoring.

Recorded replay uses the topology from the incident's first failed check, includes same-version observations only, and captures at most 15 minutes beyond incident detection. Existing Phase 1 incidents lack a graph version. Saved replay stores computed frames, so later topology changes cannot change them.

## Evaluation definitions

Run `uv run python -m backend.evaluation`. The seeded evaluation uses seven frames per scenario at five-second intervals, a 500 ms latency threshold, and three consecutive failed checks to detect an outage. The spike has an empty expected major-cause set. The seeded fixtures share the local simulator's behavior function. Real HTTP behavior is separately tested for all five recipes.

- Exact-match accuracy divides scenarios whose entire predicted cause set matches the expected set by all five scenarios. A prediction counts if emitted at any replay frame.
- Precision is true-positive service/scenario pairs divided by all predicted pairs. Recall divides those true positives by all labeled positive pairs.
- False-positive rate divides wrongly predicted pairs by all labeled negative pairs. There are 15 pairs across five scenarios and three services.
- Detection delay starts at injected fault onset and ends at the first observation that satisfies the outage threshold for each affected service. Its mean includes detected services only, including downstream symptoms.
- Diagnosis delay starts at injected fault onset and ends at the first frame that names each correctly predicted root. Its mean includes true positives only.
- Confidence calibration is omitted because five hand-authored scenarios cannot estimate reliability across confidence levels.

The local seeded suite produced 5/5 exact matches, 5 true positives, 10 true negatives, zero false positives, and zero false negatives. Mean detection delay was 10 seconds over six detected services. Mean diagnosis delay was 1 second over five correctly predicted causes. These values describe scripted local fixtures. Live observations vary with polling alignment, and a short live spike can fall between polls.

## HTTP API

| Method and route | Purpose |
| --- | --- |
| GET /dependencies | Read active topology |
| GET /dependencies/{version} | Read an immutable topology version |
| PUT /dependencies | Publish topology using the expected version |
| GET /incidents/{id}/diagnosis | Read hypotheses and separate fault records |
| GET /scenarios | List the five seeded recipes |
| GET /scenarios/{id} | Preview a seeded replay |
| POST /scenarios/{id}/run | Apply bounded faults to local simulators |
| GET /replays | List saved sessions |
| GET /replays/{id} | Load stored replay frames |
| POST /replays | Save a seeded or recorded replay |
| GET /evaluation | Compute synthetic evaluation results |

All PUT and POST routes require the existing administrator authorization. Scenario faults expire independently of the API process. Phase 3 proposes a separate dry-run recovery policy evaluator.
