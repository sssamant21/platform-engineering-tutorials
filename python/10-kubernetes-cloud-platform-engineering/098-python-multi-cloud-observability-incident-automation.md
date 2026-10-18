# Chapter 098 — Python Multi-Cloud Observability and Incident Automation

**Part 10 | Chapter 098/120 | Python 3.11+**

[Hands-on lab](labs/098-multi-cloud-observability-incident-sre-dbre-lab.md) · [Executable project](labs/098/README.md)

## Learning outcomes

Design safe cross-cloud observability and incident response using AWS CloudWatch, Azure Monitor, Google Cloud Monitoring and OpenTelemetry. Normalize metrics, traces and logs; evaluate SLIs/SLOs and error budgets; correlate alerts without falsely inferring causality; deduplicate incidents; apply approval gates, idempotency and dry-run.

## Reference architecture

```text
CloudWatch (AWS) ────────┐
Azure Monitor ───────────┼─> read-only collectors -> normalization/freshness
Cloud Monitoring (GCP) ──┤                                  |
OpenTelemetry traces ────┘                       SLI/SLO + burn-rate checks
                                                        |
                                         dedup / time-window correlation
                                                        |
                                         incident evidence + trace links
                                                        |
                                        deterministic advisory plan hash
                                                        |
                                      authenticated approval (future)
                                                        |
                                      no remediation writes in lab
```

## 1. Cloud-native telemetry sources

**AWS CloudWatch:** Use boto3 `cloudwatch.get_metric_data` for metrics with namespace, dimensions, period and time window. CloudWatch Logs Insights and X-Ray provide related logs/traces. Use explicit account and region; STS verifies identity. Handle delayed/missing datapoints.

**Azure Monitor:** Use `azure-monitor-query` MetricsQueryClient/LogsQueryClient with `azure-identity`. Select the resource URI, metric namespace, aggregation, time grain and scope. Monitor diagnostic settings and Log Analytics ingestion latency. Azure subscription and Entra ID identity must be checked.

**Google Cloud Monitoring:** Use `google-cloud-monitoring` MetricServiceClient.list_time_series, scoped to `projects/PROJECT`, filter and interval. Cloud Logging and Cloud Trace supply related evidence. Verify ADC project, quota project and IAM.

**OpenTelemetry:** Instrument services with trace/span context, stable service/resource attributes and semantic conventions. Preserve valid 32-hex trace IDs and 16-hex span IDs. Propagate W3C traceparent where applicable. Traces show temporal relationships and dependencies, but **correlation is not proof of causation**.

These SDK calls are **design references**; the executable lab is offline and does not query live cloud services.

## 2. Normalized telemetry model

Use `provider, scope, service, metric, value, unit, timestamp, severity, trace_id`. Preserve raw provider metadata separately and convert units explicitly (milliseconds vs seconds, bytes vs GiB, percentages vs fractions). Avoid combining different metric semantics. Reject NaN, negative values where invalid, future/stale timestamps and malformed trace IDs. Mark missing metrics as **unknown**, not healthy.

## 3. SLOs, error budgets and burn rate

Define request-based availability SLI as good requests / eligible requests. For target `T` over `N` eligible requests, allowable bad events = `N × (1−T)`; consumed budget = `N−good`; budget burn ratio = consumed/allowable. A burn ratio greater than one means the measured window exceeded its full allowed error budget, **not** a rate-of-consumption alarm across time windows. Production alerting should use multi-window burn-rate thresholds, minimum request volume, appropriate traffic weighting and SLO measurement windows.

Example: 9,980 good of 10,000 at 99.9% target yields 20 bad requests against 10 allowed; budget burn ratio 2.0.

## 4. Alert deduplication and incident correlation

Use stable service identity and bounded time buckets to group related alerts. Deduplicate repeated provider/scope/metric/severity signals. Preserve original timestamps, trace IDs, provider scopes and source IDs for audit. A common incident group is a **hypothesis**, not an RCA. Do not automatically merge unrelated tenants or production and staging: production collectors must include environment/tenant in grouping keys.

Use topology, deploy events, logs and traces to investigate root cause. Keep incidents open while missing telemetry or partial collector results prevent reliable conclusions.

## 5. Retries, pagination and backpressure

Bound pagination, item counts, timeouts and concurrent calls. Retry transient 429 and 5xx with capped exponential backoff and jitter; honor Retry-After. Never retry 401/403 blindly. Account for CloudWatch API quotas, Azure Monitor throttling and Google Cloud Monitoring quota/retention limits. Persist checkpointed cursors only after complete pages and ensure deduplication across retries.

## 6. Approval-gated remediation and idempotency

Separate **observe → propose → authorize → execute → verify → rollback**. A deterministic SHA-256 plan fingerprint binds incident, action and scope, but does not authenticate approval. Require a distinct approver, expiring authorization, change ticket, maintenance window, backup/rollback evidence, blast-radius checks and post-change SLO validation.

The lab deliberately supports only the advisory action `investigate`, even with simulated approval; **no restart, scale, delete or failover code exists**.

## 7. Production incident simulations

| Scenario | Response |
|---|---|
| CloudWatch high latency and errors | Correlate request SLIs and traces |
| Azure Monitor AKS CPU pressure | Inspect node, pod and autoscaler metrics |
| GCP Cloud SQL storage saturation | Check storage, IOPS, connections and HA |
| Cross-cloud dependency timeout | Trace end-to-end request, avoid causal guess |
| Repeated alerts | Deduplicate and preserve provenance |
| Stale or missing metrics | Mark unknown and suppress false recovery |
| Invalid trace ID | Reject or quarantine telemetry |
| API throttling | Bounded retry, backoff and rate budget |
| Multi-window SLO burn | Escalate per error-budget policy |
| Elasticsearch slow queries | Correlate storage IOPS, shard pressure and workload |
| PostgreSQL connection exhaustion | Check pool saturation, locks and DB metrics |
| Unauthorized remediation | Hold and audit |
| Failed rollback | Escalate, protect data and freeze further changes |

## 8. SRE/DBRE runbooks

**Collector failure:** verify cloud identity/scope, IAM/RBAC, rate limits, clock skew and telemetry freshness; mark coverage incomplete.

**SLO alert:** validate numerator/denominator, eligible traffic, window and deployment timeline; check burn and customer impact.

**Multi-cloud incident:** compare trace IDs, service topology, dependency health and per-provider evidence; document uncertain causality.

**Database incident:** check connections, replication, storage latency/IOPS, backups, query plans and change history before intervention.

**Approval/rollback:** verify incident ID, signed approval, expiry, resource scope, rollback rehearsal and post-change health. No automatic destructive actions.

## 9. Hands-on lab

The [Chapter 098 lab](labs/098-multi-cloud-observability-incident-sre-dbre-lab.md) includes a Python 3.11+ offline simulator, **36 independently executed unit tests**, synthetic three-cloud telemetry, SLO/error-budget calculation, deduplication, incident correlation, advisory plan fingerprint and no-write approval gate. The project also includes a 100-point assessment.

**Validation:** The offline Python code passed 36 local unit tests and syntax compilation before GitHub publication. Real CloudWatch/Azure Monitor/GCP Monitoring/OpenTelemetry ingestion and GitHub CI are not executed.

**Next proposed:** Chapter 099 — Python Cloud Platform Security, Secrets and Compliance Automation.
