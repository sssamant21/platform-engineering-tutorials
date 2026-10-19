# Chapter 063 — MongoDB, Redis and Elasticsearch/OpenSearch Observability, Performance and Reliability

**Part 13 — Database and Data Platform Observability**  
**Audience:** Production DBRE, SRE, platform and on-call teams.  
**Prerequisites:** Chapters 061–062; Prometheus/Grafana; MongoDB, Redis and Elasticsearch/OpenSearch operational basics.

## Outcomes

Build actionable, version-aware observability for three fundamentally different datastore engines: MongoDB document/replication/WiredTiger behavior, Redis in-memory execution/evictions/persistence, and Elasticsearch/OpenSearch shard/JVM/search pipelines. Distinguish service-level symptoms from bottlenecks and establish safe, evidence-driven recovery.

## Architecture

```text
 Application RED metrics + traces + sanitized slow logs
          |                     |
 MongoDB (serverStatus, replSetGetStatus, profiler)
 Redis (INFO, LATENCY, SLOWLOG)
 Elasticsearch/OpenSearch (_nodes/stats, _cluster/health, _cat/shards)
          |                     |
 Exporters / OTel / provider-native monitoring
          |
 Prometheus + Loki + Grafana + Alertmanager
          |
 SLO burn alerts -> DBRE runbooks -> incident timeline
```

Collection privileges should be read-only and narrowly scoped. Prometheus label sets must not include raw queries, document IDs, customer IDs or per-request trace IDs.

## Signal taxonomy and baseline

| Engine | Golden signals | Failure-specific signals | Pitfall |
|---|---|---|---|
| MongoDB | ops/sec, command latency, errors, connections | WiredTiger cache eviction, tickets, locks, replication optime, oplog, disk IOPS | slow operations and replica lag vary by version/topology |
| Redis | ops/sec, p99 latency, errors, memory | evicted_keys, blocked_clients, fragmentation, persistence, replication | single-threaded command execution; CPU% alone misleads |
| Elasticsearch | search/index latency, rejects, availability | shard sizes, JVM heap/GC, merges, disk watermarks, search thread pool | cumulative counters need rate() |
| OpenSearch | search/index latency, rejects, cluster health | shard allocation, JVM, merges, IOPS | API/metric names differ by version and distribution |

Baseline each cluster by workload, time of day, index/collection, node role and data volume. Compare with independent application p95/p99 and error rates. Distinguish cumulative counters from instantaneous gauges and cluster-wide from per-node metrics.

## MongoDB: investigation

```javascript
// Run in mongosh with an approved monitoring role.
db.adminCommand({ serverStatus: 1 })
rs.status() // only on replica-set deployments with appropriate privileges
db.currentOp({ active: true })
db.getSiblingDB("admin").runCommand({ replSetGetStatus: 1 })
```

Inspect `wiredTiger.cache` dirty/used bytes and eviction behavior, connections, global lock counters, opcounters, replication state and disk latency. Profiling may have overhead and expose sensitive query content; enable only under an approved, time-bounded change. Do not confuse `secondaryDelaySecs` with unexpected replication lag. Compare oplog window against longest expected outage and recovery time.

## Redis: investigation

```bash
redis-cli --tls -h REDIS_HOST -p 6379 INFO stats
redis-cli --tls -h REDIS_HOST -p 6379 INFO memory
redis-cli --tls -h REDIS_HOST -p 6379 INFO replication
redis-cli --tls -h REDIS_HOST -p 6379 LATENCY LATEST
redis-cli --tls -h REDIS_HOST -p 6379 SLOWLOG LEN
```

Use credential handling approved for your environment; `--tls` requires configured TLS. Prefer `SLOWLOG LEN` initially because full entries may include sensitive arguments. Review eviction policy, blocked clients, fragmentation, command rates, AOF/RDB and replica offsets. In clustered Redis, inspect all shards and distinguish proxy vs shard metrics.

## Elasticsearch / OpenSearch: investigation

```bash
curl --fail --silent --show-error -H "Authorization: Bearer REDACTED_TOKEN" \
  "https://SEARCH_ENDPOINT/_cluster/health?pretty"
curl --fail --silent --show-error -H "Authorization: Bearer REDACTED_TOKEN" \
  "https://SEARCH_ENDPOINT/_nodes/stats/jvm,thread_pool,indices,fs?pretty"
curl --fail --silent --show-error -H "Authorization: Bearer REDACTED_TOKEN" \
  "https://SEARCH_ENDPOINT/_cat/shards?v&bytes=gb"
```

