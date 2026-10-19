# Chapter 069 — Application Performance Testing and Capacity Observability Lab

**Part 14 — Application Performance Monitoring**

## Offline validation

Save `healthy.json`, `load_gate.py` and `test_load_gate.py` from [Chapter 069](../069-application-performance-testing-load-stress-soak-capacity-observability.md).

```bash
python3 load_gate.py healthy.json
python3 -m unittest -v test_load_gate.py
```

Expected PASS and 28 authored tests; capture actual output.

## Approved staging workflow

1. Confirm isolated target, change approval, load budget and abort conditions.
2. Record baseline p50/p95/p99, error rate and achieved throughput.
3. Run k6 smoke and bounded constant-arrival-rate tests.
4. Verify generator CPU, VUs and dropped iterations.
5. Compare expected vs achieved arrivals and account for coordinated omission.
6. Review application CPU, memory, GC and queue depth.
7. Correlate PostgreSQL pool waits, Redis latency and Kafka lag.
8. Conduct controlled ramp, stress and time-limited soak tests.
9. Estimate capacity headroom, autoscaler behavior and cost.
10. Stop load, restore test state and verify SLO recovery.

## Negative drills

Test missing load reviews, unsafe environment, throughput shortfall, p95/error breaches, dropped iterations, invalid percent and unsafe changes.

## Evidence

```text
UTC / owner / change:
Staging isolation and abort plan:
Workload mix / requested vs achieved RPS:
Generator CPU / dropped iterations:
p95/p99 / errors / saturation:
DB/Redis/Kafka dependency evidence:
Autoscaling / cost / soak trends:
Rollback / independent SLO recovery:
Offline gate and 28 tests:
```

Offline manifest validation is not proof of achieved service capacity.
