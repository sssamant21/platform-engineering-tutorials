# Chapter 108 — Python Production Observability, Tracing and Reliability Engineering

**Part 11 — Production Security and Performance | Chapter 108/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/108-production-observability-tracing-reliability-sre-dbre-lab.md) · [Executable offline project](labs/108/README.md)

## Objectives

Instrument Python services using OpenTelemetry (OTel) traces, structured logs and Prometheus-compatible metrics; reason about distributed trace context, RED/USE signals, SLIs/SLOs, error budgets and multi-window burn-rate alerts; correlate incidents across PostgreSQL, Elasticsearch, MongoDB, Kafka and Kubernetes. Implement safe, testable offline telemetry calculations.

## Reference architecture

```text
Python API / worker / CronJob / Kafka consumer
  |              |                |
  | OTel SDK     | JSON logs      | Prometheus metrics
  v              v                v
OTLP -> OTel Collector -> traces backend
         |               logs backend
         +-------------> metrics backend / Prometheus
                           |
                 recording rules + SLI/SLO alerts
                           |
             dashboards -> incident timeline -> runbooks
                           |
         trace_id / span_id + service + deploy version
```

Keep collection separate from export, control sampling, batch queues, retry budgets, cardinality, privacy and telemetry cost. Collector outages must not block critical business requests; instrument exporter backpressure and dropped telemetry.

## 1. Observability versus monitoring

Monitoring tests known conditions; observability enables investigating unknown failure modes from external signals. Logs explain discrete events, metrics aggregate trends and traces reveal request paths. Correlate them using stable service identity, deployment version, trace IDs, time windows and resource attributes. Beware clock skew, sampling gaps, missing propagation and asynchronous boundaries.

## 2. OpenTelemetry instrumentation

Use reviewed `opentelemetry-api`, `opentelemetry-sdk`, OTLP exporter and instrumentations compatible with your Python/framework versions. Set `service.name`, environment and deployment attributes through OTel resource configuration. Initialize `TracerProvider`, a batch span processor and OTLP exporter; use context managers for spans, set semantic attributes carefully and record exceptions without exposing payloads. Prefer W3C `traceparent` and `tracestate` propagation across HTTP; propagate explicit context through queues/jobs with trust and privacy checks.

```python
# Illustrative production integration (dependencies not included in offline lab)
from opentelemetry import trace
tracer = trace.get_tracer("platform.python")
with tracer.start_as_current_span("postgres.query") as span:
    span.set_attribute("db.system.name", "postgresql")
    # invoke a real, separately approved DB operation here
```

Avoid high-cardinality attributes such as raw patient IDs, emails, SQL literals or tokens. Verify semantic convention version and instrumentation behavior before production adoption.

## 3. Distributed tracing design

A trace is a directed parent/child span graph with trace ID, span ID, timing, status and resource identity. Cross-service propagation must retain valid IDs and context, but trust incoming baggage only after validation. Distinguish server spans, client spans, messaging producer/consumer spans and span links for batch/fanout. Head sampling is cheaper; tail sampling may retain errors/slow requests but requires collector state, capacity and correct routing. Missing spans do not prove a request did not occur.

## 4. Structured logging

Emit consistent JSON fields: UTC timestamp, severity, service, environment, version, request/trace/span IDs, operation, outcome and bounded error classification. Apply schema validation, redaction, retention, access control and sampling. Never log credentials, auth headers, patient information or raw query parameters. Avoid duplicate stack traces and unbounded payloads. A substring key redactor is a teaching device, not sufficient production DLP.

## 5. Prometheus metrics and cardinality

Use counters for requests/errors, histograms for latency/size, gauges for inflight/queue depth and appropriate process/runtime metrics. Histograms support aggregatable latency estimates when buckets and labels align. Avoid per-user, per-query, per-trace or request-ID labels; label cardinality grows multiplicatively and can overload Prometheus.

