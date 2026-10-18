# Chapter 048 — OpenTelemetry Collector Pipelines and Production Deployment Lab

**Part 10 — OpenTelemetry Architecture and Instrumentation.** Local synthetic data first; staging only for deployments.

## Offline gate

Copy `healthy.json`, `collector_gate.py`, `test_collector_gate.py` from [Chapter 048](../048-opentelemetry-collector-pipelines-processors-exporters-production-deployment.md):

```bash
cd chapter048
python3 collector_gate.py healthy.json
python3 -m unittest -v test_collector_gate.py
```

Expected PASS and 27 authored tests.

## Collector integration lab

1. Pin Collector distribution and version.
2. Save the chapter's `collector.yaml`.
3. Validate configuration using the pinned binary's supported validation command.
4. Start local Collector and check health endpoint.
5. Send synthetic traces, metrics and logs over OTLP.
6. Inspect debug output and self-metrics.
7. Introduce exporter failure in disposable staging and observe retry/backpressure.
8. Load-test within strict memory/CPU limits.
9. Restore known-good configuration and verify all three signals.

## Twelve negative drills

1. Missing OTLP receiver.
2. Missing traces pipeline.
3. Missing metrics pipeline.
4. Missing logs pipeline.
5. No memory limiter.
6. No batch processor.
7. Memory limit mismatch.
8. Queue capacity too small.
9. TLS review absent.
10. Authentication review absent.
11. Production exposure flagged.
12. Rollback untested.

## Incident evidence

```text
UTC / operator / distribution/version:
Receiver/processor/exporter wiring:
Three-signal smoke tests:
Accepted/refused/exporter failures:
Memory/CPU/queue:
TLS/auth/NetworkPolicy:
Offline gate / 27 tests:
Negative drills / rollback / reviewer:
```

The offline gate cannot verify Collector component compatibility, live ingestion or production readiness.
