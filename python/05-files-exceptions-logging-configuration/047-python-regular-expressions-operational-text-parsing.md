# Chapter 047 — Python Regular Expressions and Operational Text Parsing

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+ | 5–7 hours**

## Objectives

Write reliable Python `re` patterns, distinguish `match`/`search`/`fullmatch`, use compiled named groups, safely extract operational metrics from bounded log lines, reject malformed records, protect against catastrophic backtracking, produce structured incident summaries and test edge cases.

## 1. Why operational text parsing matters

SRE/DBRE engineers often receive PostgreSQL slow-query logs, Elasticsearch search warnings, Kafka lag diagnostics, Redis latency messages and Kubernetes events. Text parsing is a bridge to structured telemetry—not a substitute for structured source logging. Always prefer JSON or other structured formats when available.

## 2. Regex fundamentals

| Construct | Meaning | Example |
|---|---|---|
| `^...` and `\Z` | Start/end anchors | Whole log record |
| `\d+` | One or more digits | Numeric field |
| `[A-Za-z0-9_-]+` | Allowed identifier | Service name |
| `(?P<name>...)` | Named capture | Extract field |
| `(?:...)` | Noncapturing group | Alternatives |
| `re.fullmatch` | Require entire input | Validation |
| `re.search` | Find occurrence | Diagnostic exploration |
| `re.compile` | Reuse a pattern | Hot-path parsing |

Use raw string literals `r"\d+"` so Python string escaping does not interfere with regex syntax. `re.MULTILINE` changes anchor behavior; avoid enabling flags without a reason.

## 3. Contract-first parsing

The lab accepts **synthetic** records with exactly this format:

```text
2026-10-17T12:00:00Z service=pg-replica engine=postgresql metric=replication_lag value=45 unit=seconds status=warning
```

The parser enforces timestamp syntax, an allowlisted service name, engine/metric/unit consistency, finite nonnegative numeric values, and severity consistency. A strict format prevents partial matches and silent field loss. The lab uses UTC timestamp parsing, including calendar validation.

## 4. Pattern design and safety

Avoid nested ambiguous quantifiers such as `(a+)+$` on untrusted input: catastrophic backtracking can consume excessive CPU. Limit line length before regex evaluation; use anchored patterns, bounded field widths and explicit character classes. Python's standard `re` has no built-in per-match timeout. For hostile, unbounded inputs consider a regex engine with a timeout, a simple deterministic parser, or isolation in a separate process.

## 5. Parsing pipeline

```text
synthetic log file
  -> byte and line limits
  -> strict UTF-8 decoding
  -> anchored compiled regex
  -> typed field validation
  -> engine/metric/unit contract
  -> severity classification
  -> deterministic JSON report
```

Keep bad input from becoming a successful report. Do not log entire rejected lines; they may contain sensitive data.

## 6. Severity thresholds (illustrative only)

| Engine | Metric | Unit | Warning | Critical |
|---|---|---|---:|---:|
| PostgreSQL | replication_lag | seconds | 30 | 120 |
| Elasticsearch | search_latency | milliseconds | 200 | 500 |
| Kafka | consumer_lag | messages | 1,000 | 10,000 |
| Redis | latency | milliseconds | 50 | 150 |

These are lab thresholds, not production SLOs.

## 7. Operational pitfalls

- `re.match` matches a prefix, not necessarily the full record.
- Greedy `.*` can swallow adjacent fields and create ambiguous captures.
- `\d` includes Unicode digits; use `[0-9]` when ASCII is required.
- Numeric syntax is not numeric validity: reject NaN, infinity and negative values.
- A timestamp pattern alone does not validate a calendar date.
- Redaction with regex is not a complete data-loss-prevention strategy.
- Even bounded regex can be expensive if repeated across large volumes; benchmark with representative fixtures.

## 8. Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| No matches | Format or whitespace drift | Compare source contract |
| Wrong field captured | Greedy pattern | Use named bounded captures |
| CPU spikes | Ambiguous backtracking | Bound input, simplify pattern |
| Invalid timestamp | Calendar/timezone issue | Parse with datetime |
| Unexpected severity | Unit or threshold mismatch | Validate metric contract |
| Malformed UTF-8 | Incorrect source encoding | Reject and fix producer |
| Sensitive data exposure | Logging raw rejected line | Report only line number and category |
| Silent drops | Skip-on-error behavior | Fail closed or explicitly quarantine |

## 9. Production runbooks

**Log format drift:** halt automated ingestion, identify source version, update parser contract and test sanitized old/new fixtures before replay.

**Parser CPU saturation:** disable expensive pattern, cap input, inspect regex complexity, move to structured logging when possible.

**Incorrect alert severity:** validate metric units, sample freshness and thresholds against approved SLOs; do not auto-remediate.

**Data-quality incident:** preserve sanitized line numbers, count rejected records, correct upstream export and replay through change control.

**Rollback:** pin known-good parser and schema, compare deterministic output and monitor ingestion error rates.

## 10. Hands-on lab

[Chapter 047 — Regex-Based Operational Log Parser and SRE/DBRE Lab](labs/047-regex-operational-log-parser-sre-dbre-lab.md) includes complete source code, synthetic fixtures, automated tests, CLI, failure injection, troubleshooting and runbooks.

**Next:** Chapter 048 — Python Dates, Times, Time Zones and Scheduling Fundamentals (provisional).