Use an approved secret injection mechanism instead of literal tokens in shell history. Inspect `thread_pool.search.rejected` deltas, query/fetch latency, JVM GC, shard distribution, disk watermarks and merge throttle. A large `size` or `from` request can amplify fan-out; inspect slow logs and pagination strategy before scaling. Avoid running force-merge, shard moves or replica changes during diagnosis without change control.

## Metrics and alerting examples

```promql
rate(redis_commands_processed_total[5m])
```

```promql
rate(redis_evicted_keys_total[5m])
```

```promql
up{job=~"mongodb|redis|elasticsearch|opensearch"}
```

Names depend on exporter and configuration. Elasticsearch/OpenSearch native cumulative counters must be mapped to appropriately named exporter series before PromQL use. Avoid alerting on a single raw counter; combine sustained rates, service impact and error-budget burn. Use latency histograms for p95/p99, not arithmetic means.

## Cross-platform production scenario

A patient-search API sees p95 latency above its SLO. Elasticsearch reports rising search rejections and oversized shards; MongoDB CDC writes show increased storage wait; Redis reports hot-key CPU saturation and eviction. Use trace timelines to separate simultaneous but independent bottlenecks. Capture query size and shard fan-out, disk IOPS/throughput, cache-hit ratio and command latency. Mitigations may include reducing Elasticsearch result size, rate limiting, fixing Redis hot-key access and reviewing MongoDB index plans; validate each change against application SLIs and rollback conditions.

## Offline acceptance lab

The following Python gate evaluates **synthetic evidence**, not live database telemetry. It requires no third-party packages.

Save these three blocks in one directory.

### healthy.json

```json
{
  "owner": "dbre-team",
  "environment": "staging",
  "change_id": "OBS-063",
  "mongo_replica_lag_seconds": 2,
  "mongo_lag_budget_seconds": 15,
  "redis_p99_ms": 8,
  "redis_p99_budget_ms": 20,
  "search_rejection_rate": 0,
  "search_rejection_budget": 1,
  "search_shard_gb": 35,
  "search_shard_budget_gb": 50,
  "destructive_change": false,
  "checks": {
    "mongo_topology": true,
    "mongo_cache": true,
    "mongo_replication": true,
    "mongo_queries": true,
    "mongo_storage": true,
    "redis_latency": true,
    "redis_memory": true,
    "redis_replication": true,
    "redis_persistence": true,
    "search_shards": true,
    "search_rejections": true,
    "search_heap": true,
    "search_merges": true,
    "search_storage": true,
    "alert_routes": true,
    "access_review": true,
    "rollback": true
  }
}
```

### telemetry_gate.py

```python
"""Offline cross-platform telemetry acceptance gate; synthetic evidence only."""
import json,sys
from pathlib import Path
CHECKS=["mongo_topology","mongo_cache","mongo_replication","mongo_queries","mongo_storage","redis_latency","redis_memory","redis_replication","redis_persistence","search_shards","search_rejections","search_heap","search_merges","search_storage","alert_routes","access_review","rollback"]
LIMITS=[("mongo_replica_lag_seconds","mongo_lag_budget_seconds"),("redis_p99_ms","redis_p99_budget_ms"),("search_rejection_rate","search_rejection_budget"),("search_shard_gb","search_shard_budget_gb")]
def validate(data):
    errors=[]
    if not isinstance(data,dict): return ["expected JSON object"]
    for key in ("owner","environment","change_id"):
        if not isinstance(data.get(key),str) or not data[key].strip(): errors.append("missing "+key)
    if data.get("environment") not in ("lab","staging"): errors.append("unsafe environment")
    c=data.get("checks")
    if not isinstance(c,dict): c={}; errors.append("checks must be object")
    for key in CHECKS:
        if c.get(key) is not True: errors.append("review missing "+key)
    for observed,budget in LIMITS:
        a,b=data.get(observed),data.get(budget)
        if type(a) not in (int,float) or a<0: errors.append("invalid "+observed)
        if type(b) not in (int,float) or b<=0: errors.append("invalid "+budget)
        if type(a) in (int,float) and type(b) in (int,float) and a>b: errors.append("breach "+observed)
    if data.get("destructive_change") is not False: errors.append("destructive change prohibited")
    return errors
if __name__=="__main__":
    try: result=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (IndexError,OSError,ValueError) as exc: sys.exit(str(exc))
    print(json.dumps({"pass":not result,"findings":result},indent=2))
    sys.exit(bool(result))

```

