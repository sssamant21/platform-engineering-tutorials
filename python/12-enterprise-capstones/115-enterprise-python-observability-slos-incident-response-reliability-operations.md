# Chapter 115 — Enterprise Python Observability, SLOs, Incident Response and Reliability Operations

**Part 12 — Enterprise Capstone Projects | Chapter 115/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/115-enterprise-observability-slo-incident-response-sre-dbre-lab.md) · [Executable offline project](labs/115/README.md)

## Outcomes

Design production telemetry for Python APIs, workers and CDC pipelines spanning Kubernetes, PostgreSQL, Elasticsearch/OpenSearch, MongoDB, Redis, Kafka and Snowflake. Implement OpenTelemetry traces, Prometheus metrics, structured logs, RED/USE, SLI/SLO and error-budget governance, multiwindow burn-rate alerts, incident correlation, on-call escalation, postmortems and runbooks. Validate principles with a deterministic offline Python simulator.

## Architecture

```text
HTTP API -> PostgreSQL / Redis / Elasticsearch
   |                    |
Kafka producer -> consumer workers -> MongoDB / Snowflake
   |                    |
 OTel SDK spans + W3C trace context + safe structured logs
   |                    |
 OTLP -> Collector -> trace backend / log backend
                    -> Prometheus scrape/remote write
   |
Grafana dashboards -> SLO/burn-rate alerts -> on-call
   |
incident timeline -> mitigation -> rollback -> postmortem
```

Use explicit resource attributes (service.name, deployment.environment, service.version), propagate context over HTTP and Kafka headers, and link asynchronous batch spans to source events. Treat tracing, metrics and logs as complementary evidence; missing telemetry is unknown, not healthy.

## 1. OpenTelemetry implementation

Instrument Python HTTP server/client, DB drivers and Kafka with supported OpenTelemetry SDK/instrumentation versions. Configure exporters to an OTel Collector using OTLP/gRPC or HTTP, with TLS, bounded queues, sampling and resource controls. Use W3C traceparent/tracestate where supported, preserve baggage only for approved low-risk fields and avoid PHI/PII, secrets or full SQL literals in span attributes. Monitor exporter failures and dropped spans. Use trace IDs to pivot from API 5xx to PostgreSQL pool wait, Elasticsearch search, MongoDB election, Redis miss and Kafka lag.

**Offline distinction:** The bundled `validate_trace` verifies a synthetic span graph. It does not install OTel, export spans, or verify live propagation.

## 2. Structured logging

Use JSON logs with timestamp, severity, service, environment, trace/span IDs, error class, retryable flag and operation. Avoid raw request bodies, credentials, patient identifiers, bearer tokens, high-cardinality labels and uncontrolled exception details. Set retention, RBAC, integrity and incident evidence preservation. The offline redactor is key-based demonstration only; real privacy controls require schema-aware filtering and testing.

## 3. Prometheus and RED/USE

RED for services: **Rate** (requests/second), **Errors** (eligible failure ratio) and **Duration** (histogram distributions, not average alone). USE for resources: **Utilization**, **Saturation** and **Errors**. Instrument `http_server_request_duration_seconds_bucket`, request totals, pool acquisition wait, PostgreSQL locks, Elasticsearch threadpool rejections, MongoDB connection checkout, Redis evictions, Kafka consumer lag and event age, Snowflake load latency and Kubernetes CPU throttling. Use bounded label cardinality; never label with request IDs, patient IDs or SQL strings.

Example PromQL (adjust metric names and histogram labels to actual SDK):
```promql
sum(rate(http_server_request_duration_seconds_count{service_name="python-api"}[5m]))
sum(rate(http_server_request_duration_seconds_count{service_name="python-api",http_response_status_code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_server_request_duration_seconds_count{service_name="python-api"}[5m])), 1)
histogram_quantile(0.99, sum by (le) (rate(http_server_request_duration_seconds_bucket{service_name="python-api"}[5m])))
```
Validate that labels and bucket series exist; PromQL above is illustrative, not a deployed recording rule. For low traffic, denominator handling and no-data behavior require explicit alert design.

## 4. SLI/SLO and error budgets

