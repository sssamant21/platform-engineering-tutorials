# Chapter 054 — Distributed Trace Analysis, Service Graphs and Metrics Correlation Lab

**Part 11 — Distributed Tracing with Jaeger and Tempo.**

## Offline acceptance

Copy `healthy.json`, `correlation_gate.py`, and `test_correlation_gate.py` from [Chapter 054](../054-distributed-trace-analysis-service-dependencies-sampling-metrics-correlation.md).

```bash
cd chapter054
python3 correlation_gate.py healthy.json
python3 -m unittest -v test_correlation_gate.py
```

Expected PASS and 26 authored tests.

## Staging integration

1. Emit synthetic HTTP, PostgreSQL, Redis and Kafka spans.
2. Propagate W3C traceparent across service and worker boundaries.
3. Query a trace by ID in Jaeger or Tempo.
4. Reconstruct span tree and critical path.
5. Run TraceQL filters for error and slow traces.
6. Correlate a synthetic log with trace_id and span_id.
7. Compare span-derived RED rates with independent counters.
8. Validate service graph client/server pairing.
9. Introduce missing spans and observe sampling bias.
10. Restore instrumentation and confirm SLI continuity.

## Twelve negative drills

1. Invalid trace ID.
2. Invalid span ID.
3. Trace context unverified.
4. Service graph unverified.
5. Span metrics unverified.
6. Log correlation absent.
7. Sampling bias review absent.
8. Cardinality review absent.
9. PII review absent.
10. Errors exceed requests.
11. Error-rate arithmetic mismatch.
12. Latency budget exceeded.

## Evidence

```text
UTC / operator / backend versions:
Trace ID / span tree / critical path:
Service graph edges:
TraceQL / Jaeger queries:
Logs correlation:
Independent SLI counters / histogram:
Sampling bias / privacy:
Offline gate / 26 tests:
Rollback / reviewer:
```

Offline checks cannot prove runtime trace or metric accuracy.
