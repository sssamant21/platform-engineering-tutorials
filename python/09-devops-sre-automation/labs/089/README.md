# Chapter 089 — Executable Reliability, SLO and Operational Readiness Lab

**Source:** [reliability.py](reliability.py) · [test_reliability.py](test_reliability.py). Python 3.11+ standard library only.

## Run offline

\`\`\`bash
cd python/09-devops-sre-automation/labs/089
python -m compileall -q reliability.py test_reliability.py
python -m unittest -v test_reliability.py
python reliability.py --dry-run
python reliability.py --failures 0
python reliability.py --failures 20 --target 0.99
\`\`\`

Windows PowerShell: \`py -3 -m unittest -v test_reliability.py\`.

The script uses **synthetic request events** and prints a JSON report. It performs no cloud calls, database operations, alert delivery, deployment or remediation. The dry-run mode performs no evaluation or side effects.

## Model

- Each event records timestamp, eligibility, success and latency.
- Windows are half-open \`[start,end)\`; excluded events do not affect denominator.
- Availability SLI and latency SLI are computed separately.
- Error budget, remaining budget fraction and burn rate are derived from the availability SLI.
- Multiwindow burn requires both windows to have enough events and exceed a threshold.
- Release readiness requires telemetry freshness, tested rollback, owner, paging, backup/restore, capacity review, no active Sev1 and no fast burn.

## Exercises

1. Increase failures from 0 to 20; inspect budget and release gate.
2. Set \`--target 0.999\`; compare budget sensitivity.
3. Change latency thresholds and request latencies in the fixture.
4. Add excluded events; verify denominator does not change.
5. Remove all events; confirm unknown SLI and blocked release.
6. Mark \`backup_restore_tested=False\`; confirm fail-closed gate.
7. Add an active Sev1 incident; confirm gate blocks even with healthy SLI.
8. Test a fast-burn threshold and discuss alert tuning.
9. Simulate stale telemetry and duplicate events as production extensions.
10. Design a production Prometheus recording-rule pipeline.

## Limitations

- The lab is an in-memory single-process model, **not** a live Prometheus/OTEL collector or distributed SLO store.
- No event IDs, late-data reconciliation, deduplication or persisted history are implemented.
- Readiness checks are supplied as booleans; production requires signed/fresh evidence from trusted systems.
- Burn thresholds and windows are illustrative. Production alert design must consider actual SLO periods, traffic and paging load.
- A CLI \`ready=true\` result is advisory, not deployment authorization.

## CI template (not enabled)

\`\`\`yaml
name: chapter-089-reliability
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/09-devops-sre-automation/labs/089
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q reliability.py test_reliability.py
      - run: python -m unittest -v test_reliability.py
\`\`\`

Pin reviewed GitHub Actions commit SHAs before enabling.

**Validation status:** The standalone source and unit tests are published. Runtime/CI execution of the committed files remains pending.
