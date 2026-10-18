# Chapter 046 — OpenTelemetry Architecture, Signals, SDKs and Collector Fundamentals

**Part 10 — OpenTelemetry Architecture and Instrumentation** · SRE/DBRE production tutorial.

## Objectives and architecture

OpenTelemetry (OTel) provides instrumentation APIs, SDKs, semantic conventions, OTLP transport and Collector pipelines for **traces, metrics and logs**. It is not itself a telemetry storage backend.

```text
Kubernetes / APIs / database clients
   SDK / automatic instrumentation
         traces metrics logs
                  |
        OTLP HTTP 4318 / gRPC 4317
                  |
         OTel Collector agent
    receiver -> processor -> exporter
                  |
         OTel Collector gateway
                  |
 Tempo/Jaeger | Prometheus | Loki/Elastic
                  |
           Grafana / SLOs
```

## Signals and context

| Signal | Data model | Operational use |
|---|---|---|
| Traces | spans, links, events, trace/span IDs | request latency and dependencies |
| Metrics | counters, gauges, histograms | reliability and saturation |
| Logs | timestamp, severity, body, trace IDs | incident details |

Use stable `service.name`, `service.namespace`, `service.version`, `deployment.environment.name` attributes. W3C `traceparent` propagates request context. Do not put PII, credentials or patient IDs in baggage, logs or high-cardinality metric labels. Sampled traces cannot replace independent application SLO metrics.

## Collector fundamentals — local-only configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
      http:
        endpoint: 127.0.0.1:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
    spike_limit_mib: 64
  batch:
    timeout: 5s
    send_batch_size: 512
exporters:
  debug:
    verbosity: basic
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
```

Save as `collector.yaml`. Use a version-pinned Collector binary containing these components. Loopback binds only support clients in the same network namespace. Production requires reviewed TLS, authentication, RBAC, network policies, resource limits and persistent/bounded retry strategies.

### Synthetic OTLP HTTP trace

```bash
curl -fsS -X POST http://127.0.0.1:4318/v1/traces \
  -H 'Content-Type: application/json' \
  -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"orders-api"}}]},"scopeSpans":[{"scope":{"name":"chapter046"},"spans":[{"traceId":"0123456789abcdef0123456789abcdef","spanId":"0123456789abcdef","name":"synthetic-request","kind":1,"startTimeUnixNano":"1792324800000000000","endTimeUnixNano":"1792324801000000000"}]}]}]}'
