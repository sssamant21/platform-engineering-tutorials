# Chapter 062 — PostgreSQL, RDS and Aurora Observability, Query Performance, Replication and Storage

**Part 13 — Database and Data Platform Observability**  
**Audience:** PostgreSQL DBRE, SRE, cloud database and platform teams.  
**Prerequisites:** Chapter 061; SQL, Prometheus, Grafana and PostgreSQL permissions.

## Objectives and theory

Build a production monitoring model for self-managed PostgreSQL, Amazon RDS for PostgreSQL and Aurora PostgreSQL. Correlate **application RED metrics** with query plans, wait events, locks, connections, WAL, replication, checkpoints, autovacuum and underlying storage. Separate database service symptoms from upstream application pressure and cloud infrastructure limits.

## Architecture

```text
API / worker / CDC -> PostgreSQL writer -> replicas / Aurora readers
      |                    |                      |
 app RED + traces      pg_stat views        replay lag / reader load
      |                    |                      |
      +---------------- postgres exporter --------+
                              |
                  Prometheus / CloudWatch
                              |
              Grafana / Alertmanager / SLOs
                              |
             DBRE incident runbooks and recovery
```

RDS and Aurora are managed services: engine views, cloud metrics, storage behavior, replicas and supported telemetry differ from self-managed PostgreSQL. Aurora cluster storage and reader topology should not be modeled as a conventional single-instance block disk. Query Insights/Performance Insights feature availability depends on account, engine, region and service lifecycle; verify current supported monitoring capabilities.

## Signal catalog

| Layer | Signals | Operational meaning |
|---|---|---|
| User | transaction success, p95/p99 request latency | impact and SLO |
| Query | pg_stat_statements calls, total_exec_time, mean_exec_time | aggregate query workload, not p95 |
| Waits | pg_stat_activity wait_event_type/event | locks, IO, client and LWLock |
| Connections | active, idle, idle in transaction, limits | pool pressure |
| Replication | pg_stat_replication, pg_stat_wal_receiver, replay timestamps | availability and freshness |
| WAL | LSN growth, archiving, replication slot retention | durability and disk pressure |
| Maintenance | pg_stat_user_tables, autovacuum, vacuum progress | dead tuples and bloat risk |
| Storage | disk queue, latency, IOPS, throughput, free space | saturation |
| Cloud | CloudWatch RDS/Aurora, DB load | managed-service context |

**Important:** `pg_stat_statements.mean_exec_time` is an average, not p95. Build percentiles from appropriately instrumented per-query/application histograms; avoid high-cardinality SQL text metric labels.

## Read-only SQL discovery

Run with approved monitoring permissions and a query timeout. Some views/extensions require `pg_read_all_stats` or other explicitly granted roles.

```sql
SHOW server_version;
SELECT now(), pg_is_in_recovery();
SELECT state, wait_event_type, wait_event, count(*)
FROM pg_stat_activity GROUP BY 1,2,3 ORDER BY 4 DESC;
SELECT datname, numbackends, xact_commit, xact_rollback,
       deadlocks, temp_bytes, blks_read, blks_hit
FROM pg_stat_database;
SELECT pid, state, wait_event_type, wait_event,
       now()-xact_start AS transaction_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 20;
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
SELECT * FROM pg_stat_replication;
SELECT slot_name, slot_type, active, restart_lsn
FROM pg_replication_slots;
```

On a standby, use `pg_last_xact_replay_timestamp()` and `pg_stat_wal_receiver` with care: replay timestamp lag can be misleading during idle periods. A primary with no replicas returns no rows in `pg_stat_replication`.

### Query performance

```sql
-- Requires pg_stat_statements preloaded/installed and suitable permissions.
SELECT queryid, calls, round(total_exec_time::numeric,2) AS total_ms,
       round(mean_exec_time::numeric,2) AS mean_ms, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 20;
-- Explain only safe read-only SELECT statements in staging.
EXPLAIN (FORMAT JSON) SELECT 1;
```

Never run `EXPLAIN ANALYZE` on unreviewed write statements; it executes the query.

## Cloud and Prometheus checks

```bash
aws rds describe-db-instances --query 'DBInstances[].{ID:DBInstanceIdentifier,Engine:Engine,Status:DBInstanceStatus}'
aws rds describe-db-clusters --query 'DBClusters[].{ID:DBClusterIdentifier,Engine:Engine,Status:Status}'
kubectl get pods -A -l app.kubernetes.io/name=prometheus-postgres-exporter
```

These commands require authenticated AWS/Kubernetes contexts and may need permissions. Check RDS/Aurora CloudWatch metrics such as CPUUtilization, DatabaseConnections, ReadLatency, WriteLatency and FreeStorageSpace **where supported**; Aurora metrics and storage semantics differ.

```promql
pg_up
```

```promql
sum by (instance,datname) (rate(pg_stat_database_xact_commit[5m]))
```

```promql
rate(pg_stat_database_deadlocks[5m])
```

Metric names/labels vary by exporter version. Confirm the live `/metrics` endpoint before adopting queries.

## SRE/DBRE incident simulation

