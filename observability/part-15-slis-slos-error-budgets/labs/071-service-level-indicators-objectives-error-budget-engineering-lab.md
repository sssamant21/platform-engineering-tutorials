# Chapter 071 — Service Level Indicators, Objectives and Error Budgets Lab

**Part 15 — SLIs, SLOs and Error Budgets**

## Offline validation

Save `healthy.json`, `slo_gate.py` and `test_slo_gate.py` from [Chapter 071](../071-service-level-indicators-objectives-error-budget-engineering.md).

```bash
python3 slo_gate.py healthy.json
python3 -m unittest -v test_slo_gate.py
```

Expected PASS and 30 authored tests; capture actual output.

## Approved staging workflow

1. Identify service boundary, user journey, eligible requests and owner.
2. Define availability and latency good-event ratios.
3. Define Kafka/Snowflake freshness as a separate SLI.
4. Calculate allowed bad events, consumed budget and remaining budget.
5. Build Prometheus recording rules and Grafana dashboards.
6. Compare fast/slow burn rates and alert routing.
7. Validate low-traffic, missing metrics and counter-reset behavior.
8. Simulate a bounded bad-event spike in staging.
9. Apply documented change-risk decision and rollback.
10. Verify SLI recovery and publish budget review.

## Negative drills

Test missing review controls, unsafe environment, invalid request counts, impossible SLO percentages, SLO breaches and destructive changes.

## Evidence

```text
UTC / owner / change:
Eligible events and good/bad definitions:
Window and objective:
Availability/latency/freshness SLIs:
Allowed/consumed/remaining budget:
Fast and slow burn-rate windows:
Alert routing and service-owner policy:
Incident timeline and rollback:
Offline gate and 30 tests:
```

Synthetic SLO validation does not prove live alert correctness.
