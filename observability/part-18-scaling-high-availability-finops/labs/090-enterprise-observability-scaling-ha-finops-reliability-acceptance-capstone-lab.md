# Chapter 090 — Scaling, HA and FinOps Reliability Acceptance Lab

Follow [Chapter 090](../090-enterprise-observability-scaling-ha-finops-reliability-acceptance-capstone.md) for the complete reference architecture, offline Python files, 24 exercises, 24 incidents, eight runbooks and 100-point rubric.

## Offline acceptance

Save `healthy.json`, `acceptance_gate.py` and `test_acceptance_gate.py` from the chapter.

```bash
python3 acceptance_gate.py healthy.json
python3 -m unittest -v test_acceptance_gate.py
```

Expected PASS and 31 authored tests; record actual results.

## Staging game day

1. Inventory Prometheus, Alertmanager, Loki, Tempo, OTel and Grafana topology.
2. Capture ingest, series, query p95, queue, WAL and storage baselines.
3. Verify HA external labels, Alertmanager dedup and test paging.
4. Inject bounded remote-write outage and verify replay.
5. Inject Loki and Tempo ingestion disruption and verify signal recovery.
6. Simulate one-zone failure with N-1 capacity.
7. Evaluate tenant isolation, sensitive data, retention and sampling.
8. Forecast 30/90-day storage, compute and egress cost.
9. Revert a reviewed change and verify SLO continuity.
10. Score the 100-point rubric and obtain sign-off.

## Evidence worksheet

```text
UTC / owner / change ID:
Prometheus series, WAL, remote-write lag:
Alertmanager peer and paging evidence:
Loki/Tempo trace and log query IDs:
AZ fault injection / SLO / RPO / RTO:
Retention / tenant / security checks:
Cost forecast / variance:
Rollback / recovery:
Offline gate and actual tests:
Score and approvers:
```

A synthetic PASS does not certify production readiness.
