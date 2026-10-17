# Chapter 029 — Python CLI Design, argparse and Operational User Experience

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 2–3 hours**

## Outcomes
Design an operational CLI with `argparse`, subcommands, validated options, stable machine-readable JSON, human-readable output, clear exit codes, dry-run and confirmation safeguards, predictable stderr/stdout contracts, offline unit tests, and release/runbook guidance.

## 1. CLI is an operational API
A command-line interface is an API for humans, cron jobs, GitLab pipelines and incident automation. Changing exit codes or JSON field names can break downstream alerting. Design contracts before implementation.

```text
operator/CI → argparse → strict validation → policy decision → read-only adapter
                                    |
                                    +→ stdout: JSON result
                                    +→ stderr: diagnostics
                                    +→ exit status: machine contract
```

Never let `--help` import cloud clients or contact a production cluster.

## 2. argparse fundamentals
```python
import argparse
parser = argparse.ArgumentParser(prog="srectl")
sub = parser.add_subparsers(dest="command", required=True)
check = sub.add_parser("check", help="classify synthetic latency")
check.add_argument("--latency-ms", type=float, required=True)
args = parser.parse_args(["check", "--latency-ms", "300"])
```

Prefer named flags for high-risk inputs. Add descriptions, examples and meaningful validation errors. `argparse` normally exits 0 for `--help` and 2 for usage errors.

## 3. Subcommands and discoverability
Subcommands separate actions with different contracts: `check`, `batch`, `config` and `version`. Keep names consistent and support `--help` at the root and subcommand levels. A CLI should not silently infer an environment or target.

## 4. stdout, stderr and JSON
Send successful structured results to stdout, errors to stderr, and avoid progress messages in JSON output. Use `json.dumps(..., sort_keys=True, allow_nan=False)` and a documented schema version. Never serialize secrets, environment dumps or raw credentials. Deterministic key and record ordering supports testing and reproducible incident artifacts.

## 5. Exit codes
| Code | Meaning | Automation response |
|---|---|---|
| 0 | Command completed; status healthy or dry-run plan produced | Continue |
| 2 | Invalid usage or input | Correct invocation |
| 3 | Valid data, but health threshold breached | Investigate |
| 4 | Approved action blocked by safety policy | Request review |
| 5 | Read or parsing failure | Investigate data source |

Document exit codes rather than relying on an exception's string. Keep exit semantics stable across versions. `argparse` uses 2 for usage errors; the lab maps file failures to 5.

## 6. Dry-run and safety
`--dry-run` must show the intended operation without performing a mutation. It is not a guarantee unless **every side-effecting adapter** honors it. Prefer a pure planner and a separate executor. This lab contains no executor: `plan` is always non-mutating and explicitly rejects requests to execute.

For production changes, require independent authorization, least-privilege identity, explicit environment/cluster selection, idempotency and rollback. Do not rely solely on a confirmation prompt in CI.

## 7. Input validation
Reject negative latency, booleans passed through APIs, NaN/infinity, invalid thresholds, malformed JSON, duplicate service IDs and unknown keys. Validate **before** filtering or planning. Avoid accepting arbitrary code, shell snippets or paths with unclear semantics.

## 8. CLI UX guidelines
- Show units in flags: `--latency-ms`, `--timeout-seconds`.
- Use explicit environment and action flags.
- Provide examples in `--help`.
- Offer a stable JSON mode for automation.
- Avoid interactive prompts in CI; fail with actionable errors.
- Make dry-run plans visible and deterministic.
- Ensure terminal output is safe to paste into tickets.

## 9. Production SRE/DBRE examples
- `srectl check --service api --latency-ms 350`: offline classification.
- `srectl batch --input metrics.json`: synthetic multi-service report.
- `srectl plan --environment staging --target elasticsearch`: non-mutating maintenance preview.
- Similar patterns extend to PostgreSQL diagnostics, Kafka consumer checks, Kubernetes inventory and Snowflake metadata audit.

## 10. Troubleshooting
| Symptom | Root cause | Response |
|---|---|---|
| Exit 0 despite threshold breach | Health state conflated with execution success | Define distinct code 3 |
| JSON cannot be parsed | Progress output mixed into stdout | Send diagnostics to stderr |
| NaN accepted | Float parser without finite validation | Validate with `math.isfinite` |
| Dry-run accidentally mutates | Shared execution path | Separate pure planner from executor |
| CLI blocks CI | Interactive confirmation | Fail closed; use approved noninteractive workflow |
| Wrong subcommand | Parser design ambiguity | Required subparsers and help |
| Secrets in logs | Raw exception/config printing | Sanitize and allowlist fields |

## 11. Runbook
1. Verify command version and `--help`.
2. Confirm input units and target environment.
3. Run `plan` for any potentially mutating workflow.
4. Capture stdout JSON and exit code separately.
5. Treat exit 3 as a health signal, not a parser error.
6. Preserve sanitized results for audit.
7. On unexpected behavior, stop automation, pin the known-good CLI artifact, and investigate schema/exit-code changes.

## 12. Lab and acceptance
[Chapter 029 — Operational SRE CLI Lab](labs/029-operational-sre-cli-argparse-lab.md) provides a complete single-file CLI, fixture, 30 unit tests, failure injection and operational guidance. It is entirely offline and read-only.

**Next: Chapter 030 — Functions, Modules and Packaging Capstone: Production-Ready SRE CLI.**
