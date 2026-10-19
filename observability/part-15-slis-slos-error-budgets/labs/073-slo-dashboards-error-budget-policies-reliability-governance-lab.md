# Chapter 073 — SLO Dashboards and Reliability Governance Lab

**Part 15 — SLIs, SLOs and Error Budgets**

## Offline validation

Save `healthy.json`, `governance_gate.py` and `test_governance_gate.py` from [Chapter 073](../073-slo-dashboards-error-budget-policies-reliability-governance.md).

```bash
python3 governance_gate.py healthy.json
python3 -m unittest -v test_governance_gate.py
```

Expected PASS and 31 authored tests; capture actual output.

## Staging workflow

1. Identify user journey, SLI owner and eligible events.
2. Confirm rolling 30-day objective and budget arithmetic.
3. Build Grafana availability, latency and budget panels.
4. Add fast/slow burn, incident and deployment annotations.
5. Validate no-data, low-traffic and scrape-failure behavior.
6. Check dashboard permissions and customer isolation.
7. Review release-risk policy and exception approval.
8. Simulate budget burn and an unsafe rollout request.
9. Rehearse approved rollback and SLI recovery.
10. Publish service-owner review and audit evidence.

## Negative drills

Exercise missing review controls, invalid SLO counts, exhausted budget, unsupported policy values, unexpected exceptions and unsafe actions.

## Evidence worksheet

```text
UTC / owner / change:
SLI numerator and denominator:
Rolling window / objective:
Allowed, consumed and remaining budget:
Dashboard data freshness and access:
Fast/slow burn and alert routing:
Release decision / exception approver:
Rollback and SLI recovery:
Offline gate and 31 tests:
```

Synthetic governance validation does not prove live approval or dashboard correctness.
