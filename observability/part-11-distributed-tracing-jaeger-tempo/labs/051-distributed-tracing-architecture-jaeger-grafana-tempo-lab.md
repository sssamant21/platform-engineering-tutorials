# Chapter 051 — Distributed Tracing Architecture with Jaeger and Tempo Lab

**Part 11 — Distributed Tracing with Jaeger and Tempo.**

## Offline architecture gate

Copy `healthy.json`, `tracing_gate.py`, and `test_tracing_gate.py` from [Chapter 051](../051-distributed-tracing-architecture-jaeger-grafana-tempo.md).

```bash
cd chapter051
python3 tracing_gate.py healthy.json
python3 -m unittest -v test_tracing_gate.py
```

Expected PASS and 24 authored tests.

## Optional staging integration

1. Select Jaeger or Tempo and pin its version.
2. Record OTLP HTTP/gRPC endpoints and auth.
3. Deploy a local or approved staging tracing backend.
4. Send synthetic spans using the chapter's OTLP payload.
5. Search by trace ID in the backend UI and confirm persistence.
6. Add HTTP and PostgreSQL child spans.
7. Correlate a synthetic log with the same trace ID.
8. Review retention, storage, access isolation and cost.
9. Simulate a backend outage and observe Collector retries.
10. Restore healthy configuration and verify trace retrieval.

## Twelve negative drills

1. Missing trace propagation.
2. Invalid trace ID.
3. Invalid span ID.
4. No query path review.
5. No object storage review.
6. Missing tenant isolation.
7. Missing privacy review.
8. Sampling review absent.
9. Trace latency budget exceeded.
10. Backend ingestion outage.
11. Restore untested.
12. Rollback untested.

## Evidence

```text
UTC / operator / backend/version:
Trace ID / span tree / propagation:
OTLP ingestion / query retrieval:
Storage / retention / tenant isolation:
Privacy / independent SLI:
Offline gate / 24 tests:
Negative drills / rollback / reviewer:
```

Offline design checks do not verify actual backend storage or trace retrieval.
