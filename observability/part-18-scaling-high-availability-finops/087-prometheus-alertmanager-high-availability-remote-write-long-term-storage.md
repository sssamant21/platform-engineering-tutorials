# Chapter 087 — Prometheus and Alertmanager High Availability, Remote Write and Long-Term Storage

**Part 18 — Scaling, High Availability and FinOps (2/5)**

## Objectives

Engineer redundant Prometheus scrapes and Alertmanager notifications, size remote-write queues, protect TSDB/WAL storage, evaluate Thanos/Mimir long-term storage and test zone failures without false-green monitoring.

## Reference architecture

```text
                 exporters
                 /       \
          Prometheus A   Prometheus B
          replica=a     replica=b
                 \       /
           remote write queues
                   |
         Mimir / remote receiver
                   |
         object-backed retention
                   |
          Grafana / SLO queries

          Alertmanager A <--> B
             |             |
          deduped paging / silences
```

## Prometheus HA semantics

Two Prometheus replicas independently scrape the same targets and evaluate rules. Configure unique `external_labels` identifying cluster and replica. Prometheus alone does not globally deduplicate samples; the selected remote backend or query layer must explicitly support HA deduplication. Validate recording rule and alert behavior when one replica fails. Plan N-1 capacity and failure-domain spread.

```yaml
global:
  external_labels:
    cluster: staging-east
    replica: prometheus-a
remote_write:
  - url: https://remote-write.staging.example.invalid/api/v1/push
    queue_config:
      min_shards: 1
      max_shards: 8
      capacity: 10000
      max_samples_per_send: 2000
```

The example endpoint is intentionally non-routable. Tune queues from measured samples/sec, retries and receiver limits. Keep credentials out of Git and use TLS. Do not infer that increasing shards always improves throughput; it can overload receivers or increase memory.

## Remote write and WAL recovery

Remote write buffers samples through the WAL; sustained receiver outages and retention/truncation limits can lead to unrecoverable gaps. Monitor `prometheus_remote_storage_samples_pending`, retries/failures, highest sent timestamp, WAL size, disk free, ingestion lag and receiver rejection metrics. Queue capacity and WAL replay must be sized for realistic outages, not only steady state.

## Alertmanager HA

Cluster Alertmanager peers with stable network connectivity and appropriately isolated failure domains. Validate gossip membership, notification deduplication, silences and route consistency. Replication is eventually consistent; a short duplicate notification window may occur during partitions. Never assume an HA pair makes a misconfigured route safe.

## Long-term storage

Compare Thanos sidecar/store/query/compactor patterns with Mimir remote-write ingestion and distributed querying. Object storage durability, query availability, retention and compaction are separate reliability concerns. Test bucket IAM, encryption, compactor lifecycle, object listing latency and restore paths. Plan tenant isolation, retention and cross-region egress costs.

## Example validation

```bash
promtool check config prometheus.yml
amtool check-config alertmanager.yml
curl -fsS http://localhost:9090/-/ready
curl -fsS http://localhost:9093/-/ready
```

Use these only for authorized isolated staging services. Readiness endpoints do not prove remote write, paging or query correctness.

## SRE/DBRE application

PostgreSQL replication, Redis failover, Kafka consumer lag, Elasticsearch/OpenSearch storage pressure and Snowflake freshness alerts must remain visible through a Prometheus node or AZ failure. Test actual Alertmanager paging with a staging receiver and verify that remote queries reflect correct deduplicated series.

## Executable offline synthetic acceptance

### healthy.json

```json
{
  "owner": "metrics-platform-sre",
  "environment": "staging",
  "change_id": "OBS-087",
  "reviewed": true,
  "failover_verified": true,
  "delivery_verified": true,
  "destructive_action": false,
  "checks": {
    "replicas": true,
    "external_labels": true,
    "scrape": true,
    "wal": true,
    "remote_write": true,
    "queue": true,
    "retries": true,
    "tls": true,
    "auth": true,
    "ordering": true,
    "alertmanager_peers": true,
    "dedup": true,
    "silences": true,
    "failover": true,
    "remote_store": true,
    "query_continuity": true,
    "retention": true,
    "backup": true,
    "cost": true,
    "rollback": true
  }
}
```

### ha_gate.py