Define service ownership, eligible events, measurement windows, target, exclusions and no-traffic policy. Availability SLI = successful eligible requests / total eligible requests. For a 99.9% SLO, the allowed bad-event fraction is 0.1%; over 1,000 eligible requests, a single failure consumes the full fractional budget. Define separate latency and pipeline freshness SLIs; avoid mixing API requests with CDC events. Budget remaining = total × (1 − target) − bad. A zero-event window must be unknown rather than a fabricated 100% pass.

## 5. Burn-rate alerting

Burn rate = observed bad fraction / permitted bad fraction. A multiwindow, multi-burn policy pages only when both a short and a longer window breach a threshold, reducing false positives. Example 99.9% SLO with 14.4× fast-burn threshold over 5-minute and 1-hour windows; pair with slower-burn tickets and traffic/no-data guardrails. Real alert windows, budget consumption and page severity should follow an approved SLO policy. The offline `multiwindow` computes the simplified two-window decision and does not implement alert routing.

## 6. Incident correlation and triage

Correlate by incident ID, trace ID, deployment version, environment, dependency, timestamp and error class. Distinguish causation from co-occurrence. For example, API p99 + PostgreSQL pool wait + Kubernetes HPA scaling suggests connection amplification; Elasticsearch fetch latency + disk queueing suggests IOPS pressure; Kafka lag + MongoDB election suggests downstream retry backlog. Verify evidence, blast radius, and whether a recent change is involved before declaring root cause.

## 7. On-call workflows

Severity model: SEV1 for critical customer/data impact; SEV2 for significant degradation; SEV3 for limited impact (calibrate to organizational policy). Assign incident commander, communications lead and technical responders; start a timeline, establish customer impact, protect data integrity, mitigate first and preserve evidence. Escalate to DBRE/Infra/Security as appropriate. Announce status at agreed intervals, document commands, change IDs, rollback criteria and handoff. Do not automatically page or mutate production from the offline lab.

## 8. Reliability operations and release gates

Require service SLO health, minimum trace coverage, tested rollback, named owner and human approval before advisory promotion. Track error-budget policy, alert fatigue, runbook freshness, backup/restore drills and change windows. Use progressive rollout with canary comparisons and a reversible immutable artifact. Unknown telemetry or SLO state blocks release rather than silently passing.

## 9. Postmortems and continuous improvement

Capture timeline (UTC), impact and duration, detection gap, contributing factors, what helped/hindered, remediation, owners, due dates and verification evidence. Separate trigger from systemic causes; avoid blame. Example action: reduce API replica connection pool, add aggregate connection budget alert, add HPA scaling guardrail and run a staging saturation test. Close actions only with measured evidence.

## 10. Production runbooks

**API latency/5xx:** inspect RED dashboard, trace critical path, p99, pool waits, error class and recent deploy; roll back when regression is confirmed.

**PostgreSQL pool saturation:** inspect `pg_stat_activity`, locks, pool checkout and replicas × pool size; throttle traffic and reserve admin capacity.

**Elasticsearch search degradation:** inspect shard fanout, threadpool rejections, fetch latency, merges, IOPS and oversized pages; reduce load and verify recovery.

**MongoDB failover:** inspect elections, driver retries, write concern and uncertain commits; reconcile before replay.

**Redis stampede:** cap origin load, singleflight misses, TTL jitter and invalidation; avoid overwhelming PostgreSQL.

**Kafka lag/CDC freshness:** inspect end/committed offsets, event age, rebalances, connector lag, WAL/oplog retention and DLQ; bound catch-up.

**Snowflake load failures:** inspect stage manifests, `COPY INTO`, `MERGE`, rejected rows and warehouse availability; replay idempotently.

**Telemetry outage:** inspect Collector queues, credentials, exporter failures and sampling; flag SLI evidence unknown and protect application throughput.

## 11. Labs and final assessment

The [full lab](labs/115-enterprise-observability-slo-incident-response-sre-dbre-lab.md) and [offline project](labs/115/README.md) cover trace graph validation, privacy-aware sample redaction, RED/USE, percentile latency, availability SLI/error budget, multiwindow burn rate, signal correlation and advisory release gates, with automated tests and 40 guided incident scenarios.

**Validation boundary:** No real OTel SDK/Collector, Prometheus server, Grafana, PagerDuty, cloud connection, database or production mutation is included. Exact committed tests, CI, live telemetry integration and production acceptance remain pending.

**Next:** Chapter 116 — Enterprise Python Security, Compliance and Disaster Recovery Operations.