An Aurora PostgreSQL application experiences p95 latency spikes, connection pool exhaustion and rising replica delay. Cloud disk write latency also increases. Distinguish lock contention, query-plan regression, client retries, replica read pressure and storage saturation using independent application SLOs, `pg_stat_activity`, `pg_stat_statements`, CloudWatch and replay lag. Do not change instance class, kill sessions or reindex without an approved change and rollback.

## Executable offline acceptance gate

This synthetic manifest validates review attestations and numeric thresholds; it **does not** query PostgreSQL, RDS, Aurora or CloudWatch.

### healthy.json

```json
{
  "owner": "postgres-dbre",
  "environment": "staging",
  "platform": "aurora-postgresql",
  "change_id": "OBS-062",
  "query_p95_ms": 95,
  "max_query_p95_ms": 200,
  "replication_lag_seconds": 3,
  "max_replication_lag_seconds": 15,
  "connection_utilization_percent": 65,
  "max_connection_utilization_percent": 85,
  "storage_latency_ms": 8,
  "max_storage_latency_ms": 20,
  "production_delete": false,
  "pg_stat_statements_reviewed": true,
  "pg_stat_activity_reviewed": true,
  "wait_events_reviewed": true,
  "lock_monitoring_reviewed": true,
  "connections_reviewed": true,
  "replication_reviewed": true,
  "wal_reviewed": true,
  "checkpoints_reviewed": true,
  "vacuum_reviewed": true,
  "storage_iops_reviewed": true,
  "rds_cloudwatch_reviewed": true,
  "aurora_performance_insights_reviewed": true,
  "exporter_permissions_reviewed": true,
  "cardinality_reviewed": true,
  "backup_restore_reviewed": true,
  "alert_routing_reviewed": true,
  "rollback_tested": true
}
```

### postgres_gate.py

