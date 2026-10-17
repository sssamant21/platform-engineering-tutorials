# Chapter 013 — Prometheus TSDB, WAL, Retention and Capacity Engineering Lab

**Scope:** Offline Python 3.10+ acceptance gate plus optional read-only Prometheus API queries. No data deletion, WAL modification or production configuration changes.

## 1. Build the runnable project

Copy the four complete source/fixture blocks from [Chapter 013](../013-prometheus-tsdb-wal-retention-compaction-storage-capacity-engineering.md) into:

```text
chapter013/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/capacity.py
  tests/test_capacity.py
```

## 2. Execute capacity acceptance

```bash
cd chapter013
python3 scripts/capacity.py fixtures/healthy.json
if python3 scripts/capacity.py fixtures/degraded.json; then
  echo "FAIL: degraded capacity accepted"; exit 1
else
  echo "PASS: degraded capacity detected"
fi
python3 -m unittest discover -s tests -v
```

Expected: 36.21 GiB healthy estimate, 977.665 GiB degraded estimate, degraded exit code 1, 14 passing tests.

## 3. Optional read-only Prometheus evidence

```bash
curl -fsS 'http://127.0.0.1:9090/api/v1/status/tsdb'
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=prometheus_tsdb_head_series'
```

Use only authorized endpoints. No live deployment is required for the offline lab.

## 4. Twelve failure-injection drills

1. Retention 300 days.
2. Current disk usage 190 GiB of 200 GiB.
3. Query peak memory 15 GiB of 16 GiB.
4. Compaction backlog nine blocks.
5. WAL replay 500 seconds with 180-second budget.
6. Active series 3 million.
7. Zero disk capacity.
8. Missing owner.
9. Negative sample rate.
10. NaN bytes per sample.
11. Fractional active-series count.
12. Simulate 2x sample ingestion and re-evaluate headroom.

For each, document finding, potential impact, safe mitigation and rollback owner.

## 5. DBRE incident tabletop

Prometheus monitoring PostgreSQL and Elasticsearch begins ingesting millions of series after a label change. WAL replay and query memory grow, compaction falls behind, and disk reaches 90%. Identify the instrumentation regression, containment order, data-loss risk, recovery options and customer observability impact. Never delete WAL or TSDB blocks as an unreviewed quick fix.

## 6. Evidence and acceptance

```text
UTC / operator / cluster:
Samples/sec / series / retention:
Estimated retained GiB / observed disk:
Compaction / WAL replay:
Positive and negative gates:
14 unit tests / 12 drills:
RPO / RTO / backup restore:
RCA / COA / approver:
```

**Acceptance:** healthy passes, degraded fails, 14 tests pass, capacity assumptions and recovery risks are documented. The offline gate is not a production load test.
