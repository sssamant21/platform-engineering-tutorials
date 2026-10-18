# Chapter 020 — PromQL Production Query Engineering and SLO Capstone Lab

**Part 04 final capstone.** Offline Python 3.10+ with optional approved Prometheus/Alertmanager staging integration.

## 1. Prepare

Copy the four complete fixture/source blocks from [Chapter 020](../020-promql-production-query-engineering-slo-alerting-performance-capstone.md) into:

```text
chapter020/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

## 2. Execute acceptance

```bash
cd chapter020
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then
  echo "FAIL: unsafe SLO policy accepted"; exit 1
else
  echo "PASS: unsafe SLO policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 24 passing tests.

## 3. Twelve synthetic failure drills

1. Error budget exceeded.
2. Fast and slow burn thresholds both crossed.
3. Fast burn only, with slow burn below threshold.
4. Slow burn only, with fast burn below threshold.
5. Query p95 above budget.
6. Series cardinality above budget.
7. Rule evaluation slower than interval.
8. Missing expected scrape targets.
9. Cluster isolation lost.
10. Tenant isolation lost.
11. Alert route untested.
12. Rollback or restore evidence missing.

Change local JSON only. Record detection, incident impact, owner, remediation and rollback.

## 4. Optional live integration

On approved staging Prometheus, run `promtool check rules`, `promtool test rules`, inspect `/api/v1/rules`, validate query outputs, alert route delivery and rollback. The YAML in the chapter is a single-window illustration; implement a separate fast+slow multi-window alert before claiming complete SLO paging coverage.

## 5. Incident tabletop

A PostgreSQL failover causes a scrape gap and query latency spike; a new recording rule drops `cluster`, while an expensive subquery overloads Prometheus. Determine whether SLO errors are real, missing, or misaggregated; protect tenant isolation; restore alerting; roll back the rule and preserve audit evidence.

## 6. Evidence

```text
UTC / operator / environment:
SLI/SLO/error budget:
Query and recording rule review:
Fast/slow burn policy:
Target coverage / alert route:
24 tests / 12 drills:
Restore / rollback:
Go-no-go reviewer:
```

**Acceptance:** all 24 tests pass, degraded fixture is rejected, safety gates are documented, and live acceptance is explicitly separate.
