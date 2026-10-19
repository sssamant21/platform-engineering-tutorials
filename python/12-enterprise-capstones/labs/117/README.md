# Chapter 117 — Enterprise Capacity, Performance and FinOps Lab

[Offline simulator](capacity_lab.py) · [Automated tests](test_capacity_lab.py) · [Full SRE/DBRE lab](../117-capacity-performance-finops-sre-dbre-lab.md)

Python 3.11+ standard library only. No Kubernetes, databases, cloud accounts, network calls, load generation, real billing or production changes.

## Run

```bash
cd python/12-enterprise-capstones/labs/117
python -m compileall -q capacity_lab.py test_capacity_lab.py
python -m unittest -v test_capacity_lab.py
python capacity_lab.py --dry-run
python capacity_lab.py --overload
```

PowerShell: `py -3 -m unittest -v test_capacity_lab.py`.

## Implemented

- `forecast`: compound demand forecast and configurable headroom.
- `cpu_cores`: CPU-seconds/second sizing with target utilization.
- `replicas`: per-pod throughput, replica bounds and saturation.
- `storage`: ingest, retention, replication, compression and headroom.
- `iops`: disk IO amplification, utilization and safe threshold.
- `pool`: aggregate per-pod database connections vs reserved capacity.
- `cost`: illustrative hourly resource spend and team allocation.
- `loadtest`: offline sample p99/error SLO evaluation (no load generated).
- `gate`: advisory CPU, IO, connections, SLO, budget and approval decision.
- `demo`: deterministic normal/overload scenarios, zero network/production changes.

## Exercises

1. Forecast 30-day API demand and compare headroom assumptions.
2. Convert RPS and CPU milliseconds into cores.
3. Model HPA/KEDA replica caps and saturation.
4. Estimate Elasticsearch retention and replica storage.
5. Compare disk IOPS requirement against safe throughput.
6. Bound PostgreSQL connections as pod replicas increase.
7. Allocate synthetic Kubernetes/compute costs to teams.
8. Evaluate latency and error SLOs from sample load-test results.
9. Hold promotion for overload or budget risk.
10. Design real profiling, soak and canary experiments.
11. Define Kafka/MongoDB/Redis/Snowflake capacity boundaries.
12. Draft operational runbooks and a FinOps savings proposal.

## Illustrative CI (not enabled)

```yaml
name: chapter-117-capacity-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/117
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q capacity_lab.py test_capacity_lab.py
      - run: python -m unittest -v test_capacity_lab.py
```

Pin reviewed GitHub Action commit SHAs before enabling. No CI job is installed by this snippet.

**Safety:** No real load, cloud billing or production modifications. Forecast and prices are illustrative, not calibrated to a live environment.

**Validation:** Source and tests published; exact committed execution, CI, live load tests and production acceptance pending.
