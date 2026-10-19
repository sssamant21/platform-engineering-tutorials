# Chapter 109 — Python Resilience Engineering, Fault Injection and Chaos Testing

**Part 11 — Production Security and Performance | Chapter 109/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/109-resilience-engineering-fault-injection-chaos-sre-dbre-lab.md) · [Executable project](labs/109/README.md)

## Learning objectives

Engineer Python services to survive partial failure using bounded retries, exponential backoff with jitter, deadlines, circuit breakers, bulkheads, load shedding and graceful degradation. Design fault injection and chaos experiments with SLO/error-budget controls, approvals, blast-radius limits, observability and rollback. Validate behavior using deterministic offline tests and production-style SRE/DBRE incident exercises.

## Architecture

```text
HTTP / Kafka / CronJob -> admission + queue limits -> request deadline
                               |
                       retry policy (safe ops)
                       exp backoff + jitter
                               |
                    circuit breaker / bulkhead
                               |
                 PostgreSQL / Elasticsearch / MongoDB
                               |
             telemetry: rate, errors, p95/p99, saturation
                               |
         error budget + chaos gate + rollback / incident review
```

## 1. Resilience engineering foundations

A resilient system degrades gracefully when dependencies fail, recovers without amplifying an outage and protects data integrity. Classify transient failures, permanent errors, timeouts, overload, network partitions, stale reads, unavailable storage and dependency corruption. Distinguish resilience from availability: a successful retry that takes 90 seconds may violate user latency SLOs.

Failure modes include retry storms, thundering herds, queue amplification, cascading timeouts, resource leaks, duplicated writes, partial commits, failover split brain and noisy neighbors. Favor bounded work, observability and explicit service contracts over hidden retries.

## 2. Retries, exponential backoff and jitter

Use retries only for transient, retryable failures and **idempotent operations** or writes protected by idempotency keys and server-side deduplication. Typical schedule: `min(cap, base * 2**attempt)`, with randomized jitter. Full jitter chooses a random delay between zero and the capped exponential delay; equal jitter and decorrelated jitter are alternatives. The offline lab implements a deterministic bounded jitter variant for reproducibility, **not cryptographic randomness or a production retry library**.

Budget retries by maximum attempts, end-to-end deadline, downstream capacity and error budget. Honor server `Retry-After` when applicable, including 429/503 semantics. Do not retry authentication failures, validation errors or non-idempotent DB writes blindly.

## 3. Timeout design and deadline propagation

Define connection, TLS handshake, read, write, pool-acquisition and total request deadlines. Ensure nested retries fit the overall deadline, including backoff, scheduling and cleanup. Propagate deadlines across HTTP/gRPC and async boundaries. Local cancellation does not guarantee remote transaction rollback; verify remote operation outcomes before retrying a write.

## 4. Circuit breakers

A circuit breaker transitions from **closed** (requests permitted) to **open** (fail fast after threshold) to **half-open** (limited probe requests after reset interval). Count failures by dependency and failure class, not indiscriminately. Ensure half-open probe concurrency is bounded and breaker state is thread-safe in production. Use observability to detect flapping and ensure recovery does not trigger a surge.

The teaching simulator models state transitions sequentially; it does not implement concurrent half-open probe admission, distributed state or actual network requests.

## 5. Bulkheads and backpressure

Partition worker pools, semaphores, queues and connection budgets by dependency or priority. For example, isolate PostgreSQL writes from Elasticsearch read fanout so one slow dependency cannot exhaust all Python threads. Bound active tasks and queue depth, reject excess requests predictably, and preserve critical traffic. Backpressure is preferable to an unbounded backlog.

## 6. Fault injection and chaos engineering

Chaos experiments start with a steady-state hypothesis, defined blast radius, observation window, approved target, rollback and abort criteria. Begin with unit tests and synthetic faults, then isolated staging. Examples: delayed database responses, 429/503 bursts, packet loss, pod restarts, DNS resolution failure, Kafka consumer rebalance, storage latency and injected OOM. **Never inject faults into production without explicit authorization, risk assessment and controls.**

Use tooling such as Toxiproxy, Chaos Mesh or LitmusChaos only in approved environments with access control and audit logs. The executable lab **does not inject real faults**, even when its gate says `simulation-authorized`.

## 7. SLO/error-budget guardrails

Before experiments, check service health, baseline p95/p99, error ratio, queue saturation, backup/restore readiness, active incidents and remaining error budget. Define abort triggers: elevated errors, budget burn, data inconsistency, critical dependency impact or inability to restore. Require change ticket, owner, independent approval and clear rollback steps. The offline policy gate intentionally refuses production chaos and experiments with no approval, unhealthy baseline, no rollback, exhausted budget or blast radius over 5%.

## 8. Python implementation patterns

Use `asyncio.wait_for` or modern `asyncio.timeout` with explicit cancellation cleanup, bounded `asyncio.Semaphore` for concurrency and well-maintained retry/circuit-breaker libraries where appropriate. Validate exception classes and retry budgets. For threads, guard shared breaker state with locks; for processes, understand per-process state divergence. Instrument attempts, timeouts, rejected calls, breaker transitions and downstream latency with low-cardinality metrics.

## 9. SRE/DBRE incident scenarios

| Failure | Investigation and mitigation |
|---|---|
| PostgreSQL connection pool exhausted | Bound per-replica pools; inspect `pg_stat_activity` and queue wait |
| PostgreSQL transaction timeout | Check commit outcome before retrying a write |
| Elasticsearch 429 and search rejections | Reduce fanout/page size; apply bounded jittered backoff |
| Elasticsearch storage latency | Correlate shard search latency with disk IOPS and queue depth |
| MongoDB primary stepdown | Respect driver retry semantics and write concern |
| Kafka consumer lag/rebalance | Bound inflight work; preserve ordering and offset semantics |
| Kubernetes pod eviction/OOM | Inspect limits, retries, readiness and PDBs |
| DNS/TLS dependency failure | Classify as network/config error before retrying |
| Redis cache outage | Protect source database from cache stampede |
| Multi-region failover | Enforce fencing and split-brain prevention |

## 10. Troubleshooting and production runbooks

**Retry storm:** identify error rate, request amplification, downstream 429/503 and synchronized retry timing; cap attempts, add jitter, shed load and restore upstream capacity.

**Circuit breaker stuck open:** inspect failure-class policy, reset timer, probe behavior and underlying dependency; avoid force-closing before recovery.

**Database write uncertainty:** query transaction/idempotency outcome, preserve audit evidence, avoid duplicate execution and escalate consistency risk.

**Bulkhead saturation:** compare active/queued/rejected work by dependency; protect critical pools, shed low-priority work and adjust limits from measurements.

**Chaos experiment abort:** stop injection, restore healthy routing/pods, validate data consistency, monitor SLO recovery and document the experiment.

**Kubernetes cascade:** inspect rollout, readiness, HPA, CPU throttling, PDB and node pressure; roll back and reduce load amplification.

## 11. Hands-on lab

The [complete SRE/DBRE lab](labs/109-resilience-engineering-fault-injection-chaos-sre-dbre-lab.md) and [offline Python project](labs/109/README.md) implement retry/backoff/jitter policies, breaker state transitions, bulkhead admission, deadline calculations, SLO budgets, simulated chaos approval gates, synthetic incident response and automated tests.

**Validation boundary:** This project is an offline deterministic simulator. It makes no network calls, creates no cloud resources, injects no faults and performs no production mutations. Published tests require execution; CI, live chaos tooling and production readiness validation remain pending.

**Next proposed:** Chapter 110 — Python Production Security, Performance and Reliability Capstone.
