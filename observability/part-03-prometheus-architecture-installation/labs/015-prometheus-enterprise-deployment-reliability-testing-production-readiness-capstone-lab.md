# Chapter 015 — Prometheus Enterprise Production Readiness Capstone Lab

**Part 03 final capstone.** Offline Python 3.10+ synthetic acceptance with optional authorized read-only Prometheus API evidence.

## 1. Prepare runnable files

Copy all four complete fixture/code blocks from [Chapter 015](../015-prometheus-enterprise-deployment-reliability-testing-production-readiness-capstone.md) into:

```text
chapter015/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/readiness.py
  tests/test_readiness.py
```

## 2. Execute

```bash
cd chapter015
python3 scripts/readiness.py fixtures/healthy.json
if python3 scripts/readiness.py fixtures/degraded.json; then
  echo "FAIL: degraded readiness accepted"; exit 1
else
  echo "PASS: degraded readiness rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy exit 0, degraded exit 1 and 20 passing tests.

## 3. Twelve controlled failure drills

1. Reduce Prometheus replica count to one.
2. Put all replicas in one failure domain.
3. Reduce Alertmanager peers to one.
4. Lower scrape target coverage.
5. Remove an expected target.
6. Increase scrape p99 above timeout.
7. Exceed cardinality budget.
8. Increase TSDB disk use to 90%.
9. Increase remote-write lag beyond budget.
10. Degrade query availability.
11. Mark restore drill overdue.
12. Remove tested rollback evidence.

Run these only against local JSON fixtures. For each, record detection, blast radius, escalation, rollback and owner.

## 4. Optional read-only environment validation

```bash
curl -fsS 'http://127.0.0.1:9090/api/v1/targets'
curl -fsS 'http://127.0.0.1:9090/api/v1/rules'
curl -fsS 'http://127.0.0.1:9090/api/v1/status/tsdb'
```

A live staging review additionally requires query failover, target inventory reconciliation, end-to-end alert delivery, restore rehearsal, IAM review and a change-approved rollback test.

## 5. Incident tabletop

During a PostgreSQL failover, the Prometheus remote-write receiver is unavailable, the primary scraper's zone fails and Alertmanager notifications are delayed. Determine which telemetry survives, how to detect missing data, how to restore alerting, whether RPO/RTO are met, and which evidence is required before production signoff.

## 6. Evidence worksheet

```text
UTC / change ticket / environment / reviewer:
HA replica and zone evidence:
Target coverage and absence rules:
TSDB retention and headroom:
Remote-write lag and failure test:
Alertmanager routing and escalation:
Security / tenant isolation / IAM:
Restore drill and RPO/RTO:
Healthy/degraded fixture:
20 tests / 12 drills:
Rollback / go-no-go decision:
```

**Acceptance:** 20 tests pass, degraded fixture is rejected, failure drills and rollback documented, and all mandatory gates are reviewed. Live deployment readiness must be verified separately.
