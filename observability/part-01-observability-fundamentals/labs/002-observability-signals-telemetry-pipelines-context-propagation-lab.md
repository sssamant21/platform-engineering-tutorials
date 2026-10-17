# Chapter 002 — Hands-on Lab: Telemetry Pipelines and Trace Context

**Safety:** Python standard-library simulation only. No live Collector or production telemetry; no credentials.

## Learning outcomes

Validate W3C Trace Context version 00, correlate structured logs with traces, prevent sensitive baggage and unbounded metric labels, and detect simulated Collector queue pressure and dropped telemetry.

## Lab layout

```text
chapter002/
  fixtures/valid.json
  fixtures/invalid.json
  scripts/validate_context.py
  tests/test_context.py
```

Copy the complete JSON and Python source blocks from [Chapter 002](../002-observability-signals-telemetry-pipelines-context-propagation.md) into these files.

## Run positive and negative checks

```bash
cd chapter002
python3 scripts/validate_context.py fixtures/valid.json
if python3 scripts/validate_context.py fixtures/invalid.json; then
  echo "FAIL: invalid context accepted"; exit 1
else
  echo "PASS: invalid context rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: valid fixture exits 0; invalid fixture exits nonzero; six tests pass.

## 12 focused failure drills

1. Replace trace ID with all zeroes.
2. Replace parent ID with all zeroes.
3. Corrupt the traceparent syntax.
4. Mismatch the structured log trace ID.
5. Add `patient_id` to metric labels.
6. Add `trace_id` to metric labels.
7. Add `authorization` to baggage.
8. Set queue utilization to 0.95.
9. Set dropped records to 20.
10. Set batch size to zero.
11. Remove the service name.
12. Remove environment identity.

For each drill, record the validator result and the production control it models.

## Staging extension (optional; requires approval)

Deploy a pinned OpenTelemetry Collector version in an isolated namespace, validate its configuration using that version's documented command, emit synthetic OTLP spans, and inspect Collector self-metrics for exporter errors, queue utilization and dropped records. Do not send PHI/PII or real credentials. A localhost debug exporter is for development only.

## Acceptance evidence

```text
Python version / UTC:
Valid fixture exit code:
Invalid fixture exit code:
Six test results:
Trace/log correlation:
Sensitive baggage and labels:
Queue/drop checks:
12 drills:
Staging extension status (if performed):
RCA / COA / reviewer:
```

- [ ] Valid fixture accepted.
- [ ] Unsafe fixture rejected.
- [ ] Six tests pass.
- [ ] Trace/log context rules explained.
- [ ] Sensitive attributes and labels excluded.
- [ ] Collector loss/backpressure behavior understood.
- [ ] Real telemetry delivery not claimed without staging evidence.
