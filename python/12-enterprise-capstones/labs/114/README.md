# Chapter 114 — Data Pipeline Orchestration, CDC and Reconciliation Lab

[Offline pipeline simulator](pipeline_lab.py) · [Automated tests](test_pipeline_lab.py) · [Full SRE/DBRE lab](../114-data-pipeline-orchestration-cdc-reconciliation-recovery-sre-dbre-lab.md)

## Run locally

Python 3.11+ standard library only. No PostgreSQL, MongoDB, Kafka, Elasticsearch, Snowflake, orchestration engine, credentials, network or production mutations.

```bash
cd python/12-enterprise-capstones/labs/114
python -m compileall -q pipeline_lab.py test_pipeline_lab.py
python -m unittest -v test_pipeline_lab.py
python pipeline_lab.py --dry-run
python pipeline_lab.py --partial
```

PowerShell: `py -3 -m unittest -v test_pipeline_lab.py`.

## Implemented modules

- `event`: bounded PostgreSQL/MongoDB-style CDC envelope and sequence validation.
- `Checkpoints`: monotonic, source-specific illustrative integer positions.
- `Projection`: per-entity versions, idempotent replay, tombstone/delete and snapshot.
- `Pipeline`: canonical state, search and warehouse projections, sink-failure simulation and checkpoint gating.
- `diff`: missing/extra/mismatched record reconciliation.
- `plan_backfill`: inclusive bounded batch ranges.
- `dag`: dependency validation, deterministic topological ordering and cycle detection.
- `gate`: advisory reconciliation, CDC lag and human-approval checks.
- `demo`: synthetic successful and partial-failure workflows; zero network calls and production writes.

## Hands-on exercises

1. Validate PostgreSQL/MongoDB CDC event envelopes.
2. Model separate source checkpoint namespaces.
3. Reject checkpoint regression and sequence gaps.
4. Build DAG and reject dependency cycles.
5. Apply source events to search/warehouse projections.
6. Simulate warehouse failure and verify checkpoint is not advanced.
7. Replay safely using per-entity idempotency.
8. Reconcile missing/extra/mismatched records.
9. Plan bounded backfill batches.
10. Gate promotion on lag, reconciliation and approval.
11. Design real PostgreSQL LSN/MongoDB resume-token handling.
12. Draft Kafka, Elasticsearch, Snowflake and CDC recovery runbooks.

## CI example (not enabled)

```yaml
name: chapter-114-cdc-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/114
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q pipeline_lab.py test_pipeline_lab.py
      - run: python -m unittest -v test_pipeline_lab.py
```

Pin reviewed action SHAs before enabling. This is an illustrative workflow, not a configured CI job.

**Safety:** Checkpoints and projections are in-memory, not crash-durable or atomic across external sinks. The synthetic source sequence is not a PostgreSQL LSN or MongoDB resume token. Real backfills and repairs require approved plans, fencing, durable checkpoints and reconciliation.

**Validation:** Code and tests published; exact committed execution, CI, live CDC integrations and production acceptance pending.
