# Chapter 050 — Files, Exceptions, Logging and Configuration Production Capstone

**Part 05 final capstone | Python 3.10+ | 8–12 hours**

## Mission and acceptance criteria
Build a complete **offline, read-only** SRE/DBRE reporting pipeline using lessons from Chapters 041–049: safe filesystem access, strict JSON serialization, exception classification and chaining, bounded retries, structured JSON logs, configuration validation, CLI contracts, and deterministic operational reporting. Complete the linked lab, run automated tests and demonstrate incident simulations. No live infrastructure or destructive operations.

## Architecture
```text
CLI arguments
   -> config.json -> bounded UTF-8 JSON parser -> strict configuration contract
   -> events.json -> bounded UTF-8 JSON parser -> read-only retry boundary
   -> typed PostgreSQL / Elasticsearch / Kafka metric validation
   -> deterministic severity summary -> canonical JSON + SHA-256 fingerprint
   -> temporary file + fsync + atomic os.replace -> report.json
   -> sanitized structured logging / error exit code
```

## 1. Operational data contract
Config v1 requires `schema_version`, `environment`, `max_attempts`, and `secret_ref`. Secret references are validated but **never included in the report**; only `secret_configured` is exposed. No secrets are resolved.

Each event requires `service`, `engine`, `metric`, `unit`, `value`, and a UTC timestamp. Unknown fields, wrong units, NaN/Infinity, negative metrics, invalid calendar dates, duplicate JSON keys and symlinks are rejected.

| Engine | Metric | Unit | Warning | Critical |
|---|---|---|---:|---:|
| PostgreSQL | replication_lag | seconds | 30 | 120 |
| Elasticsearch | search_latency | milliseconds | 200 | 500 |
| Kafka | consumer_lag | messages | 1,000 | 10,000 |

Thresholds are synthetic teaching examples, not approved production alert rules.

## 2. Safe filesystem boundaries
The input reader caps each file at 64 KiB and uses strict UTF-8. Output is restricted to `report.json` in a trusted, existing directory. The writer creates a temporary file in the same directory, flushes and `fsync`s it, then calls `os.replace` for atomic replacement on a supported local filesystem.

**Security limitations:** This is an educational implementation for a private, trusted directory. It is not hardened against hostile multiuser path races, symlink swaps between validation and open, or cross-filesystem behavior. Directory fsync, cross-platform ACL hardening and durability guarantees beyond the file fsync are not implemented. Production code should use hardened dirfd/openat patterns where available and platform-specific ACLs.

## 3. Exceptions and resilience
Use a small hierarchy: `OpsError`, `InputFailure`, `TransientFailure`, `PermanentFailure`. Only explicitly transient, **read-only** operations may be retried. The injectable retry helper applies bounded exponential backoff and stops after at most four attempts. The current file reader does not translate ordinary filesystem failures into transient exceptions; it therefore **does not retry arbitrary I/O errors**. Real HTTP/DB clients need connect/read timeouts, overall deadlines, jitter, Retry-After support and retry budgets. A synchronous Python loop cannot forcibly interrupt a blocked network call.

Preserve exception causes with `raise ... from exc`, but return sanitized public error messages. Never emit secret-bearing config or raw rejected records in logs.

## 4. Structured logging
Use `logging` and `JsonFormatter` with a fixed event vocabulary. Optional `RotatingFileHandler` supports bounded local log files. This capstone uses a `NullHandler` by default to avoid unexpected log writes. For production, supply a managed sink, correlation IDs, trace context, rotation retention, access controls and central ingestion.

## 5. Deterministic reports
Canonical JSON uses sorted keys and compact separators. A SHA-256 digest supports change detection; it does **not** prove authenticity or replace a digital signature. Output status is in the report's `counts` object. CLI exit code 0 means processing succeeded, **not** that the synthetic datastores are healthy. Exit code 3 indicates a handled execution failure; `argparse` uses code 2 for invalid CLI syntax.

## 6. SRE/DBRE use cases
- PostgreSQL replica lag pre-maintenance assessment.
- Elasticsearch query latency investigation.
- Kafka consumer lag trend snapshots.
- Read-only change-control evidence collection.
- CI schema validation and operational reporting.

## 7. Troubleshooting
| Symptom | Root cause | Action |
|---|---|---|
| Invalid JSON | Duplicate keys, truncation or NaN | Regenerate trusted export |
| Schema failure | Missing/unknown fields | Coordinate producer contract |
| Wrong severity | Incorrect metric unit | Verify source units and thresholds |
| Retry storm | Transient classification too broad | Disable retries, enforce budget |
| Report not written | Directory permissions | Check process identity and ACL |
| Sensitive output | Unsafe serialization | Contain artifact, rotate if exposed |
| Non-atomic output | Unsupported filesystem semantics | Use approved local filesystem |
| Stale telemetry | Export not refreshed | Check timestamp and producer freshness |

## 8. Production incident runbooks
**Schema drift:** stop scheduled ingestion, retain sanitized error category, pin compatible producer/consumer versions, replay synthetic and real approved fixtures.

**Transient service outage:** check timeout/deadline policy, reduce concurrency, use jitter and error budgets, avoid retries of mutations.

**Output integrity incident:** compare report fingerprints and source snapshots; do not assume a hash alone proves authenticity.

**Secret exposure:** revoke affected access, rotate exposed credentials and audit logging/reporting paths.

**Rollback:** disable scheduled invocation, restore known-good CLI and schema, rerun acceptance tests, verify output schema before resuming.

**Change approval:** the capstone is strictly read-only with respect to infrastructure; adding remediation requires separate explicit authorization and rollback design.

## 9. Capstone lab
[Chapter 050 — Integrated Production Operations SRE/DBRE Lab](labs/050-integrated-files-exceptions-logging-configuration-sre-dbre-capstone-lab.md) contains complete runnable code, synthetic fixtures, **65 unit tests**, incident simulations and a 100-point assessment. Test execution is a separate validation step; publication alone is not proof of a passing suite.

**Next:** Chapter 051 — Advanced Python Type Hints, Protocols and Static Analysis (Part 06).
