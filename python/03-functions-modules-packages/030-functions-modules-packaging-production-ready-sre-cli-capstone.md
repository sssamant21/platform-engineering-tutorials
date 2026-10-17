# Chapter 030 — Functions, Modules and Packaging Capstone: Production-Ready SRE CLI

**Part 03 — Functions, Modules and Packages (final capstone) | Python 3.10+ | 4–6 hours**

## Objectives and acceptance contract

Integrate the skills from Chapters 021–029: functions and contracts, closures and callbacks, functional composition, decorators and timing, modules/imports, isolated environments, wheel packaging, layered configuration, safe secret references, and operational CLI design.

**Deliverable:** a fully local, read-only `srekit` command that classifies synthetic latency/error-rate records, prints deterministic JSON, validates configuration, supports an explicit maintenance **plan** without an executor, provides operational exit codes, and can be installed from a wheel into a fresh virtual environment.

This is a **production-oriented reference architecture**, not a production-connected administration client. No network calls, live credentials, production changes or registry uploads occur.

## Architecture

```text
operator / GitLab CI / scheduled job
               |
               v
        srekit.cli (argparse)
           |         |
           v         v
    config.py      io.py  ──> synthetic JSON file
           \         /
            v       v
       policy.py / models.py
                 |
                 v
         report.py (pure)
                 |
                 v
      deterministic JSON / exit code

instrument.py: optional monotonic measurement decorator
```

Dependency direction is inward: CLI and file adapters depend on pure domain logic, not vice versa. No module performs I/O at import time. Use dependency injection for file paths, environment mappings, and clock functions in future integrations.

## 1. Package structure

```text
srekit-capstone/
├── pyproject.toml
├── sample.json
├── src/srekit/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── policy.py
│   ├── report.py
│   └── instrument.py
└── tests/
    ├── test_core.py
    └── test_cli.py
```

The `src/` layout prevents accidentally importing the source tree instead of the installed package.

## 2. Contracts

**Input record:** `{"service":"api","latency_ms":180,"errors":1,"requests":100}`. No extra fields, duplicate service IDs, negative counts, nonfinite latency, boolean counts or zero requests are allowed.

**Classification:** default warning latency 200 ms and critical latency 500 ms; warning error rate 2% and critical error rate 10%. Thresholds are inclusive. Overall severity is the maximum of latency and error severities.

**Output:** JSON with `schema_version: 1`, sorted service results and aggregate counts. Structured output is safe for CI and does not contain secrets.

**Exit codes:**
| Code | Meaning |
|---|---|
| 0 | Healthy report or valid dry-run plan |
| 2 | Invalid CLI arguments, configuration or record schema |
| 3 | At least one service is warning or critical |
| 4 | Unsafe execution request explicitly blocked |
| 5 | Input file could not be read or parsed |

Errors go to stderr; successful JSON goes to stdout. No partial JSON should be emitted on validation failure.

## 3. Configuration and secret handling

Precedence: safe defaults → reviewed JSON configuration file → explicit `SREKIT_` environment overrides → CLI overrides. Only documented keys are accepted. The default environment is **staging**. The lab refuses non-dry-run production configuration and rejects `--execute` for maintenance planning.

The configuration contains a **secret reference**, never a secret value. Secret managers, workload identity, rotation, and credential transport belong in separately reviewed adapters. Environment variables are not a secure vault. Do not log raw config, `os.environ`, headers or stack traces containing credentials.

## 4. Instrumentation and performance

Use `time.perf_counter()` for monotonic elapsed-time measurement. A `functools.wraps` decorator preserves function metadata. Instrumentation should be opt-in and avoid high-cardinality labels or exposing request payloads. For production systems, send metrics to approved telemetry backends, not stdout when JSON is promised.

## 5. Packaging and supply chain

Use `pyproject.toml` with a controlled build backend and a `[project.scripts]` entry point. Build and test an immutable wheel, record its SHA-256 from a trusted build, and install the exact artifact into a clean venv with `--no-index --no-deps`. Hash verification checks integrity against a trusted expected digest; it does not prove publisher identity.

