# Chapter 052 — Jaeger Deployment, Trace Collection, Storage and Query Operations

**Part 11 — Distributed Tracing with Jaeger and Tempo**  
**Audience:** SRE, DBRE, platform engineering and tracing operations.  
**Prerequisites:** Chapter 051, OpenTelemetry Collector and Docker or Kubernetes.

## 1. Learning objectives

Deploy Jaeger v2 in an isolated lab, ingest OTLP traces, query them by trace ID, understand storage persistence and retention, secure trace access, monitor operational health, troubleshoot outages and rehearse rollback.

## 2. Jaeger v2 architecture

```text
HTTP / worker / PostgreSQL services
             |
        OTel SDKs
             |
         Collector
             |
     OTLP gRPC or HTTP
             |
      Jaeger v2 service
       /           \
  trace storage   query API / UI
       |               |
 retention/backup  operator investigation
```

Jaeger v2 builds on OpenTelemetry Collector configuration patterns. Older Jaeger v1 `collector`, `agent`, `query` and storage configuration examples are **not directly interchangeable** with v2. Production storage capabilities depend on the selected Jaeger version and backend; verify the release documentation and test persistence.

## 3. Executable isolated local lab

For an exploratory disposable environment, pin a reviewed Jaeger v2 image version or digest. Do not deploy an unpinned `latest` image in production.

```bash
# Set to a vetted Jaeger v2 image tag or digest.
export JAEGER_IMAGE='jaegertracing/jaeger:REPLACE_WITH_PINNED_V2'
docker run --rm --name jaeger-ch052 \
  -p 127.0.0.1:16686:16686 \
  -p 127.0.0.1:4317:4317 \
  -p 127.0.0.1:4318:4318 \
  "$JAEGER_IMAGE"
```

This quick-start assumes the selected release supports the corresponding ports and defaults. Validate the image's documented quick-start behavior first. Default in-memory storage is **ephemeral**, suitable only for learning; confirm the storage implementation before production use.

## 4. Send a synthetic trace over OTLP HTTP

```bash
python3 - <<'PY'
import json,time,urllib.request
now=time.time_ns()
body={"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"jaeger-ch052-lab"}}]},"scopeSpans":[{"scope":{"name":"chapter052"},"spans":[{"traceId":"0123456789abcdef0123456789abcdef","spanId":"0123456789abcdef","name":"synthetic-db-read","kind":3,"startTimeUnixNano":str(now),"endTimeUnixNano":str(now+50000000)}]}]}]}
req=urllib.request.Request("http://127.0.0.1:4318/v1/traces",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=5) as resp: print("OTLP HTTP status:",resp.status)
PY
```

Open the local Jaeger UI at `http://127.0.0.1:16686` and search for service `jaeger-ch052-lab` or trace ID `0123456789abcdef0123456789abcdef`. HTTP success confirms receiver acceptance, **not** persisted storage or successful query; verify retrieval separately.

## 5. Storage, retention and capacity

Select a supported storage backend and size for spans/second, retention, average span bytes, replicas and peak query load. Protect backup/restore credentials and enforce retention policy. Avoid deleting indices or trace storage without owner approval, legal-hold review and recoverability evidence. Track backend write failures, disk I/O, query latency, memory, CPU and ingestion drop rates.

## 6. Security and multi-tenancy

Restrict OTLP ingress, secure query UI/API, terminate TLS and authentication at approved boundaries, redact PII and SQL bind values, and apply RBAC or network isolation appropriate to the deployment. Do not assume Jaeger alone provides full enterprise multi-tenancy controls.

## 7. Kubernetes staging considerations

Pin image digests, apply resource requests/limits, readiness and startup probes, network policies, PodDisruptionBudgets, anti-affinity where justified, and explicit persistent storage configuration. Run canary queries before and after each upgrade.

## 8. Executable offline operational gate

This synthetic gate checks declared review fields. It does **not** connect to Jaeger, validate real security or prove storage persistence.

### healthy.json

