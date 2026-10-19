# Chapter 119 — Production Readiness, Chaos and Reliability Acceptance Lab

[Offline simulator](readiness_lab.py) · [Automated tests](test_readiness_lab.py) · [Full SRE/DBRE lab](../119-production-readiness-chaos-reliability-acceptance-sre-dbre-lab.md)

Python 3.11+ standard library only. No cloud, network calls, real security scanning, fault injection, production writes or release promotion.

## Execute

```bash
cd python/12-enterprise-capstones/labs/119
python -m compileall -q readiness_lab.py test_readiness_lab.py
python -m unittest -v test_readiness_lab.py
python readiness_lab.py --dry-run
python readiness_lab.py --failure
```

Windows PowerShell: `py -3 -m unittest -v test_readiness_lab.py`.

## Components

- `Evidence`: typed control evidence, owner, reference and UTC timestamp **format** checks. Does not fetch evidence or validate actual freshness.
- `review`: 100-point PRR scoring across eight domains, critical-control blocking, human approval and tested-rollback flags.
- `slo`: availability, remaining event error budget, fast/slow burn rates, explicit no-traffic unknown state.
- `load_gate`: synthetic p99/error, CPU, memory and DB pool guardrails.
- `chaos_plan`: synthetic fault selection, staging/offline scope, blast-radius cap, abort and approval checks. **Does not inject faults.**
- `incident`: severity, signals, incident owner and advisory response classification.
- `sample`: reproducible ready/failure scenarios with zero external actions and deterministic report hash.

## Exercises

1. Build an evidence inventory with owners, timestamps and artifacts.
2. Score all eight PRR domains and hold for missing evidence.
3. Demonstrate critical failure blocking despite a high score.
4. Require human approval and tested rollback.
5. Compute availability SLI, remaining budget and burn rates.
6. Treat zero traffic or missing telemetry as unknown.
7. Hold a deployment on p99, error, CPU, memory or DB pool regression.
8. Define a staging pod-kill game day with abort thresholds.
9. Reject broad blast radius or unapproved fault plans.
10. Classify an incident, assign commander and preserve a UTC timeline.
11. Design PostgreSQL/Elasticsearch/MongoDB/Redis/Kafka/Snowflake runbooks.
12. Produce a signed-off PRR, change plan, canary/rollback criteria and follow-up actions.

## Illustrative CI (not installed)

```yaml
name: chapter-119-readiness-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/119
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q readiness_lab.py test_readiness_lab.py
      - run: python -m unittest -v test_readiness_lab.py
```

Pin reviewed action commit SHAs before enabling; the above is not a configured workflow.

**Security and safety:** Evidence flags are illustrative; this simulator does not verify signatures, credentials, actual control effectiveness or operational readiness. Real release gates require independent validation and authorized human sign-off.

**Validation:** Source and test code published; exact committed execution, CI, real chaos drills and production acceptance pending.
