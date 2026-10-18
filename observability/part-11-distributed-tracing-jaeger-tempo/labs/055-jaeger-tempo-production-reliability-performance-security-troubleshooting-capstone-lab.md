# Chapter 055 — Jaeger and Tempo Enterprise Reliability Capstone Lab

**Part 11 final capstone — Distributed Tracing with Jaeger and Tempo.**

## Offline acceptance

Copy `healthy.json`, `tracing_capstone_gate.py` and `test_tracing_capstone_gate.py` from [Chapter 055](../055-jaeger-tempo-production-reliability-performance-security-troubleshooting-capstone.md).

```bash
cd chapter055
python3 tracing_capstone_gate.py healthy.json
python3 -m unittest -v test_tracing_capstone_gate.py
```

Expected PASS and 28 authored tests.

## Staging game day

1. Pin Jaeger, Tempo and Collector versions.
2. Generate synthetic HTTP, PostgreSQL and Kafka traces.
3. Verify both backend query paths and known trace IDs.
4. Test parent-child propagation and tail-sampling affinity.
5. Simulate exporter 429 and observe queue/retry behavior.
6. Simulate Tempo object storage throttling.
7. Restart an ephemeral Jaeger lab and document lost traces.
8. Recover approved persistent storage and query traces again.
9. Measure ingest success, query p95 and completeness.
10. Verify independent request metrics, tenant isolation and privacy.
11. Restore known-good versions/config and measure RPO/RTO.
12. Score the 100-point capstone and attach reviewer evidence.

## Twelve negative drills

1. Collector version unpinned.
2. Jaeger version unpinned.
3. Tempo version unpinned.
4. Trace query unverified.
5. Storage persistence unverified.
6. Trace affinity unverified.
7. Ingest success below threshold.
8. Query p95 over budget.
9. Trace completeness below threshold.
10. Tenant isolation unverified.
11. Restore untested.
12. Rollback untested.

## Evidence

```text
UTC / operator / change:
Jaeger and Tempo trace IDs:
Collector queue / refusals / export errors:
Query latency / completeness:
Object store / restore / RPO-RTO:
Security / privacy / independent SLIs:
Offline gate / 28 tests:
Final score / reviewer / rollback:
```

Offline checks alone cannot establish production readiness.
