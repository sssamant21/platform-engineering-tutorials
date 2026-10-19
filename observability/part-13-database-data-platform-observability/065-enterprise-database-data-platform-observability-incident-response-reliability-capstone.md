# Chapter 065 — Enterprise Database and Data Platform Observability, Incident Response and Reliability Capstone

**Part 13 final capstone — Database and Data Platform Observability**  
**Audience:** Enterprise SRE/DBRE, data platform on-call and incident commanders.  
**Prerequisites:** Chapters 061–064.

## Mission

Demonstrate end-to-end, production-oriented observability for PostgreSQL/RDS/Aurora, MongoDB, Redis, Elasticsearch/OpenSearch, Kafka/MSK and Snowflake. Establish independent user-impact SLIs, correlate metrics/logs/traces, preserve security boundaries, and rehearse incident response and recovery in approved staging environments.

## Reference architecture

```text
API RED metrics -> PostgreSQL / MongoDB / Redis / Elasticsearch / OpenSearch
                                   |
                         CDC -> Kafka/MSK -> Snowflake
                                   |
                    Exporters / CloudWatch / OTel / logs
                                   |
                       Prometheus / Loki / Grafana
                                   |
                      SLO burn / Alertmanager / DBRE
                                   |
                  incident response / restore / rollback
```

## Platform acceptance matrix

### 1. PostgreSQL waits, WAL, replication, vacuum and storage

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 2. MongoDB WiredTiger cache, oplog, replication and queries

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 3. Redis command latency, evictions, hot keys and persistence

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 4. Elasticsearch/OpenSearch shards, search rejections, JVM and IOPS

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 5. Kafka/MSK ISR, consumer lag, Connect and CDC

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 6. Snowflake query queues, warehouse credits and freshness

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 7. Application RED metrics, SLO burn and incident command

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.

### 8. Backup restore, measured RPO/RTO, tenant isolation and rollback

Record source of truth, service owner, monitored metrics, collection privileges, alert threshold, dashboard link, user-impact correlation and recovery evidence. Prefer rate-normalized counters, bounded metric cardinality, redacted logs and independent application SLOs. Capture timestamped staging evidence and record managed-service visibility limits.


## Incident simulation

A patient-search API suffers p95 latency regression while Elasticsearch search rejections and disk IOPS rise. MongoDB cache evictions increase; Redis hot keys saturate CPU; Kafka Connect stops advancing; Snowflake warehouse queues and target freshness deteriorate. Establish a common UTC timeline, distinguish causal failures from coincidental saturation, inspect source and target watermarks, and coordinate reversible mitigations with incident command. Never infer seconds of freshness from Kafka lag measured in records alone.

## Security and operational safety

Use read-only monitoring identities and cloud workload roles. Do not expose SQL text, MongoDB documents, Redis command arguments, PHI or credentials. Require explicit authorization for any production failover, session termination, reindex, offset reset or destructive operation. Recovery acceptance requires witnessed backup/restore, measured RPO/RTO, application SLO restoration and rollback.

## 24 executable staging exercises

1. Inventory business-critical data paths; capture commands, timestamps, source metrics, expected results and reviewer evidence.
2. Define application SLO; capture commands, timestamps, source metrics, expected results and reviewer evidence.
3. Review PostgreSQL locks; capture commands, timestamps, source metrics, expected results and reviewer evidence.
4. Review PostgreSQL replication; capture commands, timestamps, source metrics, expected results and reviewer evidence.
5. Review MongoDB cache; capture commands, timestamps, source metrics, expected results and reviewer evidence.
6. Review MongoDB oplog; capture commands, timestamps, source metrics, expected results and reviewer evidence.
7. Review Redis p99; capture commands, timestamps, source metrics, expected results and reviewer evidence.
8. Review Redis memory; capture commands, timestamps, source metrics, expected results and reviewer evidence.
9. Review Elasticsearch shards; capture commands, timestamps, source metrics, expected results and reviewer evidence.
10. Review OpenSearch rejections; capture commands, timestamps, source metrics, expected results and reviewer evidence.
11. Review storage IOPS; capture commands, timestamps, source metrics, expected results and reviewer evidence.
12. Review Kafka ISR; capture commands, timestamps, source metrics, expected results and reviewer evidence.
13. Review consumer lag; capture commands, timestamps, source metrics, expected results and reviewer evidence.
14. Review Connect task health; capture commands, timestamps, source metrics, expected results and reviewer evidence.
15. Review Snowflake queue; capture commands, timestamps, source metrics, expected results and reviewer evidence.
16. Review Snowflake credits; capture commands, timestamps, source metrics, expected results and reviewer evidence.
17. Measure CDC freshness; capture commands, timestamps, source metrics, expected results and reviewer evidence.
18. Correlate logs and traces; capture commands, timestamps, source metrics, expected results and reviewer evidence.
19. Simulate exporter outage; capture commands, timestamps, source metrics, expected results and reviewer evidence.
20. Test alert routing; capture commands, timestamps, source metrics, expected results and reviewer evidence.
21. Review tenant privacy; capture commands, timestamps, source metrics, expected results and reviewer evidence.
22. Rehearse backup restore; capture commands, timestamps, source metrics, expected results and reviewer evidence.
23. Measure RPO/RTO; capture commands, timestamps, source metrics, expected results and reviewer evidence.
24. Execute rollback; capture commands, timestamps, source metrics, expected results and reviewer evidence.

