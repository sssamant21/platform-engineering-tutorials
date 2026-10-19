# Chapter 067 — Application Distributed Tracing, Service Maps and Dependency Performance Analysis

**Part 14 — Application Performance Monitoring**  
**Audience:** SRE, DBRE, backend engineers and incident responders.  
**Prerequisites:** Chapter 066; OpenTelemetry, Jaeger/Tempo and HTTP/Kafka basics.

## Learning objectives

Instrument synchronous and asynchronous requests, propagate W3C trace context, analyze span trees and critical paths, build service maps, correlate dependency latency with metrics/logs, and operate sampling and Collector pipelines securely.

## Reference architecture

```text
User -> API gateway -> web service -> PostgreSQL / Redis
                             |
                      Kafka producer -> topic -> consumer -> Snowflake
                             |
            W3C traceparent + OTEL spans + structured logs
                             |
                    OTLP Collector / tail sampling
                             |
                   Tempo or Jaeger -> Grafana
                             |
                  dependency map / SLO correlation
```

## Span and propagation theory

A **trace** groups related spans by trace ID. Each span records an operation, parent relationship, duration, status and resource attributes. A service map infers edges from client/server and producer/consumer spans; missing instrumentation can make a service disappear without the dependency actually disappearing. Use W3C `traceparent` and `tracestate`; propagate context through HTTP and messaging metadata, not payload fields. Baggage is propagated broadly and must never contain secrets or sensitive identifiers.

**Critical path** is the longest causally dependent chain, not the sum of all overlapping span durations. Analyze concurrency and queue waits before attributing latency to a database. Tracing is sampled, so a missing trace does not prove an error did not occur; independently validate RED metrics.

## Instrumentation example — Python

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install opentelemetry-api opentelemetry-sdk
```

```python
from opentelemetry import trace, propagate, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

provider=TracerProvider(resource=Resource.create({"service.name":"orders-api"}))
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer=trace.get_tracer("chapter067")

with tracer.start_as_current_span("HTTP GET /orders"):
    carrier={}
    propagate.inject(carrier)
    with tracer.start_as_current_span("db.query"):
        pass
    print("propagated headers:", list(carrier))
