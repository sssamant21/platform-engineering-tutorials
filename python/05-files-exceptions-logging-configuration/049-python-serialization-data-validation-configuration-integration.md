# Chapter 049 — Python Serialization, Data Validation and Configuration Integration

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+ | 5–7 hours**

## Learning outcomes
Design a versioned JSON data contract, serialize deterministically, parse untrusted files with size and encoding limits, reject duplicate keys and nonfinite numbers, validate configuration and telemetry schemas, avoid secret leakage, and test safe SRE/DBRE reporting.

## 1. Serialization versus validation
Serialization converts in-memory values into a transport/storage representation. Deserialization recreates values from that representation. Neither proves the input is safe or semantically correct. A syntactically valid JSON document can contain wrong field names, unexpected types, invalid units, or excessive resource demands.

Prefer explicit allowlisted schemas and reject unknown fields. In production, use a schema registry or validated JSON Schema/Pydantic contracts when the dependency and governance model permit them. The lab intentionally uses only the Python standard library.

## 2. JSON formats and canonical output
`json.dumps(..., sort_keys=True, separators=(',', ':'), allow_nan=False)` produces deterministic compact JSON for the same Python values. A SHA-256 digest detects accidental changes to those bytes, **not authenticity**. It is not a signature or a replacement for HMAC or a digital signature.

JSON object key order is not semantically meaningful. A production canonicalization standard is needed for cross-language cryptographic interoperability. Python float formatting and schema evolution must be considered before using canonical bytes as a protocol.

## 3. Safe deserialization
The lab rejects duplicate object keys with `object_pairs_hook`, rejects `NaN`/`Infinity` with `parse_constant`, limits files to 64 KiB, enforces UTF-8, rejects symlink inputs, and checks the root shape. It does not claim protection against all adversarial filesystem races or arbitrary JSON nesting complexity. For hostile inputs, add bounded depth, isolation and resource limits.

Never use `pickle` on untrusted data: deserializing a malicious pickle can execute code. Do not treat YAML or other permissive formats as safe without appropriate safe loaders and schema checks.

## 4. Schema contracts
The configuration object has exactly `schema_version`, `environment`, `max_events`, and `secret_ref`. Only schema version 1 is supported. The telemetry record requires `service`, `engine`, `metric`, `value`, `unit`, and `timestamp`.

| Engine | Metric | Unit | Synthetic critical threshold |
|---|---|---|---:|
| PostgreSQL | replication_lag | seconds | 120 |
| Elasticsearch | search_latency | milliseconds | 500 |
| Kafka | consumer_lag | messages | 10,000 |

These are educational thresholds, **not production SLOs**. Validate metric/unit pairs before interpreting numeric values.

## 5. Configuration integration
A frozen `dataclass` represents validated configuration. The report exposes only `secret_configured`, not `secret_ref`; it never resolves or retrieves a real credential. A secret reference may reveal internal resource names, so do not log it.

Treat schema versions as explicit compatibility boundaries. Reject unknown versions, introduce new versions with tests, and migrate consumers deliberately. Do not silently coerce string metrics to numbers or accept booleans as integers.

## 6. Architecture
```text
synthetic config.json + events.json
    -> bounded file reader
    -> strict JSON decoder
    -> allowlisted schema validation
    -> immutable configuration + typed events
    -> safe, deterministic JSON report
    -> SHA-256 content fingerprint
```

## 7. SRE/DBRE scenarios
- PostgreSQL replication-lag incident summaries.
- Elasticsearch latency ingestion and threshold classification.
- Kafka consumer-lag operational reports.
- Kubernetes ConfigMap validation before deployment.
- CI configuration contract checks and schema compatibility testing.

The lab performs **no live infrastructure calls or mutations**.

## 8. Troubleshooting
| Symptom | Likely cause | Response |
|---|---|---|
| Duplicate-key error | Ambiguous producer JSON | Correct exporter |
| Invalid JSON / encoding | Corrupted export | Re-export UTF-8 |
| Unknown field | Schema drift | Coordinate schema migration |
| Wrong severity | Metric/unit mismatch | Verify contract and threshold |
| Invalid timestamp | Naive or malformed time | Require UTC seconds |
| Different hash | Data or serialization changed | Compare sanitized canonical report |
| Secret appears in output | Unsafe serialization | Stop distribution, rotate if exposed |
| File exceeds limit | Unexpected payload growth | Batch safely or adjust approved contract |

## 9. Production runbooks
**Schema incompatibility:** stop ingestion, capture sanitized schema version and error category, deploy compatible parser or revert producer, replay fixtures and verify.

**Data corruption:** quarantine affected export, validate UTF-8 and record counts, re-export from trusted source and compare fingerprints.

**Secret exposure:** restrict access to affected artifacts, rotate compromised credentials and audit serialization paths.

**Deployment rollback:** restore last known-good schema and parser, run regression tests, and verify telemetry quality before enabling automation.

**Fingerprint mismatch:** investigate source and schema differences; do not treat a bare SHA-256 digest as proof of tampering.

## 10. Hands-on lab
[Chapter 049 — Safe Serialization and Configuration Contract SRE/DBRE Lab](labs/049-safe-serialization-configuration-contract-sre-dbre-lab.md) contains full source, CLI, synthetic fixtures, **54 automated tests**, failure injection and a 100-point acceptance rubric.

**Next:** Chapter 050 — Files, Exceptions, Logging and Configuration Production Capstone.
