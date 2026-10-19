# Chapter 110 — Integrated Production Security, Performance and Reliability Capstone

[Executable Python evaluator](capstone.py) · [Automated tests](test_capstone.py) · [Complete SRE/DBRE lab](../110-production-security-performance-reliability-capstone-sre-dbre-lab.md)

## Run locally

Python 3.11+ standard library only. No cloud credentials, third-party packages, network connections, database writes or deployments.

```bash
cd python/11-production-security-performance/labs/110
python -m compileall -q capstone.py test_capstone.py
python -m unittest -v test_capstone.py
python capstone.py --dry-run
python capstone.py --partial
```

PowerShell: `py -3 -m unittest -v test_capstone.py`.

## Modules

- `identity`: simplified least-privilege role assessment.
- `secrets`: metadata-only rotation due flag.
- `compliance`: pass/fail/unknown evidence gate.
- `supply_chain`: package metadata/hash-format and trust-flag checks (no real signature verification).
- `performance`: validated p50/p95/p99 and latency budget.
- `concurrency`: bounded active, queue and rejected workload model.
- `slo`: availability and remaining error budget.
- `retry`: idempotency-aware retry attempt classification.
- `redact`: simple key-name redaction (not comprehensive sensitive-data protection).
- `release`: **advisory-only** decision; never deploys.
- `demo`: synthetic evidence and canonical SHA-256 report digest.

`--partial` marks a compliance control unknown and demonstrates fail-closed release gating.

## Operational exercises

1. Run tests and inspect synthetic evidence.
2. Verify role authorization and least-privilege failure.
3. Test overdue secret rotation without reading secrets.
4. Change compliance from pass to fail/unknown.
5. Flag an untrusted dependency and invalid digest metadata.
6. Calculate p99 and reject performance regression.
7. Model queue overload and connection pool pressure.
8. Calculate SLO breach and block release.
9. Block retries for non-idempotent operations.
10. Verify sensitive log keys are redacted; document limitations.
11. Test release gate with missing independent approval.
12. Build a change ticket with rollback and evidence retention.

## CI template (not enabled)

```yaml
name: chapter-110-capstone-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/110
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q capstone.py test_capstone.py
      - run: python -m unittest -v test_capstone.py
```

Pin reviewed GitHub Action commit SHAs before enabling. This is a CI example, not a committed workflow.

**Validation:** Code and tests published; execution of exact committed files, CI, cryptographic signature verification, real OTel/profiling, cloud integration, security review and production acceptance remain pending.
