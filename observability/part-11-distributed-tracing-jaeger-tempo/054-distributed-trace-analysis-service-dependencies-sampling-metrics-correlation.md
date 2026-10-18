# Chapter 054 — Distributed Trace Analysis, Service Dependencies, Sampling and Metrics Correlation

**Part 11 — Distributed Tracing with Jaeger and Tempo**  
**Audience:** SRE, DBRE, application and observability platform engineers.  
**Prerequisites:** Chapters 051–053, OpenTelemetry, Jaeger, Tempo, Prometheus and Grafana.

## 1. Objectives

Diagnose latency and errors using span trees, service graphs and critical-path analysis; correlate traces, logs and metrics; understand head/tail sampling bias; produce reliable RED metrics and avoid privacy/cardinality risks.

## 2. Architecture

```text
HTTP API -> order service -> PostgreSQL
                 |
                 +-> Redis cache -> Kafka worker
                         |
                   W3C traceparent
                         |
                   OTel SDK / Collector
                         |
               Jaeger / Tempo trace store
                         |
              trace ID + span graph
                /                \
          correlated logs     RED metrics
                \                /
                  Grafana incident view
```

A trace describes an observed request path; a service graph summarizes dependencies inferred from span relationships. Missing client/server spans, sampling and propagation gaps distort topology. Do not treat trace-derived RED rates as full traffic counts unless the data collection and sampling semantics justify that interpretation.

## 3. Trace analysis workflow

1. Establish user impact from independent request/error/latency SLIs.
2. Find representative trace IDs in Jaeger or Tempo.
3. Inspect root span, parent-child relationships, service transitions and critical path.
4. Separate server processing time, client waiting, retries, queue time and DB execution.
5. Compare healthy vs failing requests and inspect error status/events.
6. Correlate sanitized logs using trace_id/span_id and align UTC timestamps.
7. Verify dependency edges and cross-check with backend metrics.

## 4. Jaeger and Tempo query examples

In Grafana Explore with Tempo TraceQL:

```traceql
{ resource.service.name = "orders-api" }
```

```traceql
{ status = error }
```

```traceql
{ duration > 500ms }
```

Jaeger UI provides service, operation, tags and trace ID searches depending on the release. Check backend version and attribute semantic conventions before assuming query fields.

## 5. Span metrics, service graphs and sampling

Span metrics processors/connectors can derive request counts, error rates and latency distributions from spans. These may be biased when input spans are sampled or dropped. Independently instrumented application counters and histograms should remain authoritative for service SLOs. For service graphs, validate client/server span pairing, resource names and asynchronous hops.

Sampling tradeoffs:
- **Head sampling:** cheap but may drop rare failures.
- **Tail sampling:** retains interesting traces but needs full-trace routing, buffering and capacity.
- **Cardinality:** do not label metrics with trace IDs, user IDs, SQL text or request IDs.
- **Privacy:** do not export credentials, patient identifiers or SQL bind values.

## 6. SRE/DBRE scenario

An API has p95 2.8 seconds while traces show only 500 ms of PostgreSQL execution. Inspect retries, connection-pool waits, cache misses, Kafka queue delays and missing asynchronous spans. Verify independent service metrics before concluding the DB is healthy. Reconstruct critical path and identify instrumentation blind spots.

## 7. Executable offline correlation gate

The synthetic manifest below verifies declared controls and internally consistent example counters. It **does not** query Jaeger, Tempo, Loki or Prometheus.

### healthy.json

```json
{
  "owner": "tracing-sre",
  "environment": "staging",
  "service": "orders-api",
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "trace_context_verified": true,
  "service_graph_verified": true,
  "span_metrics_verified": true,
  "logs_correlated": true,
  "metrics_independent_of_sampling": true,
  "error_sampling_reviewed": true,
  "latency_sampling_reviewed": true,
  "high_cardinality_reviewed": true,
  "pii_redaction_reviewed": true,
  "clock_skew_reviewed": true,
  "backend_query_verified": true,
  "incident_replay_tested": true,
  "rollback_tested": true,
  "request_count": 10000,
  "error_count": 50,
  "observed_error_rate_percent": 0.5,
  "latency_p95_ms": 320,
  "latency_budget_ms": 500,
  "production_delete": false
}
```

