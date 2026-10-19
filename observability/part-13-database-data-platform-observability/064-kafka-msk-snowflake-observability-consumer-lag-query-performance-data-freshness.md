# Chapter 064 — Kafka/MSK and Snowflake Observability, Consumer Lag, Query Performance and Data Freshness

**Part 13 — Database and Data Platform Observability**  
**Audience:** Kafka/MSK SRE, DBRE and Snowflake data platform teams.  
**Prerequisites:** Chapters 061–063, Prometheus, Grafana and SQL.

## Learning outcomes

Build end-to-end telemetry across Kafka/MSK producers, brokers, consumer groups, Kafka Connect/CDC and Snowflake ingestion and query serving. Define distinct consumer lag, source heartbeat and downstream data freshness SLIs, diagnose bottlenecks and rehearse safe recovery.

## Architecture

```text
PostgreSQL / MongoDB CDC -> Kafka Connect -> Kafka/MSK brokers
                           |                   |
                     task state / DLQ      ISR / disk / lag
                           |                   |
                        consumers / stream processing
                           |
                  Snowflake raw -> transformed -> serving
                           |
                  task/pipe/query/warehouse history
                           |
              CloudWatch / Prometheus / Grafana / alerts
                           |
                source-to-visible-target freshness SLI
```

## Monitoring and operational theory

### 1. Kafka broker CPU, storage, network, request latency and partition health

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 2. ISR, under-replicated partitions and producer acks

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 3. Consumer group offsets, backlog, rebalances and throughput

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 4. Kafka Connect tasks, DLQ, CDC offsets and schema evolution

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 5. MSK CloudWatch monitoring, IAM, TLS and broker capacity

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 6. Snowflake query history, execution and queueing

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 7. Snowflake warehouse load, credit use and autosuspend

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 8. Snowflake task, pipe, load and CDC freshness

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 9. Independent source heartbeat and visible target watermark

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.

### 10. End-to-end alerting, security, SLOs and recovery

Collect read-only metrics and timestamps, record collection permissions and cardinality, compare independent user-facing SLIs and build a recovery decision tree. Kafka lag in **records** cannot be converted to freshness **seconds** without event-time and throughput evidence. Snowflake ACCOUNT_USAGE is delayed; use timely information-schema history when incident response requires it. Do not expose raw SQL, secrets or patient identifiers in metrics or tickets.


## Staging read-only examples

```bash
kafka-topics.sh --bootstrap-server BROKER:9092 --describe --topic TOPIC
kafka-consumer-groups.sh --bootstrap-server BROKER:9092 --describe --group GROUP
aws kafka describe-cluster-v2 --cluster-arn "$MSK_CLUSTER_ARN"
```

Supply approved TLS/SASL configuration as required.

```sql
SELECT QUERY_ID, WAREHOUSE_NAME, EXECUTION_STATUS,
       TOTAL_ELAPSED_TIME, EXECUTION_TIME, QUEUED_OVERLOAD_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
  DATEADD('hour',-1,CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP(), 100))
ORDER BY START_TIME DESC;
```

Confirm supported Snowflake function arguments and privileges for the target account. For warehouse load, inspect `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY` (with its ingestion delay) or an approved timely telemetry source.

## Reliability design

Define `freshness_seconds = observation_time - max(source_event_time visible in Snowflake)` with UTC normalization, bounded clock skew, late-event policy and a separate upstream source heartbeat. Track ISR and under-replicated partitions for durability, consumer offset lag for backlog, query queue/execution separately, and Snowflake credit use for cost. Alert on sustained SLO burn, not single noisy samples.

## Production incident simulation

A MongoDB CDC connector stalls while consumer lag rises and a Snowflake transformation warehouse begins queueing. MSK broker disk usage also grows. Investigate each dependency independently: connector task status, ISR, partition lag, source heartbeat, Snowflake task and query history. Restore through an approved change, avoid unreviewed offset resets, verify idempotency and record downstream freshness recovery.

## 24 hands-on exercises

1. inventory brokers.
2. review ISR.
3. review under-replicated partitions.
4. inspect broker disk.
5. inspect request latency.
6. inspect producer retries.
7. review consumer offsets.
8. compare records lag vs time.
9. inspect rebalances.
10. review connector status.
11. review DLQ.
12. review source watermark.
13. inspect Snowflake query history.
14. inspect execution vs queueing.
15. review warehouse load.
16. review credits.
17. review tasks.
18. review ingestion errors.
19. measure target freshness.
20. review independent source heartbeat.
21. configure SLO alerts.
22. simulate staging consumer stall.
23. validate idempotent replay.
24. capture rollback evidence.

## 24 production failure scenarios

