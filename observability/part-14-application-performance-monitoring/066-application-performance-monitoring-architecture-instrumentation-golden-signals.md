# Chapter 066 — Application Performance Monitoring Architecture, Instrumentation and Golden Signals

**Part 14 — Application Performance Monitoring**  
**Audience:** SRE, application platform engineers, DBRE and incident responders.  
**Prerequisites:** Chapters 001–065, Prometheus, Grafana, OpenTelemetry and HTTP services.

## Learning objectives

Design production APM with **RED** (Rate, Errors, Duration), **USE** (Utilization, Saturation, Errors), user-facing SLIs and distributed traces. Instrument applications and dependencies with OpenTelemetry, correlate structured logs, route actionable SLO alerts, control telemetry overhead and preserve security.

## Reference architecture

```text
Users -> API gateway -> application -> PostgreSQL / Redis / Kafka
           |                 |                    |
           +------ HTTP RED / dependency spans ----+
                             |
                    OTel SDK + W3C trace context
                             |
                    OTel Collector agent/gateway
                     /             |              \
               Prometheus         Tempo           Loki
                     \             |              /
                      Grafana / Alertmanager / SLOs
                                   |
                          incident runbooks
```

## Golden signals and instrumentation

| Signal | Metric or telemetry | Operational question |
|---|---|---|
| Rate | requests/sec, queue throughput | What load is served? |
| Errors | 5xx/failed transactions, dependency errors | What work fails? |
| Duration | request duration histogram p50/p95/p99 | What is user latency? |
| Utilization | CPU, heap, pool usage | How much capacity is consumed? |
| Saturation | queue depth, throttling, pool waits | Where is the bottleneck? |
| Traces | span durations and status | Which dependency contributes? |
| Logs | structured errors with trace IDs | What happened? |

Do not use averages as a replacement for p95/p99. Percentiles require appropriately bucketed histograms or supported native histograms; do not average per-instance percentiles. Use low-cardinality attributes: service, environment, route template and status class, not raw URL, user ID or SQL text.

## PromQL RED examples

```promql
sum by (service_name) (rate(http_server_request_duration_seconds_count[5m]))
```

```promql
sum by (service_name) (rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
/
clamp_min(sum by (service_name) (rate(http_server_request_duration_seconds_count[5m])), 1e-9)
```

```promql
histogram_quantile(0.95,
 sum by (le,service_name) (rate(http_server_request_duration_seconds_bucket[5m]))
)
```

These metric names and labels depend on OTel semantic convention version and Prometheus translation. Inspect live metric names and units before adopting. A classic histogram must include `le`; use separate syntax for native histograms.

## Minimal Python application instrumentation

Install in an isolated staging virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

resource=Resource.create({"service.name":"apm-demo","deployment.environment.name":"staging"})
provider=TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
metrics.set_meter_provider(MeterProvider(metric_readers=[PeriodicExportingMetricReader(ConsoleMetricExporter())],resource=resource))
tracer=trace.get_tracer("chapter066")
meter=metrics.get_meter("chapter066")
requests=meter.create_counter("demo_requests",unit="{request}")
duration=meter.create_histogram("demo_request_duration",unit="ms")
with tracer.start_as_current_span("GET /health"):
 requests.add(1,{"http.route":"/health","http.response.status_code":"200"})
 duration.record(8.0,{"http.route":"/health"})
```

Console exporters are for learning only. For production, configure OTLP transport, secure Collector endpoints, batching, sampling and authentication; instrument incoming/outgoing requests and context propagation. Do not attach secrets or patient identifiers to spans.

## Collector example (staging only)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
  batch: {}
exporters:
  debug:
    verbosity: basic
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
```

A loopback receiver is appropriate for local demonstrations, not remote agents. Production Collector configuration must include approved network access, TLS/authentication and backends.

## Incident simulation

After a deployment, an API's p99 latency increases, 5xx errors rise and Kafka consumer lag grows. PostgreSQL connection pool waits and Redis hot-key command latency are also elevated. Establish impact from independent RED metrics, inspect trace critical paths, compare release markers and retry volume, verify whether Kafka backlog is causal or downstream, then execute an approved rollback and confirm error-budget burn recovery.

## Offline acceptance gate

The following synthetic review validates declared instrumentation and thresholds; it does not query live APM.

### healthy.json

```json
{
  "owner": "application-sre",
  "environment": "staging",
  "change_id": "OBS-066",
  "requests_total": 10000,
  "requests_failed": 25,
  "max_error_rate_percent": 1,
  "p95_latency_ms": 160,
  "max_p95_latency_ms": 300,
  "collector_dropped_spans": 0,
  "max_collector_dropped_spans": 5,
  "destructive_change": false,
  "checks": {
    "service_map": true,
    "availability_sli": true,
    "latency_sli": true,
    "throughput_sli": true,
    "error_sli": true,
    "saturation": true,
    "histogram_buckets": true,
    "trace_propagation": true,
    "dependency_spans": true,
    "structured_logs": true,
    "otel_collector": true,
    "sampling": true,
    "alert_routing": true,
    "privacy": true,
    "cardinality": true,
    "rollback": true
  }
}
```

### apm_gate.py

