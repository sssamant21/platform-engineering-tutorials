# Chapter 047 — OpenTelemetry SDK Instrumentation, Context Propagation and Application Telemetry

**Part 10 — OpenTelemetry Architecture and Instrumentation**  
**Audience:** SRE, DBRE, Python engineers and platform teams.  
**Prerequisites:** Chapter 046, Python 3.10+, basic HTTP and database clients.

## 1. Objectives and architecture

Instrument real application code for traces, metrics and correlated logs, propagate W3C context through HTTP and asynchronous jobs, apply semantic conventions, bound cardinality, protect sensitive data, and diagnose export failures.

```text
HTTP request -> service span -> DB client span -> PostgreSQL
      |               |
 traceparent     metric counter/histogram
      |               |
 async task -> child span -> OTLP SDK exporter
                             |
                        OTel Collector
                             |
                    Tempo/Jaeger + metrics
```

OpenTelemetry APIs provide instrumentation contracts; SDKs implement sampling, span processing and export. Automatic instrumentation accelerates coverage but can create duplicate spans when combined with manual instrumentation. Semantic conventions vary by release: pin versions and verify emitted fields.

## 2. Executable Python SDK example

Create a virtual environment and install version-compatible pinned OpenTelemetry packages in your project lockfile:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

The example uses the **console exporter** so it can run without a Collector. For production, replace it with a reviewed OTLP exporter, authentication, TLS, batching and backpressure controls.

### app.py

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.trace import Status, StatusCode

resource = Resource.create({
    "service.name": "orders-api",
    "service.version": "0.1.0",
    "deployment.environment.name": "staging"
})
tp = TracerProvider(resource=resource)
tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(tp)
mp = MeterProvider(
    resource=resource,
    metric_readers=[PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=1000)]
)
metrics.set_meter_provider(mp)
tracer = trace.get_tracer("chapter047")
meter = metrics.get_meter("chapter047")
requests = meter.create_counter("demo.requests", unit="{request}")
latency = meter.create_histogram("demo.duration", unit="ms")

with tracer.start_as_current_span("GET /orders") as parent:
    parent.set_attribute("http.request.method", "GET")
    with tracer.start_as_current_span("db SELECT orders") as child:
        child.set_attribute("db.system.name", "postgresql")
        # Never attach SQL bind values, credentials or patient identifiers
    requests.add(1, {"service": "orders-api", "result": "ok"})
    latency.record(12.5, {"service": "orders-api"})
mp.force_flush()
tp.force_flush()
tp.shutdown()
mp.shutdown()
```

```bash
python app.py
```

Expected: two related spans plus a counter and histogram in console output. The histogram unit is milliseconds; keep application measurements and bucket configuration consistent.

## 3. W3C propagation across process boundaries

```python
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("propagation-demo")
with tracer.start_as_current_span("producer"):
    headers = {}
    propagate.inject(headers)
    print("Outbound headers:", headers)
    # In another service: ctx = propagate.extract(headers)
    # with tracer.start_as_current_span("consumer", context=ctx): ...
