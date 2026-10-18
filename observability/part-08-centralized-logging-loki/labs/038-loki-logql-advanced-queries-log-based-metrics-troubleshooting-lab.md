# Chapter 038 — Advanced LogQL and Log-Based Metrics Lab

**Part 08 — Centralized Logging with Loki**

## Prerequisites

Python 3.10+ for offline tests; optional Loki 3.x and Grafana for live queries. Use only synthetic data.

## Lab A — Offline query governance

Create the four complete files (`query_gate.py`, `healthy.json`, `degraded.json`, `test_query_gate.py`) from [Chapter 038](../038-loki-logql-advanced-queries-log-based-metrics-troubleshooting.md). Then run:

```bash
cd chapter038
python3 query_gate.py healthy.json
if python3 query_gate.py degraded.json; then exit 1; fi
python3 -m unittest -v test_query_gate.py
```

Expected: healthy PASS, degraded FAIL and 14 authored tests PASS.

## Lab B — Live LogQL exploration

Use the disposable Loki/Alloy pipeline from Chapter 036 or 037. Generate synthetic JSON records with level, message, service and timestamp; then evaluate:

```logql
{service="orders-api"} |= "timeout"
{service="orders-api"} | json | level="error"
sum by (service) (count_over_time({service="orders-api"}[5m]))
sum by (service) (rate({service="orders-api"}[5m]))
```

Record query duration, sample count, scanned time range and any parser errors. Compare log counts with independently instrumented request counters; do not assume log-derived metrics are complete.

## Twelve negative drills

1. Remove selector.
2. Select an absent namespace.
3. Choose an expired time range.
4. Introduce malformed JSON.
5. Ignore parser errors.
6. Use expensive broad regex.
7. Increase query range excessively.
8. Use request ID as index label.
9. Simulate Loki push failures.
10. Simulate collector drops.
11. Compare log rate against known request rate.
12. Restore the reviewed query and document rollback.

## SRE/DBRE incident

A PostgreSQL-backed API reports slow requests while Loki log-based error rates appear low. Verify data completeness, parser failures, ingestion and time skew; compare to Prometheus request counters and database signals. Explain discrepancies before declaring recovery.

## Evidence and assessment

```text
UTC / owner / environment:
Loki and Alloy versions:
Healthy/degraded gate / 14 tests:
LogQL selector / range / results:
Parser errors / query latency:
Independent metrics comparison:
12 drills / rollback / reviewer / score:
```

**Acceptance:** offline gate and unit tests pass; live LogQL, ingestion and alert behavior must be validated separately.
