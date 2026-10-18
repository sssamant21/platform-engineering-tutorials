# Chapter 040 — Loki Production Reliability and Enterprise Logging Capstone Lab

**Part 08 final capstone.** Complete offline acceptance plus authorized staging reliability exercises.

## 1. Files

Copy the complete `healthy.json`, `acceptance.py` and `test_acceptance.py` blocks from [Chapter 040](../040-loki-production-reliability-security-troubleshooting-logging-capstone.md) into a `chapter040/` folder.

## 2. Run the offline acceptance

```bash
cd chapter040
python3 acceptance.py healthy.json
python3 -m unittest -v test_acceptance.py
```

Expected: PASS and 26 authored tests PASS.

## 3. Twelve negative drills

1. Missing tenant owner.
2. Missing Kubernetes source.
3. Unsafe request-ID label.
4. Retention not approved.
5. Tenant isolation not reviewed.
6. Redaction not tested.
7. Ingestion SLO unreviewed.
8. Query SLO unreviewed.
9. Alert delivery untested.
10. Independent monitoring missing.
11. Stream budget exceeded.
12. Restore not tested.

## 4. Optional approved staging game day

Integrate the Loki/Alloy pipeline from Chapters 036–039. Simulate node log loss, 429 ingestion throttling, missing ruler notifications and compactor failures using **synthetic data**. Recover reviewed configurations and restore from a disposable backup. Never run destructive retention tests on production data.

## 5. Evidence and scoring

```text
UTC / operator / change ID:
Loki and Alloy versions / tenant:
Sources / labels / ingestion:
Ruler and Alertmanager delivery:
Retention and compactor:
Offline gate / 26 tests:
12 negative drills / recovery / rollback:
Reviewer / score / action items:
```

**Acceptance:** offline gate passes and staging evidence demonstrates collection, privacy controls, retention, alert delivery and restore. Offline tests alone do not prove production readiness.
