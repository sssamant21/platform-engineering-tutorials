# Chapter 108 — Production Observability, Tracing and Reliability Engineering Lab

[Offline telemetry engine](observability_lab.py) · [Automated tests](test_observability_lab.py) · [Full SRE/DBRE lab](../108-production-observability-tracing-reliability-sre-dbre-lab.md)

## Run

Python 3.11+ standard library only; no OpenTelemetry/Prometheus packages, exporters, cloud credentials, database access, network or production writes.

```bash
cd python/11-production-security-performance/labs/108
python -m compileall -q observability_lab.py test_observability_lab.py
python -m unittest -v test_observability_lab.py
python observability_lab.py --dry-run
python observability_lab.py --partial
```

PowerShell: `py -3 -m unittest -v test_observability_lab.py`.

## Implemented

- Synthetic trace/span IDs, parent relationships, duplicate/orphan/cycle detection and span status.
- RED request rate, error ratio, p95/p99; USE utilization, saturation and error ratio.
- SLI, error-budget accounting and illustrative short/long burn-rate signals.
- Structured JSON log event generation with **limited key-based teaching redaction**.
- SHA-256 report fingerprint (not digital signature).
- Coverage-aware incident classification: partial evidence → unknown.
- **Zero live exporters, network calls, alerts or mutations.**

## Exercises

1. Validate trace ID/span ID format and parent graph.
2. Reject orphan, duplicate and cyclic spans.
3. Calculate RED rate, error ratio, p95 and p99.
4. Handle zero traffic as missing SLI, not success.
5. Compare USE resource saturation against RED user impact.
6. Compute SLO error budget and fast-burn signals.
7. Generate structured logs and redact known sensitive keys.
8. Explain why key-based redaction does not replace privacy scanning.
9. Model incomplete telemetry as unknown.
10. Design OTel SDK/Collector and Prometheus exporter architecture.
11. Correlate PostgreSQL, Elasticsearch, MongoDB, Kafka and Kubernetes incidents.
12. Create actionable on-call runbooks and rollback gates.

## Production extension — NOT implemented

Use reviewed OpenTelemetry API/SDK, instrumentations and OTLP exporters; W3C context propagation; Prometheus histogram/counter instrumentation; safe labels; secure collector configuration; tail sampling capacity; log retention and access control; error-budget recording rules and multi-window alerts. Verify metric names/semantic convention versions and load-test exporter failure behavior.

## CI template (not enabled)

```yaml
name: chapter-108-observability-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/108
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q observability_lab.py test_observability_lab.py
      - run: python -m unittest -v test_observability_lab.py
```

Pin reviewed action commit SHAs before enabling. **Validation:** Tests published; exact committed execution, CI, OTel/Prometheus integrations, privacy review and live SLO acceptance remain pending.
