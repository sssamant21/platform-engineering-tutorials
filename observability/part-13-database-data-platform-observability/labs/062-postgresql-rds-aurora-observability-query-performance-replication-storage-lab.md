# Chapter 062 — PostgreSQL, RDS and Aurora Observability Lab

**Part 13 — Database and Data Platform Observability**

## Offline test lab

From [Chapter 062](../062-postgresql-rds-aurora-observability-query-performance-replication-storage.md), save the three fenced files as `healthy.json`, `postgres_gate.py` and `test_postgres_gate.py`.

```bash
python3 postgres_gate.py healthy.json
python3 -m unittest -v test_postgres_gate.py
```

Expected result: PASS and 32 authored tests. These are synthetic offline checks, not live database validation.

## Staging exercises

1. Identify PostgreSQL version and whether the node is a writer or reader.
2. Review `pg_stat_activity` for connection states and wait events.
3. Review `pg_stat_database` for transaction rates and deadlocks.
4. Inspect `pg_stat_statements` where enabled, distinguishing mean execution time from p95.
5. Run read-only EXPLAIN on an approved sample SELECT.
6. Review lock contention and long transactions.
7. Inspect autovacuum, dead tuples and checkpoint activity.
8. Inspect WAL, replication slots and replica replay lag.
9. Compare exporter metrics with managed RDS/Aurora CloudWatch monitoring.
10. Verify query, connection and storage dashboards.
11. Conduct an approved, bounded staging lock or connection-pressure simulation.
12. Validate recovery and document change control and rollback.

## Failure injection review

Exercise invalid platform, missing owner, absent query/wait/lock/replication/WAL reviews, query latency breach, replication lag breach, connection saturation and missing rollback evidence through the offline gate. Never perform unapproved destructive operations on production databases.

## Evidence worksheet

```text
UTC / operator / change:
Engine and instance role:
Application latency and error rate:
Wait events and locks:
Query plans and pg_stat_statements:
Connections and pool state:
WAL / replication / vacuum:
Cloud metrics and storage latency:
Alerts and dashboard links:
Recovery / rollback / reviewer:
Offline gate and 32 test outcomes:
```

Production acceptance requires real telemetry and witnessed operational checks.