```

Inspect Collector debug output and self-metrics. An HTTP success does not prove persistence in a backend.

## Offline executable governance lab

The manifest is **synthetic review metadata**, not Collector configuration. Attestation flags are not evidence of runtime controls.

### healthy.json

```json
{
  "service": "orders-api",
  "environment": "staging",
  "otlp_endpoint": "http://127.0.0.1:4318",
  "resource_attributes": [
    "service.name",
    "service.namespace",
    "deployment.environment.name",
    "service.version"
  ],
  "signals": [
    "traces",
    "metrics",
    "logs"
  ],
  "collector_receivers": [
    "otlp"
  ],
  "collector_processors": [
    "memory_limiter",
    "batch"
  ],
  "collector_exporters": [
    "debug"
  ],
  "sampling_reviewed": true,
  "cardinality_reviewed": true,
  "privacy_reviewed": true,
  "tls_production_required": true,
  "backpressure_reviewed": true,
  "resource_limits_reviewed": true,
  "collector_health_reviewed": true,
  "rollback_tested": true,
  "endpoint_is_local": true
}
```

### otel_gate.py

```python
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("service","environment","otlp_endpoint"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("otlp_endpoint")!="http://127.0.0.1:4318":e.append("nonlocal endpoint")
 for k in ["sampling_reviewed","cardinality_reviewed","privacy_reviewed","tls_production_required","backpressure_reviewed","resource_limits_reviewed","collector_health_reviewed","rollback_tested","endpoint_is_local"]:
  if p.get(k) is not True:e.append("unverified "+k)
 for k,req in (("signals",{"traces","metrics","logs"}),("collector_receivers",{"otlp"}),("collector_processors",{"memory_limiter","batch"}),("collector_exporters",{"debug"}),("resource_attributes",{"service.name","service.namespace","deployment.environment.name","service.version"})):
  v=p.get(k)
  if not isinstance(v,list) or not req.issubset(v):e.append("missing "+k)
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_otel_gate.py

```python
import copy,json,unittest
from pathlib import Path
from otel_gate import validate
class GateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_1(self):
  p=copy.deepcopy(self.p);p["service"]="";self.assertTrue(validate(p))
 def test_2(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_3(self):
  p=copy.deepcopy(self.p);p["otlp_endpoint"]="https://example.org";self.assertTrue(validate(p))
 def test_4(self):
  p=copy.deepcopy(self.p);p["sampling_reviewed"]=False;self.assertTrue(validate(p))
 def test_5(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_6(self):
  p=copy.deepcopy(self.p);p["privacy_reviewed"]=False;self.assertTrue(validate(p))
 def test_7(self):
  p=copy.deepcopy(self.p);p["tls_production_required"]=False;self.assertTrue(validate(p))
 def test_8(self):
  p=copy.deepcopy(self.p);p["backpressure_reviewed"]=False;self.assertTrue(validate(p))
 def test_9(self):
  p=copy.deepcopy(self.p);p["resource_limits_reviewed"]=False;self.assertTrue(validate(p))
 def test_10(self):
  p=copy.deepcopy(self.p);p["collector_health_reviewed"]=False;self.assertTrue(validate(p))
 def test_11(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_12(self):
  p=copy.deepcopy(self.p);p["endpoint_is_local"]=False;self.assertTrue(validate(p))
 def test_13(self):
  p=copy.deepcopy(self.p);p["signals"]=["metrics"];self.assertTrue(validate(p))
 def test_14(self):
  p=copy.deepcopy(self.p);p["collector_receivers"]=[];self.assertTrue(validate(p))
 def test_15(self):
  p=copy.deepcopy(self.p);p["collector_processors"]=["batch"];self.assertTrue(validate(p))
 def test_16(self):
  p=copy.deepcopy(self.p);p["collector_exporters"]=[];self.assertTrue(validate(p))
 def test_17(self):
  p=copy.deepcopy(self.p);p["resource_attributes"]=["service.name"];self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir chapter046 && cd chapter046
# Save the three blocks above as healthy.json, otel_gate.py and test_otel_gate.py
python3 otel_gate.py healthy.json
python3 -m unittest -v test_otel_gate.py
```

Expected: PASS and **19 authored tests**.

## 24 hands-on exercises

1. Inventory telemetry sources.
2. Identify traces metrics logs.
3. Choose OTLP HTTP or gRPC.
4. Set service.name.
5. Set deployment environment.
6. Define trace/span IDs.
7. Review context propagation.
8. Review baggage privacy.
9. Choose metric types.
10. Review metric labels.
11. Review histogram units.
12. Map log severity.
13. Configure OTLP receiver.
14. Configure memory limiter.
15. Configure batch processor.
16. Configure debug exporter.
17. Validate local listener.
18. Send synthetic trace.
19. Send synthetic metric.
20. Send synthetic log.
21. Inspect Collector self-metrics.
22. Simulate exporter outage.
23. Run offline unit tests.
24. Document rollback.

## 24 production failure scenarios

1. **Missing service.name:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
2. **Missing environment:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
3. **Trace context lost:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
4. **Baggage leaks secrets:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
5. **Metric cardinality surge:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
6. **Incorrect histogram unit:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
7. **Log severity mismatch:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
8. **Missing trace ID:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
9. **Wrong OTLP port:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
10. **HTTP/gRPC mismatch:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
11. **Receiver binding failure:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
12. **Exporter unavailable:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
13. **Collector OOM:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
14. **Memory limiter drops:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
15. **Queue overflow:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
16. **Sampling masks errors:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
17. **Tail sampling misconfigured:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
18. **TLS trust failure:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
19. **Auth token expires:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
20. **Clock skew:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
21. **Exporter CPU pressure:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
22. **Missing health check:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
23. **Sensitive span attributes:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.
24. **Rollback fails:** investigate SDK, context, Collector receiver, processor, exporter, network and independent SLIs.

## Eight runbooks

1. **Missing traces: inspect SDK sampling, propagators, receiver, processor and exporter.**
2. **Missing metrics: inspect instruments, temporality, collection interval and export.**
3. **Missing logs: inspect bridge, severity, resource fields and exporter.**
4. **Memory pressure: inspect memory limiter, queues, batch and container limits.**
5. **Context failure: validate traceparent through async and HTTP boundaries.**
6. **Cardinality incident: remove unbounded attributes and compare budgets.**
7. **Sensitive telemetry: stop unsafe attributes, restrict access and follow privacy response.**
8. **Rollback: restore versioned SDK/Collector configuration and validate independent SLIs.**

## Production DBRE incident simulation

During PostgreSQL query slowness, API traces lose context at an asynchronous worker and the Collector experiences memory pressure and export failures. Verify user impact independently, diagnose W3C propagation, memory limiter and queue/backpressure, restore a known-good configuration and document rollback and telemetry loss.

## 100-point acceptance

| Domain | Points |
|---|---:|
| Architecture and three signals | 20 |
| SDKs, semantics and propagation | 20 |
| Collector reliability and security | 20 |
| Offline governance and tests | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance additionally requires observed traces, metrics, logs, authentication, security tests and live rollback evidence.

**Companion:** [Chapter 046 lab](labs/046-opentelemetry-architecture-signals-sdks-collector-fundamentals-lab.md).

**Next:** Chapter 047 — OpenTelemetry SDK Instrumentation, Context Propagation and Application Telemetry.
