# Chapter 113 — Kafka Event-Driven Worker Lab

[Offline simulator](event_lab.py) · [Automated tests](test_event_lab.py) · [Complete SRE/DBRE lab](../113-event-driven-kafka-reliable-pipelines-sre-dbre-lab.md)

Python 3.11+ standard library. No Kafka broker, database, credentials, network calls or production writes.

## Execute

```bash
cd python/12-enterprise-capstones/labs/113
python -m compileall -q event_lab.py test_event_lab.py
python -m unittest -v test_event_lab.py
python event_lab.py --dry-run
```

The simulator includes validated event envelopes, stable hash-based partitioning (not Kafka's default partitioner), in-memory outbox/version tracking (not ACID), per-partition offsets, sequential consumer/idempotency, simulated DLQ, lag, bounded queues, capped retry delays (no real jitter), SLO and synthetic end-to-end flow.

## Exercises

1. Validate event IDs, versions and payloads.
2. Preserve per-key partition routing.
3. Reject out-of-order aggregate versions.
4. Drain outbox in bounded batches.
5. Publish and read ordered offsets.
6. Suppress duplicate event IDs.
7. Simulate poison message and DLQ handling.
8. Measure lag before and after consumption.
9. Model worker/queue admission.
10. Evaluate retry and error-budget policy.
11. Design durable PostgreSQL outbox/CDC connector integration.
12. Draft Kafka outage, consumer lag and DLQ replay runbooks.

## CI template (not enabled)

```yaml
name: chapter-113-kafka-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/113
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q event_lab.py test_event_lab.py
      - run: python -m unittest -v test_event_lab.py
```

Pin action commit SHAs before enabling. **Safety:** In-memory DLQ recording and offset advancement are not crash-durable or transactional. Production requires durable DLQ publication before offset commit, idempotent external effects and reviewed security controls.

**Validation:** Source and tests published; exact committed execution, CI, live Kafka/CDC and production acceptance pending.
