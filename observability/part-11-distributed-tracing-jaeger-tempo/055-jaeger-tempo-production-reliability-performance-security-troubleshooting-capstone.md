# Chapter 055 — Jaeger and Tempo Production Reliability, Performance, Security and Troubleshooting Capstone

**Part 11 — Distributed Tracing with Jaeger and Tempo: FINAL CAPSTONE**  
**Audience:** SRE, DBRE, platform and observability engineering teams.  
**Prerequisites:** Chapters 051–054, OpenTelemetry Collector, Jaeger, Tempo and Kubernetes.

## 1. Capstone mission

Build an operationally defensible distributed tracing architecture with Jaeger and Grafana Tempo, then rehearse ingest/query/storage outages, tail-sampling failures, tenant isolation, performance degradation and recovery. Capture evidence rather than relying on declarations.

## 2. Reference architecture

```text
API -> Redis -> PostgreSQL -> Kafka worker
 |            W3C traceparent       |
 +----------- OTel SDKs ------------+
                  |
           OTel Collectors
                  |
          trace-ID-aware routing
                  |
         Jaeger / Tempo gateways
             /           \
    ingest + storage   query + UI
          |                |
    durable backends    Grafana
          \                /
         independent RED SLIs
```

Jaeger and Tempo have different deployment/storage/query models. Keep version-specific configs separate and verify end-to-end trace persistence; OTLP accepted does not imply searchable traces.

## 3. Production acceptance matrix

| Domain | Required staging evidence |
|---|---|
| Ingest | synthetic trace delivered and queried in Jaeger and Tempo |
| Context | parent-child spans across HTTP, DB and async worker |
| Sampling | trace affinity and tail policy under scale changes |
| Storage | persistence, retention, backup/restore and RPO/RTO |
| Performance | ingest success, query p95 and trace completeness |
| Security | TLS/auth, tenant isolation, privacy filtering and RBAC |
| Recovery | exporter 429, storage outage, rollback and known-trace query |
| SLOs | independent request counters/histograms, not sampled trace rates |

## 4. Architecture and reliability theory

Trace completeness depends on SDK propagation, Collector health, routing, sampling and backend persistence. Backpressure and bounded retries may drop telemetry during long outages. Tempo commonly uses object storage, ingesters, query frontends and compactors; Jaeger v2 configuration is based on OpenTelemetry Collector patterns and its storage depends on the selected release. Size ingestion, WAL, queues, memory and query concurrency using measured peak load. Protect query APIs with a trusted auth layer and prevent sensitive DB values from reaching span attributes.

## 5. Game day: PostgreSQL latency plus tracing outage

A PostgreSQL-backed API's p95 rises to 2.5 seconds. During the same incident:
1. Collector exporters receive HTTP 429 and queues fill.
2. Gateway scaling breaks trace affinity and tail-sampling decisions.
3. Tempo object storage is throttled and TraceQL queries time out.
4. Jaeger storage is restarted with an ephemeral backend, losing historical traces.

Use independent application SLIs to establish user impact, correlate PostgreSQL connection waits and slow queries, inspect Collector and backend telemetry, contain data loss, restore approved persistent storage and validate trace retrieval. Record incident command timeline, blast radius, RPO/RTO, rollback criteria and owners.

## 6. Executable offline capstone gate

The following synthetic review manifest and standard-library tests **do not** query Jaeger, Tempo, Kubernetes or object storage. Replace declared booleans with independently verified evidence during a real change review.

### healthy.json

```json
{
  "owner": "tracing-platform",
  "environment": "staging",
  "change_id": "OBS-055",
  "jaeger_version_pinned": true,
  "tempo_version_pinned": true,
  "collector_version_pinned": true,
  "trace_ingestion_verified": true,
  "trace_query_verified": true,
  "storage_persistence_verified": true,
  "storage_restore_verified": true,
  "tenant_isolation_verified": true,
  "tls_auth_verified": true,
  "pii_redaction_verified": true,
  "trace_affinity_verified": true,
  "independent_slo_verified": true,
  "capacity_load_tested": true,
  "incident_drill_completed": true,
  "rollback_tested": true,
  "ingest_success_percent": 99,
  "minimum_ingest_success_percent": 98,
  "query_p95_ms": 350,
  "query_budget_ms": 1000,
  "trace_completeness_percent": 95,
  "minimum_trace_completeness_percent": 90,
  "object_storage_error_count": 0,
  "production_delete": false
}
```

### tracing_capstone_gate.py