### correlation_gate.py

```python
"""Offline trace/metrics correlation acceptance; no backend access."""
import json,sys,re
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","service"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 for k,n in (("trace_id",32),("span_id",16)):
  v=p.get(k)
  if not isinstance(v,str) or not re.fullmatch("[0-9a-f]{"+str(n)+"}",v) or int(v,16)==0:e.append("invalid "+k)
 for k in ["trace_context_verified","service_graph_verified","span_metrics_verified","logs_correlated","metrics_independent_of_sampling","error_sampling_reviewed","latency_sampling_reviewed","high_cardinality_reviewed","pii_redaction_reviewed","clock_skew_reviewed","backend_query_verified","incident_replay_tested","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 for k in ("request_count","error_count"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 if type(p.get("request_count")) is int and p["request_count"]<=0:e.append("request count zero")
 if all(type(p.get(k)) is int for k in ("request_count","error_count")) and p["error_count"]>p["request_count"]:e.append("errors exceed requests")
 v=p.get("observed_error_rate_percent")
 if type(v) not in (int,float) or not 0<=v<=100:e.append("invalid error rate")
 if all(type(p.get(k)) is int for k in ("request_count","error_count")) and p["request_count"]>0 and type(v) in (int,float) and abs(100*p["error_count"]/p["request_count"]-v)>0.01:e.append("error rate mismatch")
 for k in ("latency_p95_ms","latency_budget_ms"):
  if type(p.get(k)) is not int or p[k]<=0:e.append("invalid "+k)
 if type(p.get("latency_p95_ms")) is int and type(p.get("latency_budget_ms")) is int and p["latency_p95_ms"]>p["latency_budget_ms"]:e.append("latency budget exceeded")
 return e
if __name__=="__main__":
 try: errors=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_correlation_gate.py

```python
import copy,json,unittest
from pathlib import Path
from correlation_gate import validate
class CorrelationTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_service(self):
  p=copy.deepcopy(self.p);p["service"]="";self.assertTrue(validate(p))
 def test_04_trace_id(self):
  p=copy.deepcopy(self.p);p["trace_id"]="abc";self.assertTrue(validate(p))
 def test_05_span_id(self):
  p=copy.deepcopy(self.p);p["span_id"]="abc";self.assertTrue(validate(p))
 def test_06_trace_context_verified(self):
  p=copy.deepcopy(self.p);p["trace_context_verified"]=False;self.assertTrue(validate(p))
 def test_07_service_graph_verified(self):
  p=copy.deepcopy(self.p);p["service_graph_verified"]=False;self.assertTrue(validate(p))
 def test_08_span_metrics_verified(self):
  p=copy.deepcopy(self.p);p["span_metrics_verified"]=False;self.assertTrue(validate(p))
 def test_09_logs_correlated(self):
  p=copy.deepcopy(self.p);p["logs_correlated"]=False;self.assertTrue(validate(p))
 def test_10_metrics_independent_of_sampling(self):
  p=copy.deepcopy(self.p);p["metrics_independent_of_sampling"]=False;self.assertTrue(validate(p))
 def test_11_error_sampling_reviewed(self):
  p=copy.deepcopy(self.p);p["error_sampling_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_latency_sampling_reviewed(self):
  p=copy.deepcopy(self.p);p["latency_sampling_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_high_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["high_cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_pii_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_clock_skew_reviewed(self):
  p=copy.deepcopy(self.p);p["clock_skew_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_backend_query_verified(self):
  p=copy.deepcopy(self.p);p["backend_query_verified"]=False;self.assertTrue(validate(p))
 def test_17_incident_replay_tested(self):
  p=copy.deepcopy(self.p);p["incident_replay_tested"]=False;self.assertTrue(validate(p))
 def test_18_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_19_request_count(self):
  p=copy.deepcopy(self.p);p["request_count"]=0;self.assertTrue(validate(p))
 def test_20_error_count(self):
  p=copy.deepcopy(self.p);p["error_count"]=11000;self.assertTrue(validate(p))
 def test_21_observed_error_rate_percent(self):
  p=copy.deepcopy(self.p);p["observed_error_rate_percent"]=99;self.assertTrue(validate(p))
 def test_22_latency_p95_ms(self):
  p=copy.deepcopy(self.p);p["latency_p95_ms"]=800;self.assertTrue(validate(p))
 def test_23_latency_budget_ms(self):
  p=copy.deepcopy(self.p);p["latency_budget_ms"]=0;self.assertTrue(validate(p))
 def test_24_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter054 && cd chapter054
# Save blocks as healthy.json, correlation_gate.py, test_correlation_gate.py
python3 correlation_gate.py healthy.json
python3 -m unittest -v test_correlation_gate.py
```

Expected PASS and **26 authored Python tests**.

## 8. Twenty-four hands-on exercises

1. Build span tree.
2. Identify critical path.
3. Measure span duration.
4. Find slow PostgreSQL span.
5. Identify Redis cache miss.
6. Analyze Kafka worker hop.
7. Verify traceparent.
8. Check clock skew.
9. Find error spans.
10. Compare Jaeger vs Tempo.
11. Execute TraceQL service filter.
12. Execute TraceQL latency filter.
13. Build service graph.
14. Generate RED span metrics.
15. Compare sampled vs unsampled rates.
16. Correlate logs by trace ID.
17. Review high-cardinality tags.
18. Validate PII redaction.
19. Analyze head sampling.
20. Analyze tail sampling.
21. Measure trace completeness.
22. Simulate missing span.
23. Run offline unit tests.
24. Document incident timeline.

## 9. Twenty-four production failures

1. **Trace ID mismatch:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
2. **Parent span absent:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
3. **Clock skew distorts latency:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
4. **Sampling drops rare errors:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
5. **Tail sampler splits trace:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
6. **Service graph edge missing:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
7. **Span metrics double count:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
8. **Span metrics sampling bias:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
9. **Prometheus label explosion:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
10. **Query window too narrow:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
11. **Tempo query timeout:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
12. **Jaeger UI unavailable:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
13. **Log trace ID absent:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
14. **Database spans leak SQL values:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
15. **Async context lost:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
16. **Redis dependency not instrumented:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
17. **Kafka propagation lost:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
18. **HTTP retry duplicates spans:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
19. **Root span missing:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
20. **Metric unit mismatch:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
21. **Error-rate math wrong:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
22. **High p95 without trace:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
23. **Backend partial ingestion:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.
24. **Rollback loses correlation:** inspect trace IDs, propagation, graph edges, sampling, query, logs and independent SLIs.

## 10. Eight runbooks

1. **Slow request:** identify root trace, critical path, DB span and independent p95 metrics..
2. **Missing dependency edge:** verify client/server spans, resource names and graph processor..
3. **Sampling bias:** compare trace-derived RED with unsampled request metrics; document uncertainty..
4. **Trace/log mismatch:** verify trace_id/span_id injection, timestamps and log pipeline..
5. **Clock skew:** compare host clocks and duration measurements; avoid misleading causal ordering..
6. **PII/cardinality:** stop unsafe tags, scrub attributes and review metric dimensions..
7. **Backend query issue:** check time window, tenant, query health and storage availability..
8. **Recovery:** restore instrumentation, confirm span tree and metric SLI continuity..

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Trace tree and critical-path analysis | 20 |
| Service dependencies and RED metrics | 20 |
| Sampling, privacy and cardinality | 20 |
| Offline tests and correlation evidence | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires observed end-to-end traces, accurate SLI metrics and validated graph/log correlation.

**Companion:** [Chapter 054 hands-on lab](labs/054-distributed-trace-analysis-service-dependencies-sampling-metrics-correlation-lab.md).

**Next:** Chapter 055 — Jaeger and Tempo Production Reliability, Performance, Security and Troubleshooting Capstone.