```

Use this only for a local lab. Production should use OTLP with TLS, batching, timeouts and sampling, and automatically instrument supported frameworks. `SimpleSpanProcessor` and console output can introduce overhead.

## Service maps and dependency metrics

| Evidence | Purpose | Caveat |
|---|---|---|
| Client/server span pairs | map service-to-service edges | gaps from propagation/sampling |
| DB client spans | isolate query/connection waits | redact SQL parameters |
| Kafka producer/consumer spans | follow asynchronous workflow | consumer context may link rather than parent |
| Trace duration | identify critical path | parallel spans overlap |
| RED histogram | unbiased SLO evidence | choose appropriate histogram buckets |
| Trace ID in logs | correlate failure detail | avoid sensitive log payloads |
| Exemplars | link metric samples to traces | exporter/backend support varies |

### PromQL dependency checks

```promql
sum by (service_name) (rate(http_client_request_duration_seconds_count[5m]))
```

```promql
histogram_quantile(0.95,
 sum by (le,service_name) (rate(http_client_request_duration_seconds_bucket[5m]))
)
```

Metric and label names depend on semantic convention version and translation. Do not average precomputed p95s across instances.

## Collector sampling and safety

Head sampling chooses at span creation and cannot know eventual outcomes. Tail sampling can retain slow/error traces but needs memory, decision wait and consistent trace routing. Monitor dropped spans, queue capacity and backend ingestion. Hash or remove sensitive span attributes, restrict access, encrypt OTLP transport and apply retention controls.

## Production incident simulation

After a release, API p95 rises, Redis command latency spikes and Kafka processing lags. A partial service map omits the consumer because messaging context is not propagated. Reconstruct a UTC timeline from application RED metrics, trace paths and Kafka offsets. Fix propagation in staging, verify traces appear in Tempo/Jaeger, and confirm the independent user-facing SLO recovers after an approved rollback.

## Executable offline acceptance gate

This is a **synthetic attestation**, not a live trace validation.

### healthy.json

```json
{
  "owner": "apm-sre",
  "environment": "staging",
  "change_id": "OBS-067",
  "trace_coverage_percent": 97,
  "min_trace_coverage_percent": 90,
  "orphan_span_percent": 1,
  "max_orphan_span_percent": 5,
  "dependency_p95_ms": 180,
  "max_dependency_p95_ms": 300,
  "collector_dropped_spans": 0,
  "max_collector_dropped_spans": 10,
  "destructive_change": false,
  "checks": {
    "w3c_tracecontext": true,
    "baggage_privacy": true,
    "parent_child_spans": true,
    "async_context": true,
    "service_map": true,
    "dependency_latency": true,
    "critical_path": true,
    "error_spans": true,
    "sampling_policy": true,
    "collector_queues": true,
    "tail_sampling": true,
    "db_spans": true,
    "redis_spans": true,
    "kafka_spans": true,
    "trace_log_link": true,
    "metric_exemplars": true,
    "tenant_isolation": true,
    "rollback": true
  }
}
```

### tracing_gate.py

```python
"""Synthetic tracing readiness gate; no telemetry backends contacted."""
import json,sys
from pathlib import Path
CHECKS=["w3c_tracecontext","baggage_privacy","parent_child_spans","async_context","service_map","dependency_latency","critical_path","error_spans","sampling_policy","collector_queues","tail_sampling","db_spans","redis_spans","kafka_spans","trace_log_link","metric_exemplars","tenant_isolation","rollback"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["expected object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 for k in ("trace_coverage_percent","min_trace_coverage_percent","orphan_span_percent","max_orphan_span_percent"):
  v=p.get(k)
  if type(v) not in (int,float) or not 0<=v<=100:e.append("invalid "+k)
 for k in ("dependency_p95_ms","max_dependency_p95_ms","collector_dropped_spans","max_collector_dropped_spans"):
  v=p.get(k)
  if type(v) not in (int,float) or v<0:e.append("invalid "+k)
 for a,b,mode in (("trace_coverage_percent","min_trace_coverage_percent","min"),("orphan_span_percent","max_orphan_span_percent","max"),("dependency_p95_ms","max_dependency_p95_ms","max"),("collector_dropped_spans","max_collector_dropped_spans","max")):
  x,y=p.get(a),p.get(b)
  if type(x) in (int,float) and type(y) in (int,float) and ((mode=="min" and x<y) or (mode=="max" and x>y)):e.append("threshold breach "+a)
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as ex:sys.exit(str(ex))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_tracing_gate.py

```python
import copy,json,unittest
from pathlib import Path
from tracing_gate import validate
class TracingGateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["w3c_tracecontext"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["baggage_privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["parent_child_spans"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["async_context"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["service_map"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dependency_latency"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["critical_path"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["error_spans"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["sampling_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["collector_queues"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tail_sampling"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["db_spans"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["redis_spans"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kafka_spans"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["trace_log_link"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["metric_exemplars"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tenant_isolation"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["trace_coverage_percent"]=20
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["orphan_span_percent"]=50
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["dependency_p95_ms"]=999
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["collector_dropped_spans"]=100
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=True
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 tracing_gate.py healthy.json
python3 -m unittest -v test_tracing_gate.py
```

Expected PASS and **29 authored tests**; runtime execution not claimed.

## 24 hands-on exercises

1. Map API dependencies.
2. Instrument HTTP entry span.
3. Propagate W3C traceparent.
4. Review tracestate.
5. Review baggage privacy.
6. Instrument outbound HTTP.
7. Instrument PostgreSQL client.
8. Instrument Redis client.
9. Instrument Kafka producer.
10. Instrument Kafka consumer.
11. Link asynchronous spans.
12. Inspect parent-child topology.
13. Measure critical path.
14. Review dependency p95.
15. Correlate error span and log.
16. Review metrics exemplars.
17. Inspect OTel Collector queues.
18. Test head sampling.
19. Review tail sampling policy.
20. Review Tempo search.
21. Review Jaeger search.
22. Build service map.
23. Simulate missing propagation.
24. Validate rollback and recovery.

## 24 production failure scenarios

1. **Missing traceparent:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
2. **Broken parent-child link:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
3. **Orphaned async spans:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
4. **Trace context lost in Kafka:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
5. **Over-sampled hot endpoint:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
6. **Under-sampled errors:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
7. **Tail sampler overloaded:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
8. **Collector queue full:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
9. **OTLP TLS failure:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
10. **Exporter backpressure:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
11. **Tempo ingest delayed:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
12. **Jaeger query unavailable:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
13. **High-cardinality span attributes:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
14. **Sensitive baggage leaked:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
15. **Incorrect service.name:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
16. **Duplicate span emission:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
17. **Clock skew:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
18. **Missing dependency spans:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
19. **Span duration inflated:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
20. **Database connection wait:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
21. **Redis hot key:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
22. **Kafka processing lag:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
23. **Service map incomplete:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.
24. **Rollback fails:** identify trace evidence, independent RED impact, owner, safe mitigation and rollback.

## Eight production runbooks

1. **Missing trace context:** inspect traceparent headers, propagation inject/extract, middleware and async boundaries.
2. **Slow dependency:** compare span critical path with DB/Redis/Kafka RED metrics and connection pools.
3. **Trace ingestion failure:** inspect SDK exporter, OTLP TLS/auth, Collector queues, Tempo/Jaeger.
4. **Sampling gap:** review head/tail policies, error retention, budget and representative coverage.
5. **Service-map drift:** inspect service.name, resource attributes, span.kind and edge aggregation.
6. **Sensitive attributes:** remove raw SQL, user IDs, credentials and baggage; review retention.
7. **Latency regression:** compare trace path, release markers, retry fan-out and SLO burn.
8. **Rollback:** restore instrumentation/config, verify traces and independent user-facing SLOs.

## 100-point assessment

| Area | Points |
|---|---:|
| Tracing architecture and propagation | 20 |
| Dependency spans and service maps | 20 |
| Critical path, RED and correlation | 20 |
| Sampling, security and offline tests | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production acceptance requires witnessed trace continuity, secure sampling and a staged failure/recovery drill.

**Companion:** [Chapter 067 lab](labs/067-application-distributed-tracing-service-maps-dependency-performance-analysis-lab.md).

**Next:** Chapter 068 — Application Profiling, Runtime Diagnostics, Memory, CPU and Performance Bottlenecks.
