# Chapter 086 — Observability Scale, Capacity and HA Lab

## Offline gate

Copy `healthy.json`, `capacity_gate.py` and `test_capacity_gate.py` from [Chapter 086](../086-enterprise-observability-scale-capacity-planning-high-availability-architecture.md).

```bash
python3 capacity_gate.py healthy.json
python3 -m unittest -v test_capacity_gate.py
```

Expected PASS and 30 authored tests. Capture actual output.

## Staging capacity game day

1. Measure active series, samples/sec, WAL growth and query latency.
2. Estimate log bytes/day, span bytes/day and storage retention.
3. Model 30/90/180-day growth and burst factors.
4. Plan Prometheus replicas and external labels.
5. Inspect remote-write queues, retry rates and deduplication.
6. Review Loki/Tempo ingestion limits and tenant budgets.
7. Simulate bounded one-AZ capacity loss in isolated staging.
8. Validate alerting, queryability, backlog recovery and RPO/RTO.
9. Identify highest-cardinality labels and estimate remediation savings.
10. Produce a cost and capacity sign-off report.

## Negative drills

Reject missing growth forecasts, insufficient N-1 capacity, unverified backup recovery, duplicate HA paging and unsafe retention assumptions.

## Evidence worksheet

```text
Owner / UTC / change:
Series / samples/sec / bytes/day:
Logs and traces / retention:
N-1 headroom / AZ layout:
Prometheus remote write:
Loki and Tempo:
SLO / query latency / alert delivery:
Failure injection / RPO / RTO:
Forecast / FinOps / sign-off:
Offline gate and tests:
```

Synthetic acceptance is not a substitute for measured workload tests.
