# Chapter 083 — OpenTelemetry, Loki and Tempo Pipelines as Code Lab

## Offline gate

Copy `healthy.json`, `pipeline_gate.py` and `test_pipeline_gate.py` from [Chapter 083](../083-opentelemetry-loki-tempo-pipelines-as-code.md).

```bash
python3 pipeline_gate.py healthy.json
python3 -m unittest -v test_pipeline_gate.py
```

Expected PASS and 28 authored tests; capture actual output.

## Isolated staging game day

1. Create GitOps directories for collector, Loki, Tempo and environment overlays.
2. Pin versions and configure staging OTLP endpoints.
3. Validate collector config with its pinned distribution.
4. Add and verify log/trace attribute redaction before ingesting sensitive data.
5. Emit a synthetic span and log sharing a trace ID.
6. Confirm Tempo and Loki ingestion and Grafana cross-signal correlation.
7. Inject a bounded exporter outage and inspect queue/backpressure/drop metrics.
8. Restore backend connectivity and verify data recovery without assuming missing data can be replayed.
9. Run CI policy, secret scan and ownership checks.
10. Revert a reviewed staging change and repeat smoke tests.

## Negative drills

Reject missing redaction, unsafe environment, unreviewed changes, failed Loki ingestion, missing Tempo spans, excessive labels, bad TLS and missing rollback evidence.

## Evidence worksheet

```text
Change ID / owner / UTC:
Collector version and config validation:
Loki and Tempo endpoints:
Redaction and TLS:
Synthetic trace ID / log query:
Queue and drop metrics:
CI and GitOps reconciliation:
Rollback and recovery:
Offline gate and authored tests:
```

Synthetic gate PASS is not proof of live telemetry delivery.
