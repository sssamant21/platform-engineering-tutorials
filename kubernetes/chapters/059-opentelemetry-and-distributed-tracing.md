# Chapter 059 — OpenTelemetry and Distributed Tracing

**Track:** Kubernetes Administration · **Part 12 — Observability and Monitoring**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers and application developers  
**Prerequisites:** Chapters 056–058; kubectl, Windows PowerShell; an approved staging cluster; familiarity with HTTP and Prometheus

## 1. Production scenario

A patient-facing API request passes through an ingress controller, an application gateway, two microservices and PostgreSQL. The user experiences 12-second response times, but Pod readiness, node CPU and memory appear normal. Logs are spread across services, and no single log entry explains the end-to-end delay.

**Goal:** instrument the request path with OpenTelemetry, propagate trace context across services, collect spans safely, correlate traces with logs and metrics, and determine whether latency comes from application code, networking or a downstream dependency.

### Learning objectives

1. Explain traces, spans, trace IDs, span IDs and parent-child relationships.
2. Distinguish OpenTelemetry API, SDK, instrumentation, Collector and backend.
3. Propagate W3C Trace Context across HTTP/gRPC and asynchronous boundaries.
4. Configure OTLP ingestion and a Collector pipeline.
5. Choose head-based and tail-based sampling with cost and fidelity tradeoffs.
6. Correlate traces, logs and metrics without leaking sensitive data.
7. Investigate slow requests, missing spans, context loss and exporter failures.

## 2. Distributed tracing architecture

```text
Client -> Ingress -> API Gateway -> Service A -> Service B -> Database
             |           |            |           |
           spans        spans        spans       spans
             +-----------+------------+-----------+
                              |
                        OTLP exporter
                              |
                     OpenTelemetry Collector
                      receivers/processors
                              |
                       trace exporter
                              |
                 Jaeger / Tempo / APM backend
                              |
                    Trace waterfall view
```

A trace is a collection of related spans identified by a trace ID. Each span represents an operation with timing, status and attributes. Parent-child links describe causal relationships, not necessarily a strictly sequential execution order. Parallel operations can overlap.

### Signal model

| Signal | Primary purpose | Typical question |
|---|---|---|
| Metrics | Aggregate rates, errors, duration and saturation | How widespread is the slowdown? |
| Logs | Discrete process/application records | What error was recorded? |
| Traces | Per-request operation path | Where was time spent? |
| Profiles | CPU/heap or execution hotspots | Why is this code expensive? |

**Important:** tracing complements metrics and logs; it does not replace service-level SLIs or database diagnostics.

## 3. OpenTelemetry components

| Component | Responsibility | Operational risk |
|---|---|---|
| API | Instrumentation interfaces | Inconsistent semantic attributes |
| SDK | Span creation, processing and export | CPU/memory overhead |
| Auto-instrumentation | Framework/library instrumentation | Missing custom business operations |
| OTLP | Telemetry transport over gRPC or HTTP | TLS, auth, backpressure |
| Collector receiver | Accept spans | Endpoint exposure and overload |
| Collector processor | Batch, filter, redact, sample | Data loss from incorrect rules |
| Collector exporter | Forward to trace backend | Retry queues and connectivity |
| Trace backend | Store/search/display traces | Cost, retention and query latency |

OTLP/gRPC conventionally uses port 4317 and OTLP/HTTP uses port 4318. These are common defaults, not universal endpoints; verify the installed Collector configuration.

## 4. Safety and environment prerequisites

The labs use an isolated namespace and example service. Do not instrument production applications or enable broad tracing without approval. Healthcare, financial and identity-related workloads require strict controls: **never export patient identifiers, access tokens, raw SQL parameters, credentials, request bodies or other sensitive attributes by default**.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get namespaces
kubectl get pods -A | Select-String 'otel|collector|jaeger|tempo'
kubectl auth can-i create deployments -n default
```

**Expected:** identify an approved staging context and existing telemetry infrastructure. If Collector or backend is unavailable, complete the configuration and tabletop labs without deploying an unapproved stack.

## 5. Lab 1 — Map a request path and trace model

**Scenario:** `POST /api/orders` calls an inventory service and then a PostgreSQL query.

```text
trace_id: 4bf92f3577b34da6a3ce929d0e0e4736
root span: POST /api/orders                800 ms
  child: HTTP GET inventory                110 ms
  child: validate business rules            40 ms
  child: PostgreSQL SELECT                 570 ms
  child: serialize response                  20 ms
