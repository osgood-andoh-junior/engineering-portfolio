# Phase 5 proposal

Start with independent review and a preregistered evaluation on workload traces created by reviewers. Add calibration for diagnosis and detection separately, and validate the traffic model against instrumented simulator measurements.

Strengthen release operations with an independent checkpoint storage procedure, role-change reviews, session lifecycle controls, dependency and license inventory, and a CI matrix that verifies migrations on PostgreSQL 17. Keep rollout, recovery, and observability experiments local until a separate authorization and security review establishes external scope.

The workload generator, statistical comparison utilities, and pure policy components are candidates for independently reviewed open-source packages.