### test_telemetry_gate.py

```python
import copy,json,unittest
from pathlib import Path
from telemetry_gate import validate
class CrossPlatformTests(unittest.TestCase):
    def setUp(self): self.base=json.loads(Path(__file__).with_name("healthy.json").read_text())
    def test_healthy(self): self.assertEqual(validate(self.base),[])
    def test_not_object(self): self.assertTrue(validate([]))
    def test_negative_01(self):
        x=copy.deepcopy(self.base)
        x["checks"]["mongo_topology"]=False
        self.assertTrue(validate(x))
    def test_negative_02(self):
        x=copy.deepcopy(self.base)
        x["checks"]["mongo_cache"]=False
        self.assertTrue(validate(x))
    def test_negative_03(self):
        x=copy.deepcopy(self.base)
        x["checks"]["mongo_replication"]=False
        self.assertTrue(validate(x))
    def test_negative_04(self):
        x=copy.deepcopy(self.base)
        x["checks"]["mongo_queries"]=False
        self.assertTrue(validate(x))
    def test_negative_05(self):
        x=copy.deepcopy(self.base)
        x["checks"]["mongo_storage"]=False
        self.assertTrue(validate(x))
    def test_negative_06(self):
        x=copy.deepcopy(self.base)
        x["checks"]["redis_latency"]=False
        self.assertTrue(validate(x))
    def test_negative_07(self):
        x=copy.deepcopy(self.base)
        x["checks"]["redis_memory"]=False
        self.assertTrue(validate(x))
    def test_negative_08(self):
        x=copy.deepcopy(self.base)
        x["checks"]["redis_replication"]=False
        self.assertTrue(validate(x))
    def test_negative_09(self):
        x=copy.deepcopy(self.base)
        x["checks"]["redis_persistence"]=False
        self.assertTrue(validate(x))
    def test_negative_10(self):
        x=copy.deepcopy(self.base)
        x["checks"]["search_shards"]=False
        self.assertTrue(validate(x))
    def test_negative_11(self):
        x=copy.deepcopy(self.base)
        x["checks"]["search_rejections"]=False
        self.assertTrue(validate(x))
    def test_negative_12(self):
        x=copy.deepcopy(self.base)
        x["checks"]["search_heap"]=False
        self.assertTrue(validate(x))
    def test_negative_13(self):
        x=copy.deepcopy(self.base)
        x["checks"]["search_merges"]=False
        self.assertTrue(validate(x))
    def test_negative_14(self):
        x=copy.deepcopy(self.base)
        x["checks"]["search_storage"]=False
        self.assertTrue(validate(x))
    def test_negative_15(self):
        x=copy.deepcopy(self.base)
        x["checks"]["alert_routes"]=False
        self.assertTrue(validate(x))
    def test_negative_16(self):
        x=copy.deepcopy(self.base)
        x["checks"]["access_review"]=False
        self.assertTrue(validate(x))
    def test_negative_17(self):
        x=copy.deepcopy(self.base)
        x["checks"]["rollback"]=False
        self.assertTrue(validate(x))
    def test_negative_18(self):
        x=copy.deepcopy(self.base)
        x["owner"]=""
        self.assertTrue(validate(x))
    def test_negative_19(self):
        x=copy.deepcopy(self.base)
        x["environment"]=""
        self.assertTrue(validate(x))
    def test_negative_20(self):
        x=copy.deepcopy(self.base)
        x["change_id"]=""
        self.assertTrue(validate(x))
    def test_negative_21(self):
        x=copy.deepcopy(self.base)
        x["environment"]="production"
        self.assertTrue(validate(x))
    def test_negative_22(self):
        x=copy.deepcopy(self.base)
        x["mongo_replica_lag_seconds"]=100000
        self.assertTrue(validate(x))
    def test_negative_23(self):
        x=copy.deepcopy(self.base)
        x["redis_p99_ms"]=100000
        self.assertTrue(validate(x))
    def test_negative_24(self):
        x=copy.deepcopy(self.base)
        x["search_rejection_rate"]=100000
        self.assertTrue(validate(x))
    def test_negative_25(self):
        x=copy.deepcopy(self.base)
        x["search_shard_gb"]=100000
        self.assertTrue(validate(x))
    def test_negative_26(self):
        x=copy.deepcopy(self.base)
        x["destructive_change"]=True
        self.assertTrue(validate(x))
if __name__=="__main__": unittest.main()

```

