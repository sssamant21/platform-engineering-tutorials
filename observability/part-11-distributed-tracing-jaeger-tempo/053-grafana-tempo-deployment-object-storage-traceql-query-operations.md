# Chapter 053 — Grafana Tempo Deployment, Object Storage, TraceQL and Query Operations

**Part 11 — Distributed Tracing with Jaeger and Tempo**  
**Audience:** SRE, DBRE, Kubernetes and observability platform teams.  
**Prerequisites:** Chapters 051–052; OTLP, Kubernetes and object storage.

## 1. Objectives

Understand Tempo monolithic and distributed architectures, OTLP ingest, object storage, WAL, compaction, retention, TraceQL querying, Grafana integration, tenant isolation, operational metrics, incident response and recovery.

## 2. Architecture

```text
Applications -> OpenTelemetry Collector -> Tempo distributor
                                           |
                                        ingesters
                                       WAL / blocks
                                           |
                                 S3 / GCS / Azure Blob
                                           |
                                      compactor
                                           |
Grafana TraceQL -> query frontend -> querier -> storage
```

Tempo is optimized for storing and retrieving distributed traces with an object-storage-backed architecture. The exact component boundaries depend on deployment mode and release. A monolithic lab simplifies learning; production scale requires carefully reviewed distributed deployment and storage.

## 3. Tempo vs Jaeger operations

Jaeger and Tempo both support distributed trace investigations, but their query languages, deployment components and storage backends differ. Tempo integrates with Grafana and TraceQL; Jaeger has its own query/UI stack. Neither backend makes sampling loss disappear.

## 4. Local Tempo lab design

Pin a reviewed Tempo release. For a disposable local-only deployment, a **version-compatible single-binary Tempo config** can use filesystem storage; for enterprise environments use supported object storage and enforce auth/TLS at approved boundaries.

Example **configuration sketch** (verify schema against your pinned Tempo version):

```yaml
server:
  http_listen_port: 3200
distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 127.0.0.1:4317
        http:
          endpoint: 127.0.0.1:4318
storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks
    wal:
      path: /tmp/tempo/wal
compactor:
  compaction:
    block_retention: 168h
```

This is **not a production-ready configuration**: use persistent object storage, approved retention, correct replication, ingress controls, secure credentials and verified component compatibility. Local filesystem paths are disposable.

## 5. TraceQL queries

Example TraceQL queries in Grafana Explore, subject to the backend version and attribute conventions:

```traceql
{ resource.service.name = "orders-api" }
```

```traceql
{ span.http.request.method = "GET" }
```

```traceql
{ status = error }
```

```traceql
{ duration > 500ms }
```

Always scope time ranges, review cardinality, and compare with independent request metrics. The query path can be degraded even when ingestion succeeds.

## 6. Object storage, compaction and retention

Design buckets, access policies, encryption, replication, retention, legal holds and restore procedures. Compactor and ingester availability affect block lifecycle and query completeness. Monitor storage request errors, WAL pressure, ingest rejects, query p95 and query frontend saturation. Do not delete object-store data without owner approval and recovery evidence.

## 7. Security and tenancy

Tempo deployments often rely on an external authentication layer; enabling multi-tenancy does not automatically authenticate callers. Secure tenant identifiers at trusted gateways, isolate credentials, restrict network access and redact sensitive span attributes. Never expose unrestricted query APIs publicly.

## 8. Offline executable acceptance gate

This synthetic manifest records review assertions, not actual Tempo/S3 observations.

### healthy.json

```json
{
  "owner": "tracing-platform",
  "environment": "staging",
  "tempo_version_pinned": true,
  "storage_backend": "s3",
  "storage_bucket": "synthetic-tempo-staging",
  "retention_hours": 168,
  "query_p95_ms": 400,
  "query_budget_ms": 1000,
  "ingest_success_percent": 99,
  "minimum_ingest_success_percent": 98,
  "traceql_query_tested": true,
  "otlp_ingest_tested": true,
  "storage_write_tested": true,
  "storage_read_tested": true,
  "compactor_reviewed": true,
  "tenant_isolation_reviewed": true,
  "tls_auth_reviewed": true,
  "pii_redaction_reviewed": true,
  "capacity_reviewed": true,
  "restore_tested": true,
  "rollback_tested": true,
  "production_delete": false
}
```

