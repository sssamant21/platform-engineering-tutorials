# Chapter 111 — Enterprise Python Architecture and Project Foundations SRE/DBRE Lab

[Offline evaluator](111/enterprise_lab.py) · [Automated tests](111/test_enterprise_lab.py) · [Project guide](111/README.md)

## Scenario

A Python API and Kafka worker platform on Kubernetes integrates PostgreSQL, Elasticsearch/OpenSearch, MongoDB and Redis. Design dependency contracts, capacity boundaries, SLOs, security controls and recovery procedures before implementing production adapters.

## Lab 1 — Baseline

```bash
cd python/12-enterprise-capstones/labs/111
python -m compileall -q enterprise_lab.py test_enterprise_lab.py
python -m unittest -v test_enterprise_lab.py
python enterprise_lab.py --dry-run
python enterprise_lab.py --partial
```

The `--partial` option removes trace coverage evidence and must hold the advisory release. Record the report fingerprint and verify zero network/mutations.

## Lab 2 — Architecture and repository foundation

Create an ADR for source-of-truth ownership and cross-store consistency. Sketch `src/platform_app/api`, `workers`, `domain`, `ports`, `adapters`, `security`, `telemetry`, `tests`, `deploy` and `docs/runbooks`. Define API input contracts, error taxonomy, idempotency and deadlines; design Kafka consumer offset and partition-order semantics.

## Lab 3 — Data-store capacity and isolation

Compute aggregate PostgreSQL connections as replicas × per-replica pool, reserving administrative headroom. Specify Elasticsearch search concurrency, pagination and alias-based reindexing; MongoDB read/write concern, indexes and failover; Redis TTL and stampede protection; Kafka partitions, retries and DLQ.

## Lab 4 — Kubernetes, security and telemetry

Design Kubernetes service accounts/workload identity, NetworkPolicies, probes, CPU/memory budgets, HPA/PDB and GitOps promotion. Specify trace context across HTTP/Kafka, structured redacted logs, Prometheus RED/USE metrics and availability/p99 SLOs.

## Lab 5 — Failure-mode and incident exercises

| # | Incident | Expected investigation |
|---|---|---|
| 1 | Unsupported dependency edge | Reject architecture |
| 2 | Duplicate dependency contract | Reject |
| 3 | Zero/oversized timeout | Reject |
| 4 | Invalid inflight budget | Reject |
| 5 | Excess retry count | Reject |
| 6 | PostgreSQL connection overcommit | Hold scaling |
| 7 | Connection reserve exhausted | Reject configuration |
| 8 | Queue overload | Reject excess work |
| 9 | Invalid latency samples | Reject |
| 10 | p99 regression | Investigate and roll back |
| 11 | SLO error-budget breach | Halt promotion |
| 12 | No-traffic SLI | Unknown |
| 13 | Unauthorized API role | Hold |
| 14 | Overdue secret rotation | Hold |
| 15 | Missing tracing evidence | Hold |
| 16 | Missing rollback plan | Hold |
| 17 | PostgreSQL pool wait and locks | Inspect sessions and queries |
| 18 | Elasticsearch search rejections | Bound fanout, inspect shards and IOPS |
| 19 | MongoDB primary failover | Validate write concern and idempotency |
| 20 | Redis cache stampede | Limit origin load |
| 21 | Kafka consumer lag | Check partition skew and worker CPU |
| 22 | Kafka rebalance duplicates | Validate commit/idempotency |
| 23 | Kubernetes CPU throttling | Adjust worker/pod budgets |
| 24 | Kubernetes OOMKilled | Inspect memory and restart policy |
| 25 | OpenTelemetry Collector outage | Preserve app traffic and mark evidence unknown |
| 26 | Compromised workload identity | Contain, revoke and audit |
| 27 | Dependency vulnerability | Block release, review provenance |
| 28 | Unsafe migration | Restore/rollback plan |
| 29 | Multi-region failover | Fencing and consistency |
| 30 | Canary SLO breach | Roll back and verify recovery |

## Runbooks

**PostgreSQL saturation:** inspect `pg_stat_activity`, pool wait, locks and aggregate replicas; throttle ingress and protect admin reserve.

**Elasticsearch slowness:** inspect shard fanout, large page sizes, rejections, disk IOPS and merge pressure; narrow queries and lower concurrency.

**MongoDB failover:** inspect election, driver retry behavior, oplog and uncertain writes; reconcile data before replay.

**Redis outage:** cap cache-miss concurrency and monitor origin database; recover TTL/invalidation safely.

**Kafka lag:** inspect consumer health, rebalance, processing CPU, partitions and offsets; preserve ordering.

**Kubernetes rollout:** inspect events, readiness, quotas, HPA/PDB, OOM and CPU throttling; roll back immutable artifact if needed.

**Telemetry outage:** preserve evidence, check Collector/exporter queues, credentials and sampling; report unknown coverage.

## Final 100-point assessment

| Domain | Points |
|---|---:|
| Architecture, ADRs and project layout | 20 |
| API/worker contracts and data consistency | 20 |
| Database/cache/search/Kafka capacity | 20 |
| Kubernetes security and infrastructure boundaries | 15 |
| Observability, SLOs and reliability runbooks | 15 |
| Executable tests and evidence | 10 |
| **Total** | **100** |

Pass at least 90 points with local tests executed, an architecture review, failure-mode checklist, and approved rollback design.

**Validation:** Offline source and tests published; exact committed runtime execution, CI, live adapters and production acceptance pending.
