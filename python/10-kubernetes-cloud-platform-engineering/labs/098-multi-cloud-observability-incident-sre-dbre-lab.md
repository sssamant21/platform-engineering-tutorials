# Chapter 098 — Multi-Cloud Observability and Incident Automation SRE/DBRE Lab

[Standalone project](098/README.md) · [Python source](098/incident_lab.py) · [Automated tests](098/test_incident_lab.py)

## Mission and architecture

Build a safe, offline cross-cloud incident response pipeline for AWS CloudWatch, Azure Monitor, GCP Cloud Monitoring and OpenTelemetry-shaped trace data.

```text
Synthetic AWS/Azure/GCP metrics + OTel trace ID
   -> normalize and validate freshness
   -> bounded pagination
   -> SLO/error-budget calculation
   -> deduplicate alerts and correlate by service/window
   -> incident evidence, no causality claim
   -> deterministic advisory plan and simulated approval
   -> JSON report, zero mutations
```

## Lab 1 — Execute

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/098
python -m compileall -q incident_lab.py test_incident_lab.py
python -m unittest -v test_incident_lab.py
python incident_lab.py --dry-run
```

## Lab 2 — Normalize CloudWatch, Azure Monitor and GCP Monitoring

Compare provider identity, scope, service, metric, value, timestamp and severity. Reject stale/future/NaN samples and malformed trace IDs. Design live read-only collectors for boto3 CloudWatch GetMetricData, Azure Monitor MetricsQueryClient and Google Cloud Monitoring MetricServiceClient; **the published code does not call these APIs**.

## Lab 3 — OpenTelemetry traces and incident correlation

Use a synthetic valid trace ID to connect provider alerts to the same service. Deduplicate identical signals. Group by service and 300-second buckets. Verify that the report explicitly says `causality: not-established`. In production, include tenant/environment and dependency topology to prevent false merges.

## Lab 4 — SLOs and error budgets

Calculate availability from 9,980 good / 10,000 total requests at a 99.9% target. The allowed error budget is approximately 10 requests; 20 failures yield a 2.0 consumption ratio for the measured window. Design multi-window burn-rate alerts for production, with low-traffic safeguards.

## Lab 5 — Change governance

Generate a canonical SHA-256 fingerprint for the `investigate` advisory action. Simulate owner approval, digest match and rollback evidence. Reject restart, failover and delete actions. Even with simulated approval, **zero cloud writes** are possible.

## Production incident simulations

| Scenario | Expected result | Mode |
|---|---|---|
| Valid AWS/Azure/GCP signals | Normalize | Automated |
| Unsupported provider | Reject | Automated |
| NaN/negative telemetry | Reject | Automated |
| Invalid trace ID | Reject | Automated |
| Invalid severity | Reject | Automated |
| Stale/future signal | Reject | Automated |
| Malformed record | Reject | Automated |
| Empty/paginated response | Handle | Automated |
| Page/item budget exceeded | Fail closed | Automated |
| Repeated continuation token | Reject | Automated |
| Malformed page | Reject | Automated |
| Healthy SLO | Not breached | Automated |
| Breached SLO | Flag | Automated |
| Invalid/empty SLO denominator | Reject | Automated |
| Excess error budget consumption | Burn ratio >1 | Automated |
| Repeated alert | Deduplicate | Automated |
| Multi-cloud same-service alert | Correlate | Automated |
| Correlation vs causation | Not established | Automated |
| Different time buckets | Separate incidents | Automated |
| Different services | Separate incidents | Automated |
| Unstable plan ordering | Stable digest | Automated |
| Destructive remediation | Reject | Automated |
| Missing approval | Hold | Automated |
| Wrong plan digest | Hold | Automated |
| Missing rollback evidence | Hold | Automated |
| Approved advisory action | Zero writes | Automated |
| CloudWatch API 429 | Bounded retry | Guided |
| Azure Monitor missing series | Mark unknown | Guided |
| GCP Monitoring quota | Check quotas | Guided |
| OTel trace gap | Check sampling/exporter | Guided |
| Elasticsearch disk IOPS saturation | Check queue/latency/shards | Guided |
| PostgreSQL connection saturation | Check pools/locks | Guided |
| Multi-region outage | Apply reviewed DR plan | Guided |

## Troubleshooting runbooks

**Collector failures:** validate provider identity, IAM/RBAC, API quota, time range, dimensions and completeness. Never silently treat absent metrics as zero.

**SLO burn:** confirm eligible requests, denominator, target, time window, deployments and customer impact. Escalate per error-budget policy.

**Trace gaps:** check instrumentation, context propagation, exporter backpressure, sampling, clock skew and PII redaction.

**Cross-cloud correlation:** inspect service topology and deployment history; do not claim root cause from timestamp coincidence.

**DBRE incident:** correlate PostgreSQL locks/connections, Elasticsearch query/shard pressure and cloud disk throughput before changes.

**Change gate:** require authenticated, expiring approval, owner, blast radius, tested rollback and immutable audit.

## 100-point assessment

| Competency | Points |
|---|---:|
| CloudWatch, Azure Monitor, GCP Monitoring architecture | 20 |
| Telemetry normalization and OpenTelemetry | 20 |
| SLO/error-budget calculations | 20 |
| Alert deduplication and incident correlation | 15 |
| Approval, dry-run and idempotency | 15 |
| Tests, incident simulations and runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90/100 plus independently executed offline tests, no-write evidence and reviewed incident runbooks.

**Validation:** Equivalent offline source and 36 tests passed locally before publication; GitHub CI and live cloud integrations remain pending.