```python
"""Offline APM architecture and RED signal acceptance, synthetic data only."""
import json,sys
from pathlib import Path
CHECKS=["service_map","availability_sli","latency_sli","throughput_sli","error_sli","saturation","histogram_buckets","trace_propagation","dependency_spans","structured_logs","otel_collector","sampling","alert_routing","privacy","cardinality","rollback"]
def validate(d):
 e=[]
 if not isinstance(d,dict):return ["expected object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(d.get(k),str) or not d[k].strip():e.append("missing "+k)
 if d.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=d.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 for k in ("requests_total","requests_failed","max_error_rate_percent","p95_latency_ms","max_p95_latency_ms","collector_dropped_spans","max_collector_dropped_spans"):
  x=d.get(k)
  if type(x) not in (int,float) or x<0:e.append("invalid "+k)
 n,f=d.get("requests_total"),d.get("requests_failed")
 if type(n) in (int,float) and type(f) in (int,float):
  if n<=0 or f>n:e.append("invalid request counts")
  elif type(d.get("max_error_rate_percent")) in (int,float) and 100*f/n>d["max_error_rate_percent"]:e.append("error budget breach")
 for a,b in (("p95_latency_ms","max_p95_latency_ms"),("collector_dropped_spans","max_collector_dropped_spans")):
  x,y=d.get(a),d.get(b)
  if type(x) in (int,float) and type(y) in (int,float) and x>y:e.append("threshold breached "+a)
 if d.get("destructive_change") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_apm_gate.py

```python
import copy,json,unittest
from pathlib import Path
from apm_gate import validate
class APMTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_not_object(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["service_map"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["availability_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["latency_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["throughput_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["error_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["saturation"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["histogram_buckets"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["trace_propagation"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dependency_spans"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["structured_logs"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["otel_collector"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["sampling"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["alert_routing"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["cardinality"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["requests_total"]=0
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["requests_failed"]=99999
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["max_error_rate_percent"]=0
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["p95_latency_ms"]=500
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["collector_dropped_spans"]=100
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=True
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 apm_gate.py healthy.json
python3 -m unittest -v test_apm_gate.py
```

Expected PASS and **28 authored Python tests**. Runtime execution is not claimed.

## 24 hands-on exercises

1. Map service dependencies.
2. Define user-facing availability SLI.
3. Define p95/p99 latency SLI.
4. Measure throughput.
5. Classify application errors.
6. Review saturation.
7. Instrument HTTP server.
8. Instrument outbound HTTP.
9. Instrument PostgreSQL calls.
10. Instrument Redis calls.
11. Instrument Kafka producer.
12. Instrument Kafka consumer.
13. Propagate trace context.
14. Record request duration histogram.
15. Record error counter.
16. Record queue depth gauge.
17. Instrument structured logs.
18. Configure OTel SDK sampler.
19. Configure OTel Collector.
20. Review service dashboards.
21. Design multi-window burn alerts.
22. Review cardinality and privacy.
23. Simulate staging latency fault.
24. Validate recovery and rollback.

## 24 production failure scenarios

1. **High p99 latency:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
2. **HTTP 5xx spike:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
3. **Timeout storm:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
4. **Connection pool exhaustion:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
5. **PostgreSQL lock waits:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
6. **Redis hot key:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
7. **Kafka consumer backlog:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
8. **Thread pool saturation:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
9. **CPU throttling:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
10. **Memory leak:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
11. **GC pause spike:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
12. **Excessive retries:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
13. **Circuit breaker opens:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
14. **Downstream TLS error:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
15. **DNS failure:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
16. **Missing trace propagation:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
17. **Collector overload:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
18. **Sampling drops critical traces:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
19. **High-cardinality labels:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
20. **Sensitive attributes leak:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
21. **Dashboard mismatch:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
22. **Noisy alert:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
23. **Instrumentation overhead:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.
24. **Rollback fails:** collect independent user impact, traces, dependency metrics, recent changes and rollback evidence.

## Eight production runbooks

1. **Latency regression:** compare p95/p99 histograms, traces, dependency timings and release markers.
2. **Error spike:** classify HTTP/gRPC errors, correlate logs, traces, deployment and retry amplification.
3. **Dependency bottleneck:** inspect DB pool, Redis command latency, Kafka lag and queueing.
4. **Saturation:** inspect CPU, heap/GC, worker queues, thread pools and autoscaling.
5. **Trace gaps:** inspect W3C trace context, sampler, exporter and Collector queues.
6. **Telemetry overload:** inspect cardinality, scrape pressure, batching, drops and sampling policy.
7. **Security:** redact PII, credentials and raw SQL; verify tenant isolation and RBAC.
8. **Recovery:** rollback safely, validate independent SLIs, burn rate, logs and incident evidence.

## 100-point assessment

| Area | Points |
|---|---:|
| APM architecture and golden signals | 20 |
| Instrumentation and trace context | 20 |
| PromQL, SLOs and dashboards | 20 |
| Security, offline tests and Collector | 20 |
| Incident simulation and rollback | 20 |
| **Total** | **100** |

Suggested pass 85/100. Production acceptance requires witnessed instrumentation, SLO alerts, security reviews and staging rollback.

**Companion:** [Chapter 066 lab](labs/066-application-performance-monitoring-architecture-instrumentation-golden-signals-lab.md).

**Next:** Chapter 067 — Application Distributed Tracing, Service Maps and Dependency Performance Analysis.
