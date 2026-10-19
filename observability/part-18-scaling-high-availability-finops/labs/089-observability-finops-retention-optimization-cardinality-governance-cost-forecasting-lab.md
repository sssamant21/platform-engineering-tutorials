# Chapter 089 — Observability FinOps, Retention and Cardinality Lab

## Offline gate

Copy `healthy.json`, `finops_gate.py` and `test_finops_gate.py` from [Chapter 089](../089-observability-finops-retention-optimization-cardinality-governance-cost-forecasting.md).

```bash
python3 finops_gate.py healthy.json
python3 -m unittest -v test_finops_gate.py
```

Expected PASS and 28 authored tests; record actual output.

## Staging exercises

1. Collect Prometheus active series, samples/sec and churn.
2. Collect Loki ingest bytes, streams, query rates and retention.
3. Collect Tempo spans/sec, sampling and object-store growth.
4. Map costs to bounded tenant/team ownership.
5. Build 30/90-day forecasts with growth, replication and failure headroom.
6. Simulate a high-cardinality instrumentation regression.
7. Test CI policy rejection and a reviewed rollback.
8. Test retention policy in staging without deleting production data.
9. Compare budget alerts and SLO visibility before and after optimization.
10. Record approval, cost estimates and corrective actions.

## Negative drills

Reject missing owner, unbounded labels, unexpected retention deletion, unapproved sampling, missing forecast and optimization that suppresses critical alerts.

## Evidence

Record UTC, owner, ingest baselines, retention, estimated unit costs, observed bill, forecast error, alert results, rollback and actual test output. Synthetic PASS is not billing validation.