```bash
python3 telemetry_gate.py healthy.json
python3 -m unittest -v test_telemetry_gate.py
```

Expected: PASS and **28 authored unit tests**. Run and capture actual output before claiming validation.

## 24 hands-on exercises

1. Establish application RED SLO.
2. Inventory MongoDB topology.
3. Capture MongoDB serverStatus.
4. Inspect WiredTiger cache.
5. Inspect MongoDB replica lag.
6. Inspect MongoDB slow operation evidence.
7. Review MongoDB connections.
8. Inspect MongoDB disk latency.
9. Inventory Redis deployment.
10. Capture Redis INFO stats.
11. Inspect Redis command latency.
12. Inspect Redis slowlog safely.
13. Review Redis eviction policy.
14. Review Redis replication health.
15. Review Redis fragmentation.
16. Inventory Elasticsearch/OpenSearch nodes.
17. Inspect cluster health.
18. Inspect shard sizes.
19. Review search thread pool rejections.
20. Review JVM heap and GC.
21. Review merge throttling.
22. Review storage latency and IOPS.
23. Build correlated Grafana dashboard.
24. Perform staged fault and recovery drill.

## 24 production failure scenarios

1. **MongoDB WiredTiger cache eviction:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
2. **MongoDB replica lag:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
3. **MongoDB slow queries:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
4. **MongoDB connection saturation:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
5. **MongoDB disk latency:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
6. **MongoDB oplog window shrink:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
7. **MongoDB index scan regression:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
8. **MongoDB election churn:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
9. **Redis CPU saturation:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
10. **Redis hot keys:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
11. **Redis command p99 latency:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
12. **Redis evictions:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
13. **Redis blocked clients:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
14. **Redis replication lag:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
15. **Redis persistence stalls:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
16. **Redis memory fragmentation:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
17. **Elasticsearch search rejection:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
18. **Elasticsearch oversized shards:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
19. **Elasticsearch JVM GC pressure:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
20. **Elasticsearch merge throttling:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
21. **OpenSearch cluster red health:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
22. **OpenSearch unassigned shards:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
23. **OpenSearch storage IOPS bottleneck:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.
24. **Cross-platform telemetry exporter outage:** collect engine evidence, correlate user-facing SLIs, identify owner, mitigate safely, verify recovery and document rollback.

## Eight runbooks

1. **MongoDB query slowdown: compare profiler, plan, cache eviction, locks and storage.**
2. **MongoDB replication lag: inspect optime, oplog window, network, write concern and secondary load.**
3. **Redis latency: inspect hot keys, slowlog, command rate, CPU and blocked clients.**
4. **Redis memory pressure: inspect used_memory, maxmemory, evictions, fragmentation and persistence.**
5. **Elasticsearch search slowdown: inspect slowlogs, search thread pools, shard sizes, disk IOPS and query fan-out.**
6. **OpenSearch shard instability: inspect allocation explain, watermarks, JVM and cluster health.**
7. **Telemetry loss: check exporter credentials, scrape targets, native APIs and cloud provider fallback.**
8. **Recovery and rollback: confirm independent SLIs, alert clearance, ownership and incident evidence.**

## 100-point assessment

| Domain | Points |
|---|---:|
| Architecture and golden signals | 20 |
| MongoDB diagnosis and replication | 20 |
| Redis latency, memory and persistence | 20 |
| Elasticsearch/OpenSearch shards, JVM and search | 20 |
| Lab evidence, security, recovery and rollback | 20 |
| **Total** | **100** |

Suggested passing score: 85. Production sign-off additionally requires witnessed staging exercises, exporter access review, safe alert thresholds and a reviewed incident runbook.

**Companion:** [Chapter 063 lab](labs/063-mongodb-redis-elasticsearch-opensearch-observability-performance-reliability-lab.md).

**Next:** Chapter 064 — Kafka/MSK and Snowflake Observability, Consumer Lag, Query Performance and Data Freshness.
