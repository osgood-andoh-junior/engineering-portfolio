# CloudRescue Traces

A dependency-free Python 3.12+ parser for bounded reliability workloads. Install the package from this directory with `python -m pip install .`, then run `cloudrescue-traces examples/trace.csv`.

The Python API is `cloudrescue_traces.load(Path("examples/trace.csv"))`. It returns immutable frames with relative millisecond timestamps, request counts, and named fault states.

CSV uses exactly the header `time_ms,requests,fault`. JSON is an array of objects with the same keys. Provide 1–30 rows spaced exactly 1000 milliseconds apart. The first timestamp is normalized to zero. Requests per row range from 1 to 8. Faults are healthy, latency, error, or disconnect. Fields for URLs, credentials, identifiers, and commands are rejected. The examples are authored fixtures. Supply provenance separately and remove sensitive identifiers before importing a trace.

The package uses the MIT license. It has no CloudRescue backend, database, HTTP client, or frontend dependency.
