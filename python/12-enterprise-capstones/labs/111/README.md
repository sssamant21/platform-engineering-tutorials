# Chapter 111 — Enterprise Python SRE/DBRE Architecture Foundations

[Offline evaluator](enterprise_lab.py) · [Automated tests](test_enterprise_lab.py) · [Full lab](../111-enterprise-python-architecture-project-foundations-sre-dbre-lab.md)

Python 3.11+ standard library only. No cloud credentials, external services, database writes, network requests, Kubernetes mutations or real fault injection.

## Execute

```bash
cd python/12-enterprise-capstones/labs/111
python -m compileall -q enterprise_lab.py test_enterprise_lab.py
python -m unittest -v test_enterprise_lab.py
python enterprise_lab.py --dry-run
python enterprise_lab.py --partial
```

The simulator validates API/worker/dependency topology, timeouts, inflight/retry limits, PostgreSQL aggregate connection capacity, queue backpressure, p99 latency, SLO budgets, role/secret/trace/rollback policy and synthetic incident classification.

## Hands-on tasks

Design API and Kafka worker architecture, PostgreSQL connection pools, Elasticsearch aliases and query budgets, MongoDB replica-set failure handling, Redis cache stampede protection, Kubernetes workload identity and readiness, OTel traces and RED/USE metrics. Create ADRs, threat model, SLO and operational runbooks.

## CI example (not enabled)

```yaml
name: chapter-111-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/111
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q enterprise_lab.py test_enterprise_lab.py
      - run: python -m unittest -v test_enterprise_lab.py
```

Pin action SHAs before enabling. **Validation:** Test code published; exact committed execution, CI, integration and production acceptance pending. This is an offline architecture evaluator, not a deployed enterprise platform.
