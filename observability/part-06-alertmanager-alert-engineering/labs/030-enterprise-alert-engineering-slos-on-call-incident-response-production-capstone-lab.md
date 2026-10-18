# Chapter 030 — Enterprise Alert Engineering Production Capstone Lab

**Part 06 final capstone.** Python 3.10+ offline acceptance; optional approved staging Prometheus/Alertmanager/on-call drill.

## 1. Project layout

Copy all four complete JSON/Python blocks from [Chapter 030](../030-enterprise-alert-engineering-slos-on-call-incident-response-production-capstone.md) into:

```text
chapter030/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/capstone_gate.py
  tests/test_capstone_gate.py
```

## 2. Run

```bash
cd chapter030
python3 scripts/capstone_gate.py fixtures/healthy.json
if python3 scripts/capstone_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 30 tests PASS.

## 3. Twelve negative drills

1. Missing SLO owner.
2. SLO target 100%.
3. Missing runbook.
4. High-cardinality request ID label.
5. Invalid fast-burn windows.
6. No backup escalation.
7. Untested notification route.
8. Missing synthetic page receipt.
9. Missing low-traffic test.
10. Missing no-data test.
11. Weekly noise budget exceeded.
12. Acknowledgement SLO missed.

## 4. Optional staging drills

- Validate Prometheus rules using `promtool check rules`.
- Validate Alertmanager config using `amtool check-config`.
- Simulate a service error-budget burn and disappearing scrape target.
- Confirm test-only primary and fallback notification routing.
- Exercise narrow silences, inhibition, peer failure and receiver 429.
- Verify rollback and recovery notification.
- Record incident commander, DBRE owner, acknowledgements and review.

## 5. 100-point scoring

SLO/alert quality 20; routing/HA/security 20; delivery/escalation 20; offline tests 20; incident/DR/rollback 20. Recommended pass 85; safety gates mandatory.

## 6. Evidence

```text
UTC / operator / environment:
SLO / PromQL rule / promtool:
Routing / amtool / receiver:
Healthy/degraded gate / 30 tests:
12 negative drills:
Optional staging failure and rollback:
Incident timeline / reviewer / score:
```

**Acceptance:** 30 offline tests pass and degraded manifest fails; production deployment and end-to-end paging require independent operational verification.
