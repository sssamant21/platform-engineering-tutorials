# Chapter 061 — Database and Data Platform Observability Architecture, Metrics and Reliability Signals

**Part 13 — Database and Data Platform Observability**  
**Audience:** DBRE, SRE, data platform engineers and incident responders.  
**Prerequisites:** Prometheus, Grafana, OpenTelemetry, database fundamentals and Chapters 001–060.

## Learning objectives

Design end-to-end observability for PostgreSQL, MongoDB, Elasticsearch/OpenSearch, Redis, Kafka/MSK and Snowflake. Define user-impact SLIs, platform metrics, replication/freshness, saturation, recovery signals, alert routing and secure multi-tenant dashboards.

## Architecture

```text
Applications -> API RED / traces / logs -> Grafana
      |
      +-> PostgreSQL / MongoDB / Elasticsearch / OpenSearch / Redis
      +-> Kafka / MSK -> CDC / Snowflake
                   |
       exporters / native metrics / audit logs
                   |
          Prometheus / OTel Collector
                   |
     recording rules -> Grafana -> Alertmanager
                   |
       SLO burn / DBRE runbooks / incident response
```

For managed services, provider APIs may be the authoritative source for metrics not exposed by SQL or native exporters. Do not assume identical signals or units across platforms.

## Reliability signal taxonomy

| Signal | Questions | Examples |
|---|---|---|
| Availability | Can clients successfully read/write? | successful transactions, healthy endpoints |
| Latency | How long do requests and queries take? | p95/p99, lock wait, query queue time |
| Throughput | What work is performed? | queries/sec, operations/sec, records/sec |
| Errors | What work fails? | timeouts, rejects, failed commits |
| Saturation | Which resource is limiting? | CPU, heap, disk IOPS, connections |
| Replication | Is redundancy healthy? | WAL replay delay, oplog lag, ISR |
| Freshness | Is downstream data current? | CDC lag, ingestion watermark |
| Recovery | Can data be restored? | backup age, tested RPO/RTO |

**Caution:** replication lag and data freshness are different. Kafka consumer lag is often measured in records, while replica lag may be time or bytes; do not compare them as identical units.

## Platform instrumentation matrix

| Platform | Critical DBRE metrics | Collection pattern |
|---|---|---|
| PostgreSQL/RDS/Aurora | connections, locks, WAL, replication, checkpoints, IOPS, query p95 | pg_stat views, postgres exporter, CloudWatch |
| MongoDB | opcounters, WiredTiger cache/evictions, replication lag, locks, connections, disk | serverStatus, exporter, Atlas/Ops Manager |
| Elasticsearch/OpenSearch | search/index latency, rejections, heap/GC, shard size, merge throttle, disk | cluster/node APIs, exporters, cloud metrics |
| Redis | command latency, ops/sec, blocked clients, evictions, fragmentation, replication | INFO, latency monitoring, exporter |
| Kafka/MSK | consumer lag, ISR, under-replicated partitions, broker IO, request latency | JMX/exporter, CloudWatch |
| Snowflake | query queue/execution, warehouse load, credits, failures, data freshness | ACCOUNT_USAGE, INFORMATION_SCHEMA, query history |

Snowflake ACCOUNT_USAGE may have latency; use the appropriate live history views or other timely sources for incident response. Never put query text, PHI or credentials into high-cardinality metric labels.

## PromQL patterns

```promql
up{job=~".*(postgres|mongodb|redis|kafka|elasticsearch).*"}
```

```promql
sum by (cluster,instance) (rate(pg_stat_database_xact_commit[5m]))
```

```promql
rate(redis_commands_processed_total[5m])
```

Metric names vary by exporter and version. Verify deployed labels, scrape targets and permissions before adopting queries. Use application RED SLIs as independent user-impact evidence.

## Production incident simulation

A MongoDB-to-Kafka-to-Snowflake pipeline falls behind while Elasticsearch search latency rises. MongoDB WiredTiger eviction and disk latency increase, Kafka consumer lag grows, Snowflake warehouse queues expand and Elasticsearch thread-pool rejections rise. Determine independent causes and downstream effects rather than assuming a single shared root cause. Correlate timestamps, storage throughput, query profiles, consumer offsets and freshness watermarks; document safe mitigation and rollback.

## Executable offline architecture gate

This synthetic attestation checks declared review flags and numeric thresholds. It **does not** access production databases or verify actual telemetry.

### healthy.json

