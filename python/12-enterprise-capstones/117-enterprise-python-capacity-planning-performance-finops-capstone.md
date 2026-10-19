# Chapter 117 — Enterprise Python Capacity Planning, Performance Engineering and FinOps Capstone

**Part 12 — Enterprise Capstone Projects | Chapter 117/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/117-capacity-performance-finops-sre-dbre-lab.md) · [Executable offline project](labs/117/README.md)

## Objectives

Build evidence-driven enterprise capacity and cost plans across Python APIs, Kafka workers, Kubernetes, PostgreSQL, Elasticsearch/OpenSearch, MongoDB, Redis and Snowflake. Profile workloads, forecast CPU/memory/storage/IOPS, model database connection budgets, plan autoscaling and load tests, allocate cloud costs, protect SLOs and document production change gates.

## Architecture

```text
  business demand / traffic forecasts / retention / SLO
                        |
       workload characterization and baselines
                        |
          Python profiling + OTel/Prometheus
                        |
 CPU/memory/network/IOPS | DB connections/shards | queue lag
                        |
       scenario forecast + load/soak tests
                        |
 K8s HPA/Karpenter | DB sizing | storage tiers | Snowflake
                        |
      cost attribution + rightsizing + savings plan
                        |
  change review -> canary -> SLO guardrail -> rollback
```

## 1. Capacity planning fundamentals

Measure baseline p50/p95/p99, request and event throughput, payload distribution, query complexity, peak-to-average ratio, concurrency, retry amplification, batch size, storage growth and retention. Build a demand model from observed utilization and business seasonality; avoid extrapolating a single peak blindly. Separate capacity (what can be served), performance (latency/throughput under load), and resilience (survival during failures). Model headroom for node loss, maintenance, bursts and forecast error.

Forecast example: demand at day N = baseline × (1 + daily growth)^N; required provisioned capacity = forecast / (1 − reserved headroom). State assumptions, confidence interval, forecast horizon and owner. Compound growth is an illustrative scenario, not a statistically fitted prediction.

## 2. Python workload profiling

Use `cProfile`/`pstats` for CPU-bound hotspots, `tracemalloc` for allocation analysis, structured timers and OTel traces for IO wait. Profile realistic payloads and steady-state warmed services, not only microbenchmarks. Distinguish wall-clock from CPU time and thread concurrency from process-level parallelism; investigate GIL constraints for CPU-heavy code. Track worker RSS, object retention, GC, file descriptors and async event-loop blocking. Limit profiling overhead and avoid capturing sensitive payloads.

## 3. CPU, memory and throughput sizing

Estimate CPU cores from arrival rate × CPU milliseconds per request / 1000 / target utilization. Example 500 RPS × 4 ms CPU = 2 CPU-seconds/second; at 65% utilization, budget approximately 3.08 cores before per-pod overhead and failure headroom. Use queueing theory carefully: Little's Law L = λW under stable steady-state assumptions; as utilization nears saturation, queueing latency may rise nonlinearly. Estimate memory from baseline RSS + in-flight request buffers + caches + connection overhead + safety margin. Validate Kubernetes memory limits against measured p99 RSS and OOM history.

## 4. Kubernetes and autoscaling

Set measured requests/limits and appropriate HPA targets; choose KEDA/event-driven scaling for Kafka lag when applicable, subject to partition count and downstream limits. Plan node allocatable after kube/system reserved, daemonsets, disruption budgets, topology spread, zonal failure and pod startup delays. Scale APIs without exhausting PostgreSQL connection pools or Redis/Elasticsearch capacity. Consider VPA recommendations separately from HPA, and Karpenter/Cluster Autoscaler provisioning lead times. Model replica cap and saturation rather than assuming infinite scaling.

## 5. PostgreSQL and MongoDB

For PostgreSQL, measure `pg_stat_statements`, `pg_stat_activity`, lock waits, buffer cache, WAL rate, checkpoint IO, storage latency, replication lag and total pool demand (replicas × per-pod connections + admin reserve). Use PgBouncer or equivalent where appropriate and validate transaction pooling compatibility. For MongoDB, monitor WiredTiger cache/evictions, replication lag, oplog window, working set, connection checkout, query plans and shard distribution. Rightsize CPU/RAM/IOPS together; a larger instance does not fix missing indexes.

## 6. Elasticsearch/OpenSearch, Redis and Kafka

For Elasticsearch/OpenSearch, forecast indexed bytes × retention × (1 + replica count) × compression/overhead, plus disk watermarks and merge headroom. Monitor shard size, segment merges, disk queue/IOPS, query fanout, heap/GC, threadpool rejections and coordinator pressure. For Redis, track memory fragmentation, hot keys, evictions, CPU saturation, connection count and origin-protection behavior. For Kafka, plan ingress/egress throughput, partitions, consumer parallelism, retention storage, broker disk/network, ISR replication and catch-up capacity. Model backpressure to avoid cascading retries.

