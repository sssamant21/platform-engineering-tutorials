# Chapter 086 — Enterprise Observability Scale, Capacity Planning and High Availability Architecture

**Part 18 — Scaling, High Availability and FinOps (1/5)**

## Objectives

Design and capacity-plan resilient Prometheus, Alertmanager, Grafana, Loki, Tempo and OpenTelemetry services using measured telemetry rates, growth forecasts, multi-AZ failure domains, retention, cost allocation and recovery objectives.

## Reference architecture

```text
Applications + Kubernetes + DBRE exporters
                 |
       OTel Collector gateways (HA)
                 |
       /---------+---------\
   Prometheus HA          Loki / Tempo
       |                     |
 remote write -> scalable object-backed stores
       |                     |
       +--- Grafana query ---+
                 |
     SLO alerting / paging / audit
                 |
      multi-AZ + backups + DR tests
```

## Capacity engineering

Collect baseline active series, samples/sec, bytes/sample, query concurrency, rule evaluation time, log bytes/day, spans/sec, average span size and retention. For planning only:

- Metric raw ingest bytes/day ≈ samples/sec × bytes/sample × 86,400. Account separately for WAL, index, compression, replicas, churn and head block overhead.
- Log storage ≈ ingested bytes/day × retained days × effective compression/replication factor.
- Trace storage ≈ spans/sec × bytes/span × 86,400 × retained days × sampling rate × replication/overhead.
- Required capacity ≈ observed peak × forecast growth × safety factor, adjusted for node/AZ failure and replay bursts.

**Illustrative metric calculation:** 200,000 samples/sec × 2 bytes/sample × 86,400 ≈ 34.56 GB/day of idealized compressed sample payload, **not** total Prometheus disk. WAL, index, metadata and operational headroom can materially increase actual disk.

## HA and failure-domain design

Use two Prometheus replicas with unique external labels, redundant scraping and alert deduplication; avoid confusing duplicate samples with distinct time series. Evaluate Thanos, Mimir or another compatible remote storage system when long retention, multi-cluster federation or horizontal query scale is required. Prometheus local TSDB is not horizontally sharded by default. Plan Alertmanager quorum, Grafana stateless replicas and shared database dependencies, Loki distributed ingestion/query components and Tempo distributor/ingester/compactor capacity. Validate each product's version-specific HA semantics.

## Multi-AZ and disaster recovery

Distribute replicas across availability zones using anti-affinity and topology spread; reserve enough remaining capacity to tolerate one zone's failure. Object storage durability is not equivalent to recoverability: test credentials, bucket policies, backup integrity, restore times and query availability. State explicit RPO/RTO and verify customer-facing SLOs after failover.

## Capacity SLOs and alert examples

```promql
sum(rate(prometheus_tsdb_head_samples_appended_total[5m]))
sum(prometheus_tsdb_head_series)
histogram_quantile(0.95, sum by (le) (rate(prometheus_http_request_duration_seconds_bucket{handler="/api/v1/query"}[5m])))
```

Metric names vary by release; validate availability and labels in staging. Add dashboards for remote-write queue, collector exporter failures, Loki ingester limits, Tempo ingestion and object store errors.

## FinOps tradeoffs

Reduce high-cardinality labels before adding hardware. Use recording rules, downsampling where supported, tiered retention, sampling and tenant budgets. Avoid over-aggressive sampling that destroys incident investigation. Forecast per-tenant ingest, storage, compute and cross-region egress costs.

## DBRE scale examples

PostgreSQL per-query labels, Redis per-key telemetry, Kafka per-partition series, Elasticsearch per-index/shard series and Snowflake per-query IDs can multiply cardinality. Prefer bounded service, cluster and environment labels. Preserve diagnostic detail in secured logs/traces rather than unbounded metric labels.

## Executable offline synthetic gate

### healthy.json

```json
{
  "owner": "observability-capacity-sre",
  "environment": "staging",
  "change_id": "OBS-086",
  "reviewed": true,
  "headroom_verified": true,
  "failover_tested": true,
  "destructive_action": false,
  "checks": {
    "source_inventory": true,
    "samples": true,
    "series": true,
    "metrics_retention": true,
    "logs": true,
    "traces": true,
    "replicas": true,
    "headroom": true,
    "query_latency": true,
    "cardinality": true,
    "sharding": true,
    "prometheus_ha": true,
    "remote_write": true,
    "loki": true,
    "tempo": true,
    "multi_az": true,
    "failure_test": true,
    "backup": true,
    "finops": true,
    "owner": true
  }
}
```

### capacity_gate.py

```python
"""Offline synthetic capacity acceptance evidence gate."""
import json,sys
from pathlib import Path
CHECKS=["source_inventory","samples","series","metrics_retention","logs","traces","replicas","headroom","query_latency","cardinality","sharding","prometheus_ha","remote_write","loki","tempo","multi_az","failure_test","backup","finops","owner"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("reviewed","headroom_verified","failover_tested"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))

```

### test_capacity_gate.py

