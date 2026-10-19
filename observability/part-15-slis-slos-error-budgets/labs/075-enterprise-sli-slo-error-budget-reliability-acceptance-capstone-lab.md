# Chapter 075 — Enterprise SLI/SLO and Error Budget Reliability Acceptance Lab

**Part 15 final capstone**

## Offline setup and validation

Copy `healthy.json`, `slo_acceptance_gate.py` and `test_slo_acceptance_gate.py` from [Chapter 075](../075-enterprise-sli-slo-error-budget-reliability-acceptance-capstone.md).

```bash
python3 slo_acceptance_gate.py healthy.json
python3 -m unittest -v test_slo_acceptance_gate.py
```

Expected PASS and 33 authored tests. Record actual results.

## Approved staging game day

1. Confirm owner, change ticket, incident commander and rollback plan.
2. Validate user-facing availability, latency and freshness SLI contracts.
3. Check Prometheus counter labels, histogram buckets and missing-data handling.
4. Calculate 30-day allowed, consumed and remaining error budget.
5. Verify 5m/1h and 30m/6h burn alerts and Alertmanager routing.
6. Inspect Grafana dashboards and release/incident annotations.
7. Simulate bounded API errors and separate Kafka/Snowflake freshness delay.
8. Correlate PostgreSQL, Redis and Elasticsearch dependency evidence.
9. Apply reviewed change policy and approved rollback.
10. Confirm independent SLI recovery and service-owner sign-off.

## Negative drills

Test missing controls, invalid event counts, impossible objectives, exhausted budget, latency failure, unsafe environment and destructive changes.

## Evidence worksheet

```text
UTC / owner / change:
SLI contracts / exclusions:
Availability, latency and freshness:
Allowed / consumed / remaining budget:
Fast and slow burn alerts:
Grafana / Prometheus / Alertmanager validation:
Customer impact / incident severity:
Change approval / exception / rollback:
Recovery SLI and service-owner sign-off:
Offline gate and 33 tests:
```

The offline gate does not substitute for witnessed staging acceptance.
