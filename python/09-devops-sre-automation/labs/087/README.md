# Chapter 087 — Executable Infrastructure Monitoring Lab

Standalone files: [monitor.py](monitor.py), [test_monitor.py](test_monitor.py), [exporter.py](exporter.py), [otel_demo.py](otel_demo.py), [requirements.txt](requirements.txt).

## Run offline tests

\`\`\`bash
cd python/09-devops-sre-automation/labs/087
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q monitor.py test_monitor.py exporter.py otel_demo.py
python -m unittest -v test_monitor.py
python monitor.py --dry-run
\`\`\`

Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_monitor.py\`.

## Optional local host sampling and exporters

\`\`\`bash
python -m pip install -r requirements.txt
python monitor.py --format json
python monitor.py --format prometheus
python exporter.py --dry-run
python exporter.py --port 9109 --interval 15
# In another terminal:
curl http://127.0.0.1:9109/metrics
python otel_demo.py
\`\`\`

The Prometheus HTTP server binds **127.0.0.1 only**. Do not expose the exporter externally without an approved access boundary. The OTEL demonstration uses an in-memory metric reader, **not** a remote OTLP endpoint. Avoid interpreting a host sample as container cgroup telemetry.

## Test coverage

24 deterministic tests for invalid/NaN values, sampling injection, warning/critical/recovery, alert cooldown and dedup, hysteresis, SLO availability and error budget, bounded windows, Prometheus exposition and dry-run. The project has no production pager or remote alert receiver. For durable alerting use Prometheus alert rules and Alertmanager.

## Operational limitations

- In-process cooldown is reset on restart; production deduplication must persist outside this process.
- One CPU/memory/disk sample is not an alert-quality sustained window. Aggregate in Prometheus with duration and burn-rate rules.
- CPU and memory percentages are host-scoped; disk percentage is space used, not disk latency or IOPS.
- No OTLP exporter, distributed collector, database exporter, or production notification integration is configured.
- Use monotonic time for production cooldown logic; the lab's event timestamps are wall-clock values to enable deterministic tests.
- Dependency ranges are educational; pin exact reviewed versions and hashes for deployment.

## CI template (not enabled)

\`\`\`yaml
name: chapter-087-offline-monitoring
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/09-devops-sre-automation/labs/087
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q monitor.py test_monitor.py exporter.py otel_demo.py
      - run: python -m unittest -v test_monitor.py
\`\`\`

Pin action SHAs before enabling. No credentials or production systems are needed for tests.

**Validation status:** The repository contains standalone code and test files. Offline code was also independently prototyped in a working container with 24 passing tests; the final committed version should be executed again in CI. Prometheus listener, OTEL integration and production monitoring are not live-validated.
