# Chapter 087 — Python Infrastructure Monitoring, Metrics and Alert Automation

**Part 09 — DevOps, SRE and Automation | Chapter 087/120 | Python 3.11+**

## Learning objectives

Design and implement a safe host monitoring pipeline with psutil, the Prometheus Python client, OpenTelemetry SDK concepts, metric exporters, threshold/hysteresis alerting, alert deduplication, SLO/error-budget calculations, automated tests and incident runbooks. Distinguish host signals from application golden signals and prevent alert storms.

**Lab:** [Chapter 087 hands-on lab](labs/087-infrastructure-monitoring-metrics-alert-automation-sre-dbre-lab.md) · [Standalone Python project](labs/087/README.md).

## 1. Monitoring architecture

\`\`\`text
CPU / memory / disk / HTTP request outcomes
      -> bounded sampler + input validation
      -> metric registry (Prometheus) + OTEL instruments
      -> /metrics scrape endpoint or approved collector
      -> Prometheus / OTEL Collector -> TSDB
      -> SLO recording rules + alert evaluation
      -> dedup/group/inhibit/routing -> on-call
      -> runbook / incident / remediation approval
\`\`\`

Telemetry must be observational: avoid destructive actions or automatic restart loops. Exporters are not monitoring systems by themselves. Prometheus pulls metric endpoints; OpenTelemetry supports instrumentation and export through an SDK and collector. The chapter lab demonstrates both a Prometheus exposition endpoint and OTEL metric instruments; deployment to a real collector is opt-in.

## 2. Host metrics

\`psutil.cpu_percent(interval=0.1)\` measures CPU usage over an interval; a nonblocking first call may be meaningless. \`psutil.virtual_memory().percent\` reports memory pressure at host level, while container cgroup limits can differ. \`psutil.disk_usage(path).percent\` measures filesystem space, **not disk IOPS, throughput, or latency**. For production storage monitoring, add node-exporter disk I/O metrics, filesystem inode utilization, and cloud volume metrics. Avoid assuming host metrics represent a Pod's resources.

Use \`time.monotonic()\` for intervals/cooldowns and wall time only for timestamps. Validate NaN, infinities, negative values and percentage bounds. Rate-limit sampling to prevent CPU-intensive collectors.

## 3. Prometheus Python client

Create \`Gauge\` instruments for CPU, memory and disk percent; \`Counter\` for sampling failures; \`Histogram\` for scrape/operation duration. Expose a dedicated \`/metrics\` endpoint via \`start_http_server\` only on approved interfaces, with network policy, authentication gateway if required and scrape timeout. Keep labels bounded (e.g., service, environment); **never label with user IDs, resource IDs, raw error messages, secrets or dynamic Pod names**. Multi-process Gunicorn deployments require Prometheus client multiprocess handling rather than sharing ordinary process-local gauges.

Metric names should include units: \`sre_host_cpu_usage_percent\`, \`sre_host_disk_usage_percent\`, \`sre_monitor_sample_errors_total\`. Avoid exporting values from a previous failed scrape as though fresh; track last successful sample time.

## 4. OpenTelemetry

OpenTelemetry Python uses \`opentelemetry-api\` for instrument interfaces and \`opentelemetry-sdk\` for providers/readers/exporters. A \`MeterProvider\` can create observable gauges or counters, with an \`OTLPMetricExporter\` configured through the exporter package and collector endpoint. Use resource attributes such as \`service.name\`, explicit histogram buckets and controlled sampling/cardinality. Do not double-count by instrumenting the same event through multiple exporters. OTEL semantic conventions evolve; pin compatible package versions. The standalone lab includes an optional SDK demonstration without remote export.

## 5. Thresholds, hysteresis and deduplication

Single-sample CPU thresholds cause noisy paging. Use warning/critical thresholds, sustained windows, hysteresis, cooldown and deduplication. Example: warning at 75%, critical at 90%, clear below 70%. The lab's in-process alert engine sends a state-change event immediately, suppresses repeats during a cooldown, and sends a recovery event on clear. This is **not durable distributed alert routing**; production deduplication should be handled by Alertmanager or an incident-management platform with persisted state and grouping.

Correlate metrics before paging: high CPU with normal latency might be expected; elevated error rate and burn rate should generally be higher priority.

## 6. SLOs and error budgets

Availability SLI: \`successful_requests / eligible_requests\`. For an SLO target \`T\`, error budget fraction is \`1 - T\`. Over a window of \`N\` requests, allowed failures \`N(1-T)\`; remaining budget is \`(allowed - observed_failures) / allowed\`. A negative result means exhausted budget. Example: 99.9% target permits about 0.1% failures. Define eligible traffic, exclusions, minimum sample sizes, rolling windows and missing-data behavior. Prefer multiwindow/multiburn alerts over instantaneous availability thresholds.

The lab includes a bounded in-memory request window as a teaching aid, **not** a distributed production SLO evaluator.

## 7. Production SRE/DBRE examples

- **PostgreSQL:** connection saturation, replication lag, transaction age, lock waits, storage growth, checkpoints and query latency.
- **Elasticsearch/OpenSearch:** query/fetch latency, threadpool rejections, shard sizes, disk IOPS, JVM pressure and cluster health.
- **MongoDB:** WiredTiger cache eviction, replication lag, journal/checkpoint latency and disk space.
- **Kafka/MSK:** consumer lag, under-replicated partitions, request queue time and broker disk utilization.
- **Kubernetes:** Pod readiness, restart rate, CPU throttling, PVC pressure, API latency and node conditions.
- **Snowflake:** query queue time, warehouse credits, failed queries and ingestion freshness.

Host CPU/disk alone cannot diagnose these systems. Use service-level telemetry and traces alongside infrastructure signals.

## 8. Incident simulations

1. CPU spike; 2. memory pressure; 3. disk fullness; 4. filesystem inode exhaustion; 5. disk IOPS bottleneck; 6. exporter unavailable; 7. stale scrape; 8. NaN sample; 9. negative sample; 10. warning-to-critical escalation; 11. flapping threshold; 12. duplicate alert storm; 13. cooldown expiry; 14. recovery event; 15. alert routing outage; 16. missing Prometheus target; 17. high-cardinality label explosion; 18. OTLP exporter failure; 19. SLO budget exhaustion; 20. no-traffic SLI; 21. clock skew; 22. counter reset; 23. host/container scope mismatch; 24. production incident during deployment.

## 9. Troubleshooting

| Symptom | Investigation | Response |
|---|---|---|
| Missing metrics | scrape target, port, RBAC/network policy | Restore scrape path and exporter health |
| CPU 100% | load average, throttling, process profile | Correlate latency, saturation and workload |
| Memory >90% | RSS, cgroup limit, page cache, OOM | Review pressure and capacity |
| Disk >90% | mount path, inodes, retention, IOPS | Follow approved cleanup/expansion plan |
| Repeated pages | alert state, grouping, cooldown | Fix rule and route; do not silence blindly |
| No alerts | missing data, thresholds, pipeline | Test alert rule and notification route |
| OTEL export failure | collector, TLS, credentials, queue | Repair exporter and inspect dropped data |
| Error budget negative | SLI definition, sample volume | Freeze risky changes and mitigate impact |

## 10. Runbooks

**Exporter outage:** confirm target reachability, process health, scrape duration, TLS and metric freshness; restore telemetry before interpreting absence as health.

**CPU/memory pressure:** correlate host and container metrics, inspect top processes, application latency, workload change and autoscaler behavior; do not restart stateful DBs without failover analysis.

**Disk pressure:** inspect mount/inodes, growth rate and I/O latency; escalate retention or capacity changes to data owner.

**Alert storm:** verify active incident, suppress duplicates through routing, apply bounded inhibition and preserve critical signal.

**SLO burn:** validate SLI and traffic eligibility, check deployments and dependencies, initiate incident response and stop risky rollouts.

## 11. Lab, tests and assessment

The [executable lab](labs/087-infrastructure-monitoring-metrics-alert-automation-sre-dbre-lab.md) includes actual Python source, offline unit tests, Prometheus and OTEL examples, incident drills and a 100-point assessment. Runtime validation is separately recorded; no production exporter is started during publication.

**Next proposed:** Chapter 088 — Python Incident Response, Diagnostics and Automated Remediation.
