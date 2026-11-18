# Contributing

CloudRescue is MIT-licensed. Keep experiments confined to local simulator services. Use a dedicated PostgreSQL test database, run the checks in the README, and include the seed and model version when reporting benchmark results. Preserve migration history and add new revisions for schema changes. Keep credentials, logs, generated reports, and database files outside commits.

Potential independent contributions include the deterministic workload generator, paired benchmark statistics, and pure recovery policy components. Separate them from CloudRescue-specific persistence and document their assumptions before proposing upstream work. Review runtime and development dependency licenses and advisory reports before a release. Do not send contributions on behalf of this project without maintainer authorization.
