# Chapter 051 — Distributed Tracing Architecture with Jaeger and Grafana Tempo

**Part 11 — Distributed Tracing with Jaeger and Tempo**  
**Audience:** SRE/DBRE, platform engineers and observability architects.  
**Prerequisites:** Chapters 046–050; OpenTelemetry SDKs and Collector.

## 1. Objectives

Understand distributed tracing architecture, Jaeger and Grafana Tempo deployment patterns, OTLP ingestion, query paths, trace storage, retention, security, cost, correlation and incident response.

## 2. Reference architecture

```text
API -> worker -> PostgreSQL
 |       |          |
 +-- W3C traceparent --+
           |
        OTel SDK
           |
     OTel Collector
           |
       OTLP export
           |
  Jaeger OR Grafana Tempo
           |
    trace search/query
           |
 Grafana / Jaeger UI + logs + metrics
```

A trace is a causal collection of spans sharing a 128-bit trace ID; spans have 64-bit span IDs. Correct context propagation is essential across HTTP, messaging and asynchronous boundaries.

## 3. Jaeger vs Tempo

| Area | Jaeger | Grafana Tempo |
|---|---|---|
| Role | Open-source distributed tracing backend and UI | Open-source tracing backend integrated with Grafana |
| Ingestion | OTLP supported in modern deployments | OTLP via distributors |
| Storage | Depends on Jaeger version/deployment and configured backend | Object-storage-oriented architecture |
| Query | Jaeger UI/APIs | Grafana and TraceQL |
| Scaling | Architecture varies by version and storage choice | Distributors, ingesters, queriers, query frontend, compactor |
| Caveat | Verify Jaeger v2 configuration and storage support | Validate tenant/auth layer and object store durability |

Do not treat Jaeger and Tempo as interchangeable YAML deployments. Pin versions and validate compatibility.

## 4. Trace modeling

Instrument inbound HTTP spans, outbound dependencies and database calls with correct parent relationships. Attach bounded safe attributes such as service, operation and DB system; avoid credentials, patient identifiers and SQL bind values. Correlate logs through trace and span IDs. Avoid using sampled trace counts as the sole error-rate SLI.

## 5. Tempo operational architecture

Tempo commonly separates distributors (ingest), ingesters (buffer/write), queriers/query frontends (retrieve) and compactors (block lifecycle). Production requires durable object storage, access isolation, capacity planning, TLS/auth at appropriate boundaries, safe retention and restore drills. A single-binary local demo is useful for learning but not HA.

## 6. Jaeger operational architecture

Jaeger provides trace collection, storage and query components; topology and supported storage backends vary across releases. In particular, Jaeger v2 is built on OpenTelemetry Collector architecture, so do not reuse old v1 component configuration blindly. Test actual OTLP endpoints, query UI, storage persistence and RBAC.

## 7. Synthetic OTLP trace smoke test

With an approved **local** Collector or backend OTLP HTTP receiver on `127.0.0.1:4318`:

```bash
curl -fsS -X POST http://127.0.0.1:4318/v1/traces \
  -H 'Content-Type: application/json' \
  -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"orders-api"}}]},"scopeSpans":[{"scope":{"name":"chapter051"},"spans":[{"traceId":"0123456789abcdef0123456789abcdef","spanId":"0123456789abcdef","name":"GET /orders","kind":2,"startTimeUnixNano":"1792324800000000000","endTimeUnixNano":"1792324800250000000"}]}]}]}'
```

The timestamp is illustrative; use current timestamps when testing. A successful OTLP response does not prove storage or query retrieval. Verify the trace ID in the backend UI.

## 8. Executable offline architecture gate

The following manifest is **synthetic attestation**, not proof of live security or backend health.

### healthy.json

```json
{
  "owner": "tracing-sre",
  "environment": "staging",
  "backend": "tempo",
  "service": "orders-api",
  "signals": [
    "traces"
  ],
  "resource_attributes": [
    "service.name",
    "service.version"
  ],
  "trace_propagation_tested": true,
  "otlp_transport_tested": true,
  "query_path_tested": true,
  "retention_reviewed": true,
  "object_storage_reviewed": true,
  "tenant_isolation_reviewed": true,
  "pii_redaction_tested": true,
  "sampling_reviewed": true,
  "capacity_reviewed": true,
  "restore_tested": true,
  "rollback_tested": true,
  "trace_id_length": 32,
  "span_id_length": 16,
  "trace_duration_ms": 250,
  "trace_latency_budget_ms": 1000,
  "production_delete": false
}
```

