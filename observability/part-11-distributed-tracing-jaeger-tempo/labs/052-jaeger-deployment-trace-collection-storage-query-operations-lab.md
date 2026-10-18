# Chapter 052 — Jaeger Deployment, Trace Collection, Storage and Query Lab

**Part 11 — Distributed Tracing with Jaeger and Tempo.**

## Offline acceptance

Copy `healthy.json`, `jaeger_gate.py` and `test_jaeger_gate.py` from [Chapter 052](../052-jaeger-deployment-trace-collection-storage-query-operations.md).

```bash
cd chapter052
python3 jaeger_gate.py healthy.json
python3 -m unittest -v test_jaeger_gate.py
```

Expected PASS and 25 authored Python tests.

## Local Jaeger v2 integration

1. Pin a vetted Jaeger v2 image and check supported quick-start options.
2. Start Jaeger with loopback-bound ports.
3. Send the synthetic OTLP HTTP span from the chapter.
4. Verify receiver acceptance and query the exact trace ID in the UI.
5. Add parent and PostgreSQL client child spans.
6. Restart the ephemeral lab and document trace loss.
7. Switch to a supported persistent storage backend in staging.
8. Test query latency, authentication/TLS and PII redaction.
9. Simulate a storage outage and verify recovery.
10. Restore pinned image/config and confirm trace retrieval.

## Twelve negative drills

1. Wrong Jaeger major version.
2. Missing OTLP receiver.
3. Wrong query port.
4. Export success below budget.
5. Query latency over budget.
6. Storage persistence untested.
7. Retention review absent.
8. Authentication unreviewed.
9. TLS unreviewed.
10. Privacy review absent.
11. Backup/restore untested.
12. Rollback untested.

## Evidence checklist

```text
UTC / operator / image version:
OTLP accepted / trace ID:
Query result and latency:
Storage backend and retention:
TLS/auth / privacy:
Restore / rollback:
Offline gate / 25 tests:
Reviewer / change ID:
```

Offline checks cannot establish real backend readiness.
