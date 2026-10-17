# Chapter 044 — Python Logging, Structured Logs and Operational Observability

**Part 05 | Python 3.10+ | SRE/DBRE | 4–6 hours**

## Objectives
Build a structured logging pipeline with Python `logging`, JSON lines, validated event metadata, `contextvars` correlation IDs, secret redaction, rotating file handlers, deterministic tests and operational runbooks.

## 1. Logging architecture
A logger creates `LogRecord` objects. Levels filter events; handlers route them; formatters serialize them. Prefer a named logger with `propagate=False` when configuring a standalone application. Reconfiguration must close old handlers to avoid duplicate records and file-descriptor leaks.

```python
import logging
logger = logging.getLogger("sre.preflight")
logger.warning("synthetic replication lag threshold exceeded")
```

| Level | Meaning | Operational use |
|---|---|---|
| DEBUG | Developer diagnostics | Usually disabled in production |
| INFO | Expected state transitions | Startup, successful preflight |
| WARNING | Degraded but functioning | Elevated replica lag |
| ERROR | Failed operation | Search request failed |
| CRITICAL | Severe service failure | Broad outage |

## 2. JSON structured logging
A stable allowlisted schema is easier to query than free-form messages. This chapter emits timestamp, level, logger, event, service, status, correlation_id and message. A JSON formatter ensures each event is one parseable line. Reject unknown event types and services instead of accepting arbitrary untrusted `extra` fields.

```json
{"timestamp":"2026-10-17T12:00:00","level":"WARNING","logger":"sre_ch044","event":"probe_result","service":"postgresql","status":"warning","correlation_id":"incident_001","message":"synthetic lag exceeded threshold"}
```

The example timestamp is illustrative. The lab uses the host's local timezone; production should emit explicit UTC timestamps with timezone offsets.

## 3. Correlation IDs and context propagation
Use `contextvars.ContextVar` to carry request identity across asynchronous task contexts. Validate IDs (length and characters) and always reset the token in `finally`. Do not use PHI, credentials or user secrets as correlation IDs. Trace IDs and span IDs remain separate distributed tracing concepts.

## 4. Sensitive-data minimization
Prefer **never logging sensitive values**. The lab demonstrates basic redaction for assignments such as `password=...`, `token:...`, `secret=...` and `api_key=...`. Regex-based redaction is incomplete for encoded, nested or unusual secrets; it is not a production guarantee. Avoid raw SQL parameters, connection URLs, patient records, bearer tokens and unreviewed exception strings.

## 5. Rotation and retention
`RotatingFileHandler(maxBytes=..., backupCount=...)` bounds individual file size and number of backups. It is not multiprocess-safe when multiple processes rotate the same file. Prefer stdout with centralized collection in containers. Enforce least-privilege filesystem permissions, disk alerts and retention policies.

## 6. Logs, metrics and traces
Logs explain events; metrics quantify behavior and SLOs; traces connect operations across components. Use correlation IDs to link signals, but do not replace metrics and tracing with logs alone.

## 7. SRE/DBRE use cases
- PostgreSQL: synthetic replication-lag warning and recovery event.
- Elasticsearch: synthetic search timeout and failure classification.
- Kafka: synthetic consumer-lag event and correlation ID.
- Redis: synthetic cache health events.

The executable lab is offline and never connects to these systems.

## 8. Failure matrix

| Symptom | Root cause | Response |
|---|---|---|
| Missing logs | Level or handler mismatch | Inspect logger/handler levels |
| Duplicate events | Multiple installed handlers | Close and remove previous handlers |
| Unparseable lines | Mixed formatters | Use a single JSON schema |
| Credential leakage | Untrusted message payload | Contain, rotate, redact at source |
| Disk full | Rotation/retention misconfiguration | Cap files and ship centrally |
| Wrong request ID | Global mutable context | ContextVar set/reset |
| Time disagreement | Local time or clock skew | UTC with explicit offset |
| Rotation errors | Multiple writers or ACLs | Single writer or stdout |

## 9. Production runbooks

**Logging outage:** inspect disk space, permissions, logger levels and collection health; restore safe logging before changing infrastructure.

**Secret exposure:** restrict access to affected logs, coordinate credential rotation, preserve incident evidence and update data-minimization controls.

**High log volume:** inspect duplicate handlers and per-service cardinality, reduce DEBUG volume, retain actionable ERROR/WARNING events.

**Correlation incident:** test concurrent request scopes and context reset; verify tracing context propagation.

**Rollback:** restore last known-good formatter/schema, replay sanitized fixtures and validate downstream dashboards and alert queries.

## 10. Lab and assessment
[Chapter 044 — Structured Logging and Correlation SRE/DBRE Lab](labs/044-structured-logging-correlation-sre-dbre-lab.md) contains complete executable modules, 40 unit tests, synthetic scenarios, failure injection, troubleshooting and acceptance checklist. **All 40 tests passed in the authoring Linux sandbox.**

**Next:** Chapter 045 — Python Configuration Management and Environment Variables.