A production release pipeline should add pinned build tools, dependency scans, SBOM/provenance attestations, signatures or trusted publishing, change approval, and a rollback artifact. The lab uses no third-party **runtime** dependencies, but build tooling may need provisioning.

## 6. CI/CD reference workflow

```text
PR review
 → static compile / tests
 → configuration and safety checks
 → wheel build
 → SHA-256 + artifact metadata
 → fresh-venv install
 → CLI smoke tests
 → approved release gate
```

Do not use an unreviewed wheel, dynamically fetch packages on production hosts, or rebuild between staging and production.

## 7. SRE/DBRE scenarios

- PostgreSQL: evaluate synthetic replication-lag or query-latency samples before adding a read-only metrics adapter.
- Elasticsearch: classify synthetic search latency while avoiding write/index-delete privileges.
- Kafka: assess synthetic consumer-lag and error metrics with a future domain-specific policy.
- Kubernetes: render a dry-run inventory plan, never mutate workloads.
- Snowflake: build a sanitized report from synthetic query-duration data.

Do not mistake a synthetic `healthy` result for a real service health check.

## 8. Failure-mode and troubleshooting matrix

| Symptom | Root cause | Runbook |
|---|---|---|
| `ModuleNotFoundError` | Wrong venv / package not installed | Check interpreter and install wheel |
| Relative-import error | Running `cli.py` directly | Use `python -m srekit` |
| `nan` or `inf` accepted | Missing finite validation | Reject at schema boundary |
| Duplicate service in report | Missing uniqueness check | Fail entire batch |
| Exit 0 on degraded service | Lost status-to-exit mapping | Assert exit 3 in tests |
| CLI JSON polluted by logs | Debug output to stdout | Send diagnostics to stderr |
| Secret reference printed | Raw configuration serialization | Use sanitized summary |
| Production execution possible | Planner wired to mutating executor | Remove executor; block `--execute` |
| Wheel fails on clean host | Build/import leakage | Fresh-venv install outside checkout |
| Dependency/hash mismatch | Artifact drift or compromised build | Stop promotion; investigate provenance |

## 9. Production operational runbooks

**Preflight:** confirm interpreter, artifact digest, package version, approved config source, staging profile, file schema and read-only identity. Run unit tests before promotion.

**Degraded classification:** capture JSON and exit 3, verify source data and thresholds, correlate with authoritative metrics, and escalate using service SLOs. Do not initiate remediation based solely on synthetic data.

**Configuration failure:** exit 2, stop job, inspect sanitized config and precedence, correct approved inputs, rerun tests, and preserve an audit record.

**Artifact integrity failure:** quarantine the artifact, preserve expected and observed hashes, examine builder provenance and CI logs, and restore a previously approved version.

**Unsafe action request:** exit 4, record blocked operation, require separate reviewed workflow with least privilege and rollback. This lab intentionally provides no executor.

## 10. Capstone lab

[Chapter 030 — Packaged SRE CLI Capstone Lab](labs/030-production-ready-sre-cli-capstone-lab.md) contains complete code for every file, synthetic fixtures, unit tests, build/install commands, failure injection, and a 100-point acceptance assessment.

## 11. 100-point assessment

| Area | Points |
|---|---:|
| Package architecture and clean imports | 15 |
| Strict schema and domain policy | 20 |
| Layered configuration and redaction | 15 |
| CLI contracts, JSON and exit codes | 15 |
| Dry-run safety and blocked execution | 10 |
| Unit tests and failure injection | 15 |
| Wheel install, provenance and runbooks | 10 |
| **Total** | **100** |

Passing target: **85/100**, with **all safety-critical checks mandatory**: no real mutations, no secret leakage, blocked execution, strict input validation and clean installation. Local execution evidence is required; publication alone is not a test pass.

**Part 03 completes with this chapter. Next: Chapter 031 — Python Classes, Objects and Encapsulation**, beginning Part 04 — Object-Oriented Programming.