```

The numbers are illustrative. Span durations can overlap, and the difference between total root duration and child durations includes uninstrumented work and timing gaps.

### Required exercise

1. Identify service boundaries and potential context propagation points.
2. Name root and child spans using low-cardinality operation names.
3. Identify where database calls, queue operations and external APIs occur.
4. Define attributes such as `service.name`, deployment environment, HTTP route and DB system.
5. List attributes that must be excluded or redacted.
6. Decide which traces should be retained during errors and slow requests.

**Expected:** a trace map and data-classification checklist.

## 6. Lab 2 — Understand W3C trace context

W3C Trace Context uses the `traceparent` HTTP header:

```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

It encodes version, trace ID, parent span ID and trace flags. A downstream service extracts the incoming context and starts a child span with the same trace ID and an appropriate parent relationship.

### Common context propagation failures

- HTTP clients omit trace headers.
- Proxies strip or rewrite trace headers.
- Async job publishers fail to inject context into message headers.
- Background workers do not extract context.
- Services use incompatible propagator configuration.
- Custom code creates new root spans instead of child spans.

**Important:** trace context headers are not an authentication mechanism. Do not trust them for authorization, tenant isolation or security decisions.

## 7. Lab 3 — Configure an isolated OpenTelemetry Collector

**Staging only.** This Collector example receives OTLP and exports traces to its own logs for learning. It is **not** a production backend and may generate substantial log volume if exposed to broad traffic.

Save `ch059-collector.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch059
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: ch059
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 128
        spike_limit_mib: 32
      batch:
        timeout: 5s
        send_batch_size: 128
    exporters:
      debug:
        verbosity: basic
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [debug]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: ch059
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.111.0
          args: ["--config=/etc/otelcol/config.yaml"]
          ports:
            - containerPort: 4317
            - containerPort: 4318
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          volumeMounts:
            - name: config
              mountPath: /etc/otelcol
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: ch059
spec:
  selector:
    app: otel-collector
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
```

The image version is an illustrative pinned example; review supported Collector releases, image provenance and component compatibility before execution.

```powershell
kubectl apply -f .\ch059-collector.yaml
kubectl -n ch059 rollout status deployment/otel-collector --timeout=180s
kubectl -n ch059 get pods,services,configmaps
kubectl -n ch059 logs deployment/otel-collector --tail=100
```

**Expected:** Collector starts with OTLP receiver and debug exporter. It has no tracing backend; spans are visible only through its debug logs.

## 8. Lab 4 — Instrument a simple Python service

The following is an **application-side code example**, not a complete Kubernetes Deployment. Use an approved isolated Python environment with compatible OpenTelemetry packages installed.

```python
from flask import Flask
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

app = Flask(__name__)
provider = TracerProvider(resource=Resource.create({"service.name": "ch059-api"}))
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
    )
)
trace.set_tracer_provider(provider)
FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer(__name__)

@app.route("/work")
def work():
    with tracer.start_as_current_span("business-operation"):
        return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=8080)
```

For local testing, forward the Collector's OTLP/HTTP port:

```powershell
kubectl -n ch059 port-forward service/otel-collector 4318:4318
```

