# Chapter 117 — Capacity Planning, Performance Engineering and FinOps SRE/DBRE Lab

[Offline simulator](117/capacity_lab.py) · [Automated tests](117/test_capacity_lab.py) · [Project guide](117/README.md)

## Mission

A Kubernetes Python API scales during a peak; PostgreSQL pools exhaust, Elasticsearch disk IOPS queues, Kafka lag increases and Snowflake spend rises. Forecast demand, quantify capacity and cost, test SLO gates and plan a reversible optimization without touching production.

## Execute

```bash
cd python/12-enterprise-capstones/labs/117
python -m compileall -q capacity_lab.py test_capacity_lab.py
python -m unittest -v test_capacity_lab.py
python capacity_lab.py --dry-run
python capacity_lab.py --overload
```

## Hands-on labs

**Lab 1 — Baseline and forecast:** define workload RPS, CPU milliseconds, peak ratio, daily growth, retention, replica count and forecast confidence. Model 30-day demand and failure headroom.

**Lab 2 — Python and Kubernetes:** derive CPU core demand, per-pod throughput, HPA caps and connection amplification. Design staging profiling with cProfile, tracemalloc, OTel and a 30-minute soak test.

**Lab 3 — Stateful services:** model PostgreSQL connection reserve, Elasticsearch IOPS/storage, MongoDB working set, Redis cache limits, Kafka partition throughput and Snowflake warehouse utilization.

**Lab 4 — Load and SLO:** compare synthetic latency samples/errors against p99/error thresholds, simulate overload and hold release when saturation is detected.

**Lab 5 — FinOps:** allocate synthetic resource costs by team, calculate USD/1k requests and evaluate rightsizing with SLO, reliability and migration effort tradeoffs.

## Forty production incident simulations

| # | Failure | Response |
|---|---|---|
| 1 | Negative demand forecast | Reject |
| 2 | Invalid growth assumptions | Reject |
| 3 | Zero capacity headroom | Review |
| 4 | CPU saturation | Profile/scale |
| 5 | CPU target misconfigured | Correct |
| 6 | CPU-bound Python hot path | Profile |
| 7 | Async event loop blocking | Isolate work |
| 8 | Memory leak | Trace allocations |
| 9 | Kubernetes OOM | Right-size |
| 10 | CPU throttling | Inspect limits |
| 11 | HPA cap reached | Hold/rate-limit |
| 12 | Node provision delay | Add headroom |
| 13 | Zonal capacity loss | Validate N+1 |
| 14 | PostgreSQL pool exhaustion | Bound connections |
| 15 | PostgreSQL lock waits | Inspect blocking |
| 16 | PostgreSQL WAL IOPS spike | Inspect checkpoints |
| 17 | MongoDB cache eviction | Inspect working set |
| 18 | MongoDB shard imbalance | Rebalance plan |
| 19 | Elasticsearch merge throttling | Inspect IOPS |
| 20 | Elasticsearch oversized shards | Reindex plan |
| 21 | Elasticsearch search fanout | Optimize queries |
| 22 | Redis hot key | Coalesce load |
| 23 | Redis eviction storm | Revisit sizing |
| 24 | Kafka partition skew | Repartition plan |
| 25 | Kafka consumer lag | Inspect bottleneck |
| 26 | Disk IOPS cap | Upgrade/throttle |
| 27 | Disk throughput cap | Check bandwidth |
| 28 | Network egress spike | Attribute cost |
| 29 | Retention growth | Lifecycle policy |
| 30 | Snapshot storage growth | Adjust retention |
| 31 | Snowflake credit spike | Query/warehouse review |
| 32 | Snowflake concurrency queue | Tune warehouse |
| 33 | p99 latency breach | Hold release |
| 34 | Error rate breach | Hold release |
| 35 | Soak-test memory creep | Reject change |
| 36 | Load-test unsafe target | Use staging |
| 37 | Unallocated cloud cost | Fix tagging |
| 38 | Budget threshold breach | Hold optimization |
| 39 | Canary regression | Roll back |
| 40 | Multi-region capacity failure | Validate failover |

## Operational runbooks

**CPU/p99:** correlate RED, profile CPU vs IO, inspect concurrency and retry amplification; mitigate before scaling blindly.

**Kubernetes:** inspect node allocatable, HPA events, Karpenter lead time, CPU throttling and RSS/OOM; retain N+1 headroom.

**PostgreSQL:** inspect `pg_stat_activity`, locks and aggregate connection pools; reserve administrative connections.

**MongoDB:** inspect WiredTiger cache, evictions, query plans, oplog and disk latency.

**Elasticsearch:** inspect shards, merges, rejections, disk queue/IOPS and large search pages; throttle and plan disk remediation.

**Redis:** inspect hot keys, memory fragmentation and origin load; protect against cache stampede.

**Kafka:** inspect partitions, event age, consumer lag, rebalance and downstream bottlenecks.

**Snowflake:** inspect query history, warehouse utilization, `MERGE`, task load and credits.

**FinOps:** audit resource tags, idle spend, retention, unit cost and savings assumptions; protect SLOs.

## Final assessment — 100 points

| Domain | Points |
|---|---:|
| Workload forecasting and Python profiling | 20 |
| Kubernetes, CPU/memory and autoscaling | 20 |
| Database, IOPS, storage and connection budgets | 20 |
| Load tests, SLOs and guardrails | 15 |
| FinOps attribution and optimization | 15 |
| Automated tests and runbooks | 10 |
| **Total** | **100** |

Pass at 90+ with locally executed tests, assumptions and unit costs documented, load/soak test plan, reversible change and owner approval.

**Validation:** Offline source and tests published; exact committed execution, CI, real load tests and production acceptance pending.
