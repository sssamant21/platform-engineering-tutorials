# Chapter 024 — Grafana Alerting and Incident Workflows Lab

**Part 05 — Grafana Dashboards and Visualization.** Offline Python 3.10+ policy testing; optional Grafana staging alert drills.

## 1. Project files

Copy the four complete fixture/source blocks from [Chapter 024](../024-grafana-alerting-contact-points-notification-policies-sre-incident-workflows.md) into:

```text
chapter024/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/alert_gate.py
  tests/test_alert_gate.py
```

## 2. Execute

```bash
cd chapter024
python3 scripts/alert_gate.py fixtures/healthy.json
if python3 scripts/alert_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe alert policy accepted"; exit 1
else
  echo "PASS: unsafe alert policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 24 tests PASS.

## 3. Twelve failure drills

1. Missing service owner.
2. Missing cluster label.
3. Unknown severity.
4. Evaluation interval too aggressive.
5. Invalid pending period.
6. Wrong datasource UID.
7. Empty alert expression.
8. Contact point untested.
9. Inline secret instead of external reference.
10. Receiver mismatch.
11. Missing cluster/service grouping.
12. Missing rollback approval.

Use local JSON fixture copies; no production alerts are changed.

## 4. Optional staging drill

Create an authorized test Grafana-managed alert with a **test webhook/contact point**. Verify Normal → Pending → Alerting → Recovering transitions, No Data and Error handling, route selection, grouping, contact delivery and recovery notification. Record Grafana version and screenshots/API results. Restore the original rule afterward.

## 5. DBRE tabletop

A PostgreSQL scrape target vanishes from service discovery while an alert only checks `up == 0`. The dashboard appears empty and no page arrives. Diagnose missing inventory coverage, Grafana No Data policy, notification route and responder ownership. Design a corrective alert and safe rollout.

## 6. Evidence

```text
UTC / operator / environment:
Rule evaluator and query:
No Data/Error state policy:
Contact point / route / secret source:
Healthy/degraded gate / 24 tests:
12 drills / optional page test:
Rollback / incident owner / reviewer:
```

**Acceptance:** offline policy gate and 24 tests pass, degraded fixture rejected, and paging reliability is treated as a separate live integration requirement.
