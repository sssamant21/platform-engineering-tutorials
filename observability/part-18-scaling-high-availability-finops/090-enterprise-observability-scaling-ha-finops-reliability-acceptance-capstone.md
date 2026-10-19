# Chapter 090 — Enterprise Observability Scaling, High Availability and FinOps Reliability Acceptance Capstone

**Part 18 — Scaling, High Availability and FinOps (5/5, final capstone)**

## Mission

Combine Chapters 086–089 into a production-readiness acceptance exercise for Prometheus, Alertmanager, Grafana, OpenTelemetry, Loki and Tempo. Verify multi-AZ availability, capacity headroom, remote-write/WAL recovery, retention governance, cost forecasts, rollback and SLO continuity. Perform fault injection only in approved isolated staging.

## Enterprise reference architecture

```text
DBRE exporters / applications / Kubernetes
             |              |
       Prometheus HA     OTel gateway HA
             |              |
       remote write     Loki / Tempo distributed
             |              |
       long-term store  object storage
             \              /
         Grafana + SLO alerts
                 |
      Alertmanager HA + paging
                 |
       GitOps, audit and FinOps
```

## Capacity and reliability design

Measure baseline active series, samples/sec, WAL disk, remote-write backlog, logs bytes/sec, streams, spans/sec, trace lookup, query p95 and object-store errors. Forecast peak × growth × headroom and ensure remaining AZ capacity tolerates a zone failure. Prometheus HA replicas require unique external labels and downstream deduplication; Alertmanager clustering reduces duplicate notifications but does not guarantee zero duplicates during partitions. Validate remote-write retention/replay windows; sustained outages may lose samples. Loki and Tempo need tenant quotas, compactor lifecycle, encryption and version-specific distributed HA configuration.

## Security, retention and FinOps

Require workload identity, TLS, scoped object-store IAM, tenant isolation and PII redaction. Avoid per-request identifiers and SQL literals as metric/log labels. Compute storage and egress forecasts from measured compression, retention, replicas and object-store requests. Changes to retention or sampling require security/compliance review; deletion may be irreversible. Do not trade away incident investigation or paging coverage for cost savings.

## Staging game day

1. Capture before-state SLO, ingest, storage and cost baselines.
2. Introduce a bounded high-cardinality synthetic workload and test policy detection.
3. Fail one Prometheus replica and verify remote query and Alertmanager test page.
4. Simulate remote-write receiver failure; measure WAL backlog and replay.
5. Fail a Loki ingester and confirm log retrieval.
6. Interrupt Tempo/OTel exporter briefly and confirm trace recovery or measured loss.
7. Simulate one AZ unavailable while maintaining N-1 headroom.
8. Restore services, validate error budget, query availability, and cost forecast.
9. Revert reviewed GitOps change and capture UTC evidence and approvals.

## DBRE acceptance

Ensure PostgreSQL replication and connections, Redis memory/latency, Kafka lag, Elasticsearch/OpenSearch shard/storage pressure, Snowflake freshness and Kubernetes SLO signals survive telemetry platform faults. Record customer-impact thresholds and responsible on-call owners.

## Offline executable synthetic acceptance gate

Save `healthy.json`:

```json
{
  "owner": "observability-sre",
  "environment": "staging",
  "change_id": "OBS-090",
  "approved": true,
  "failover_witnessed": true,
  "rollback_witnessed": true,
  "destructive_action": false,
  "gates": {
    "metrics_baseline": true,
    "series_budget": true,
    "wal_headroom": true,
    "remote_write": true,
    "prometheus_ha": true,
    "alertmanager_ha": true,
    "paging": true,
    "loki_ingest": true,
    "loki_retention": true,
    "loki_tenant": true,
    "tempo_ingest": true,
    "trace_lookup": true,
    "otel_queue": true,
    "object_store": true,
    "multi_az": true,
    "n_minus_one": true,
    "failover": true,
    "dr_restore": true,
    "slo": true,
    "finops": true,
    "rollback": true,
    "approval": true
  }
}
```

