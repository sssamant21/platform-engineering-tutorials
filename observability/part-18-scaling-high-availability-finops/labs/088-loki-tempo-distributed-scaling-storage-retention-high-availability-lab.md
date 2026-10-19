# Chapter 088 — Loki and Tempo Scaling, Storage, Retention and HA Lab

## Offline gate

Copy `healthy.json`, `storage_gate.py` and `test_storage_gate.py` from [Chapter 088](../088-loki-tempo-distributed-scaling-storage-retention-high-availability.md).

```bash
python3 storage_gate.py healthy.json
python3 -m unittest -v test_storage_gate.py
```

Expected PASS and 30 authored tests; capture actual output.

## Staging lab

1. Baseline Loki bytes/sec, active streams, ingestion errors and query latency.
2. Baseline Tempo spans/sec, trace lookup success and compaction backlog.
3. Review object-store IAM, TLS, retention and tenant limits.
4. Inspect ingester/distributor/query component replicas across AZs.
5. Emit synthetic log and trace with a common trace ID.
6. Simulate a bounded Loki ingester failure; verify log query continuity.
7. Simulate Tempo ingester or collector exporter failure; verify retry/drop metrics.
8. Test object-store transient failure and recovery without destructive retention changes.
9. Estimate storage, compute, retention and cross-region egress costs.
10. Document GitOps rollback and independent Grafana query verification.

## Negative drills

Reject missing tenant isolation, unbounded labels, unexpected retention deletion, absent trace correlation and insufficient AZ headroom.

## Evidence

Record UTC, owner, tenant, ingest rates, storage bytes, retention, trace ID, error rates, failover timing, cost forecast, rollback and actual test output.

Synthetic PASS is not live HA certification.
