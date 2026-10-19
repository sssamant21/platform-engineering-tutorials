# Chapter 118 — Multi-Region HA, Failover and Recovery Lab

[Offline simulator](failover_lab.py) · [Automated tests](test_failover_lab.py) · [Full SRE/DBRE lab](../118-multi-region-ha-failover-recovery-sre-dbre-lab.md)

Python 3.11+ standard library only. No cloud accounts, database clients, actual leader election, network calls, region failover, traffic changes or production mutations.

## Execute

```bash
cd python/12-enterprise-capstones/labs/118
python -m compileall -q failover_lab.py test_failover_lab.py
python -m unittest -v test_failover_lab.py
python failover_lab.py --dry-run
python failover_lab.py --failure
```

PowerShell: `py -3 -m unittest -v test_failover_lab.py`.

## Components

- `region`: synthetic health, replication lag, backup age and restore estimate.
- `lease` / `write_allowed`: illustrative epoch/lease checks; **not authoritative fencing**.
- `elect`: simple deterministic vote tally; **not consensus or leader election for real deployments**.
- `recovery`: advisory gate for target health, RPO/RTO, old-writer fencing, quorum, approval and data verification.
- `dependencies`: recovery DAG with cycle/missing-dependency rejection.
- `reconcile`: missing/extra/mismatched source-target keys.
- `chaos`: labels synthetic faults only, zero real fault injection.
- `demo`: deterministic normal/failure scenarios, zero network/production changes.

## Exercises

1. Compare active-passive and active-active topologies.
2. Model region health, replication lag and RPO/RTO.
3. Reject expired leases and stale writer epochs.
4. Hold promotion when quorum or fencing is missing.
5. Reject promotion to unhealthy/lagging standby.
6. Construct dependency-ordered recovery plans.
7. Reconcile divergent source/target records.
8. Simulate region outage and network partition safely.
9. Design PostgreSQL and MongoDB failover with vendor tooling.
10. Define Kafka offset translation and Elasticsearch snapshot/CCR strategy.
11. Design Redis cache warmup and Snowflake failover validation.
12. Draft staging chaos test, runbooks and post-incident repatriation.

## Illustrative CI (not enabled)

```yaml
name: chapter-118-multiregion-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/118
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q failover_lab.py test_failover_lab.py
      - run: python -m unittest -v test_failover_lab.py
```

Pin reviewed action SHAs before enabling. This is a template, not an installed CI workflow.

**Safety:** Real quorum, leader election and fencing must be implemented with proven consensus and authoritative storage controls; this offline simulator does not guarantee split-brain prevention.

**Validation:** Source/tests published; exact committed execution, CI, staging DR drills and production acceptance pending.
