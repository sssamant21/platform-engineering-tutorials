# Chapter 066 — Application Performance Monitoring Architecture Lab

**Part 14 — Application Performance Monitoring**

## Offline acceptance

Save `healthy.json`, `apm_gate.py` and `test_apm_gate.py` from [Chapter 066](../066-application-performance-monitoring-architecture-instrumentation-golden-signals.md).

```bash
python3 apm_gate.py healthy.json
python3 -m unittest -v test_apm_gate.py
```

Expected PASS and 28 authored tests; capture actual output.

## Approved staging workflow

1. Record service map, dependencies, owner and change ID.
2. Instrument incoming HTTP server RED metrics with bounded route templates.
3. Instrument outgoing PostgreSQL, Redis, Kafka and HTTP dependency spans.
4. Verify W3C trace context propagation and log/trace correlation.
5. Export to a staging OTel Collector and inspect exporter health.
6. Build p95/p99 latency, error rate and throughput dashboards.
7. Define independent user-facing SLIs and multi-window burn alerts.
8. Simulate bounded staging latency and a downstream timeout.
9. Review sampling, cardinality, privacy and Collector drops.
10. Roll back the change and verify application SLO recovery.

## Negative drills

Test missing instrumentation reviews, missing owner, production environment, invalid request counts, error-rate breach, p95 latency breach, dropped spans breach and destructive-action rejection.

## Evidence

```text
UTC / owner / change:
Service and dependency map:
RED metrics and histogram buckets:
Trace ID and span dependency evidence:
Structured log correlation:
Collector drops and queue:
Cardinality and sensitive-data review:
SLO alert firing/clearance:
Mitigation, rollback and postmortem:
Offline gate and 28 tests:
```

Offline review is not live APM validation.