In another terminal, run the Python application and call:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/work
kubectl -n ch059 logs deployment/otel-collector --since=5m
```

**Expected:** HTTP request generates a server span and a child business-operation span. The Collector debug exporter logs received span summaries. Python dependencies and port-forwarding must be validated in the actual lab environment.

## 9. Lab 5 — Trace-to-log correlation

Application logs should include trace and span identifiers when a valid active span exists, allowing engineers to pivot between trace waterfall and structured logs.

Example conceptual JSON log:

```json
{
  "timestamp": "2026-10-13T15:00:00Z",
  "service": "ch059-api",
  "severity": "ERROR",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "Downstream dependency timed out"
}
```

### Acceptance questions

1. Does the log collector preserve trace/span IDs?
2. Can the tracing backend link to logs by trace ID?
3. Are trace IDs propagated across synchronous and asynchronous calls?
4. Are log timestamps UTC and synchronized?
5. Are high-cardinality identifiers kept out of metric labels?
6. Are sensitive request and database attributes redacted?

**Expected:** documented correlation fields and a data-handling policy. Trace IDs are correlation identifiers, not proof of user identity.

## 10. Lab 6 — Sampling and collector resilience

### Sampling strategies

| Strategy | Advantage | Risk |
|---|---|---|
| Always on | Maximum trace completeness | High overhead and storage cost |
| Head-based probability | Low cost, simple | Rare failures may be missed |
| Parent-based | Consistent distributed decision | Depends on upstream flags |
| Tail-based | Retain slow/error traces selectively | Buffering, memory, latency, topology complexity |

Tail sampling requires Collector architecture that keeps all spans for a trace together at the decision point. Multi-replica Collectors may require trace-ID-aware routing; otherwise spans can be split and sampling decisions incomplete.

### Collector production safeguards

- Configure memory limiter and batching.
- Size queues and retry policy for exporter outages.
- Monitor refused/dropped spans, queue length and exporter failures.
- Restrict receivers with NetworkPolicy/TLS/auth where appropriate.
- Set sampling and attribute redaction before expensive export.
- Avoid exposing debug exporters in production.

**Expected:** a capacity and failure-mode worksheet for traffic bursts, backend outages and Collector restarts.

## 11. Lab 7 — Slow request investigation tabletop

**Scenario:** p95 API latency increases from 200 ms to 8 seconds. CPU and memory are normal. Trace waterfalls show 6.8 seconds in a PostgreSQL client span, while application logs show connection pool wait warnings.

### Investigation workflow

1. Confirm error rate, throughput and latency from metrics.
2. Locate representative slow and successful traces for the same route.
3. Compare critical-path span durations, not only total summed durations.
4. Distinguish pool wait time from actual database query execution.
5. Correlate DB connection count, lock waits, query latency and application pool metrics.
6. Check whether tracing instrumentation includes connection acquisition.
7. Validate hypothesis with PostgreSQL logs/statistics and application metrics.
8. Apply approved remediation and verify p95, error rate and DB health.

**Expected:** a reasoned conclusion supported by traces **and** database telemetry. A slow database client span alone does not prove PostgreSQL execution is slow.

## 12. Trace instrumentation patterns

### HTTP/gRPC

Propagate W3C Trace Context, instrument client/server operations and record bounded HTTP route labels. Do not use raw URLs containing user identifiers as span names.

### Asynchronous messaging

Inject context into message headers, extract on consumers and use appropriate span links where one message depends on multiple producers. Avoid leaking headers containing credentials.

### Databases

Capture operation type and safe DB system metadata. Avoid raw SQL parameters, credentials and personally identifiable data. For high-throughput systems, tune sampling and instrument pool acquisition separately from query execution.

### Kubernetes metadata

Attach low-cardinality resource attributes such as service name, namespace and cluster where useful. Pod UID and container IDs can be helpful in traces but can increase storage/cardinality; apply retention and privacy controls.

## 13. Production troubleshooting matrix

| Symptom | Likely cause | Safe check |
|---|---|---|
| No traces | SDK/exporter disabled or unreachable | App config, Collector logs |
| Partial traces | Context propagation broken | Traceparent across boundaries |
| Missing child spans | Library not instrumented | SDK and instrumentation versions |
| Collector OOM | Buffering, high volume, tail sampling | Memory and queue metrics |
| Export failures | TLS/auth/network/backend | Collector exporter errors |
| Traces sampled unexpectedly | Head/tail policies | Sampling configuration |
| Trace/log mismatch | IDs not injected or log pipeline drops | Structured log fields |
| Excessive trace cost | Sampling/cardinality too high | Span rate, attributes, retention |
| Backend slow | Indexing/query saturation | Backend storage and query metrics |
| Sensitive attributes | Unsafe instrumentation | Redaction/filtering audit |

## 14. Production tracing runbook

### Detect

1. Confirm customer impact through SLIs and request traces.
2. Verify tracing pipeline health and sampling coverage.
3. Check whether missing traces reflect no traffic or telemetry loss.

### Investigate

1. Compare slow and healthy traces on the same route.
2. Identify the critical path and slow spans.
3. Correlate service metrics, logs, DB stats and deployment changes.
4. Form competing hypotheses; distinguish pool wait, network and execution time.

### Mitigate

1. Fix proven application/dependency issues through approved changes.
2. Preserve telemetry access while protecting sensitive data.
3. Verify request latency, error rate and backend health after remediation.

### Close

Record trace IDs as incident evidence only in approved internal systems, capture telemetry gaps, adjust instrumentation/sampling and assign follow-ups.

## 15. Acceptance checklist

- [ ] Trace, span, trace ID and context propagation understood.
- [ ] OpenTelemetry API, SDK, Collector and backend roles distinguished.
- [ ] W3C Trace Context and async propagation reviewed.
- [ ] Isolated Collector configured and logs inspected.
- [ ] Example service instrumentation reviewed or executed in staging.
- [ ] Trace-to-log correlation and UTC timestamps validated.
- [ ] Sampling and Collector backpressure risks assessed.
- [ ] Sensitive attribute handling and access controls documented.
- [ ] Slow-request incident tabletop completed.
- [ ] Production runbook and SLI acceptance documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 16. Cleanup

```powershell
kubectl -n ch059 get deployment,service,configmap,pods
kubectl delete namespace ch059
```

Stop local port-forward and Python processes separately. This lab does not install or change any production tracing infrastructure.

**Status:** Draft — runtime validation and technical review pending.

## 17. References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [OpenTelemetry Sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Kubernetes Observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)

**Next:** Chapter 060 — Production Observability and Alerting Project (Part 12 capstone).
