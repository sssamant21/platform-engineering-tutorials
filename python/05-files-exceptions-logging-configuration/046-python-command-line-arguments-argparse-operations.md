# Chapter 046 — Python Command-Line Arguments and argparse for Operations

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+ | 5–7 hours**

## Learning outcomes
Build production-style SRE/DBRE command-line tools using `argparse`, typed options, subcommands, strict input validation, machine-readable JSON/CSV output, predictable exit codes, read-only dry-run behavior and automated acceptance tests.

## Architecture
```text
operator/CI -> argparse -> strict local JSON inventory -> validated records
 -> synthetic datastore severity classifier -> validate/check/plan
 -> JSON or CSV stdout + deterministic exit status
```

The chapter uses synthetic PostgreSQL replication lag, Elasticsearch query latency and Kafka consumer lag. No credentials, cloud calls or infrastructure changes.

## 1. CLI contracts
A CLI is an API for humans and automation. Treat option names, help, subcommand semantics, stdout/stderr, exit status and output schema as versioned contracts. Use `ArgumentParser` and `add_subparsers(required=True)`. Global flags appear before subcommands; command-specific flags appear afterward.

```python
import argparse
parser=argparse.ArgumentParser(prog="sre-cli")
parser.add_argument("--inventory", required=True)
sub=parser.add_subparsers(dest="command", required=True)
sub.add_parser("validate")
sub.add_parser("check")
sub.add_parser("plan")
```

The lab supports:
- `validate`: validate a local fixture, report record count.
- `check`: classify metrics, optionally filter by datastore engine.
- `plan`: output advisory recommendations **without executing changes**.

## 2. Input validation
JSON parsing should reject duplicate keys and nonfinite numbers. Validate expected fields, value types, service names, record counts and size limits. Avoid treating boolean as a number: `isinstance(True,int)` is true in Python. Limit input to 1 MiB and 1,000 records. Reject symlinks and malformed UTF-8. This lab assumes a trusted local directory, not a hostile multiuser filesystem.

## 3. Synthetic thresholds
| Engine | Unit | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication lag seconds | 30 | 120 |
| Elasticsearch | query latency milliseconds | 200 | 500 |
| Kafka | consumer lag messages | 1,000 | 10,000 |

These are **teaching thresholds**, not production alerting recommendations.

## 4. Exit codes
| Code | Meaning |
|---|---|
| 0 | healthy or valid input |
| 1 | warning |
| 2 | critical |
| 3 | invalid inventory / I/O failure |

**Design caveat:** standard `argparse` also exits with 2 for command-line usage errors, so code 2 is ambiguous. This lab exposes that limitation intentionally. In production, reserve distinct codes (for example 64 for usage errors using a custom parser) or place health status in a structured result and reserve exit codes for execution success/failure. CI consumers must inspect stderr and the output schema rather than assuming code 2 always means critical health.

## 5. Output contracts
JSON output contains `schema_version`, `dry_run`, `total`, severity `counts` and sorted `results`. CSV uses a stable header. Write intended output to stdout and errors to stderr. Restrict service names to alphanumeric/dash/underscore to reduce spreadsheet formula injection; broader CSV exporters need explicit cell escaping.

## 6. Safety and idempotency
All three commands are read-only. A `plan` operation produces advice only. Do not introduce an `--execute` switch that silently turns inspection into deletion, failover or restarts. Future mutation tools require separate approval, RBAC, target confirmation, idempotency, auditing and rollback.

## 7. Troubleshooting
| Symptom | Cause | Response |
|---|---|---|
| Unrecognized arguments | Global option placed after subcommand | Move it before the command |
| Exit code 2 | Usage error or critical metric | Inspect stderr and JSON; fix ambiguous contract |
| Invalid JSON | Truncated file or duplicate keys | Re-export and validate |
| Wrong severity | Unit mismatch | Verify source metric and thresholds |
| CSV parser failure | Changed schema | Version and regression-test output |
| Access denied | Permissions/ACL | Inspect process identity and parent directory |
| Automation false positive | Synthetic thresholds used in production | Calibrate against SLOs |
| Unexpected writes | Unreviewed feature | Disable and audit command implementation |

## 8. Production runbooks
**Invalid inventory:** halt automation, preserve sanitized metadata, correct export schema and replay known-good fixtures.

**Critical classification:** corroborate with authoritative telemetry, check freshness and user impact, escalate per SLO policy; do not auto-remediate.

**CLI compatibility incident:** pin previous CLI version, compare JSON schema and exit codes, run contract tests before resuming CI jobs.

**Security review:** prohibit secret-bearing command-line flags, validate filesystem access and audit imports/dependencies.

## 9. Lab and assessment
[Chapter 046 — Production-Style SRE/DBRE argparse CLI Lab](labs/046-production-style-sre-dbre-argparse-cli-lab.md) contains executable source, a synthetic fixture, unit tests, failure injection, runbooks and a 100-point assessment. An authoring implementation passed 50 unit tests in Linux; learners must run the published lab independently.

**Next:** Chapter 047 — Python Regular Expressions and Operational Text Parsing (provisional).
