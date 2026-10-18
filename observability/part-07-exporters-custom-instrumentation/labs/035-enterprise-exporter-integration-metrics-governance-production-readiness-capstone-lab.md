# Chapter 035 — Enterprise Exporter Integration and Production Readiness Capstone Lab

**Part 07 final capstone.** Offline Python acceptance and optional authorized staging exporter fleet game day.

## 1. Project layout

Copy the four complete fixture/Python blocks from [Chapter 035](../035-enterprise-exporter-integration-metrics-governance-production-readiness-capstone.md) into:

```text
chapter035/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

## 2. Offline acceptance

```bash
cd chapter035
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected healthy PASS, degraded FAIL and 29 tests PASS.

## 3. Twelve negative drills

1. Missing exporter.
2. Duplicate exporter name.
3. Missing exporter owner.
4. Exporter scrape failure.
5. Missing target.
6. Negative series count.
7. Fleet series budget exceeded.
8. Unsafe scrape timeout.
9. Missing security review.
10. Missing notification receipt.
11. Missing rollback test.
12. Missing incident drill evidence.

## 4. Optional staging game day

Integrate Node Exporter, postgres_exporter, Blackbox Exporter and a Python custom exporter using the standalone labs in Chapters 031–034. Validate target inventory, service SLIs, safe alert routing, bounded labels and incident recovery. Simulate PostgreSQL failover and custom exporter cardinality explosion **only in approved staging**.

## 5. Evidence and 100-point score

```text
UTC / operator / change ID:
Exporter versions / owners / targets:
Prometheus up / pg_up / probe_success:
Active series / retention / cardinality:
Healthy/degraded gate / 29 tests:
12 negative drills:
Staging incident / notification / rollback:
Reviewer / score / follow-up actions:
```

**Acceptance:** offline gate and tests pass; actual production readiness requires separately witnessed integration, alert delivery, security review and DR evidence.