```json
{
  "owner": "tracing-platform",
  "environment": "staging",
  "jaeger_major_version": 2,
  "version_pinned": true,
  "otlp_grpc_port": 4317,
  "otlp_http_port": 4318,
  "query_port": 16686,
  "trace_ingestion_tested": true,
  "trace_query_tested": true,
  "storage_persistence_tested": true,
  "retention_reviewed": true,
  "authentication_reviewed": true,
  "tls_reviewed": true,
  "pii_redaction_tested": true,
  "capacity_reviewed": true,
  "backup_restore_tested": true,
  "rollback_tested": true,
  "export_success_percent": 99,
  "minimum_export_success_percent": 98,
  "query_p95_ms": 450,
  "query_p95_budget_ms": 1000,
  "production_delete": false
}
```

### jaeger_gate.py

```python
"""Synthetic Jaeger v2 operational acceptance gate; no Jaeger calls."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if type(p.get("jaeger_major_version")) is not int or p["jaeger_major_version"]!=2:e.append("unreviewed Jaeger major version")
 for k in ["version_pinned","trace_ingestion_tested","trace_query_tested","storage_persistence_tested","retention_reviewed","authentication_reviewed","tls_reviewed","pii_redaction_tested","capacity_reviewed","backup_restore_tested","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("otlp_grpc_port","otlp_http_port","query_port"):
  if type(p.get(k)) is not int or not 1<=p[k]<=65535:e.append("invalid "+k)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 for k in ("export_success_percent","minimum_export_success_percent"):
  if type(p.get(k)) is not int or not 0<=p[k]<=100:e.append("invalid "+k)
 for k in ("query_p95_ms","query_p95_budget_ms"):
  if type(p.get(k)) is not int or p[k]<=0:e.append("invalid "+k)
 if type(p.get("export_success_percent")) is int and type(p.get("minimum_export_success_percent")) is int and p["export_success_percent"]<p["minimum_export_success_percent"]:e.append("export threshold missed")
 if type(p.get("query_p95_ms")) is int and type(p.get("query_p95_budget_ms")) is int and p["query_p95_ms"]>p["query_p95_budget_ms"]:e.append("query latency threshold missed")
 return e
if __name__=="__main__":
 try: errors=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_jaeger_gate.py

```python
import copy,json,unittest
from pathlib import Path
from jaeger_gate import validate
class JaegerGateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_jaeger_major_version(self):
  p=copy.deepcopy(self.p);p["jaeger_major_version"]=1;self.assertTrue(validate(p))
 def test_04_otlp_grpc_port(self):
  p=copy.deepcopy(self.p);p["otlp_grpc_port"]=0;self.assertTrue(validate(p))
 def test_05_otlp_http_port(self):
  p=copy.deepcopy(self.p);p["otlp_http_port"]=0;self.assertTrue(validate(p))
 def test_06_query_port(self):
  p=copy.deepcopy(self.p);p["query_port"]=0;self.assertTrue(validate(p))
 def test_07_version_pinned(self):
  p=copy.deepcopy(self.p);p["version_pinned"]=False;self.assertTrue(validate(p))
 def test_08_trace_ingestion_tested(self):
  p=copy.deepcopy(self.p);p["trace_ingestion_tested"]=False;self.assertTrue(validate(p))
 def test_09_trace_query_tested(self):
  p=copy.deepcopy(self.p);p["trace_query_tested"]=False;self.assertTrue(validate(p))
 def test_10_storage_persistence_tested(self):
  p=copy.deepcopy(self.p);p["storage_persistence_tested"]=False;self.assertTrue(validate(p))
 def test_11_retention_reviewed(self):
  p=copy.deepcopy(self.p);p["retention_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_authentication_reviewed(self):
  p=copy.deepcopy(self.p);p["authentication_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_tls_reviewed(self):
  p=copy.deepcopy(self.p);p["tls_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_pii_redaction_tested(self):
  p=copy.deepcopy(self.p);p["pii_redaction_tested"]=False;self.assertTrue(validate(p))
 def test_15_capacity_reviewed(self):
  p=copy.deepcopy(self.p);p["capacity_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_backup_restore_tested(self):
  p=copy.deepcopy(self.p);p["backup_restore_tested"]=False;self.assertTrue(validate(p))
 def test_17_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_18_export_success_percent(self):
  p=copy.deepcopy(self.p);p["export_success_percent"]=70;self.assertTrue(validate(p))
 def test_19_minimum_export_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_export_success_percent"]=101;self.assertTrue(validate(p))
 def test_20_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_ms"]=1200;self.assertTrue(validate(p))
 def test_21_query_p95_budget_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_budget_ms"]=0;self.assertTrue(validate(p))
 def test_22_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter052 && cd chapter052
# Save blocks as healthy.json, jaeger_gate.py and test_jaeger_gate.py
python3 jaeger_gate.py healthy.json
python3 -m unittest -v test_jaeger_gate.py
```

Expected PASS and **24 authored Python tests**.

## 9. Twenty-four hands-on exercises

1. Pin Jaeger v2 image.
2. Review Jaeger v2 architecture.
3. Choose dev vs production storage.
4. Configure OTLP gRPC receiver.
5. Configure OTLP HTTP receiver.
6. Configure query UI access.
7. Run Jaeger in isolated lab.
8. Create synthetic parent span.
9. Create synthetic child span.
10. Inject W3C traceparent.
11. Export via OTel Collector.
12. Verify backend ingestion.
13. Search trace by ID.
14. Check service and operation queries.
15. Validate span timing.
16. Validate storage persistence.
17. Plan retention.
18. Inspect Jaeger process metrics.
19. Review TLS and authentication.
20. Redact sensitive attributes.
21. Load test ingest throughput.
22. Simulate storage outage.
23. Restore from backup.
24. Execute rollback.

## 10. Twenty-four production failures

1. **Receiver bind conflict:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
2. **OTLP transport mismatch:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
3. **Jaeger v1 config reused on v2:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
4. **Bad Collector exporter endpoint:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
5. **Missing service.name:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
6. **Malformed trace ID:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
7. **Broken parent relationship:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
8. **Storage not persistent:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
9. **Storage write denied:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
10. **Query UI unavailable:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
11. **Query latency high:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
12. **Sampling hides trace:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
13. **Retention deletes expected trace:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
14. **Disk pressure:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
15. **Object store unavailable:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
16. **TLS certificate expired:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
17. **Unauthorized query access:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
18. **PII exposed in tags:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
19. **Collector queue full:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
20. **Ingest OOM:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
21. **Clock skew:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
22. **Query returns partial trace:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
23. **Backup restore incomplete:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.
24. **Rollback incompatible:** inspect Jaeger v2 configuration, OTLP, storage, query, security and independent SLIs.

## 11. Eight production runbooks

1. **Ingest failure:** inspect OTLP receiver, SDK/Collector export, accepted/rejected spans and Jaeger logs..
2. **Query failure:** verify trace ID, query endpoint, storage read path and query latency..
3. **Storage incident:** inspect backend durability, disk/object-store access, compaction and retention..
4. **High latency:** isolate backend query saturation from application latency and inspect storage throughput..
5. **Missing spans:** verify W3C context, sampling, Collector routing and span timing..
6. **Security incident:** restrict access, stop PII ingestion, rotate secrets and follow incident handling..
7. **Upgrade failure:** revert pinned Jaeger v2 image/config with verified compatible storage schema..
8. **Restore:** recover staging storage, validate a known trace and record RPO/RTO evidence..

## 12. SRE/DBRE incident simulation

During a PostgreSQL latency incident, Jaeger ingest appears healthy but queries return no spans. The tracing backend was restarted using ephemeral storage. Prove application impact independently, inspect storage settings and Jaeger logs, verify trace IDs, restore the approved persistent backend in staging and document RPO/RTO and rollback.

## 13. 100-point assessment

| Area | Points |
|---|---:|
| Jaeger v2 architecture and deployment | 20 |
| OTLP ingestion and trace querying | 20 |
| Storage, retention and capacity | 20 |
| Automated gate and troubleshooting | 20 |
| Incident response and recovery | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Production acceptance requires witnessed ingestion, query, storage persistence, security and recovery tests.

**Companion:** [Chapter 052 hands-on lab](labs/052-jaeger-deployment-trace-collection-storage-query-operations-lab.md).

**Next:** Chapter 053 — Grafana Tempo Deployment, Object Storage, TraceQL and Query Operations.
