# Chapter 067 — Application Distributed Tracing and Service Maps Lab

**Part 14 — Application Performance Monitoring**

## Offline acceptance

Save `healthy.json`, `tracing_gate.py` and `test_tracing_gate.py` from [Chapter 067](../067-application-distributed-tracing-service-maps-dependency-performance-analysis.md).

```bash
python3 tracing_gate.py healthy.json
python3 -m unittest -v test_tracing_gate.py
```

Expected PASS and 29 authored tests; capture actual results.

## Approved staging workflow

1. Record service dependencies, instrumentation owners and change ID.
2. Generate a synthetic HTTP request and inspect parent-child spans.
3. Verify W3C traceparent propagation through outbound HTTP.
4. Propagate context through Kafka headers and inspect async links.
5. Inspect PostgreSQL and Redis dependency spans with sanitized attributes.
6. Query Tempo or Jaeger and build a service map.
7. Compare critical path with application RED latency histograms.
8. Test head/tail sampling, Collector queues and backend ingestion.
9. Simulate missing propagation and a bounded slow dependency.
10. Roll back instrumentation and verify trace continuity and SLO recovery.

## Negative drills

Exercise each of 18 missing tracing/security controls, missing owner/change, unsafe environment, low trace coverage, orphan spans, dependency p95 breach, dropped span breach and destructive-change rejection.

## Evidence worksheet

```text
UTC / owner / change:
Trace ID and service map:
W3C propagation:
DB/Redis/Kafka span evidence:
Critical path and p95:
Sampling/Collector drops:
Sensitive-attribute review:
Incident SLO and rollback:
Offline gate and 29 tests:
```

Offline attestation does not establish live trace quality.