## 24 failure simulations

1. **PostgreSQL lock storm:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
2. **PostgreSQL replication lag:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
3. **MongoDB eviction:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
4. **MongoDB election:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
5. **Redis hot key:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
6. **Redis evictions:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
7. **Elasticsearch oversharding:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
8. **OpenSearch heap pressure:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
9. **Merge throttling:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
10. **Disk IOPS bottleneck:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
11. **Kafka ISR shrink:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
12. **Consumer backlog:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
13. **Connect failure:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
14. **Schema drift:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
15. **Snowflake queueing:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
16. **Query regression:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
17. **Credit spike:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
18. **Data freshness breach:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
19. **Prometheus scrape outage:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
20. **Loki log gap:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
21. **OTel trace loss:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
22. **Alert storm:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
23. **Restore failure:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.
24. **Rollback failure:** capture independent impact, platform evidence, mitigation owner, rollback and post-incident validation.

## Eight production runbooks

1. **Incident command:** declare severity from user-impact SLI, establish roles and timeline.
2. **PostgreSQL/MongoDB:** inspect locks, query plans, WAL/oplog, cache, replication and storage.
3. **Redis:** inspect hot keys, command p99, evictions, blocked clients and persistence.
4. **Elasticsearch/OpenSearch:** inspect slow logs, shard sizes, rejections, GC, merge throttle and IOPS.
5. **Kafka/MSK:** inspect broker health, ISR, consumer offsets, Connect tasks and DLQ.
6. **Snowflake:** inspect query/warehouse queues, credits, tasks and source-to-target freshness.
7. **Disaster recovery:** verify backup age, restore integrity, data consistency and measured RPO/RTO.
8. **Rollback and postmortem:** verify independent SLO recovery, close alerts and assign preventive actions.

## Offline acceptance example

The following script checks a **synthetic** staging review and does not connect to real services. Save as `capstone_gate.py`.

```python
import json,sys
from pathlib import Path
REQUIRED=["postgresql","mongodb","redis","elasticsearch","opensearch","kafka_msk","snowflake","application_slo","backup_restore","rollback"]
def validate(d):
    if not isinstance(d,dict):return ["expected object"]
    errors=[]
    if d.get("environment") not in ("lab","staging"):errors.append("unsafe environment")
    if not d.get("owner"):errors.append("missing owner")
    for k in REQUIRED:
        if d.get("checks",{}).get(k) is not True:errors.append("unverified "+k)
    for metric,budget in [("rpo_minutes","rpo_budget_minutes"),("rto_minutes","rto_budget_minutes"),("freshness_seconds","freshness_budget_seconds")]:
        a,b=d.get(metric),d.get(budget)
        if type(a) not in (int,float) or a<0 or type(b) not in (int,float) or b<0:errors.append("invalid "+metric)
        elif a>b:errors.append("breach "+metric)
    if d.get("destructive_change") is not False:errors.append("unsafe action")
    return errors
if __name__=="__main__":
    errors=validate(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
    sys.exit(bool(errors))
```

Save as `healthy.json`:

```json
{"owner":"dbre","environment":"staging","checks":{"postgresql":true,"mongodb":true,"redis":true,"elasticsearch":true,"opensearch":true,"kafka_msk":true,"snowflake":true,"application_slo":true,"backup_restore":true,"rollback":true},"rpo_minutes":10,"rpo_budget_minutes":15,"rto_minutes":25,"rto_budget_minutes":30,"freshness_seconds":30,"freshness_budget_seconds":120,"destructive_change":false}
```

Save as `test_capstone_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from capstone_gate import validate
class AcceptanceTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(Path("healthy.json").read_text())
    def test_healthy(self):self.assertEqual(validate(self.p),[])
    def test_not_object(self):self.assertTrue(validate(None))
    def test_unsafe_environment(self):
        p=copy.deepcopy(self.p);p["environment"]="production";self.assertTrue(validate(p))
    def test_missing_review(self):
        p=copy.deepcopy(self.p);p["checks"]["mongodb"]=False;self.assertTrue(validate(p))
    def test_rpo_breach(self):
        p=copy.deepcopy(self.p);p["rpo_minutes"]=50;self.assertTrue(validate(p))
    def test_rto_breach(self):
        p=copy.deepcopy(self.p);p["rto_minutes"]=90;self.assertTrue(validate(p))
    def test_freshness_breach(self):
        p=copy.deepcopy(self.p);p["freshness_seconds"]=200;self.assertTrue(validate(p))
    def test_unsafe_change(self):
        p=copy.deepcopy(self.p);p["destructive_change"]=True;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

```bash
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Eight authored tests; execution not claimed.

## 100-point final assessment

| Domain | Points |
|---|---:|
| Cross-platform architecture and SLOs | 20 |
| Database and search troubleshooting | 20 |
| Kafka/MSK and Snowflake freshness | 20 |
| Security, tests and alerting | 20 |
| Incident command, recovery and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100, subject to live staging validation.

**Companion:** [Chapter 065 capstone lab](labs/065-enterprise-database-data-platform-observability-incident-response-reliability-capstone-lab.md).

**Part 13 complete. Next:** Chapter 066 — Application Performance Monitoring Architecture, Instrumentation and Golden Signals (Part 14).