Save `acceptance_gate.py`:

```python
import json,sys
from pathlib import Path
GATES=["metrics_baseline","series_budget","wal_headroom","remote_write","prometheus_ha","alertmanager_ha","paging","loki_ingest","loki_retention","loki_tenant","tempo_ingest","trace_lookup","otel_queue","object_store","multi_az","n_minus_one","failover","dr_restore","slo","finops","rollback","approval"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("approved","failover_witnessed","rollback_witnessed"):
  if p.get(k) is not True:e.append("missing "+k)
 g=p.get("gates")
 if not isinstance(g,dict):e.append("invalid gates");g={}
 for k in GATES:
  if g.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:e=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as x:sys.exit(str(x))
 print("PASS" if not e else "FAIL: "+",".join(e));sys.exit(bool(e))
```

Save `test_acceptance_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from acceptance_gate import validate
class Tests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_pass(self):self.assertFalse(validate(self.p))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["gates"]["metrics_baseline"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["gates"]["series_budget"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["gates"]["wal_headroom"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["gates"]["remote_write"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["gates"]["prometheus_ha"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["gates"]["alertmanager_ha"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["gates"]["paging"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["gates"]["loki_ingest"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["gates"]["loki_retention"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["gates"]["loki_tenant"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["gates"]["tempo_ingest"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["gates"]["trace_lookup"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["gates"]["otel_queue"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["gates"]["object_store"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["gates"]["multi_az"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["gates"]["n_minus_one"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["gates"]["failover"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["gates"]["dr_restore"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["gates"]["slo"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["gates"]["finops"]=False
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["gates"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["gates"]["approval"]=False
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["approved"]=false
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["failover_witnessed"]=false
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["rollback_witnessed"]=false
  self.assertTrue(validate(p))
 def test_negative_29(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_30(self):
  p=copy.deepcopy(self.p)
  p=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

```bash
python3 acceptance_gate.py healthy.json
python3 -m unittest -v test_acceptance_gate.py
```

Expected PASS and **31 authored tests**. The synthetic gate only validates attestations; no live tests or production deployment are claimed.

## 24 hands-on exercises

1. Inventory telemetry sources: capture baseline, execution, validation, failure evidence and rollback.
2. Baseline Prometheus samples: capture baseline, execution, validation, failure evidence and rollback.
3. Measure TSDB active series: capture baseline, execution, validation, failure evidence and rollback.
4. Size remote-write queues: capture baseline, execution, validation, failure evidence and rollback.
5. Validate WAL headroom: capture baseline, execution, validation, failure evidence and rollback.
6. Configure Prometheus HA: capture baseline, execution, validation, failure evidence and rollback.
7. Test Alertmanager dedup: capture baseline, execution, validation, failure evidence and rollback.
8. Verify paging receiver: capture baseline, execution, validation, failure evidence and rollback.
9. Baseline Loki ingest: capture baseline, execution, validation, failure evidence and rollback.
10. Audit Loki tenant limits: capture baseline, execution, validation, failure evidence and rollback.
11. Verify Loki compaction: capture baseline, execution, validation, failure evidence and rollback.
12. Test log retention: capture baseline, execution, validation, failure evidence and rollback.
13. Baseline Tempo spans: capture baseline, execution, validation, failure evidence and rollback.
14. Validate trace correlation: capture baseline, execution, validation, failure evidence and rollback.
15. Tune collector retry queues: capture baseline, execution, validation, failure evidence and rollback.
16. Test trace retention: capture baseline, execution, validation, failure evidence and rollback.
17. Review object-store IAM: capture baseline, execution, validation, failure evidence and rollback.
18. Model N-1 AZ capacity: capture baseline, execution, validation, failure evidence and rollback.
19. Simulate AZ loss: capture baseline, execution, validation, failure evidence and rollback.
20. Test remote-store outage: capture baseline, execution, validation, failure evidence and rollback.
21. Validate SLO continuity: capture baseline, execution, validation, failure evidence and rollback.
22. Forecast 90-day spend: capture baseline, execution, validation, failure evidence and rollback.
23. Verify rollback: capture baseline, execution, validation, failure evidence and rollback.
24. Collect acceptance signatures: capture baseline, execution, validation, failure evidence and rollback.

## 24 production incident simulations

1. **Prometheus OOM:** triage impact, isolate bottleneck, restore SLOs and update runbook.
2. **WAL full:** triage impact, isolate bottleneck, restore SLOs and update runbook.
3. **Remote-write 429:** triage impact, isolate bottleneck, restore SLOs and update runbook.
4. **Remote-write lag:** triage impact, isolate bottleneck, restore SLOs and update runbook.
5. **Duplicate alert:** triage impact, isolate bottleneck, restore SLOs and update runbook.
6. **Alertmanager peer partition:** triage impact, isolate bottleneck, restore SLOs and update runbook.
7. **Missing on-call page:** triage impact, isolate bottleneck, restore SLOs and update runbook.
8. **High-cardinality regression:** triage impact, isolate bottleneck, restore SLOs and update runbook.
9. **Loki 429:** triage impact, isolate bottleneck, restore SLOs and update runbook.
10. **Loki ingester loss:** triage impact, isolate bottleneck, restore SLOs and update runbook.
11. **Loki retention deletion:** triage impact, isolate bottleneck, restore SLOs and update runbook.
12. **Loki tenant isolation failure:** triage impact, isolate bottleneck, restore SLOs and update runbook.
13. **Tempo distributor overload:** triage impact, isolate bottleneck, restore SLOs and update runbook.
14. **Tempo missing traces:** triage impact, isolate bottleneck, restore SLOs and update runbook.
15. **Collector queue exhaustion:** triage impact, isolate bottleneck, restore SLOs and update runbook.
16. **Object-store outage:** triage impact, isolate bottleneck, restore SLOs and update runbook.
17. **AZ loss:** triage impact, isolate bottleneck, restore SLOs and update runbook.
18. **Cross-zone replication lag:** triage impact, isolate bottleneck, restore SLOs and update runbook.
19. **Query latency SLO breach:** triage impact, isolate bottleneck, restore SLOs and update runbook.
20. **Missing DR restore:** triage impact, isolate bottleneck, restore SLOs and update runbook.
21. **Cost anomaly:** triage impact, isolate bottleneck, restore SLOs and update runbook.
22. **Forecast underestimation:** triage impact, isolate bottleneck, restore SLOs and update runbook.
23. **Rollback failure:** triage impact, isolate bottleneck, restore SLOs and update runbook.
24. **Audit evidence gap:** triage impact, isolate bottleneck, restore SLOs and update runbook.

## Eight production runbooks

1. Prometheus HA, external labels and TSDB recovery.
2. Remote-write queue, WAL pressure and replay recovery.
3. Alertmanager cluster health, route deduplication and paging.
4. Loki ingestion, retention and tenant isolation.
5. Tempo trace ingestion, storage and sampling recovery.
6. Multi-AZ failover, DR restore and SLO verification.
7. Cardinality, retention, storage and FinOps optimization.
8. Approved GitOps rollback, evidence and operational sign-off.

## 100-point acceptance rubric

| Domain | Points |
|---|---:|
| Metrics HA, remote write and WAL | 20 |
| Logs, traces, retention and tenant safety | 20 |
| Multi-AZ resilience, SLO and DR | 20 |
| Capacity forecast and FinOps governance | 20 |
| Incident response, rollback and evidence | 20 |
| **Total** | **100** |

Recommended passing threshold 85/100, with mandatory security and witnessed staging failover/rollback checks. Approval: platform owner, on-call lead, service owner and security.

[Companion lab](labs/090-enterprise-observability-scaling-ha-finops-reliability-acceptance-capstone-lab.md)

**Part 18 complete. Next:** Chapter 091 — Enterprise Observability Security Architecture, Identity, RBAC and Tenant Isolation (Part 19).
