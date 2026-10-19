# Chapter 072 — Advanced SLO and Multiwindow Burn-Rate Alerting Lab

## Prerequisites

Read [Chapter 072](../072-advanced-slo-design-multiwindow-burn-rate-alerting-prometheus-recording-rules.md). Use an isolated staging Prometheus, synthetic traffic and an approved change ID.

## Local exercises

1. Copy `healthy.json`, `burn_gate.py` and `test_burn_gate.py` from Chapter 072 into one directory.
2. Run `python3 burn_gate.py healthy.json` and capture the error-budget calculations.
3. Run `python3 -m unittest -v test_burn_gate.py` and retain the results.
4. Review the 30-day SLO's eligible good and total events.
5. Validate the recording rules with `promtool check rules slo-rules.yaml`.
6. Compare 5m/1h and 30m/6h burn-rate windows.
7. Test a sustained synthetic error burst in staging.
8. Check missing-series and low-traffic behavior.
9. Validate Alertmanager notification routing in a test receiver.
10. Restore baseline and record recovery evidence.

## Acceptance checklist

- Confirm SLI ownership, request eligibility, objective and rolling window.
- Verify each paired burn-rate window independently.
- Record rule validation and notification test results.
- Document budget remaining, rollback and follow-up owner.
- Do not interpret synthetic manifest success as live production validation.

## Evidence worksheet

```text
Owner / change / UTC:
SLO objective and window:
Eligible total and bad events:
Allowed / consumed / remaining budget:
5m and 1h burn:
30m and 6h burn:
Rule validation:
Alert routing:
Recovery and rollback:
Python test results:
```

## Assessment

Score 20 points each for SLI design, burn-rate calculations, recording rules, operational safeguards and incident recovery. Passing recommendation: 85/100.
