# Chapter 050 — OpenTelemetry Enterprise Instrumentation and Incident Response Capstone Lab

**Part 10 final capstone.** Synthetic offline review plus optional approved staging game day.

## Offline acceptance

Copy `healthy.json`, `capstone_gate.py` and `test_capstone_gate.py` from [Chapter 050](../050-opentelemetry-enterprise-instrumentation-collector-reliability-incident-response-capstone.md):

```bash
cd chapter050
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Expected PASS and 28 authored tests.

## Staging integration game day

1. Pin SDK and Collector versions.
2. Generate synthetic HTTP, database and async spans.
3. Export traces, metrics and logs to test backends.
4. Verify context, safe attributes and bounded metric labels.
5. Test Collector agent/gateway and trace-ID affinity.
6. Introduce exporter 429; inspect queues and memory.
7. Introduce a propagation failure and repair it.
8. Simulate gateway scaling and verify trace completeness.
9. Test privacy controls using fake sensitive values.
10. Restore known-good configuration and verify recovery.
11. Record RCA, action owners, RPO/RTO and SLO impact.
12. Score the 100-point capstone using observed evidence.

## Twelve negative drills

1. Missing trace signal.
2. Missing metric signal.
3. Missing log signal.
4. Unpinned SDK version.
5. Broken propagation.
6. No trace affinity.
7. No tail sampling review.
8. No privacy test.
9. No TLS/auth test.
10. Export success below budget.
11. Collector memory above budget.
12. Rollback untested.

## Evidence

```text
UTC / operator / version:
Three signals / propagation / backend persistence:
Collector queues / memory / refusals:
Tail sampling / trace affinity:
Security and privacy:
Independent SLIs / recovery / rollback:
Offline gate / 28 tests:
Final score / approver:
```

Offline checks cannot establish live enterprise readiness.
