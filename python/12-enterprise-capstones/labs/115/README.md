# Chapter 115 — Enterprise Python Observability and Reliability Lab

[Offline engine](observability_lab.py) · [Automated tests](test_observability_lab.py) · [Complete SRE/DBRE lab](../115-enterprise-observability-slo-incident-response-sre-dbre-lab.md)

Python 3.11+ standard library only. No external packages, network, OTel exporters, monitoring services, paging or production mutations.

## Execute

```bash
cd python/12-enterprise-capstones/labs/115
python -m compileall -q observability_lab.py test_observability_lab.py
python -m unittest -v test_observability_lab.py
python observability_lab.py --dry-run
python observability_lab.py --partial
```

PowerShell: `py -3 -m unittest -v test_observability_lab.py`.

## Implemented

- Synthetic parent/child span graph validation, cycle/missing-parent checks and service correlation.
- Key-based sample log redaction (not complete PII detection).
- Interpolated p50/p95/p99 latency percentile helper.
- RED request/error/latency and USE utilization/saturation/error summaries.
- Availability SLI, remaining error budget and explicit no-traffic unknown state.
- Simplified multiwindow burn-rate decision (no real paging).
- Grouped incident signals across logs, metrics, traces and changes.
- Advisory release gate for SLO, trace coverage, rollback, owner and approval.
- Deterministic SHA-256 report fingerprint, `--partial` failure simulation and zero network/writes.

## Exercises

1. Validate distributed span parent relationships and errors.
2. Reject malformed spans, cycles and missing parents.
3. Redact sensitive sample log fields.
4. Compute p99 latency and RED request/error metrics.
5. Interpret USE saturation/CPU signals.
6. Calculate SLI and remaining error budget.
7. Compare fast and slow burn windows.
8. Correlate API and PostgreSQL incident signals.
9. Hold promotion when telemetry coverage is incomplete.
10. Design live OTel/Prometheus instrumentation and on-call escalation.
11. Write an incident timeline and postmortem action plan.
12. Draft rollback, alert tuning and operational acceptance criteria.

## Illustrative CI (not enabled)

```yaml
name: chapter-115-observability-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/115
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q observability_lab.py test_observability_lab.py
      - run: python -m unittest -v test_observability_lab.py
```

Pin reviewed action SHAs before enabling. This template does not create a CI workflow by itself.

**Safety:** No real alerts, production dashboards, collector, token handling or data mutations. The release gate is advisory only.

**Validation:** Source and automated tests published; exact committed execution, CI, live OTel/Prometheus integrations and production acceptance pending.
