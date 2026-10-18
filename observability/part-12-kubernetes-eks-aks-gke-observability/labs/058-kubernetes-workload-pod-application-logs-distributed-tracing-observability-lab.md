# Chapter 058 — Kubernetes Workload, Pod, Logs and Tracing Lab

**Part 12 — EKS, AKS and GKE Observability**

## Offline acceptance

Copy `healthy.json`, `workload_gate.py` and `test_workload_gate.py` from [Chapter 058](../058-kubernetes-workload-pod-application-logs-distributed-tracing-observability.md).

```bash
cd chapter058
python3 workload_gate.py healthy.json
python3 -m unittest -v test_workload_gate.py
```

Expected PASS and 29 authored tests.

## Staging integration

1. Select approved namespace and inspect workloads, pods and events.
2. Collect synthetic structured JSON logs.
3. Verify log delivery to Loki with correct low-cardinality labels.
4. Propagate W3C trace context across HTTP and Kafka.
5. Query a synthetic trace in Tempo or Jaeger.
6. Correlate trace_id with Loki log fields and independent RED metrics.
7. Simulate log-agent outage and Collector exporter backpressure.
8. Review RBAC, network policies, sampling, retention and redaction.
9. Recover pipelines and verify log/trace retrieval.
10. Record rollback and reviewer evidence.

## Twelve negative drills

1. Missing owner.
2. Unsupported cloud.
3. Invalid trace ID.
4. Loki pipeline unreviewed.
5. Collector unreviewed.
6. Log delivery below threshold.
7. Trace query latency over budget.
8. Trace context unverified.
9. RBAC unreviewed.
10. PII redaction unreviewed.
11. Alert routing unreviewed.
12. Rollback untested.

## Evidence worksheet

```text
UTC / cluster / namespace / operator:
Pod status / restarts / events:
LogQL result / delivery lag:
Trace ID / TraceQL result:
RED metrics / impact:
RBAC / privacy / cardinality:
Failure drill / recovery / rollback:
Offline gate / 29 tests:
```

Offline checks cannot prove live workload visibility.