```

Use supported instrumentation to inject/extract `traceparent` and optionally `tracestate` and baggage. Explicitly propagate context through queue messages and asynchronous workers. Never put PII or secrets into baggage; it can travel to external services.

## 4. DBRE instrumentation patterns

Capture database client duration, operation, error status, pool wait, connection errors and transaction boundaries without exposing SQL bind values. Use separate metrics for pool utilization and database server saturation. Span events and exception details must be sanitized. Avoid user ID, patient ID, query text or request ID as metric labels.

## 5. Sampling, metric design and production controls

- Prefer application request counters and histograms for SLIs; sampled traces are not complete request accounting.
- Limit metric dimensions and span attributes; monitor SDK memory, CPU and exporter drops.
- Use `BatchSpanProcessor` with bounded queues for production instead of the teaching-only simple processor.
- Choose trace sampling based on cost, error capture and downstream consistency.
- Set service/resource attributes once and version configuration for rollback.

## 6. Offline executable instrumentation design gate

This manifest is **synthetic review metadata**, not SDK configuration or runtime proof.

### healthy.json

```json
{
  "service": "orders-api",
  "environment": "staging",
  "tracer": "orders-api",
  "meter": "orders-api",
  "propagators": [
    "tracecontext",
    "baggage"
  ],
  "attributes": [
    "service.name",
    "service.version",
    "deployment.environment.name"
  ],
  "instrumentation": [
    "http.server",
    "http.client",
    "db.client"
  ],
  "collector_endpoint": "http://127.0.0.1:4318",
  "sample_rate_percent": 10,
  "max_metric_dimensions": 8,
  "span_attribute_limit": 64,
  "privacy_reviewed": true,
  "baggage_reviewed": true,
  "db_statement_redaction_reviewed": true,
  "async_propagation_tested": true,
  "errors_recorded": true,
  "metric_units_reviewed": true,
  "rollback_tested": true
}
```

### sdk_gate.py

```python
"""Offline instrumentation design gate; does not run OTel SDK or Collector."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("service","environment","tracer","meter"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("collector_endpoint")!="http://127.0.0.1:4318":e.append("unsafe lab endpoint")
 for k,required in (("propagators",{"tracecontext","baggage"}),("attributes",{"service.name","service.version","deployment.environment.name"}),("instrumentation",{"http.server","http.client","db.client"})):
  v=p.get(k)
  if not isinstance(v,list) or not required.issubset(v):e.append("missing "+k)
 for k in ["privacy_reviewed","baggage_reviewed","db_statement_redaction_reviewed","async_propagation_tested","errors_recorded","metric_units_reviewed","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 for k,lo,hi in (("sample_rate_percent",0,100),("max_metric_dimensions",1,12),("span_attribute_limit",1,128)):
  v=p.get(k)
  if type(v) is not int or not lo<=v<=hi:e.append("invalid "+k)
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_sdk_gate.py

```python
import copy,json,unittest
from pathlib import Path
from sdk_gate import validate
class InstrumentationTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_service(self):
  p=copy.deepcopy(self.p);p["service"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_tracer(self):
  p=copy.deepcopy(self.p);p["tracer"]="";self.assertTrue(validate(p))
 def test_04_meter(self):
  p=copy.deepcopy(self.p);p["meter"]="";self.assertTrue(validate(p))
 def test_05_collector_endpoint(self):
  p=copy.deepcopy(self.p);p["collector_endpoint"]="http://example.org:4318";self.assertTrue(validate(p))
 def test_06_propagators(self):
  p=copy.deepcopy(self.p);p["propagators"]=[];self.assertTrue(validate(p))
 def test_07_attributes(self):
  p=copy.deepcopy(self.p);p["attributes"]=[];self.assertTrue(validate(p))
 def test_08_instrumentation(self):
  p=copy.deepcopy(self.p);p["instrumentation"]=[];self.assertTrue(validate(p))
 def test_09_privacy_reviewed(self):
  p=copy.deepcopy(self.p);p["privacy_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_baggage_reviewed(self):
  p=copy.deepcopy(self.p);p["baggage_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_db_statement_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["db_statement_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_async_propagation_tested(self):
  p=copy.deepcopy(self.p);p["async_propagation_tested"]=False;self.assertTrue(validate(p))
 def test_13_errors_recorded(self):
  p=copy.deepcopy(self.p);p["errors_recorded"]=False;self.assertTrue(validate(p))
 def test_14_metric_units_reviewed(self):
  p=copy.deepcopy(self.p);p["metric_units_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_16_sample_rate_percent(self):
  p=copy.deepcopy(self.p);p["sample_rate_percent"]=101;self.assertTrue(validate(p))
 def test_17_sample_rate_percent(self):
  p=copy.deepcopy(self.p);p["sample_rate_percent"]=-1;self.assertTrue(validate(p))
 def test_18_max_metric_dimensions(self):
  p=copy.deepcopy(self.p);p["max_metric_dimensions"]=100;self.assertTrue(validate(p))
 def test_19_span_attribute_limit(self):
  p=copy.deepcopy(self.p);p["span_attribute_limit"]=0;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Execute

```bash
mkdir -p chapter047 && cd chapter047
# Save the three blocks as healthy.json, sdk_gate.py, test_sdk_gate.py
python3 sdk_gate.py healthy.json
python3 -m unittest -v test_sdk_gate.py
```

Expected PASS and **21 authored tests**.

## 7. Twenty-four hands-on exercises

1. Install pinned SDK packages.
2. Initialize Resource.
3. Initialize TracerProvider.
4. Configure OTLP exporter.
5. Create parent span.
6. Create child span.
7. Add safe span attributes.
8. Record exception.
9. Set span error status.
10. Instrument HTTP server.
11. Instrument HTTP client.
12. Propagate traceparent.
13. Propagate asynchronous task context.
14. Review baggage content.
15. Instrument DB client.
16. Suppress SQL bind values.
17. Create counter.
18. Create latency histogram.
19. Check metric units.
20. Limit dimensions.
21. Correlate log trace ID.
22. Simulate collector outage.
23. Run policy unit tests.
24. Document rollback.

## 8. Twenty-four production failure scenarios

1. **No spans exported:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
2. **Incorrect service.name:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
3. **Trace ID broken between services:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
4. **Async worker loses parent:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
5. **Baggage leaks PII:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
6. **SQL statement leaks credentials:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
7. **Excessive span attributes:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
8. **Metric dimension explosion:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
9. **Wrong histogram units:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
10. **Duplicate auto and manual spans:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
11. **Missing exception status:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
12. **Span ended twice:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
13. **OTLP HTTP/gRPC mismatch:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
14. **Exporter 401:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
15. **Exporter TLS error:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
16. **Collector unavailable:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
17. **Exporter queue saturation:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
18. **Sampling hides rare error:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
19. **Clock skew:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
20. **Span context injected twice:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
21. **Log trace ID missing:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
22. **Resource schema mismatch:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
23. **High SDK CPU overhead:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.
24. **Rollback removes SLI:** inspect SDK initialization, context propagation, exporter, privacy and independent SLIs.

## 9. Eight production runbooks

1. **Missing spans:** inspect provider registration, sampler, exporter, endpoint and collector receiver.
2. **Broken propagation:** inspect W3C traceparent extraction/injection at HTTP, messaging and async boundaries.
3. **Sensitive attributes:** stop unsafe instrumentation, redact and rotate secrets; coordinate approved data handling.
4. **Metric cardinality:** remove unbounded dimensions and validate aggregation accuracy.
5. **SDK overhead:** compare latency/CPU baselines and adjust batch, sampling and attribute limits.
6. **Collector failure:** check export errors, retries, backpressure and independent service metrics.
7. **Database tracing:** confirm safe SQL redaction, query timing and correct parent span.
8. **Rollback:** restore pinned SDK/config and validate service SLIs and telemetry completeness.

## 10. SRE/DBRE incident simulation

An API backed by PostgreSQL shows increased p95 latency. Auto-instrumentation creates duplicate spans; asynchronous worker traces are disconnected; a database span accidentally contains SQL bind values. Diagnose request latency from independent metrics, repair propagation, remove sensitive attributes, validate cardinality and roll back the SDK change with a safe deployment.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| SDK initialization and traces | 20 |
| Propagation and async/database instrumentation | 20 |
| Metrics, correlation and cardinality | 20 |
| Offline gate and automated tests | 20 |
| Incident response, privacy and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires actual application instrumentation, end-to-end propagation, safe data handling and observed export to a test backend.

**Companion:** [Chapter 047 hands-on lab](labs/047-opentelemetry-sdk-instrumentation-context-propagation-application-telemetry-lab.md).

**Next:** Chapter 048 — OpenTelemetry Collector Pipelines, Processors, Exporters and Production Deployment.
