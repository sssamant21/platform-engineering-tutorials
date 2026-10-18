# Chapter 046 — OpenTelemetry Architecture, SDKs and Collector Fundamentals Lab

**Part 10 — OpenTelemetry Architecture and Instrumentation.** Use synthetic data only.

## Offline review

Copy `healthy.json`, `otel_gate.py`, and `test_otel_gate.py` from [Chapter 046](../046-opentelemetry-architecture-signals-sdks-collector-fundamentals.md):

```bash
cd chapter046
python3 otel_gate.py healthy.json
python3 -m unittest -v test_otel_gate.py
```

Expected PASS and 19 authored tests.

## Optional local Collector lab

1. Pin a Collector distribution and record the exact version.
2. Save the chapter's `collector.yaml` and start the local Collector.
3. Send the synthetic OTLP HTTP trace from the chapter.
4. Inspect debug exporter output and receiver counters.
5. Repeat with a synthetic metric and log record using the target OTLP schema.
6. Introduce an unreachable exporter and inspect retries/refused records.
7. Review memory-limiter behavior with bounded synthetic load.
8. Restore the healthy config and document rollback.

## Twelve negative drills

1. Missing service name.
2. Missing environment.
3. Missing traces pipeline.
4. Missing metrics pipeline.
5. Missing logs pipeline.
6. No OTLP receiver.
7. No memory limiter.
8. No batch processor.
9. Missing exporter.
10. Unreviewed PII.
11. Unreviewed cardinality.
12. Missing rollback.

## Evidence

```text
UTC / operator / Collector distribution and version:
Signals / resource attributes:
OTLP HTTP and gRPC listeners:
Receiver / processor / exporter evidence:
Queue and memory behavior:
Offline gate / 19 tests:
Negative drills / rollback / reviewer:
```

Offline governance tests alone do not prove successful end-to-end telemetry export.
