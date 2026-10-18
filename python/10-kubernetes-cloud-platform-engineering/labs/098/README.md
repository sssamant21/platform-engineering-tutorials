# Chapter 098 — Executable Multi-Cloud Observability and Incident Lab

[Python simulator](incident_lab.py) · [36 automated tests](test_incident_lab.py) · [Complete lab](../098-multi-cloud-observability-incident-sre-dbre-lab.md)

## Run offline

Python 3.11+ standard library only. No AWS/Azure/GCP credentials, SDKs or network access.

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/098
python -m compileall -q incident_lab.py test_incident_lab.py
python -m unittest -v test_incident_lab.py
python incident_lab.py --dry-run
```

The simulator emits three synthetic signals (CloudWatch-shaped AWS latency, Azure Monitor-shaped CPU and Google Cloud Monitoring-shaped errors) with an OpenTelemetry-shaped trace ID. It validates timestamps, deduplicates alerts, correlates incidents by service and time bucket, calculates request availability and error-budget consumption, generates a SHA-256 advisory plan and enforces simulated approval. **No cloud API calls or remediation writes exist.**

## Exercises

1. Normalize provider/scope/service metrics.
2. Reject NaN, negative, future and stale samples.
3. Reject malformed 32-hex trace IDs.
4. Exercise fake pagination and item/page limits.
5. Calculate a 99.9% request-availability SLO.
6. Simulate error-budget exhaustion and burn ratio.
7. Deduplicate repeated alerts.
8. Correlate AWS/Azure/GCP signals by service and time window.
9. Preserve trace IDs and avoid assuming causality.
10. Verify plan fingerprint stability.
11. Reject `restart-db` and other remediation actions.
12. Verify simulated approval always yields zero writes.

## Production integration blueprint (not implemented)

- **AWS:** boto3 CloudWatch GetMetricData, CloudWatch Logs Insights, STS identity check, X-Ray/OTel trace links.
- **Azure:** azure-identity + azure-monitor-query metrics/logs, scoped resource URI, Entra ID/RBAC.
- **GCP:** google-cloud-monitoring MetricServiceClient, ADC and project allowlist, Cloud Trace/Logging.
- **OpenTelemetry:** instrument services with stable resource attributes, trace/span IDs and W3C context; use an OTLP collector with bounded buffers and PII redaction.
- Normalize units and dimensions, track collector completeness, use provider API quotas and bounded retries, and implement multi-window SLO alerts.
- Require independently authenticated approval, audit, tested rollback and staged integration tests before introducing write adapters.

## CI template (not enabled)

```yaml
name: chapter-098-observability-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/098
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q incident_lab.py test_incident_lab.py
      - run: python -m unittest -v test_incident_lab.py
```

Pin reviewed GitHub Actions commit SHAs before enabling. **Validation:** An equivalent offline implementation passed 36 local tests and compilation before publication. GitHub CI and live cloud integrations remain pending.
