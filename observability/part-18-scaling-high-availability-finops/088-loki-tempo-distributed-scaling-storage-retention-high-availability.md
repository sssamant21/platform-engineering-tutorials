# Chapter 088 — Loki and Tempo Distributed Scaling, Storage, Retention and High Availability

**Part 18 — Scaling, High Availability and FinOps (3/5)**

## 1. Architecture: OpenTelemetry gateways feed Loki distributors/ingesters and Tempo distributors/ingesters; object storage, compactors and query frontends enable retrieval. Spread replicas across availability zones and validate ring health and tenant isolation.

## 2. Capacity: measure logs bytes/sec, active streams, spans/sec, span size, ingestion errors, query latency, object store operations, compaction backlog and retention. Estimate daily bytes as throughput × 86,400; account for compression, replicas and failure headroom.

## 3. Security: TLS, workload identity, scoped object-store IAM, tenant-specific limits, redaction and retention change control. Avoid patient data, SQL literals, Redis keys and per-request identifiers as labels.

## 4. Reliability: test bounded ingester failures, collector retry queue pressure, object-store unavailability, missing trace propagation and staged rollback. Validate Grafana Loki/Tempo correlation with a known trace ID.

## 5. FinOps: right-size retention and sampling; cap active streams; attribute ingestion, compute and object-store costs to owners. Never reduce sampling without SRE incident-readiness review.

## Offline executable lab

Save as `storage_gate.py`:

```python
import json,sys
from pathlib import Path
FIELDS=["ingest","streams","queries","storage","retention","tenant","sampling","traces","queue","multi_az","failover","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["not object"]
 e=[]
 if p.get("environment")!="staging":e.append("environment")
 if not p.get("owner"):e.append("owner")
 for k in FIELDS:
  if p.get(k) is not True:e.append(k)
 return e
if __name__=="__main__":
 try:e=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as x:sys.exit(str(x))
 print("PASS" if not e else "FAIL: "+",".join(e));sys.exit(bool(e))
```

Save as `healthy.json`:

```json
{
  "environment": "staging",
  "owner": "sre",
  "ingest": true,
  "streams": true,
  "queries": true,
  "storage": true,
  "retention": true,
  "tenant": true,
  "sampling": true,
  "traces": true,
  "queue": true,
  "multi_az": true,
  "failover": true,
  "rollback": true
}
```

Save as `test_storage_gate.py`:

