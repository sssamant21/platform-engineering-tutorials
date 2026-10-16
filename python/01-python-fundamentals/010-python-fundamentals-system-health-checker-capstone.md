# Chapter 010 — Python Fundamentals Capstone: System Health Checker

**Part 01 — Python Fundamentals | Python 3.10+ | Capstone | 2–3 hours**

## Mission
Combine Python fundamentals from Chapters 001–009 into a **read-only, cross-platform SRE health checker** that validates a local JSON fixture, evaluates CPU, memory and disk thresholds, reports health in JSON and returns meaningful exit codes. No production API, cloud credential, or privileged access is required.

## Learning outcomes
- Apply variables, types, operators, conditions, loops, strings and collections.
- Build a command-line interface with `argparse`.
- Parse and validate JSON without silently treating missing data as healthy.
- Produce deterministic, machine-readable reports.
- Test threshold boundaries, invalid inputs, duplicates and failure behavior.
- Distinguish a simulated capacity report from live system observability.

## 1. Architecture

```text
local fixture (JSON)
        |
        v
CLI + UTF-8 file reader
        |
        v
schema and range validation
        |
        v
per-host health classification
        |
        v
fleet aggregation and JSON output
        |
        v
documented process exit code
```

The design separates validation, classification and presentation so each component can be tested independently. The fixture contains synthetic telemetry; the program does not query actual host metrics.

## 2. Data contract
Each host has a unique `name` and numeric `cpu_pct`, `memory_pct`, `disk_pct` values in the closed interval [0, 100]. All fields are required. Booleans, nulls, non-finite values, negative values and percentages above 100 are invalid.

Example:
```json
[
  {"name":"node-a","cpu_pct":45,"memory_pct":60,"disk_pct":50},
  {"name":"node-b","cpu_pct":81,"memory_pct":70,"disk_pct":65},
  {"name":"node-c","cpu_pct":92,"memory_pct":91,"disk_pct":96}
]
```

## 3. Threshold policy
| Metric | Warning threshold | Critical threshold |
|---|---:|---:|
| CPU | >= 75% | >= 90% |
| Memory | >= 80% | >= 95% |
| Disk | >= 80% | >= 95% |

Any critical metric makes a host critical; otherwise any warning metric makes it warning; otherwise healthy. Fleet severity uses critical > warning > healthy. Invalid telemetry is a **validation failure**, not a healthy measurement.

These are educational thresholds. Production alert policies require workload-specific baselines, sustained evaluation windows, telemetry freshness, SLOs and owner approval.

## 4. Implementation strategy
The [companion lab](labs/010-system-health-checker-capstone-lab.md) contains the complete executable `health_checker.py`, a JSON fixture, a `unittest` suite, CLI commands and negative tests. Build it incrementally:

1. Parse CLI arguments and read UTF-8 JSON.
2. Validate the root list, each record, unique names and metric types.
3. Evaluate severity using ordered comparisons.
4. Loop through records and construct deterministic summaries.
5. Emit JSON on stdout, diagnostics on stderr and documented exit codes.
6. Execute tests and inspect boundary behavior.

## 5. CLI contract
```bash
python health_checker.py --input hosts.json
python -m unittest -v test_health_checker.py
python -m py_compile health_checker.py
```

Successful report generation returns 0 for healthy, 1 for warning, 2 for critical. Argument and input validation errors use argparse's exit code 2 and **do not emit a report**. Because critical and invalid input both use exit 2, callers must distinguish them by checking for a valid JSON report on stdout; before production integration, consider a separate error code such as 4.

## 6. Reliability and security
- Never execute commands from untrusted fixture content.
- Never auto-remediate or delete infrastructure.
- Do not put secrets, credentials or patient information in fixtures.
- Reject duplicates and missing telemetry.
- Use stable sorting for reproducible incident evidence.
- Do not confuse a single sampled percentage with a sustained service incident.
- Avoid reading arbitrarily large input files in a production implementation; impose an explicit file-size bound.

## 7. Troubleshooting
| Failure | Likely cause | Resolution |
|---|---|---|
| `FileNotFoundError` | Wrong fixture path | Use the correct relative/absolute path |
| `JSONDecodeError` | Malformed JSON | Validate syntax and remove trailing commas |
| `ValueError` | Missing/out-of-range metric | Correct the fixture |
| `TypeError` | Unexpected type | Validate booleans, strings and nulls |
| Unexpected critical | Critical branch evaluated | Check exact thresholds |
| Output parsing fails | Logs mixed into stdout | Keep JSON stdout-only |
| Tests not discovered | Wrong working directory | Run beside source and tests |

## 8. Capstone acceptance rubric (100 points)
| Area | Points |
|---|---:|
| Input schema and type validation | 25 |
| Correct boundary/severity classification | 25 |
| CLI and JSON report contract | 15 |
| Automated tests and negative scenarios | 20 |
| Operational safety and troubleshooting | 15 |

**Pass recommendation:** 85+ points and all critical validation tests passing.

## 9. Extensions
Add a `--format text` output, explicit telemetry timestamps with freshness checks, configuration-driven thresholds, and a read-only live metrics adapter in a later advanced chapter. Keep the capstone's core validation logic independent of data sources.

## Part 01 completion
This capstone concludes **Chapters 001–010 — Python Fundamentals**. Next, Part 02 deepens collection and algorithmic skills.

**Next:** Chapter 011 — Advanced List Operations and Comprehensions.
