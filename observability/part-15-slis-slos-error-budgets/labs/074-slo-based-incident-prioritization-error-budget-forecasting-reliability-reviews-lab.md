# Chapter 074 — SLO Incident Prioritization and Error Budget Forecasting Lab

**Part 15 — SLIs, SLOs and Error Budgets**

## Offline validation

Save `healthy.json`, `incident_forecast_gate.py` and `test_incident_forecast_gate.py` from [Chapter 074](../074-slo-based-incident-prioritization-error-budget-forecasting-reliability-reviews.md).

```bash
python3 incident_forecast_gate.py healthy.json
python3 -m unittest -v test_incident_forecast_gate.py
```

Expected PASS and 32 authored tests; capture actual results.

## Approved staging workflow

1. Confirm user-facing SLI ownership and eligible events.
2. Compute allowed failures, budget consumed and remaining.
3. Validate 5m/1h and 30m/6h burn windows.
4. Classify incident severity using independent customer impact.
5. Review PostgreSQL, Redis, Kafka and Snowflake dependency signals.
6. Compare recent burn against longer-term trends.
7. Estimate forecast scenarios using measured future request-rate assumptions.
8. Record uncertainty and rolling-window expiration effects.
9. Rehearse a bounded incident and safe rollback.
10. Publish a reliability review with corrective owners and dates.

## Negative drills

Exercise missing SLO ownership, invalid event counts, exhausted budget, invalid recent error fractions, unsafe environment and unapproved changes.

## Evidence worksheet

```text
UTC / owner / change:
SLI numerator and denominator:
Objective and rolling window:
Budget allowed / consumed / remaining:
5m/1h and 30m/6h burn:
Incident severity and customer impact:
Traffic assumptions and forecast uncertainty:
Reliability action owner / deadline:
Rollback and SLI recovery:
Offline gate and 32 tests:
```

Synthetic forecast validation is not a live reliability forecast.