```python
"""Synthetic Jaeger/Tempo reliability acceptance; no live backend access."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 for k in ["jaeger_version_pinned","tempo_version_pinned","collector_version_pinned","trace_ingestion_verified","trace_query_verified","storage_persistence_verified","storage_restore_verified","tenant_isolation_verified","tls_auth_verified","pii_redaction_verified","trace_affinity_verified","independent_slo_verified","capacity_load_tested","incident_drill_completed","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 for k in ("ingest_success_percent","minimum_ingest_success_percent","trace_completeness_percent","minimum_trace_completeness_percent"):
  v=p.get(k)
  if type(v) is not int or not 0<=v<=100:e.append("invalid "+k)
 for k in ("query_p95_ms","query_budget_ms"):
  v=p.get(k)
  if type(v) is not int or v<=0:e.append("invalid "+k)
 v=p.get("object_storage_error_count")
 if type(v) is not int or v<0:e.append("invalid object storage errors")
 for a,b,rule in (("ingest_success_percent","minimum_ingest_success_percent","min"),("trace_completeness_percent","minimum_trace_completeness_percent","min"),("query_p95_ms","query_budget_ms","max")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((rule=="min" and x<y) or (rule=="max" and x>y)):e.append("threshold missed "+a)
 return e
if __name__=="__main__":
 try: findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_tracing_capstone_gate.py

```python
import copy,json,unittest
from pathlib import Path
from tracing_capstone_gate import validate
class TracingCapstoneTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_change_id(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_04_jaeger_version_pinned(self):
  p=copy.deepcopy(self.p);p["jaeger_version_pinned"]=False;self.assertTrue(validate(p))
 def test_05_tempo_version_pinned(self):
  p=copy.deepcopy(self.p);p["tempo_version_pinned"]=False;self.assertTrue(validate(p))
 def test_06_collector_version_pinned(self):
  p=copy.deepcopy(self.p);p["collector_version_pinned"]=False;self.assertTrue(validate(p))
 def test_07_trace_ingestion_verified(self):
  p=copy.deepcopy(self.p);p["trace_ingestion_verified"]=False;self.assertTrue(validate(p))
 def test_08_trace_query_verified(self):
  p=copy.deepcopy(self.p);p["trace_query_verified"]=False;self.assertTrue(validate(p))
 def test_09_storage_persistence_verified(self):
  p=copy.deepcopy(self.p);p["storage_persistence_verified"]=False;self.assertTrue(validate(p))
 def test_10_storage_restore_verified(self):
  p=copy.deepcopy(self.p);p["storage_restore_verified"]=False;self.assertTrue(validate(p))
 def test_11_tenant_isolation_verified(self):
  p=copy.deepcopy(self.p);p["tenant_isolation_verified"]=False;self.assertTrue(validate(p))
 def test_12_tls_auth_verified(self):
  p=copy.deepcopy(self.p);p["tls_auth_verified"]=False;self.assertTrue(validate(p))
 def test_13_pii_redaction_verified(self):
  p=copy.deepcopy(self.p);p["pii_redaction_verified"]=False;self.assertTrue(validate(p))
 def test_14_trace_affinity_verified(self):
  p=copy.deepcopy(self.p);p["trace_affinity_verified"]=False;self.assertTrue(validate(p))
 def test_15_independent_slo_verified(self):
  p=copy.deepcopy(self.p);p["independent_slo_verified"]=False;self.assertTrue(validate(p))
 def test_16_capacity_load_tested(self):
  p=copy.deepcopy(self.p);p["capacity_load_tested"]=False;self.assertTrue(validate(p))
 def test_17_incident_drill_completed(self):
  p=copy.deepcopy(self.p);p["incident_drill_completed"]=False;self.assertTrue(validate(p))
 def test_18_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_19_ingest_success_percent(self):
  p=copy.deepcopy(self.p);p["ingest_success_percent"]=50;self.assertTrue(validate(p))
 def test_20_minimum_ingest_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_ingest_success_percent"]=101;self.assertTrue(validate(p))
 def test_21_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_ms"]=1200;self.assertTrue(validate(p))
 def test_22_query_budget_ms(self):
  p=copy.deepcopy(self.p);p["query_budget_ms"]=0;self.assertTrue(validate(p))
 def test_23_trace_completeness_percent(self):
  p=copy.deepcopy(self.p);p["trace_completeness_percent"]=50;self.assertTrue(validate(p))
 def test_24_minimum_trace_completeness_percent(self):
  p=copy.deepcopy(self.p);p["minimum_trace_completeness_percent"]=101;self.assertTrue(validate(p))
 def test_25_object_storage_error_count(self):
  p=copy.deepcopy(self.p);p["object_storage_error_count"]=-1;self.assertTrue(validate(p))
 def test_26_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter055 && cd chapter055
# Save blocks as healthy.json, tracing_capstone_gate.py, test_tracing_capstone_gate.py
python3 tracing_capstone_gate.py healthy.json
python3 -m unittest -v test_tracing_capstone_gate.py
```

Expected PASS and **28 authored Python tests**.

## 7. Twenty-four hands-on exercises

1. Inventory tracing services.
2. Pin Jaeger version.
3. Pin Tempo version.
4. Pin Collector version.
5. Review Jaeger ingestion.
6. Review Tempo ingestion.
7. Validate OTLP receiver.
8. Verify W3C propagation.
9. Verify trace-ID routing.
10. Review tail sampling.
11. Query Jaeger trace.
12. Query Tempo TraceQL.
13. Compare trace completeness.
14. Validate object storage.
15. Review retention.
16. Test storage restore.
17. Measure query p95.
18. Measure ingest success.
19. Review tenant isolation.
20. Review TLS/auth.
21. Validate PII redaction.
22. Simulate exporter 429.
23. Simulate object storage outage.
24. Execute rollback.

## 8. Twenty-four production failure scenarios

1. **Collector exporter 429:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
2. **Collector queue saturation:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
3. **Trace ID split across gateways:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
4. **Tail sampling drops errors:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
5. **Jaeger query timeout:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
6. **Tempo query timeout:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
7. **Jaeger storage outage:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
8. **Tempo object store throttling:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
9. **Object store permissions denied:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
10. **Ingester WAL pressure:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
11. **Compactor backlog:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
12. **Retention too short:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
13. **Missing parent spans:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
14. **Clock skew:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
15. **TraceQL syntax error:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
16. **Tenant isolation failure:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
17. **Unprotected query API:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
18. **PII in span attributes:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
19. **Query p95 SLO breached:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
20. **Ingest success SLO breached:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
21. **Trace completeness low:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
22. **Collector memory limiter rejects:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
23. **Restore incomplete:** inspect ingest, query, storage, security, sampling and independent SLI evidence.
24. **Rollback breaks query:** inspect ingest, query, storage, security, sampling and independent SLI evidence.

## 9. Eight production runbooks

1. **Ingest outage:** verify SDKs, Collector receivers/exporters, OTLP auth and backend ingest counters..
2. **Query outage:** inspect Jaeger/Tempo query endpoints, time ranges, storage reads and query p95..
3. **Storage failure:** review durable backend, object-store errors, WAL, compaction and retention..
4. **Trace gaps:** inspect propagation, trace-ID affinity, sampling policy and refused spans..
5. **Capacity incident:** review CPU/memory, queues, shard/block growth and load-test evidence..
6. **Security incident:** isolate affected tenants, restrict access, redact PII and follow approved escalation..
7. **Restore drill:** recover pinned config/storage, verify known trace IDs and measure RPO/RTO..
8. **Rollback:** revert versioned configs, confirm three-signal SLI independence and document closure..

## 10. 100-point enterprise assessment

| Domain | Points |
|---|---:|
| Jaeger/Tempo architecture and deployment | 20 |
| Ingestion, sampling and trace completeness | 20 |
| Storage, query performance and security | 20 |
| Offline gate, tests and observed evidence | 20 |
| Incident command, recovery and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. **Production acceptance additionally requires** witnessed ingestion/query, durable storage, privacy checks, performance/load tests and successful restore/rollback.

## 11. Evidence worksheet

```text
UTC / owner / change ID:
Jaeger / Tempo / Collector pinned versions:
Synthetic trace IDs and retrieval proof:
Ingest success / trace completeness / query p95:
Storage retention / WAL / object store / RPO-RTO:
Tenant isolation / TLS/auth / PII review:
Independent SLI metrics:
Exporter 429 / storage outage drill:
Rollback result / incident timeline:
Offline gate / 28 tests / final score:
```

**Companion:** [Chapter 055 enterprise capstone lab](labs/055-jaeger-tempo-production-reliability-performance-security-troubleshooting-capstone-lab.md).

**Part 11 complete. Next:** Chapter 056 — Kubernetes Observability Architecture for EKS, AKS and GKE (Part 12).