```python
"""Synthetic HA readiness evidence gate, no live services."""
import json,sys
from pathlib import Path
CHECKS=["replicas","external_labels","scrape","wal","remote_write","queue","retries","tls","auth","ordering","alertmanager_peers","dedup","silences","failover","remote_store","query_continuity","retention","backup","cost","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("reviewed","failover_verified","delivery_verified"):
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

### test_ha_gate.py

```python
import copy,json,unittest
from pathlib import Path
from ha_gate import validate
class HATests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["replicas"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["external_labels"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["scrape"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["wal"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["remote_write"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["queue"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["retries"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tls"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["auth"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["ordering"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["alertmanager_peers"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dedup"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["silences"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["failover"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["remote_store"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["query_continuity"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["retention"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["backup"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["checks"]["cost"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
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
  p["failover_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["delivery_verified"]=false
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
python3 ha_gate.py healthy.json
python3 -m unittest -v test_ha_gate.py
```

Expected PASS and **30 authored tests**. No live execution is claimed; manifest attestations do not verify actual HA behavior.

## 24 hands-on exercises

1. Baseline Prometheus ingest: document commands, evidence and recovery conditions.
2. Deploy HA replicas: document commands, evidence and recovery conditions.
3. Set replica external labels: document commands, evidence and recovery conditions.
4. Verify duplicate scraping: document commands, evidence and recovery conditions.
5. Inspect TSDB head series: document commands, evidence and recovery conditions.
6. Inspect WAL size: document commands, evidence and recovery conditions.
7. Set remote-write queues: document commands, evidence and recovery conditions.
8. Inspect pending samples: document commands, evidence and recovery conditions.
9. Test retry backoff: document commands, evidence and recovery conditions.
10. Test receiver authentication: document commands, evidence and recovery conditions.
11. Check TLS certificates: document commands, evidence and recovery conditions.
12. Review out-of-order samples: document commands, evidence and recovery conditions.
13. Configure Alertmanager peers: document commands, evidence and recovery conditions.
14. Verify peer mesh: document commands, evidence and recovery conditions.
15. Test route deduplication: document commands, evidence and recovery conditions.
16. Test silences propagation: document commands, evidence and recovery conditions.
17. Simulate one replica failure: document commands, evidence and recovery conditions.
18. Simulate remote store outage: document commands, evidence and recovery conditions.
19. Verify local query continuity: document commands, evidence and recovery conditions.
20. Evaluate Thanos sidecar: document commands, evidence and recovery conditions.
21. Compare Mimir remote-write: document commands, evidence and recovery conditions.
22. Model long-term retention: document commands, evidence and recovery conditions.
23. Rehearse recovery: document commands, evidence and recovery conditions.
24. Approve HA acceptance: document commands, evidence and recovery conditions.

## 24 production incident scenarios

1. **Prometheus replica OOM:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
2. **Duplicate HA alerts:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
3. **External label collision:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
4. **Remote-write 429:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
5. **Remote-write 5xx:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
6. **Remote-write auth failure:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
7. **WAL fills disk:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
8. **Remote-write backlog:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
9. **Dropped remote samples:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
10. **Out-of-order rejects:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
11. **Thanos sidecar unavailable:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
12. **Object store permission denied:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
13. **Mimir tenant limit:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
14. **Query partial response:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
15. **Alertmanager peer partition:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
16. **Lost silence:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
17. **Split notification route:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
18. **Rule evaluation lag:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
19. **Single-AZ failure:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
20. **Certificate expiry:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
21. **Prometheus compaction pressure:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
22. **Retention misconfiguration:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
23. **Restored data gap:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.
24. **SLO query false green:** determine impact, failure domain, diagnosis, safe mitigation and acceptance checks.

## Eight production runbooks

1. **Prometheus replica health and TSDB baseline:** define owner, trigger, triage, action, rollback and evidence.
2. **External labels and HA deduplication validation:** define owner, trigger, triage, action, rollback and evidence.
3. **Remote-write queue backlog and recovery:** define owner, trigger, triage, action, rollback and evidence.
4. **Alertmanager clustering, routing and silences:** define owner, trigger, triage, action, rollback and evidence.
5. **Long-term storage availability and object store recovery:** define owner, trigger, triage, action, rollback and evidence.
6. **Zone failure and replica capacity acceptance:** define owner, trigger, triage, action, rollback and evidence.
7. **Retention, cost and cardinality optimization:** define owner, trigger, triage, action, rollback and evidence.
8. **Failback, rollback and independent SLO verification:** define owner, trigger, triage, action, rollback and evidence.

## 100-point assessment

| Domain | Points |
|---|---:|
| Prometheus HA and labels | 20 |
| Remote write and WAL resilience | 20 |
| Alertmanager clustering and paging | 20 |
| Long-term storage and FinOps | 20 |
| Failover, rollback and SLO verification | 20 |
| **Total** | **100** |

Recommended pass 85/100; require witnessed staging failover, alert delivery and remote-write recovery before production acceptance.

**Companion:** [Chapter 087 lab](labs/087-prometheus-alertmanager-high-availability-remote-write-long-term-storage-lab.md).

**Next:** Chapter 088 — Loki and Tempo Distributed Scaling, Storage, Retention and High Availability.
