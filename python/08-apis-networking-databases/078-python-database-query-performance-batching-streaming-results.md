# Chapter 078 — Python Database Query Performance, Batching and Streaming Results

**Part 08 — APIs, Networking and Databases | Python 3.11+ | PostgreSQL 15+ | psycopg 3**

## Outcomes
Diagnose slow SQL with PostgreSQL \`EXPLAIN (ANALYZE, BUFFERS)\`, build safe psycopg 3 batch inserts and COPY pipelines, stream large query results through server-side cursors, bound memory and transaction duration, and respond to production SRE/DBRE incidents. The companion lab requires a **disposable PostgreSQL database** for full integration tests; guard tests run offline.

## Architecture
\`\`\`text
Python ETL/SRE worker -> psycopg 3 connection
  -> prepared/parameterized SQL -> PostgreSQL planner + indexes
  -> EXPLAIN ANALYZE / BUFFERS / pg_stat_statements
  -> cursor.fetchmany / named server cursor -> bounded batches
  -> COPY FROM STDIN -> WAL/checkpoints/replication
  -> query timeouts + transaction lifecycle -> metrics/runbooks
\`\`\`

## 1. Query plans
Use \`EXPLAIN\` to inspect estimated cost without executing a query. \`EXPLAIN ANALYZE\` **executes** the statement, so for mutating statements use a disposable database or explicit transaction rollback; even a rolled-back statement can have side effects such as sequence advancement and external function calls. \`BUFFERS\` reveals shared hits, reads, dirtied and written blocks. Inspect actual versus estimated rows, sequential/index/bitmap scans, nested-loop/hash/merge joins, sort spills, temp blocks, planning time and execution time. Plans depend on statistics, parameter selectivity, indexes, work_mem and PostgreSQL version. Avoid assuming an index scan is always better than a sequential scan.

## 2. Performance baselines
Record p50/p95/p99 latency, rows processed per second, client memory high-water mark, WAL volume, CPU, IOPS, temp files, lock waits and transaction age. Capture sanitized SQL fingerprints and query IDs, not patient identifiers. Compare warm/cold cache and realistic row distributions. Use \`ANALYZE\` after large data changes; check \`pg_stat_statements\` only where enabled. Avoid changing global settings without change control.

## 3. psycopg 3 parameterization
Use \`cur.execute("SELECT ... WHERE id = %s", (value,))\` for values. For SQL identifiers, use \`psycopg.sql.Identifier\` with a strict allowlist; never interpolate untrusted table/column names. Do not put secrets in DSNs printed to logs. For bulk inserts, \`executemany\` can batch protocol operations; measure it against COPY for large ingest.

## 4. Batch inserts and COPY
Bound batch size and transaction size to control memory, WAL spikes and lock duration. \`executemany\` is convenient for moderate volumes; psycopg 3 COPY supports high-throughput ingestion. For row-wise COPY, use \`with cur.copy("COPY ... FROM STDIN") as copy: copy.write_row(tuple)\`. Use explicit column lists and a staging table where appropriate. COPY can increase WAL, checkpoint pressure and replication lag; coordinate with DBRE capacity controls. Do not treat successful COPY as proof downstream replicas are caught up.

## 5. Streaming large results
A regular cursor's \`fetchmany\` bounds the number of rows returned to the application per call, but may still buffer the entire result client-side depending on driver and query mode. A **named server-side cursor** (\`conn.cursor(name="...")\`) fetches incremental batches from PostgreSQL, keeping client memory bounded. Named cursors generally require an open transaction and hold a snapshot; long-lived cursors can impede VACUUM and increase MVCC bloat. Prefer keyset pagination or short-lived batched transactions for sustained production exports when possible. Avoid OFFSET pagination at very large offsets.

## 6. Timeouts
Set driver \`connect_timeout\`, session \`statement_timeout\`, \`lock_timeout\` and \`idle_in_transaction_session_timeout\` to approved values. PostgreSQL SQLSTATE \`57014\` denotes query cancellation, often from statement timeout. A statement timeout is not a full job deadline. Bound overall job time and use safe cancellation/rollback. Avoid retrying non-idempotent COPY after an ambiguous COMMIT; reconcile by batch/job key.

## 7. Indexes and execution-plan tradeoffs
B-tree indexes support equality and ordered ranges. Composite index order, covering/index-only scans, partial indexes and selectivity affect plans. Index-only scans depend on visibility map coverage. A query that reads a large fraction of a table may favor a sequential scan. \`CREATE INDEX CONCURRENTLY\` reduces write blocking but has operational requirements and may leave invalid indexes on failure. Measure write amplification and storage cost.

## 8. Production incident simulations
1. Large SELECT consumes application memory due to eager \`fetchall\`.
2. Named cursor holds a transaction open and delays VACUUM.
3. COPY bulk load causes WAL/replication lag.
4. Misestimated cardinality selects a poor join plan.
5. Missing index causes excessive heap reads.
6. Index-only scan performs heap fetches due to visibility.
7. Sort spills to disk.
8. Connection timeout during database failover.
9. Statement timeout cancels a slow query.
10. Lock timeout blocks ingestion.
11. COPY fails on invalid row; transaction rolls back.
12. Duplicate batch replay creates duplicate rows without idempotency.
13. Pool exhaustion under parallel exporters.
14. Autovacuum competes with ingestion I/O.
15. Huge OFFSET pagination degrades over time.
16. Long transaction bloats a high-churn table.
17. Read replica lag increases during batch loads.
18. Disk full during COPY or temp-file spill.
19. Stale statistics cause row estimate errors.
20. Query text logging leaks sensitive parameters.

## 9. Troubleshooting matrix
| Signal | Hypothesis | Safe first action |
|---|---|---|
| Slow scan, many shared reads | Missing index/low selectivity | EXPLAIN, stats and index review |
| Large temp read/write | Sort/hash spill | Inspect plan, cardinality, work_mem budget |
| Long \`xact_start\` | Open named cursor/transaction | Close cursor, shorten batch |
| WAL/replication lag surge | COPY or large commit | Reduce batch size, throttle ingest |
| SQLSTATE 57014 | Statement timeout/cancel | Investigate query plan and approved SLO |
| SQLSTATE 55P03 | Lock timeout | Inspect blockers and lock order |
| High RSS | Eager result materialization | Stream with named cursor |
| Slow large OFFSET | Deep pagination | Keyset pagination |
| Unexpected seq scan | Planner statistics/cost | Analyze stats and actual selectivity |

## 10. Production runbooks
**Slow query:** capture sanitized query ID, \`EXPLAIN (ANALYZE, BUFFERS)\` on an approved safe query, inspect stats, index selectivity and I/O; change only after baseline comparison.

**Export memory pressure:** replace eager materialization with bounded server-side streaming, monitor cursor transaction age, reduce batch size and consider keyset checkpoints.

**COPY-induced lag:** throttle ingest, shorten commits, monitor WAL/checkpoint/replica lag and verify downstream freshness before resuming full rate.

**Timeout incident:** distinguish connect, pool, lock, statement and job deadline; roll back incomplete work and reconcile ambiguous commits.

**Rollback:** revert approved query/index/batch settings, rerun disposable tests and canaries, verify latency, memory and replication SLOs.

## 11. Lab and assessment
[Chapter 078 — Query Performance, COPY and Streaming SRE/DBRE Lab](labs/078-postgresql-query-performance-batching-streaming-sre-dbre-lab.md) includes complete psycopg 3 source, an opt-in disposable PostgreSQL test suite, EXPLAIN plan checks, named cursor streaming, executemany, COPY, timeout and rollback tests, incident drills and a 100-point assessment.

**Next proposed:** Chapter 079 — Python Database Migrations, Schema Evolution and Operational Automation.