### tempo_gate.py

```python
"""Synthetic Tempo review gate; no Tempo, S3 or Grafana API calls."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","storage_bucket"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("storage_backend") not in ("s3","gcs","azure"):e.append("unsupported production storage")
 for k in ["tempo_version_pinned","traceql_query_tested","otlp_ingest_tested","storage_write_tested","storage_read_tested","compactor_reviewed","tenant_isolation_reviewed","tls_auth_reviewed","pii_redaction_reviewed","capacity_reviewed","restore_tested","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 v=p.get("retention_hours")
 if type(v) is not int or not 1<=v<=8760:e.append("invalid retention")
 for k in ("query_p95_ms","query_budget_ms"):
  v=p.get(k)
  if type(v) is not int or v<=0:e.append("invalid "+k)
 for k in ("ingest_success_percent","minimum_ingest_success_percent"):
  v=p.get(k)
  if type(v) is not int or not 0<=v<=100:e.append("invalid "+k)
 for a,b,rule in (("query_p95_ms","query_budget_ms","max"),("ingest_success_percent","minimum_ingest_success_percent","min")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((rule=="max" and x>y) or (rule=="min" and x<y)):e.append("SLO threshold missed "+a)
 return e
if __name__=="__main__":
 try: errors=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_tempo_gate.py

```python
import copy,json,unittest
from pathlib import Path
from tempo_gate import validate
class TempoGateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_storage_backend(self):
  p=copy.deepcopy(self.p);p["storage_backend"]="memory";self.assertTrue(validate(p))
 def test_04_storage_bucket(self):
  p=copy.deepcopy(self.p);p["storage_bucket"]="";self.assertTrue(validate(p))
 def test_05_retention_hours(self):
  p=copy.deepcopy(self.p);p["retention_hours"]=0;self.assertTrue(validate(p))
 def test_06_retention_hours(self):
  p=copy.deepcopy(self.p);p["retention_hours"]=100000;self.assertTrue(validate(p))
 def test_07_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_ms"]=1500;self.assertTrue(validate(p))
 def test_08_query_budget_ms(self):
  p=copy.deepcopy(self.p);p["query_budget_ms"]=0;self.assertTrue(validate(p))
 def test_09_ingest_success_percent(self):
  p=copy.deepcopy(self.p);p["ingest_success_percent"]=80;self.assertTrue(validate(p))
 def test_10_minimum_ingest_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_ingest_success_percent"]=101;self.assertTrue(validate(p))
 def test_11_tempo_version_pinned(self):
  p=copy.deepcopy(self.p);p["tempo_version_pinned"]=False;self.assertTrue(validate(p))
 def test_12_traceql_query_tested(self):
  p=copy.deepcopy(self.p);p["traceql_query_tested"]=False;self.assertTrue(validate(p))
 def test_13_otlp_ingest_tested(self):
  p=copy.deepcopy(self.p);p["otlp_ingest_tested"]=False;self.assertTrue(validate(p))
 def test_14_storage_write_tested(self):
  p=copy.deepcopy(self.p);p["storage_write_tested"]=False;self.assertTrue(validate(p))
 def test_15_storage_read_tested(self):
  p=copy.deepcopy(self.p);p["storage_read_tested"]=False;self.assertTrue(validate(p))
 def test_16_compactor_reviewed(self):
  p=copy.deepcopy(self.p);p["compactor_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_tenant_isolation_reviewed(self):
  p=copy.deepcopy(self.p);p["tenant_isolation_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_tls_auth_reviewed(self):
  p=copy.deepcopy(self.p);p["tls_auth_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_pii_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_20_capacity_reviewed(self):
  p=copy.deepcopy(self.p);p["capacity_reviewed"]=False;self.assertTrue(validate(p))
 def test_21_restore_tested(self):
  p=copy.deepcopy(self.p);p["restore_tested"]=False;self.assertTrue(validate(p))
 def test_22_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_23_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter053 && cd chapter053
# Save blocks as healthy.json, tempo_gate.py, test_tempo_gate.py
python3 tempo_gate.py healthy.json
python3 -m unittest -v test_tempo_gate.py
```

Expected PASS and **25 authored Python tests**.

## 9. Twenty-four exercises

1. Review Tempo architecture.
2. Choose monolithic vs distributed.
3. Pin Tempo image.
4. Review OTLP receiver.
5. Configure staging storage.
6. Verify S3/GCS/Azure permissions.
7. Review ingester WAL.
8. Review distributor.
9. Review query frontend.
10. Review querier.
11. Review compactor.
12. Set retention policy.
13. Generate synthetic spans.
14. Query trace ID.
15. Execute TraceQL filter.
16. Correlate Grafana metrics.
17. Validate tenant isolation.
18. Test TLS/auth gateway.
19. Inspect ingest rate.
20. Inspect query p95.
21. Simulate object store outage.
22. Test restore.
23. Run offline unit tests.
24. Document rollback.

## 10. Twenty-four production failure scenarios

1. **OTLP receiver unreachable:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
2. **Wrong transport protocol:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
3. **Distributor overloaded:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
4. **Ingester OOM:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
5. **Ingester WAL corrupt:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
6. **Object store access denied:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
7. **Object store throttled:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
8. **Missing storage bucket:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
9. **Compactor stalled:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
10. **Retention misconfigured:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
11. **Query frontend saturated:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
12. **Querier times out:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
13. **TraceQL syntax invalid:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
14. **Query time range wrong:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
15. **Grafana datasource misconfigured:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
16. **Tenant header missing:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
17. **Tenant data leakage:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
18. **TLS handshake failure:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
19. **PII in spans:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
20. **Ingest success below budget:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
21. **Query p95 above budget:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
22. **Cache pressure:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
23. **Restore fails:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.
24. **Rollback fails:** inspect ingestion, storage, compaction, query, tenancy and independent SLIs.

## 11. Eight production runbooks

1. **No traces:** inspect SDK/Collector export, distributor, ingester and storage write path..
2. **Query outage:** inspect TraceQL syntax, time range, query frontend, querier and storage reads..
3. **Object storage failure:** check permissions, throttling, regional availability and WAL buffering..
4. **Retention incident:** review compactor state, retention policy and approved data governance..
5. **High ingest:** inspect distributor/ingester CPU, memory, WAL and accepted/rejected spans..
6. **Tenant isolation:** verify auth proxy, tenant headers, query permissions and audit evidence..
7. **Privacy:** stop unsafe spans, review redaction and coordinate authorized data handling..
8. **Restore:** recover approved storage/config, verify trace IDs and record RPO/RTO and rollback..

## 12. SRE/DBRE incident simulation

An API backed by PostgreSQL slows down during a Tempo object-storage throttling event. Spans arrive at distributors, but Grafana TraceQL searches intermittently time out. Verify user impact from metrics, inspect ingester WAL and object-store read/write errors, test query frontend capacity, restore backend health and record recovery evidence.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| Tempo architecture and deployment | 20 |
| Object storage, compaction and retention | 20 |
| TraceQL and Grafana operations | 20 |
| Offline tests and governance | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires witnessed OTLP ingestion, query retrieval, object storage persistence, security and restore tests.

**Companion:** [Chapter 053 hands-on lab](labs/053-grafana-tempo-deployment-object-storage-traceql-query-operations-lab.md).

**Next:** Chapter 054 — Distributed Trace Analysis, Service Dependencies, Sampling and Metrics Correlation.
