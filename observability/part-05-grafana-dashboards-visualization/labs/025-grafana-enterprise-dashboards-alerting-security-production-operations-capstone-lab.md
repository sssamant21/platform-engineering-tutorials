# Chapter 025 — Grafana Enterprise Production Operations Capstone Lab

**Part 05 final capstone.** Python 3.10+ offline acceptance plus optional authorized staging Grafana/Prometheus/Alertmanager.

## 1. Project layout

Copy all four complete fixture and Python blocks from [Chapter 025](../025-grafana-enterprise-dashboards-alerting-security-production-operations-capstone.md) into:

```text
chapter025/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

## 2. Execute

```bash
cd chapter025
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then
  echo "FAIL: unsafe capstone accepted"; exit 1
else
  echo "PASS: unsafe capstone rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 26 tests PASS.

## 3. Twelve negative drills

1. Metadata database HA review missing.
2. Backup/restore test missing.
3. Rollback evidence missing.
4. Secret scan failed.
5. RBAC review failed.
6. Datasource tenant isolation failed.
7. Alert delivery untested.
8. Missing-data policy untested.
9. Dashboard UID duplicated.
10. Refresh interval too short.
11. Query cost above budget.
12. Notification route untested.

Modify local fixtures only and capture expected/actual gate findings.

## 4. Optional staging validation

Verify Grafana HA health, datasource isolation, dashboard provisioning, query performance, alert evaluation, test receiver delivery, backup restoration and rollback. Use approved test receivers; do not send synthetic pages to real production on-call.

## 5. DBRE incident tabletop

A PostgreSQL failover, stale dashboard variable, misrouted alert and Prometheus query overload occur together. Restore trustworthy observability and alert delivery, distinguish real database impact from telemetry failure, and roll back the unsafe change.

## 6. Evidence and acceptance

```text
UTC / operator / environment:
Grafana version / HA and backup evidence:
Dashboard/datasource/alert owners:
Healthy/degraded gate / 26 tests:
12 negative drills:
Optional staging restore and paging:
RCA / rollback / reviewer / 100-point score:
```

**Acceptance:** offline 26 tests pass, degraded fixture rejected and safety gates documented. Live production readiness is separately assessed.