1. **broker down:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
2. **ISR shrink:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
3. **under-replicated partitions:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
4. **producer retries:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
5. **network saturation:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
6. **disk pressure:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
7. **partition skew:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
8. **consumer lag:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
9. **rebalance storm:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
10. **poison message:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
11. **connector failed:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
12. **DLQ overflow:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
13. **schema drift:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
14. **CDC stopped:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
15. **source clock skew:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
16. **Snowflake queueing:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
17. **warehouse suspended:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
18. **long-running query:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
19. **failed task:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
20. **failed pipe:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
21. **credit spike:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
22. **data freshness breach:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
23. **metrics outage:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.
24. **unsafe offset reset:** collect broker, consumer, connector and Snowflake evidence, quantify freshness impact, assign an owner and validate recovery.

## Eight runbooks

1. **Broker outage: inspect leadership, ISR, replication, storage and networking.**
2. **Consumer lag: compare producer rate, offsets, processing rate and rebalances.**
3. **Connect failure: inspect tasks, DLQ, schema changes and source offsets.**
4. **MSK pressure: inspect CloudWatch, disk, network, partitions and retention.**
5. **Snowflake slowness: inspect query profile, execution, warehouse queues and spill.**
6. **Freshness breach: compare source heartbeat, CDC watermark and target visibility.**
7. **Credit anomaly: compare load, query history, auto-suspend and budget.**
8. **Recovery: restore safe ingestion, verify idempotency, freshness SLI and rollback.**

## Offline lab and tests

The [companion lab](labs/064-kafka-msk-snowflake-observability-consumer-lag-query-performance-data-freshness-lab.md) specifies staging validation, a synthetic manifest and negative drills. An offline check is not live Kafka/MSK or Snowflake verification.

Example standalone Python gate (save as `freshness_gate.py`):

```python
import json,sys
from pathlib import Path
def validate(d):
    errors=[]
    if not isinstance(d,dict):return ["manifest must be object"]
    for key in ("owner","environment","change_id"):
        if not isinstance(d.get(key),str) or not d[key].strip():errors.append("missing "+key)
    if d.get("environment") not in ("staging","lab"):errors.append("unsafe environment")
    for key in ("lag_records","lag_budget_records","freshness_seconds","freshness_budget_seconds","queue_seconds","queue_budget_seconds"):
        if type(d.get(key)) not in (int,float) or d[key]<0:errors.append("invalid "+key)
    for a,b in (("lag_records","lag_budget_records"),("freshness_seconds","freshness_budget_seconds"),("queue_seconds","queue_budget_seconds")):
        if type(d.get(a)) in (int,float) and type(d.get(b)) in (int,float) and d[a]>d[b]:errors.append("breach "+a)
    if d.get("destructive_change") is not False:errors.append("unsafe action")
    return errors
if __name__=="__main__":
    result=validate(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps({"status":"PASS" if not result else "FAIL","findings":result},indent=2))
    sys.exit(bool(result))
```

Save `healthy.json`:

```json
{"owner":"data-sre","environment":"staging","change_id":"OBS-064","lag_records":200,"lag_budget_records":1000,"freshness_seconds":35,"freshness_budget_seconds":120,"queue_seconds":2,"queue_budget_seconds":15,"destructive_change":false}
```

Save `test_freshness_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from freshness_gate import validate
class GateTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(Path("healthy.json").read_text())
    def test_healthy(self):self.assertEqual(validate(self.p),[])
    def test_nonobject(self):self.assertTrue(validate(None))
    def test_unsafe_environment(self):
        x=copy.deepcopy(self.p);x["environment"]="production";self.assertTrue(validate(x))
    def test_lag_breach(self):
        x=copy.deepcopy(self.p);x["lag_records"]=2000;self.assertTrue(validate(x))
    def test_freshness_breach(self):
        x=copy.deepcopy(self.p);x["freshness_seconds"]=300;self.assertTrue(validate(x))
    def test_queue_breach(self):
        x=copy.deepcopy(self.p);x["queue_seconds"]=30;self.assertTrue(validate(x))
    def test_destructive_action(self):
        x=copy.deepcopy(self.p);x["destructive_change"]=True;self.assertTrue(validate(x))
if __name__=="__main__":unittest.main()
```

```bash
python3 freshness_gate.py healthy.json
python3 -m unittest -v test_freshness_gate.py
```

Seven authored tests; not executed in a live environment.

## 100-point assessment

| Area | Points |
|---|---:|
| Kafka/MSK broker and replication telemetry | 20 |
| Consumer lag, Connect and CDC | 20 |
| Snowflake warehouse and query performance | 20 |
| Freshness SLO and executable tests | 20 |
| Incident simulation, privacy and rollback | 20 |
| **Total** | **100** |

Suggested pass 85/100; production acceptance additionally requires witnessed telemetry and recovery drills.

**Next:** Chapter 065 — Enterprise Database and Data Platform Observability, Incident Response and Reliability Capstone.