```json
{
  "owner": "dbre",
  "environment": "staging",
  "change_id": "OBS-061",
  "platform": "postgresql",
  "availability_percent": 99,
  "minimum_availability_percent": 98,
  "p95_query_latency_ms": 80,
  "max_p95_query_latency_ms": 150,
  "replication_lag_seconds": 2,
  "max_replication_lag_seconds": 10,
  "data_freshness_seconds": 30,
  "max_data_freshness_seconds": 120,
  "production_delete": false,
  "availability_reviewed": true,
  "latency_reviewed": true,
  "throughput_reviewed": true,
  "error_rate_reviewed": true,
  "saturation_reviewed": true,
  "replication_lag_reviewed": true,
  "storage_capacity_reviewed": true,
  "backup_restore_reviewed": true,
  "data_freshness_reviewed": true,
  "query_performance_reviewed": true,
  "security_reviewed": true,
  "cardinality_reviewed": true,
  "alert_routing_reviewed": true,
  "runbook_reviewed": true,
  "rollback_tested": true
}
```

### dbre_signals_gate.py

```python
"""Offline DBRE observability architecture review; no live database access."""
import json,sys
from pathlib import Path
PLATFORMS=["postgresql","mongodb","elasticsearch","opensearch","redis","kafka","snowflake"]
CHECKS=["availability_reviewed","latency_reviewed","throughput_reviewed","error_rate_reviewed","saturation_reviewed","replication_lag_reviewed","storage_capacity_reviewed","backup_restore_reviewed","data_freshness_reviewed","query_performance_reviewed","security_reviewed","cardinality_reviewed","alert_routing_reviewed","runbook_reviewed","rollback_tested"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("platform") not in PLATFORMS:e.append("unsupported platform")
 for k in CHECKS:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("availability_percent","minimum_availability_percent"):
  if type(p.get(k)) is not int or not 0<=p[k]<=100:e.append("invalid "+k)
 for k in ("p95_query_latency_ms","max_p95_query_latency_ms","replication_lag_seconds","max_replication_lag_seconds","data_freshness_seconds","max_data_freshness_seconds"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 for a,b,kind in (("availability_percent","minimum_availability_percent","min"),("p95_query_latency_ms","max_p95_query_latency_ms","max"),("replication_lag_seconds","max_replication_lag_seconds","max"),("data_freshness_seconds","max_data_freshness_seconds","max")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((kind=="min" and x<y) or (kind=="max" and x>y)):e.append("threshold missed "+a)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_dbre_signals_gate.py

```python
import copy,json,unittest
from pathlib import Path
from dbre_signals_gate import validate
class DBRESignalsTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_change_id(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_04_platform(self):
  p=copy.deepcopy(self.p);p["platform"]="unknown";self.assertTrue(validate(p))
 def test_05_availability_reviewed(self):
  p=copy.deepcopy(self.p);p["availability_reviewed"]=False;self.assertTrue(validate(p))
 def test_06_latency_reviewed(self):
  p=copy.deepcopy(self.p);p["latency_reviewed"]=False;self.assertTrue(validate(p))
 def test_07_throughput_reviewed(self):
  p=copy.deepcopy(self.p);p["throughput_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_error_rate_reviewed(self):
  p=copy.deepcopy(self.p);p["error_rate_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_saturation_reviewed(self):
  p=copy.deepcopy(self.p);p["saturation_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_replication_lag_reviewed(self):
  p=copy.deepcopy(self.p);p["replication_lag_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_storage_capacity_reviewed(self):
  p=copy.deepcopy(self.p);p["storage_capacity_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_backup_restore_reviewed(self):
  p=copy.deepcopy(self.p);p["backup_restore_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_data_freshness_reviewed(self):
  p=copy.deepcopy(self.p);p["data_freshness_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_query_performance_reviewed(self):
  p=copy.deepcopy(self.p);p["query_performance_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_security_reviewed(self):
  p=copy.deepcopy(self.p);p["security_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_alert_routing_reviewed(self):
  p=copy.deepcopy(self.p);p["alert_routing_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_runbook_reviewed(self):
  p=copy.deepcopy(self.p);p["runbook_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_20_availability_percent(self):
  p=copy.deepcopy(self.p);p["availability_percent"]=50;self.assertTrue(validate(p))
 def test_21_minimum_availability_percent(self):
  p=copy.deepcopy(self.p);p["minimum_availability_percent"]=101;self.assertTrue(validate(p))
 def test_22_p95_query_latency_ms(self):
  p=copy.deepcopy(self.p);p["p95_query_latency_ms"]=200;self.assertTrue(validate(p))
 def test_23_max_p95_query_latency_ms(self):
  p=copy.deepcopy(self.p);p["max_p95_query_latency_ms"]=0;self.assertTrue(validate(p))
 def test_24_replication_lag_seconds(self):
  p=copy.deepcopy(self.p);p["replication_lag_seconds"]=30;self.assertTrue(validate(p))
 def test_25_max_replication_lag_seconds(self):
  p=copy.deepcopy(self.p);p["max_replication_lag_seconds"]=-1;self.assertTrue(validate(p))
 def test_26_data_freshness_seconds(self):
  p=copy.deepcopy(self.p);p["data_freshness_seconds"]=200;self.assertTrue(validate(p))
 def test_27_max_data_freshness_seconds(self):
  p=copy.deepcopy(self.p);p["max_data_freshness_seconds"]=-1;self.assertTrue(validate(p))
 def test_28_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter061 && cd chapter061
# Save blocks as healthy.json, dbre_signals_gate.py and test_dbre_signals_gate.py
python3 dbre_signals_gate.py healthy.json
python3 -m unittest -v test_dbre_signals_gate.py
```

Expected PASS and **30 authored Python tests**.

## 24 hands-on exercises

1. Map application-to-database dependencies.
2. Define availability SLI.
3. Define p95 query latency SLI.
4. Define throughput SLI.
5. Define error rate SLI.
6. Define storage saturation SLI.
7. Review PostgreSQL exporters.
8. Review MongoDB metrics.
9. Review Elasticsearch metrics.
10. Review OpenSearch metrics.
11. Review Redis metrics.
12. Review Kafka/MSK metrics.
13. Review Snowflake query history.
14. Review replication lag.
15. Review CDC freshness.
16. Review backup and restore metrics.
17. Design Grafana overview.
18. Design DBRE RED/USE dashboard.
19. Review high-cardinality labels.
20. Review secret handling.
21. Design alert routing.
22. Simulate replication lag.
23. Simulate storage saturation.
24. Document recovery evidence.

## 24 production failure scenarios

1. **PostgreSQL connections exhausted:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
2. **PostgreSQL replication lag:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
3. **MongoDB replication lag:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
4. **MongoDB WiredTiger cache pressure:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
5. **Elasticsearch thread-pool rejections:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
6. **Elasticsearch shard oversizing:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
7. **OpenSearch JVM heap pressure:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
8. **Redis eviction storm:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
9. **Redis command latency spike:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
10. **Kafka consumer lag:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
11. **Kafka under-replicated partitions:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
12. **MSK broker storage pressure:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
13. **Snowflake warehouse queueing:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
14. **Snowflake credit spike:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
15. **CDC pipeline freshness breach:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
16. **Database storage IOPS saturation:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
17. **Disk full:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
18. **Backup freshness unknown:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
19. **Restore verification missing:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
20. **Exporter down:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
21. **Metrics label explosion:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
22. **TLS credential expired:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
23. **Alert fatigue:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.
24. **Rollback failure:** correlate independent SLIs, platform metrics, logs, query evidence and safe rollback.

## Eight production runbooks

1. **Database latency:** correlate app p95, query plans, locks, connection pools and storage IOPS.
2. **Replication delay:** inspect replica health, WAL/oplog/broker offsets and downstream freshness.
3. **Storage saturation:** inspect disk latency, queue depth, free space and compaction/merge workload.
4. **Exporter outage:** verify authentication, target discovery, network, scrape and provider-native signals.
5. **Capacity pressure:** compare CPU, heap/cache, connections, shards/partitions and workload growth.
6. **Snowflake delay:** inspect warehouse queues, query history, load freshness and credit consumption.
7. **Security and cardinality:** rotate credentials safely, redact sensitive labels and bound dimensions.
8. **Recovery:** restore approved config, confirm independent SLIs, backups and rollback evidence.

## 100-point assessment

| Domain | Points |
|---|---:|
| DBRE architecture and signal taxonomy | 20 |
| Platform metrics and instrumentation | 20 |
| SLIs, replication, freshness and alerts | 20 |
| Offline tests, security and evidence | 20 |
| Incident diagnosis and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Production acceptance requires observed exporter/provider data, access reviews, restore tests and witnessed incident drills.

**Companion:** [Chapter 061 hands-on lab](labs/061-database-data-platform-observability-architecture-metrics-reliability-signals-lab.md).

**Next:** Chapter 062 — PostgreSQL, RDS and Aurora Observability, Query Performance, Replication and Storage.