```python
import copy,unittest
from storage_gate import validate
BASE={"environment":"staging","owner":"sre",**{k:True for k in ["ingest","streams","queries","storage","retention","tenant","sampling","traces","queue","multi_az","failover","rollback"]}}
class Tests(unittest.TestCase):
 def test_pass(self):self.assertFalse(validate(BASE))
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_missing_0(self):
  p=copy.deepcopy(BASE);p["ingest"]=False;self.assertTrue(validate(p))
 def test_missing_1(self):
  p=copy.deepcopy(BASE);p["streams"]=False;self.assertTrue(validate(p))
 def test_missing_2(self):
  p=copy.deepcopy(BASE);p["queries"]=False;self.assertTrue(validate(p))
 def test_missing_3(self):
  p=copy.deepcopy(BASE);p["storage"]=False;self.assertTrue(validate(p))
 def test_missing_4(self):
  p=copy.deepcopy(BASE);p["retention"]=False;self.assertTrue(validate(p))
 def test_missing_5(self):
  p=copy.deepcopy(BASE);p["tenant"]=False;self.assertTrue(validate(p))
 def test_missing_6(self):
  p=copy.deepcopy(BASE);p["sampling"]=False;self.assertTrue(validate(p))
 def test_missing_7(self):
  p=copy.deepcopy(BASE);p["traces"]=False;self.assertTrue(validate(p))
 def test_missing_8(self):
  p=copy.deepcopy(BASE);p["queue"]=False;self.assertTrue(validate(p))
 def test_missing_9(self):
  p=copy.deepcopy(BASE);p["multi_az"]=False;self.assertTrue(validate(p))
 def test_missing_10(self):
  p=copy.deepcopy(BASE);p["failover"]=False;self.assertTrue(validate(p))
 def test_missing_11(self):
  p=copy.deepcopy(BASE);p["rollback"]=False;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

Run `python3 storage_gate.py healthy.json` and `python3 -m unittest -v test_storage_gate.py`. Expected PASS; 14 authored tests, execution pending. Synthetic evidence cannot prove live ingestion.

## 24 hands-on exercises

1. Loki ingestion: measure baseline, configure, test, record evidence and rollback.
2. Loki active streams: measure baseline, configure, test, record evidence and rollback.
3. Loki distributor: measure baseline, configure, test, record evidence and rollback.
4. Loki ingester: measure baseline, configure, test, record evidence and rollback.
5. Loki querier: measure baseline, configure, test, record evidence and rollback.
6. Loki query frontend: measure baseline, configure, test, record evidence and rollback.
7. Object storage: measure baseline, configure, test, record evidence and rollback.
8. Loki compactor: measure baseline, configure, test, record evidence and rollback.
9. Retention policy: measure baseline, configure, test, record evidence and rollback.
10. Tenant quotas: measure baseline, configure, test, record evidence and rollback.
11. Label cardinality: measure baseline, configure, test, record evidence and rollback.
12. Tempo span rate: measure baseline, configure, test, record evidence and rollback.
13. Tempo distributor: measure baseline, configure, test, record evidence and rollback.
14. Tempo ingester: measure baseline, configure, test, record evidence and rollback.
15. Tempo compactor: measure baseline, configure, test, record evidence and rollback.
16. Trace lookup: measure baseline, configure, test, record evidence and rollback.
17. Trace propagation: measure baseline, configure, test, record evidence and rollback.
18. Collector retry queue: measure baseline, configure, test, record evidence and rollback.
19. Collector drop metrics: measure baseline, configure, test, record evidence and rollback.
20. Multi-AZ spread: measure baseline, configure, test, record evidence and rollback.
21. Ingester failover: measure baseline, configure, test, record evidence and rollback.
22. Storage outage: measure baseline, configure, test, record evidence and rollback.
23. Cost forecast: measure baseline, configure, test, record evidence and rollback.
24. Rollback: measure baseline, configure, test, record evidence and rollback.

## 24 production incident scenarios

1. **Loki 429:** investigate component, customer impact, mitigation and recovery.
2. **Loki OOM:** investigate component, customer impact, mitigation and recovery.
3. **Loki timeout:** investigate component, customer impact, mitigation and recovery.
4. **Label explosion:** investigate component, customer impact, mitigation and recovery.
5. **Storage permission failure:** investigate component, customer impact, mitigation and recovery.
6. **Compactor backlog:** investigate component, customer impact, mitigation and recovery.
7. **Unexpected retention:** investigate component, customer impact, mitigation and recovery.
8. **Duplicate streams:** investigate component, customer impact, mitigation and recovery.
9. **Tenant access issue:** investigate component, customer impact, mitigation and recovery.
10. **Index lag:** investigate component, customer impact, mitigation and recovery.
11. **Tempo overload:** investigate component, customer impact, mitigation and recovery.
12. **Tempo ingester crash:** investigate component, customer impact, mitigation and recovery.
13. **Missing traces:** investigate component, customer impact, mitigation and recovery.
14. **Tempo storage failure:** investigate component, customer impact, mitigation and recovery.
15. **Compactor stall:** investigate component, customer impact, mitigation and recovery.
16. **Sampling gap:** investigate component, customer impact, mitigation and recovery.
17. **Collector queue full:** investigate component, customer impact, mitigation and recovery.
18. **Exporter drops:** investigate component, customer impact, mitigation and recovery.
19. **AZ failure:** investigate component, customer impact, mitigation and recovery.
20. **Node pressure:** investigate component, customer impact, mitigation and recovery.
21. **Egress spike:** investigate component, customer impact, mitigation and recovery.
22. **Grafana partial result:** investigate component, customer impact, mitigation and recovery.
23. **Backfill overload:** investigate component, customer impact, mitigation and recovery.
24. **Restore failure:** investigate component, customer impact, mitigation and recovery.

## Eight runbooks

1. Loki ingestion and tenant limits.
2. Loki query latency and object store.
3. Loki compactor and retention.
4. Tempo ingestion and context propagation.
5. Tempo search and storage.
6. Multi-AZ failover and SLO validation.
7. Security, privacy and cost optimization.
8. Disaster recovery and GitOps rollback.

## 100-point acceptance

Loki ingestion/query 20; Tempo ingestion/search 20; storage/retention 20; HA/security 20; FinOps/recovery 20. Passing recommendation 85/100; production approval requires witnessed staging failover and recovery.

[Companion lab](labs/088-loki-tempo-distributed-scaling-storage-retention-high-availability-lab.md)

**Next:** Chapter 089 — Observability FinOps, Retention Optimization, Cardinality Governance and Cost Forecasting.