Illustrative PromQL:
```promql
sum(rate(http_server_request_duration_seconds_count{service="api"}[5m]))
sum(rate(http_server_requests_total{service="api",outcome="error"}[5m]))
/
clamp_min(sum(rate(http_server_requests_total{service="api"}[5m])), 1e-9)
histogram_quantile(0.99, sum by (le) (rate(http_server_request_duration_seconds_bucket{service="api"}[5m])))
```

Metric names and labels depend on instrumentation; validate numerator/denominator populations, histogram conventions and missing series. Do not average pod-level p99 values into fleet p99.

## 6. RED and USE

**RED** (request-driven): Rate, Errors, Duration. Measure throughput, error ratio and latency distribution for each critical request class.

**USE** (resource-driven): Utilization, Saturation, Errors. For CPU, disk, network, worker pools and database connections, track capacity usage, queue/wait and failures. CPU saturation may show up as cgroup throttling; storage saturation as queue depth and latency; PostgreSQL pool saturation as acquisition wait.

## 7. SLI, SLO and error budget mathematics

Availability SLI = good events / eligible events. Define good and eligible precisely, exclude only agreed classes, and avoid sampling bias. An SLO target of 99.9% over a 30-day window permits 0.1% bad eligible events. For 1,000,000 eligible requests, the nominal budget is 1,000 failures; this is a ratio budget, not a guarantee of continuous uptime.

Error-budget burn rate compares observed bad-event fraction with allowed bad-event fraction. Multi-window multi-burn-rate alerts use both a short and a longer window to distinguish persistent, actionable breaches from transient spikes. Choose thresholds and windows based on SLO period, traffic, paging policy and organization practice; 14.4x is an **illustrative** fast-burn threshold, not universal. When there is no traffic, mark SLI/burn rate unknown or insufficient data rather than treating it as 100% success.

## 8. Reliability incident correlation

Correlate trace spans and RED changes with USE saturation and recent deploys. For PostgreSQL, examine pool wait, query plans, locks, WAL/storage I/O and replication; for Elasticsearch, shard fanout, search rejections, oversized queries and disk latency; for MongoDB, connection wait, slow queries and WiredTiger; for Kafka, consumer lag, broker request latency and rebalance; for Kubernetes, CPU throttling, OOMs, restarts and node pressure.

Use a timeline: first symptom → request class → trace correlation → resource pressure → recent change → rollback/mitigation → recovery evidence. Do not infer causation from mere metric correlation.

## 9. SLO-driven incident response

Define alert severity, ownership, service dependencies, dashboards, on-call escalation and rollback criteria. Page for user-impacting sustained burn, not every raw resource threshold. During telemetry outages, preserve last known complete evidence and explicitly flag unknown coverage. Audit dashboard and alert rule changes.

## 10. Production runbooks

**OTel Collector outage:** check receiver/exporter queue, dropped spans, retry pressure, network/auth/TLS and backend capacity; protect app traffic and restore telemetry safely.

**Trace gap:** inspect propagation headers, instrumentation, sampling policy, async queue context and clock skew.

**Cardinality explosion:** identify unbounded labels, block offending release, apply safe relabeling and restore storage capacity.

**SLO burn:** verify eligibility/error classification, correlate traces with recent deploy and downstream USE, mitigate, canary and verify burn recovery.

**PostgreSQL/Elasticsearch latency:** isolate client queue time from server processing and storage saturation before tuning pool sizes or retry rates.

**Missing logs:** validate sink, retention, permissions and redaction; do not disable sensitive-data controls.

## 11. Hands-on project

The [full lab](labs/108-production-observability-tracing-reliability-sre-dbre-lab.md) and [offline Python project](labs/108/README.md) implement trace-graph validation, synthetic RED/USE, p95/p99 interpolation, structured-log field redaction, SLI/SLO and error budgets, short/long burn calculations, coverage-aware incident classification, tests and guided incidents.

**Validation boundary:** The project does not install OpenTelemetry, export OTLP, serve Prometheus metrics, collect live traces, query production databases or create real alerts. Published test code and lab instructions require independent execution, CI and live staging integration validation.

**Next proposed:** Chapter 109 — Python Resilience Engineering, Fault Injection and Chaos Testing.
