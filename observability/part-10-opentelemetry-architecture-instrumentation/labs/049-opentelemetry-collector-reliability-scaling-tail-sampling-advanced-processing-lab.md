# Chapter 049 — OpenTelemetry Collector Reliability, Scaling and Tail Sampling Lab

**Part 10 — OpenTelemetry Architecture and Instrumentation.**

## Offline lab

Copy `healthy.json`, `sampling_gate.py`, and `test_sampling_gate.py` from [Chapter 049](../049-opentelemetry-collector-reliability-scaling-tail-sampling-advanced-processing.md).

```bash
cd chapter049
python3 sampling_gate.py healthy.json
python3 -m unittest -v test_sampling_gate.py
```

Expected PASS and 25 authored tests.

## Staging integration

1. Pin Collector contrib distribution and component versions.
2. Deploy disposable synthetic tracing sources and gateway.
3. Send known good, error and slow traces.
4. Verify tail sampling policy decisions.
5. Test trace-ID-aware routing across multiple gateways.
6. Introduce scale-up and scale-down; measure trace completeness.
7. Introduce exporter 429 and measure queues and refusals.
8. Load-test memory limiter and trace cache under a strict budget.
9. Test privacy filtering using fake sensitive values.
10. Restore known-good routing and sampling policy.

## Twelve negative drills

1. Round-robin routing.
2. Missing trace affinity.
3. Decision wait below trace duration.
4. Trace cache too small.
5. Queue too small.
6. Memory limiter above container limit.
7. No error sampling.
8. No latency sampling.
9. Privacy review missing.
10. No Collector metrics.
11. No load test.
12. No rollback.

## Evidence

```text
UTC / owner / Collector version:
Routing/trace affinity:
Sampling policies and decision metrics:
Active traces / cache / memory:
Exporter errors / queues / refused spans:
Privacy / SLO independence:
Offline gate / 25 tests:
Negative drills / rollback / reviewer:
```

Offline checks cannot prove real trace completeness or capacity.
