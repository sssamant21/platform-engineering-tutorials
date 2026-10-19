# Chapter 120 — Final Enterprise Python SRE/DevOps/DBRE Capstone

[Offline simulator](platform_lab.py) · [Automated tests](test_platform_lab.py) · [Complete lab](../120-enterprise-final-platform-sre-dbre-assessment-lab.md) · [Chapter theory](../../120-enterprise-python-final-sre-devops-dbre-capstone-operational-assessment.md)

**Requirements:** Python 3.11+, standard library only. No cloud account, database, Kafka, Kubernetes cluster, credentials or network access required.

## Run locally

```bash
cd python/12-enterprise-capstones/labs/120
python -m compileall -q platform_lab.py test_platform_lab.py
python -m unittest -v test_platform_lab.py
python platform_lab.py --dry-run
python platform_lab.py --failure
```

Windows PowerShell: `py -3 -m unittest -v test_platform_lab.py`.

## Lab components

- `Event`: tenant-scoped typed envelope, monotonic version, SHA-256 payload digest.
- `authorized`: illustrative role/tenant metadata check; not real authentication.
- `Pipeline.submit`: bounded in-memory source and outbox, revision rejection, admission.
- `Pipeline.publish`: stable partition mapping and synthetic broker logs.
- `Pipeline.consume`: version-aware idempotent projections and no offset advance on simulated sink failure.
- `Pipeline.reconcile`: missing/extra/mismatched record and version/hash detection.
- `capacity`: CPU/replica sizing with saturation cap.
- `slo`: availability, error budget and no-traffic unknown status.
- `dr`: advisory RPO/RTO, fencing, approval and verification checks.
- `acceptance`: 100-point all-gates advisory readiness decision.
- `demo`: deterministic normal and failure scenarios with zero network/production actions.

**Important limitations:** Outbox/source operations are not ACID or durable; broker has no replication, persistence, transactions, consumer groups or real Kafka protocol. Search and warehouse are Python dictionaries, not Elasticsearch/Snowflake. The security flags do not validate tokens, permissions or encryption; the DR flags do not perform fencing or failover. The hash is for data comparison, not authentication.

## Twelve exercises

1. Model API auth and tenant boundaries.
2. Submit typed source events with monotonic versions.
3. Simulate outbox admission and backpressure.
4. Publish deterministic partitions.
5. Consume and idempotently project search/warehouse records.
6. Simulate sink failure before offset commit.
7. Reconcile source, search and analytics versions.
8. Forecast CPU/replicas and overload.
9. Calculate SLO status and error-budget impact.
10. Evaluate DR RPO/RTO and fencing gates.
11. Hold release on any critical readiness failure.
12. Prepare real staging integration, chaos, restore and operational acceptance evidence.

## CI template (not installed)

```yaml
name: chapter-120-final-offline
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/120
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q platform_lab.py test_platform_lab.py
      - run: python -m unittest -v test_platform_lab.py
```

Pin reviewed immutable action SHAs before enabling. The template is not an installed CI workflow.

## Acceptance evidence checklist

Record commit SHA, Python version, compilation/test output, normal/failure CLI reports, security review, staging architecture validation, Kafka/CDC replay, PostgreSQL/MongoDB recovery, Elasticsearch/Snowflake reconciliation, Redis cache failover, Kubernetes capacity/rollout, SLO burn-rate analysis, approved restore drill, rollback and incident game day. The offline simulator cannot replace any of these production checks.

**Validation status:** Published source/tests; exact committed runtime execution, CI, live integrations, security audit, staging DR and production acceptance pending.