## 7. Storage, IOPS and network

Translate transactions/sec into IO operations/sec and bytes/sec using observed read/write amplification, cache-hit rate, compaction/merge and checkpoint behavior. Compare both IOPS and throughput limits; provision for latency under burst, not only average bandwidth. Separate cloud disk classes, throughput quotas and queue depth. Model retention, snapshots, backup copies, cross-region replication and lifecycle tiers. Example: 600 ops/sec × 2 disk IO/op = 1,200 IOPS; a 5,000 IOPS disk is at 24% raw utilization, but actual latency and burst credits must still be measured.

## 8. Snowflake and data pipeline cost

Attribute Snowflake warehouse credits, cloud services, storage, Time Travel, fail-safe, tasks, streams and data transfer by owner/workload. Use query history and warehouse load to distinguish concurrency pressure from inefficient SQL. Compare warehouse size vs runtime, auto-suspend/resume, multi-cluster policy, materialization and pruning. For data pipelines, measure CDC freshness and cost per processed GB/event; throttling cost cannot violate agreed freshness SLOs.

## 9. FinOps attribution and optimization

Use cost allocation tags, namespaces, service/team owners, workload labels, account/project, environment and billing exports. Allocate shared infrastructure transparently (usage-based or agreed ratio). Track unit economics: USD/1k requests, USD/GB indexed, USD/million events, USD/query and USD/tenant with privacy-safe aggregation. Compare on-demand vs commitments, spot risk, storage tiering, reserved capacity and rightsizing. Include migration/engineering labor and availability risk when calculating savings; do not optimize only for lowest bill.

## 10. Load, stress, soak and chaos testing

Define workload mix, baseline, ramp-up, steady state, spike, soak, failure injection and recovery. Use k6/Locust or approved load tools in staging; apply explicit traffic caps and owner approval. Measure p95/p99, throughput, errors, queue depth, CPU, RSS, IOPS, DB connections and downstream latency. Keep synthetic test data and avoid PHI/PII. Test rollback thresholds and repeatability. The offline `loadtest` evaluates sample latency/error thresholds; it does not generate traffic.

## 11. SLO and change guardrails

Require sufficient CPU headroom, safe disk IO, database connection reserve, passing load-test latency/error thresholds, budget approval, rollback plan and accountable owner. Set canary stop conditions for 5xx, p99, saturation, Kafka lag, DB locks and cloud spend. Define error-budget policy and freeze risky changes when exhausted. Unknown telemetry should block automated promotion. The simulator's gate is advisory only.

## 12. Troubleshooting and operational runbooks

**API latency under load:** profile CPU vs IO wait, trace dependencies, inspect p99 and retry storms, throttle or roll back.

**Kubernetes CPU throttling/OOM:** compare requests/limits, node allocatable, RSS and HPA; revise sizing and validate with soak test.

**PostgreSQL connection exhaustion:** inspect `pg_stat_activity`, total pod pools, reserved admin slots and PgBouncer; cap replica/pool combinations.

**Elasticsearch IOPS bottleneck:** inspect disk queue, merges, fetch latency, shard size and oversized queries; reduce pressure and plan storage class upgrade.

**MongoDB cache pressure:** inspect working set, eviction, checkpoint IO and query plans; optimize index/data model before adding RAM.

**Redis hot key/stampede:** bound request amplification, add coalescing/jitter and protect the origin.

**Kafka lag:** inspect partition skew, processing time, downstream saturation and rebalance; cap catch-up throughput.

**Snowflake cost spike:** inspect query history, warehouse sizing, auto-suspend and data scans; measure savings without SLO regression.

**Budget overrun:** trace unallocated costs, anomalies, cross-region transfer and idle resources; document risk-adjusted savings.

## 13. Executable capstone and assessment

The [complete lab](labs/117-capacity-performance-finops-sre-dbre-lab.md) and [offline Python project](labs/117/README.md) implement growth forecasting, CPU sizing, replica saturation, retention/replica storage, disk IOPS, connection budgets, cost attribution, load-test SLO evaluation and advisory production gates. Automated tests and 40 incident exercises cover failure boundaries.

**Validation boundary:** No real cloud APIs, profilers, load generators, Kubernetes clusters, billing exports or production changes are included. Actual costs require current rate cards and measured utilization; simulated costs are examples. Exact committed tests, CI, live load tests and production acceptance remain pending.

**Next:** Chapter 118 — Enterprise Python Multi-Region High Availability, Failover and Recovery Capstone.