```python
import copy,json,unittest
from pathlib import Path
from capacity_gate import validate
class CapacityTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["source_inventory"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["samples"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["series"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["metrics_retention"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["logs"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["traces"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["replicas"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["headroom"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["query_latency"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["cardinality"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["sharding"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["prometheus_ha"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["remote_write"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["loki"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tempo"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["multi_az"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["failure_test"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["backup"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["checks"]["finops"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["checks"]["owner"]=False
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["headroom_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["failover_tested"]=false
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["checks"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 capacity_gate.py healthy.json
python3 -m unittest -v test_capacity_gate.py
```

Expected PASS and **30 authored tests**. Synthetic attestation does not measure real capacity; live execution remains pending.

## 24 hands-on exercises

1. Inventory telemetry sources: capture baseline, model peak, test and document evidence.
2. Baseline ingest throughput: capture baseline, model peak, test and document evidence.
3. Measure active series: capture baseline, model peak, test and document evidence.
4. Estimate sample rate: capture baseline, model peak, test and document evidence.
5. Forecast metric storage: capture baseline, model peak, test and document evidence.
6. Forecast log ingestion: capture baseline, model peak, test and document evidence.
7. Forecast trace volume: capture baseline, model peak, test and document evidence.
8. Define retention tiers: capture baseline, model peak, test and document evidence.
9. Model replica overhead: capture baseline, model peak, test and document evidence.
10. Calculate headroom: capture baseline, model peak, test and document evidence.
11. Measure p95 query latency: capture baseline, model peak, test and document evidence.
12. Set cardinality limits: capture baseline, model peak, test and document evidence.
13. Define sharding strategy: capture baseline, model peak, test and document evidence.
14. Review Prometheus HA pairs: capture baseline, model peak, test and document evidence.
15. Design remote write: capture baseline, model peak, test and document evidence.
16. Review Thanos/Mimir options: capture baseline, model peak, test and document evidence.
17. Review Loki scaling: capture baseline, model peak, test and document evidence.
18. Review Tempo scaling: capture baseline, model peak, test and document evidence.
19. Plan multi-AZ topology: capture baseline, model peak, test and document evidence.
20. Test AZ loss: capture baseline, model peak, test and document evidence.
21. Inspect queue saturation: capture baseline, model peak, test and document evidence.
22. Plan restore: capture baseline, model peak, test and document evidence.
23. Review FinOps allocation: capture baseline, model peak, test and document evidence.
24. Approve capacity gate: capture baseline, model peak, test and document evidence.

## 24 production incident scenarios

1. **Prometheus OOM:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
2. **TSDB WAL saturation:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
3. **Remote-write queue backlog:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
4. **High-cardinality release:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
5. **Scrape target explosion:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
6. **Grafana slow dashboard:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
7. **Alert evaluation delays:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
8. **Duplicate HA pages:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
9. **Single-AZ failure:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
10. **Remote store outage:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
11. **Loki ingester pressure:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
12. **Loki query timeout:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
13. **Tempo distributor overload:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
14. **Tempo compactor lag:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
15. **Collector memory pressure:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
16. **Dropped spans:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
17. **Disk exhaustion:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
18. **Retention miscalculation:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
19. **Thanos query partial data:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
20. **Mimir tenant limit:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
21. **Kubernetes node pressure:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
22. **Cross-region egress spike:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
23. **Backup restore failure:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.
24. **Capacity forecast miss:** establish impact, bottleneck, failure domain, mitigation, recovery and forecast correction.

## Eight production runbooks

1. **Capacity baseline: inventory series, samples, logs, spans, query concurrency and retention:** document owner, preconditions, commands, safety checks, recovery and evidence.
2. **Prometheus HA: validate paired replicas, external labels, deduplication and alert routing:** document owner, preconditions, commands, safety checks, recovery and evidence.
3. **Remote write: queue sizing, retries, backpressure and outage recovery:** document owner, preconditions, commands, safety checks, recovery and evidence.
4. **Loki and Tempo scale: ingestion, tenant limits, storage, retention and compaction:** document owner, preconditions, commands, safety checks, recovery and evidence.
5. **Multi-AZ failure: isolate zone, validate service continuity and paging:** document owner, preconditions, commands, safety checks, recovery and evidence.
6. **Cardinality surge: identify labels, revert instrumentation and verify TSDB recovery:** document owner, preconditions, commands, safety checks, recovery and evidence.
7. **Storage forecast: model headroom, growth, replication, retention and cost:** document owner, preconditions, commands, safety checks, recovery and evidence.
8. **Disaster recovery: verify backups, object store durability, restore and independent SLO recovery:** document owner, preconditions, commands, safety checks, recovery and evidence.

## 100-point acceptance assessment

| Domain | Points |
|---|---:|
| Workload inventory and forecasts | 20 |
| Metrics/logs/traces sizing | 20 |
| HA and multi-AZ failover | 20 |
| Retention, cost and cardinality | 20 |
| DR, SLO verification and runbooks | 20 |
| **Total** | **100** |

Recommended passing score: 85/100. Production approval requires observed baseline data, witnessed staging failure tests, owner review and verified recovery.

**Companion:** [Chapter 086 lab](labs/086-enterprise-observability-scale-capacity-planning-high-availability-architecture-lab.md).

**Next:** Chapter 087 — Prometheus and Alertmanager High Availability, Remote Write and Long-Term Storage.