### tracing_gate.py

```python
"""Offline tracing architecture review, not live backend validation."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","service"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("backend") not in ("jaeger","tempo"):e.append("invalid backend")
 for k,req in (("signals",{"traces"}),("resource_attributes",{"service.name","service.version"})):
  v=p.get(k)
  if not isinstance(v,list) or not req.issubset(v):e.append("missing "+k)
 for k in ["trace_propagation_tested","otlp_transport_tested","query_path_tested","retention_reviewed","object_storage_reviewed","tenant_isolation_reviewed","pii_redaction_tested","sampling_reviewed","capacity_reviewed","restore_tested","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe action")
 for k,v in (("trace_id_length",32),("span_id_length",16)):
  if type(p.get(k)) is not int or p[k]!=v:e.append("invalid "+k)
 for k in ("trace_duration_ms","trace_latency_budget_ms"):
  if type(p.get(k)) is not int or p[k]<=0:e.append("invalid "+k)
 if type(p.get("trace_duration_ms")) is int and type(p.get("trace_latency_budget_ms")) is int and p["trace_duration_ms"]>p["trace_latency_budget_ms"]:e.append("latency budget exceeded")
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_tracing_gate.py

```python
import copy,json,unittest
from pathlib import Path
from tracing_gate import validate
class TracingTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_backend(self):
  p=copy.deepcopy(self.p);p["backend"]="invalid";self.assertTrue(validate(p))
 def test_04_service(self):
  p=copy.deepcopy(self.p);p["service"]="";self.assertTrue(validate(p))
 def test_05_signals(self):
  p=copy.deepcopy(self.p);p["signals"]=[];self.assertTrue(validate(p))
 def test_06_resource_attributes(self):
  p=copy.deepcopy(self.p);p["resource_attributes"]=[];self.assertTrue(validate(p))
 def test_07_trace_propagation_tested(self):
  p=copy.deepcopy(self.p);p["trace_propagation_tested"]=False;self.assertTrue(validate(p))
 def test_08_otlp_transport_tested(self):
  p=copy.deepcopy(self.p);p["otlp_transport_tested"]=False;self.assertTrue(validate(p))
 def test_09_query_path_tested(self):
  p=copy.deepcopy(self.p);p["query_path_tested"]=False;self.assertTrue(validate(p))
 def test_10_retention_reviewed(self):
  p=copy.deepcopy(self.p);p["retention_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_object_storage_reviewed(self):
  p=copy.deepcopy(self.p);p["object_storage_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_tenant_isolation_reviewed(self):
  p=copy.deepcopy(self.p);p["tenant_isolation_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_pii_redaction_tested(self):
  p=copy.deepcopy(self.p);p["pii_redaction_tested"]=False;self.assertTrue(validate(p))
 def test_14_sampling_reviewed(self):
  p=copy.deepcopy(self.p);p["sampling_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_capacity_reviewed(self):
  p=copy.deepcopy(self.p);p["capacity_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_restore_tested(self):
  p=copy.deepcopy(self.p);p["restore_tested"]=False;self.assertTrue(validate(p))
 def test_17_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_18_trace_id_length(self):
  p=copy.deepcopy(self.p);p["trace_id_length"]=12;self.assertTrue(validate(p))
 def test_19_span_id_length(self):
  p=copy.deepcopy(self.p);p["span_id_length"]=8;self.assertTrue(validate(p))
 def test_20_trace_duration_ms(self):
  p=copy.deepcopy(self.p);p["trace_duration_ms"]=2000;self.assertTrue(validate(p))
 def test_21_trace_latency_budget_ms(self):
  p=copy.deepcopy(self.p);p["trace_latency_budget_ms"]=0;self.assertTrue(validate(p))
 def test_22_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter051 && cd chapter051
# Save the three blocks as healthy.json, tracing_gate.py, test_tracing_gate.py
python3 tracing_gate.py healthy.json
python3 -m unittest -v test_tracing_gate.py
```

Expected PASS and **24 authored Python tests**.

## 9. Twenty-four exercises

1. Diagram tracing architecture.
2. Choose Jaeger vs Tempo.
3. Review collector ingestion.
4. Define OTLP transport.
5. Review trace/span IDs.
6. Create parent-child spans.
7. Trace HTTP dependencies.
8. Trace PostgreSQL calls.
9. Propagate W3C context.
10. Correlate logs.
11. Inspect sampling impact.
12. Model retention.
13. Review object storage.
14. Model ingest volume.
15. Review query path.
16. Test tenant boundaries.
17. Review TLS/auth.
18. Test redaction.
19. Inspect query latency.
20. Inspect storage errors.
21. Simulate lost spans.
22. Simulate backend outage.
23. Run offline gate.
24. Document rollback.

## 10. Twenty-four production failures

1. **OTLP receiver unavailable:** inspect propagation, ingestion, storage, query, security and independent SLIs.
2. **Trace context lost:** inspect propagation, ingestion, storage, query, security and independent SLIs.
3. **Parent span missing:** inspect propagation, ingestion, storage, query, security and independent SLIs.
4. **Duplicate spans:** inspect propagation, ingestion, storage, query, security and independent SLIs.
5. **Jaeger query unavailable:** inspect propagation, ingestion, storage, query, security and independent SLIs.
6. **Tempo query frontend unavailable:** inspect propagation, ingestion, storage, query, security and independent SLIs.
7. **Object storage throttling:** inspect propagation, ingestion, storage, query, security and independent SLIs.
8. **Compactor stalled:** inspect propagation, ingestion, storage, query, security and independent SLIs.
9. **Distributor overload:** inspect propagation, ingestion, storage, query, security and independent SLIs.
10. **Ingester OOM:** inspect propagation, ingestion, storage, query, security and independent SLIs.
11. **Trace ID invalid:** inspect propagation, ingestion, storage, query, security and independent SLIs.
12. **Span ID invalid:** inspect propagation, ingestion, storage, query, security and independent SLIs.
13. **Query times out:** inspect propagation, ingestion, storage, query, security and independent SLIs.
14. **Sampling hides errors:** inspect propagation, ingestion, storage, query, security and independent SLIs.
15. **Tenant leakage:** inspect propagation, ingestion, storage, query, security and independent SLIs.
16. **Unauthorized export:** inspect propagation, ingestion, storage, query, security and independent SLIs.
17. **TLS trust failure:** inspect propagation, ingestion, storage, query, security and independent SLIs.
18. **PII in span attributes:** inspect propagation, ingestion, storage, query, security and independent SLIs.
19. **Retention mismatch:** inspect propagation, ingestion, storage, query, security and independent SLIs.
20. **Clock skew:** inspect propagation, ingestion, storage, query, security and independent SLIs.
21. **Missing log correlation:** inspect propagation, ingestion, storage, query, security and independent SLIs.
22. **Service graph incomplete:** inspect propagation, ingestion, storage, query, security and independent SLIs.
23. **Restore fails:** inspect propagation, ingestion, storage, query, security and independent SLIs.
24. **Rollback fails:** inspect propagation, ingestion, storage, query, security and independent SLIs.

## 11. Eight production runbooks

1. **No traces:** inspect SDK, OTLP receiver, Collector exporter and backend ingest..
2. **Broken trace tree:** inspect traceparent, parent IDs and async propagation..
3. **Slow trace queries:** inspect backend query frontend, storage and query scope..
4. **Storage incident:** inspect object store errors, retention, compaction and permissions..
5. **Ingest pressure:** inspect accepted/rejected spans, queue, CPU, memory and scaling..
6. **Tenant/security issue:** verify auth, tenancy headers, access controls and redaction..
7. **Sampling gap:** compare independent request SLIs; validate head/tail policy..
8. **Recovery:** restore pinned config, validate trace retrieval and record rollback evidence..

## 12. Production SRE/DBRE scenario

A PostgreSQL-backed API experiences slow queries. Grafana traces disappear during an object-storage throttling event, while the Collector reports successful OTLP delivery. Compare independent request metrics, verify trace IDs, inspect backend ingest/storage/query health, correlate PostgreSQL performance and restore trace retrieval safely.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| Architecture and trace data model | 20 |
| Jaeger/Tempo deployment and storage | 20 |
| Correlation, privacy and sampling | 20 |
| Offline gate and tests | 20 |
| Incident investigation and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires observed end-to-end ingestion and query, storage durability, access controls and recovery.

**Companion:** [Chapter 051 hands-on lab](labs/051-distributed-tracing-architecture-jaeger-grafana-tempo-lab.md).

**Next:** Chapter 052 — Jaeger Deployment, Trace Collection, Storage and Query Operations.
