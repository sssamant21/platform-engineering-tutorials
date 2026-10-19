# Chapter 115 — Enterprise Observability, SLO and Incident Response Lab

[Offline simulator](115/observability_lab.py) · [Automated tests](115/test_observability_lab.py) · [Project guide](115/README.md)

## Scenario

A Python API and Kafka/CDC workers on Kubernetes experience p99 regression, PostgreSQL pool pressure, Elasticsearch rejections, MongoDB elections, Redis stampedes and Snowflake lag. Use traces, RED/USE, SLOs and correlated signals to diagnose safely. This is offline simulation, not live monitoring.

## Execute

```bash
cd python/12-enterprise-capstones/labs/115
python -m compileall -q observability_lab.py test_observability_lab.py
python -m unittest -v test_observability_lab.py
python observability_lab.py --dry-run
python observability_lab.py --partial
```

## Hands-on sequence

1. Validate parent/child spans, detect cycles, missing parents and duplicate IDs; design OTel propagation.
2. Redact sample log fields; design JSON logs, privacy controls and trace IDs.
3. Calculate RED request/error/p99 and USE utilization/saturation/error signals.
4. Compute availability SLI, remaining error budget and no-traffic unknown state.
5. Evaluate multiwindow burn-rate page/observe decisions.
6. Correlate traces, metrics, logs and change events by incident.
7. Simulate missing telemetry and block advisory promotion.
8. Draft a UTC incident timeline, on-call escalation, communications and rollback.
9. Write a postmortem with detection gaps, owners and measurable actions.
10. Define staging acceptance for OTel Collector, Prometheus and dashboards.

## Forty production incident simulations

| # | Scenario | Response |
|---|---|---|
| 1 | Malformed span | Reject |
| 2 | Duplicate span | Reject |
| 3 | Orphan span | Investigate propagation |
| 4 | Trace cycle | Reject |
| 5 | Negative duration | Reject |
| 6 | OTel Collector outage | Unknown coverage |
| 7 | Exporter queue full | Inspect drops |
| 8 | Kafka trace broken | Restore headers |
| 9 | Sensitive logs | Redact/contain |
| 10 | Metrics cardinality | Bound labels |
| 11 | API 5xx | RED and trace correlation |
| 12 | API p99 | Critical-path diagnosis |
| 13 | PostgreSQL pool exhausted | Connection budget |
| 14 | PostgreSQL locks | Blocked sessions |
| 15 | Elasticsearch 429 | Reduce fanout |
| 16 | Elasticsearch IOPS | Disk diagnosis |
| 17 | MongoDB election | Reconcile writes |
| 18 | Redis stampede | Protect origin |
| 19 | Kafka lag | Inspect partitions |
| 20 | CDC WAL retention | Inspect slots |
| 21 | Snowflake load lag | Inspect tasks |
| 22 | Kubernetes CPU throttling | Resource limits |
| 23 | Kubernetes OOM | Memory analysis |
| 24 | HPA pool amplification | Bound replicas |
| 25 | SLO breach | Error-budget policy |
| 26 | No traffic | Unknown SLI |
| 27 | Fast burn | Page per policy |
| 28 | Slow burn | Ticket/escalate |
| 29 | Short-window noise | Require confirmation |
| 30 | Trace coverage gap | Hold release |
| 31 | Rollback missing | Hold |
| 32 | Owner missing | Hold |
| 33 | Approval missing | Hold |
| 34 | Canary regression | Roll back |
| 35 | Correlated alarm flood | Deduplicate |
| 36 | Stale dashboard | Verify freshness |
| 37 | Alert fatigue | Tune alerts |
| 38 | Handoff failure | Preserve timeline |
| 39 | Postmortem action overdue | Escalate |
| 40 | Multi-region incident | Validate RPO/RTO |

## Runbooks

**API:** Inspect RED, p99, traces, recent deployments and timeouts; roll back verified regressions.

**PostgreSQL:** Inspect `pg_stat_activity`, locks and aggregate pool limits; reserve admin access.

**Elasticsearch:** Inspect shard fanout, fetch latency, rejections and disk IOPS; reduce pressure.

**MongoDB:** Inspect election, replication lag, write concern and uncertain writes.

**Redis:** Inspect hot keys, evictions, TTL and origin pressure; prevent stampedes.

**Kafka/CDC:** Inspect offsets, event age, DLQ, connector lag and WAL/oplog retention.

**Snowflake:** Inspect load history, stage manifests, `MERGE`, task failures and cost.

**Telemetry:** Inspect Collector, TLS, queue drops and sampling; mark missing evidence unknown.

**On-call:** Record severity, customer impact, incident commander, UTC timeline, mitigations, communications and follow-up.

## 100-point assessment

| Domain | Points |
|---|---:|
| OTel tracing and structured logging | 20 |
| Prometheus RED/USE | 15 |
| SLOs, error budgets and burn rates | 20 |
| Incident correlation and on-call | 20 |
| Runbooks, postmortems and gates | 15 |
| Automated tests and evidence | 10 |
| **Total** | **100** |

Pass at 90+ with executed tests, no-live-write evidence, an SLO specification, incident timeline and rollback design.

**Validation:** Source and tests published; exact committed execution, CI, live telemetry and production acceptance pending.