```python
"""Offline PostgreSQL/RDS/Aurora observability review; no database access."""
import json,sys
from pathlib import Path
FLAGS=["pg_stat_statements_reviewed","pg_stat_activity_reviewed","wait_events_reviewed","lock_monitoring_reviewed","connections_reviewed","replication_reviewed","wal_reviewed","checkpoints_reviewed","vacuum_reviewed","storage_iops_reviewed","rds_cloudwatch_reviewed","aurora_performance_insights_reviewed","exporter_permissions_reviewed","cardinality_reviewed","backup_restore_reviewed","alert_routing_reviewed","rollback_tested"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be an object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("platform") not in ("postgresql","rds-postgresql","aurora-postgresql"):e.append("unsupported platform")
 for k in FLAGS:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("query_p95_ms","max_query_p95_ms","replication_lag_seconds","max_replication_lag_seconds","storage_latency_ms","max_storage_latency_ms"):
  if type(p.get(k)) not in (int,float) or p[k]<0:e.append("invalid "+k)
 for k in ("connection_utilization_percent","max_connection_utilization_percent"):
  if type(p.get(k)) not in (int,float) or not 0<=p[k]<=100:e.append("invalid "+k)
 for a,b in (("query_p95_ms","max_query_p95_ms"),("replication_lag_seconds","max_replication_lag_seconds"),("connection_utilization_percent","max_connection_utilization_percent"),("storage_latency_ms","max_storage_latency_ms")):
  x,y=p.get(a),p.get(b)
  if type(x) in (int,float) and type(y) in (int,float) and x>y:e.append("threshold missed "+a)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_postgres_gate.py

```python
import copy,json,unittest
from pathlib import Path
from postgres_gate import validate
class PostgreSQLObservabilityTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_platform(self):
  p=copy.deepcopy(self.p);p["platform"]="mysql";self.assertTrue(validate(p))
 def test_04_change_id(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_05_pg_stat_statements_reviewed(self):
  p=copy.deepcopy(self.p);p["pg_stat_statements_reviewed"]=False;self.assertTrue(validate(p))
 def test_06_pg_stat_activity_reviewed(self):
  p=copy.deepcopy(self.p);p["pg_stat_activity_reviewed"]=False;self.assertTrue(validate(p))
 def test_07_wait_events_reviewed(self):
  p=copy.deepcopy(self.p);p["wait_events_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_lock_monitoring_reviewed(self):
  p=copy.deepcopy(self.p);p["lock_monitoring_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_connections_reviewed(self):
  p=copy.deepcopy(self.p);p["connections_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_replication_reviewed(self):
  p=copy.deepcopy(self.p);p["replication_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_wal_reviewed(self):
  p=copy.deepcopy(self.p);p["wal_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_checkpoints_reviewed(self):
  p=copy.deepcopy(self.p);p["checkpoints_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_vacuum_reviewed(self):
  p=copy.deepcopy(self.p);p["vacuum_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_storage_iops_reviewed(self):
  p=copy.deepcopy(self.p);p["storage_iops_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_rds_cloudwatch_reviewed(self):
  p=copy.deepcopy(self.p);p["rds_cloudwatch_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_aurora_performance_insights_reviewed(self):
  p=copy.deepcopy(self.p);p["aurora_performance_insights_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_exporter_permissions_reviewed(self):
  p=copy.deepcopy(self.p);p["exporter_permissions_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_backup_restore_reviewed(self):
  p=copy.deepcopy(self.p);p["backup_restore_reviewed"]=False;self.assertTrue(validate(p))
 def test_20_alert_routing_reviewed(self):
  p=copy.deepcopy(self.p);p["alert_routing_reviewed"]=False;self.assertTrue(validate(p))
 def test_21_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_22_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_ms"]=300;self.assertTrue(validate(p))
 def test_23_max_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["max_query_p95_ms"]=-1;self.assertTrue(validate(p))
 def test_24_replication_lag_seconds(self):
  p=copy.deepcopy(self.p);p["replication_lag_seconds"]=30;self.assertTrue(validate(p))
 def test_25_max_replication_lag_seconds(self):
  p=copy.deepcopy(self.p);p["max_replication_lag_seconds"]=-1;self.assertTrue(validate(p))
 def test_26_connection_utilization_percent(self):
  p=copy.deepcopy(self.p);p["connection_utilization_percent"]=99;self.assertTrue(validate(p))
 def test_27_max_connection_utilization_percent(self):
  p=copy.deepcopy(self.p);p["max_connection_utilization_percent"]=101;self.assertTrue(validate(p))
 def test_28_storage_latency_ms(self):
  p=copy.deepcopy(self.p);p["storage_latency_ms"]=30;self.assertTrue(validate(p))
 def test_29_max_storage_latency_ms(self):
  p=copy.deepcopy(self.p);p["max_storage_latency_ms"]=-1;self.assertTrue(validate(p))
 def test_30_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter062 && cd chapter062
# Save blocks as healthy.json, postgres_gate.py and test_postgres_gate.py
python3 postgres_gate.py healthy.json
python3 -m unittest -v test_postgres_gate.py
```

Expected PASS and **32 authored Python tests**.

## 24 hands-on exercises

1. Identify PostgreSQL version and role.
2. Inspect pg_stat_activity.
3. Aggregate wait events.
4. Review blocking lock chains.
5. Review connection utilization.
6. Review pg_stat_database.
7. Review pg_stat_statements.
8. Compare query total vs mean time.
9. Review EXPLAIN (FORMAT JSON).
10. Check index scan vs sequential scan.
11. Inspect autovacuum activity.
12. Inspect dead tuples.
13. Inspect checkpoint counters.
14. Inspect WAL generation.
15. Review replication sender status.
16. Review replica replay delay.
17. Review replication slots and retained WAL.
18. Review RDS CloudWatch metrics.
19. Review Aurora reader lag.
20. Review Performance Insights or Database Insights.
21. Correlate disk IOPS and query p95.
22. Build Grafana DBRE dashboard.
23. Simulate blocked query in staging.
24. Validate recovery and rollback.

## 24 production failure scenarios

1. **Connections exhausted:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
2. **Idle-in-transaction pileup:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
3. **Lock contention:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
4. **Deadlock spike:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
5. **Long-running query:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
6. **Missing index:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
7. **Plan regression:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
8. **pg_stat_statements not enabled:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
9. **Autovacuum falling behind:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
10. **Dead tuple bloat:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
11. **Checkpoint pressure:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
12. **WAL disk growth:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
13. **Replication slot retains WAL:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
14. **Replica replay lag:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
15. **Aurora reader lag:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
16. **RDS storage latency:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
17. **IOPS saturation:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
18. **Burst balance depletion where applicable:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
19. **CPU saturation:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
20. **Memory pressure:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
21. **Exporter permissions denied:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
22. **CloudWatch data delayed:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
23. **Alert storm:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.
24. **Rollback incomplete:** correlate app impact, engine statistics, managed-service metrics, change history and rollback.

## Eight production runbooks

1. **Slow query:** compare p95 and pg_stat_statements, wait events, EXPLAIN plans and storage latency.
2. **Lock storm:** identify blockers in pg_locks/pg_stat_activity and follow approved termination escalation.
3. **Connection exhaustion:** inspect pools, idle transactions, max_connections and safe client backoff.
4. **Replication lag:** inspect pg_stat_replication, replay positions, network, WAL and reader load.
5. **WAL/storage growth:** inspect replication slots, archive failures, checkpoint and cloud disk capacity.
6. **Autovacuum/bloat:** inspect dead tuples, vacuum progress and safe scheduling before maintenance.
7. **Managed-service blind spot:** compare CloudWatch, Aurora telemetry, PostgreSQL views and exporter scrape.
8. **Recovery:** verify application SLO, replicas, backups, alert clear and documented rollback.

## 100-point assessment

| Area | Points |
|---|---:|
| PostgreSQL monitoring architecture | 20 |
| Query, wait and lock diagnosis | 20 |
| Replication, WAL, vacuum and storage | 20 |
| Cloud metrics, security and offline tests | 20 |
| Incident simulation and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires witnessed metrics, access reviews, backup restore verification and safe incident drills.

**Companion:** [Chapter 062 hands-on lab](labs/062-postgresql-rds-aurora-observability-query-performance-replication-storage-lab.md).

**Next:** Chapter 063 — MongoDB, Redis and Elasticsearch/OpenSearch Observability, Performance and Reliability.
