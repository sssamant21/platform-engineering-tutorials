# Chapter 047 — OpenTelemetry SDK Instrumentation and Context Propagation Lab

**Part 10 — OpenTelemetry Architecture and Instrumentation.**

## 1. Offline tests

Copy `healthy.json`, `sdk_gate.py` and `test_sdk_gate.py` from [Chapter 047](../047-opentelemetry-sdk-instrumentation-context-propagation-application-telemetry.md):

```bash
cd chapter047
python3 sdk_gate.py healthy.json
python3 -m unittest -v test_sdk_gate.py
```

Expected PASS and 21 authored tests.

## 2. Executable SDK demonstration

Use the chapter's `app.py` example in a Python virtual environment with compatible pinned SDK packages. Run it and inspect two parent/child spans, a request counter and a latency histogram. Execute the propagation example; confirm that injected `traceparent` is extracted into a child span in the consumer.

## 3. Optional Collector integration

Start the local Collector from Chapter 046. Replace the console span exporter with the OTLP HTTP span exporter, configure `http://127.0.0.1:4318/v1/traces` and observe Collector debug output. Verify SDK and Collector versions, exporter errors and no sensitive attributes.

## 4. Twelve negative drills

1. Missing service name.
2. Missing tracecontext.
3. Baggage privacy review absent.
4. Missing async propagation.
5. Database redaction unreviewed.
6. Metric dimensions above budget.
7. Attribute count above budget.
8. Sampling above 100%.
9. Missing error status.
10. Collector endpoint mismatch.
11. No rollback test.
12. Duplicate spans from automatic/manual instrumentation.

## 5. Incident evidence

```text
UTC / operator / SDK version:
Parent-child trace IDs:
W3C propagation headers:
Database span and redaction:
Counter / histogram / units:
Collector export evidence:
Offline gate / 21 tests:
Negative drills / rollback / reviewer:
```

Offline governance tests do not prove runtime SDK behavior or production readiness.
