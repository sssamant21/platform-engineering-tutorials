# Chapter 108 — Production Observability, Tracing and Reliability Engineering SRE/DBRE Lab

[Python engine](108/observability_lab.py) · [Automated tests](108/test_observability_lab.py) · [Project README](108/README.md)

## Mission

A Python API serving Kubernetes workloads depends on PostgreSQL, Elasticsearch, MongoDB and Kafka. Users report elevated p99 and intermittent errors while dashboards show CPU and queue saturation. Build an offline evidence-based investigation, SLI/SLO budget and runbook without touching production.

```text
Synthetic traces + request samples + resource telemetry
 -> trace graph / log schema validation
 -> RED/USE / p50-p95-p99 / error ratio
 -> SLI/SLO + budget + burn-rate signals
 -> incident correlation + coverage check
 -> advisory recovery and rollback / zero writes
```

## Lab 1 — Execute

```bash
cd python/11-production-security-performance/labs/108
python -m compileall -q observability_lab.py test_observability_lab.py
python -m unittest -v test_observability_lab.py
python observability_lab.py --dry-run
python observability_lab.py --partial
```

## Lab 2 — OpenTelemetry architecture and distributed traces

Validate synthetic trace/span IDs, parent graph, orphan detection and error status. Design production Python OTel SDK, Collector, OTLP, W3C context propagation, span links for Kafka fanout and head/tail sampling. Compare trace data completeness with sampled traces. The executable project uses **no actual OTel dependencies**.

## Lab 3 — Structured logs and Prometheus metrics

Generate JSON logs with trace correlation and known-key redaction. Design stronger production privacy filters, log sampling and retention. Map synthetic RED/USE outputs to counters, histograms and gauges; derive PromQL queries for rate, errors and latency. Discuss histogram bucket boundaries and label cardinality.

## Lab 4 — SLI, SLO and error budgets

Calculate eligible/good request ratio, remaining error budget and short/long burn-rate signals. Handle zero traffic, missing samples, invalid values and partial telemetry explicitly. Explain why burn-rate thresholds and windows must be tuned to a service's SLO and alert policy.

## Lab 5 — SRE/DBRE incident correlation

Join a slow Python trace with PostgreSQL query/pool wait, Elasticsearch shard fanout/rejections, MongoDB connection wait, Kafka consumer lag and Kubernetes CPU throttling. Build a timeline, prioritize user-impacting signals and define rollback gates.

## Incident simulations

| # | Scenario | Expected result | Mode |
|---|---|---|---|
| 1 | Valid trace/span IDs | Accept | Automated |
| 2 | Invalid trace ID | Reject | Automated |
| 3 | Invalid span ID | Reject | Automated |
| 4 | Self-parent span | Reject | Automated |
| 5 | Negative/NaN span duration | Reject | Automated |
| 6 | Unknown status/service | Reject | Automated |
| 7 | Parent/child trace | Count | Automated |
| 8 | Error span | Count | Automated |
| 9 | Duplicate span | Reject | Automated |
| 10 | Orphan span | Reject | Automated |
| 11 | Cyclic span graph | Reject | Automated |
| 12 | p50/p95/p99 | Correct | Automated |
| 13 | Invalid latency/percentile | Reject | Automated |
| 14 | RED request rate/error ratio | Calculate | Automated |
| 15 | Zero traffic | Unknown percentiles | Automated |
| 16 | Invalid counts/window/coverage | Reject | Automated |
| 17 | USE saturation | Report | Automated |
| 18 | Invalid utilization | Reject | Automated |
| 19 | SLI ratio and zero traffic | Calculate/unknown | Automated |
| 20 | Invalid SLI counts | Reject | Automated |
| 21 | Within/breached SLO budget | Classify | Automated |
| 22 | Invalid SLO target | Reject | Automated |
| 23 | High/low burn rate | Classify | Automated |
| 24 | Missing burn window | Insufficient data | Automated |
| 25 | Known-key secret redaction | Redact | Automated |
| 26 | Invalid structured log | Reject | Automated |
| 27 | Stable report hash | Deterministic | Automated |
| 28 | Changed report | Digest changes | Automated |
| 29 | SLO breach incident | Page candidate | Automated |
| 30 | Partial telemetry | Unknown | Automated |
| 31 | OTel Collector queue overload | Inspect exporter/drop metrics | Guided |
| 32 | Missing trace propagation | Inspect W3C headers/context | Guided |
| 33 | Prometheus label explosion | Remove high-cardinality labels | Guided |
| 34 | PostgreSQL pool wait | Correlate query/connection spans | Guided |
| 35 | Elasticsearch search rejections | Correlate fanout/disk pressure | Guided |
| 36 | MongoDB cursor slowness | Inspect pool/index telemetry | Guided |
| 37 | Kafka lag/rebalance | Inspect consumer traces | Guided |
| 38 | Kubernetes CPU throttling | Correlate cgroup/RED | Guided |
| 39 | Privacy leak in logs | Contain and rotate credentials | Guided |
| 40 | High error-budget burn | Mitigate and verify recovery | Guided |

## Troubleshooting and runbooks

**Collector/exporter outage:** protect app traffic, inspect queue and dropped spans, restore TLS/auth, validate backend health and record coverage gaps.

**Missing trace context:** inspect HTTP traceparent, Kafka headers, async context propagation, sampling and clock skew.

**Metric cardinality:** identify unbounded labels, stop bad instrumentation and recover metrics storage.

**SLO burn:** validate request eligibility, compare traces and resource saturation, halt risky deployments and verify recovery.

**DBRE latency:** correlate PostgreSQL query plans/locks, Elasticsearch shard/I/O pressure and MongoDB pool wait before scaling clients.

**Log privacy incident:** restrict access, preserve forensic evidence, rotate exposed secrets and apply robust structured redaction.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| OTel and distributed tracing architecture | 20 |
| Structured logs, Prometheus metrics and RED/USE | 20 |
| SLI/SLO/error budget and burn-rate correctness | 20 |
| Incident correlation across databases/Kubernetes | 15 |
| Troubleshooting, privacy and on-call runbooks | 15 |
| Automated tests and validation evidence | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, local tests executed, correct unknown-coverage behavior, no-write evidence and reviewed production instrumentation/rollback design.

**Validation:** Test source published; exact committed execution, CI, real exporters and live SLO validation pending.
