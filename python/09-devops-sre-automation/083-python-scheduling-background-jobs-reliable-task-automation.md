# Chapter 083 — Python Scheduling, Background Jobs and Reliable Task Automation

**Part 09 — DevOps, SRE and Automation | Chapter 083/120**

## Mission and learning outcomes
Design, implement and operate reliable recurring jobs for SRE/DBRE workflows. Compare Python \`sched\`, \`asyncio\` timers, operating-system cron, Kubernetes CronJobs and APScheduler. Implement persistent run records, idempotency, bounded retries, lease-based coordination, missed-run policy, graceful shutdown, metrics, fault injection and operational runbooks.

## Reference architecture
\`\`\`text
schedule (cron / APScheduler / external controller)
     -> durable job definition -> admission policy
     -> lease / unique run key -> worker -> bounded retry
     -> transactional result + run ledger -> metrics / alerts
     -> reconcile missed / stuck runs -> operator runbook
\`\`\`
The scheduler triggers work; the job's correctness depends on persistence, ownership, fencing, idempotency and the transaction boundary. A timer alone cannot guarantee exactly-once effects.

## 1. Python sched
\`sched.scheduler(timefunc=time.monotonic, delayfunc=time.sleep)\` runs callbacks from an in-process priority queue. \`enter(delay, priority, action)\` schedules a callback; \`cancel(event)\` cancels it before execution; \`run(blocking=False)\` processes due callbacks. It has no durable job store, automatic retries or leader election. It is appropriate for short-lived local orchestration and deterministic clock-injected tests, not durable production schedules.

## 2. asyncio scheduling
\`asyncio.sleep\`, \`loop.call_later\` and \`asyncio.create_task\` coordinate nonblocking tasks. Retain task references and await cancellation during shutdown. A semaphore limits concurrent work. Use \`time.monotonic()\` for elapsed-time deadlines and \`datetime.now(timezone.utc)\` for recorded timestamps. A process restart loses in-memory schedules; persist intended due times elsewhere. Never block the event loop with synchronous database I/O or \`time.sleep\`.

## 3. Cron and timezone correctness
A five-field cron expression represents minute, hour, day of month, month and day of week, but dialect semantics vary. Cron expressions do not imply durable replay or single execution. Configure an explicit IANA timezone; test DST spring gaps and fall repeats, leap days and month boundaries. Linux cron, Kubernetes CronJob and APScheduler may differ in day-field logic, missed execution behavior and concurrency. In Kubernetes, \`concurrencyPolicy: Forbid\` is not an exactly-once guarantee and jobs can occasionally be created more than once or missed; application idempotency remains mandatory.

## 4. APScheduler
APScheduler supplies interval, date and cron-style triggers and configurable job stores/executors. **Major-version warning:** APScheduler 3.x uses \`BackgroundScheduler\`, \`BlockingScheduler\`, \`add_job\`, \`max_instances\`, \`misfire_grace_time\` and \`coalesce\`. APScheduler 4.x has a substantially different task/schedule API. The companion lab explicitly pins the APScheduler 3.x major line. Do not copy 3.x code into a 4.x installation. A persistent job store stores scheduling metadata, not business idempotency. Multiple independent APScheduler 3.x schedulers must not share a job store without a coordination design.

## 5. Persistence and missed runs
Store stable \`job_id\`, scheduled due time, run key, status, attempts, started/completed times, last error class and output checksum. Define a missed-run policy: skip, coalesce, replay within a bounded catch-up window or escalate. Unlimited catch-up can overload PostgreSQL, Kafka, Elasticsearch or cloud APIs after an outage. Persist a watermark for reconciliation; distinguish a missed trigger from a job that started but did not commit.

## 6. Locks, leases and fencing
A lease must have a finite expiry, an owner identity and an incrementing fencing token. A crashed worker may resume after its lease expires; a fencing token only prevents stale writes when the protected resource checks it. Database row locks and advisory locks are alternatives, each with connection and transaction lifetime implications. The lab uses SQLite's transactional uniqueness and an expiry timestamp for a **single-host educational lease**. It is not a distributed exactly-once or fencing implementation. For production, consider PostgreSQL transactional job claims, conditional updates, durable queues and service-specific idempotency keys.

## 7. Retries and ambiguous completion
Retry only transient failures, with capped exponential backoff, jitter, maximum attempts and a total deadline. Never assume an exception means the external operation did not complete. Reconcile external effects by a stable operation key before replay. Poison jobs should move to a dead-letter or failed state with an escalation owner. Retrying non-idempotent backups, deletes, failovers or billing operations can cause severe harm.

## 8. SRE/DBRE applications
- PostgreSQL: backup verification, vacuum/analyze advisory checks, replication lag audits and migration preflight.
- Elasticsearch/OpenSearch: read-only shard size and index lifecycle audits; owner-approved maintenance.
- MongoDB: replication status and storage pressure checks.
- Kafka/MSK: consumer lag sampling and broker health.
- Kubernetes: CronJob observability, restart-loop audits and SLO reporting.
- Snowflake: query credit/cost summaries with bounded catch-up.
Schedule checks during safe windows and do not perform destructive maintenance automatically.

## 9. Observability and SLOs
Record \`job_scheduled_total\`, \`job_started_total\`, \`job_success_total\`, \`job_failed_total\`, \`job_retry_total\`, \`job_missed_total\`, \`job_duration_seconds\`, lease contention, backlog age and last-success timestamp. Alert on missed deadlines, stuck leases, excessive retry counts and prolonged time since success. Label metrics with low-cardinality job type rather than arbitrary run IDs. Correlate logs with run ID and trace ID; redact secrets.

## 10. Incident simulation catalogue
1. Duplicate schedule trigger; 2. Worker crash after claim; 3. Crash after side effect before ACK; 4. Lease expiry; 5. Stale worker resumes; 6. Clock skew; 7. DST skipped time; 8. DST repeated time; 9. APScheduler misfire; 10. Coalesced backlog; 11. Overlapping job executions; 12. PostgreSQL unavailable; 13. Deadlock/serialization retry; 14. Network timeout; 15. HTTP 429; 16. Persistent 503; 17. Poison job; 18. Unbounded catch-up; 19. Disk full; 20. Graceful shutdown; 21. Job store corruption; 22. Scheduler upgrade mismatch; 23. CronJob duplicate pod; 24. Missing owner/alert route.

## 11. Troubleshooting
| Signal | Root-cause candidates | Response |
|---|---|---|
| No recent success | scheduler stopped, missed trigger, worker crash | Inspect last-success watermark and due backlog |
| Duplicate effects | missing idempotency, lease expired | Reconcile by stable key; add conditional writes |
| Jobs stuck running | worker lost, lease not expired | Check heartbeat and safe lease recovery |
| Burst after outage | unbounded catch-up | Coalesce or throttle with explicit policy |
| Unexpected run time | timezone or DST | Compare UTC due time and trigger configuration |
| High DB connections | excessive workers | Cap executor and connection pools |
| Repeated failures | poison payload, permission denied | Stop retries, quarantine and escalate |

## 12. Production runbooks
**Missed schedule:** check UTC due time, scheduler health and last-success marker; replay only within approved catch-up window.

**Duplicate job:** freeze unsafe writers, identify stable run key, reconcile committed side effects, fix idempotency and concurrency.

**Lease stuck:** inspect owner heartbeat and expiry; reclaim only when safe; protect downstream effects with fencing or conditional operations.

**Retry storm:** reduce concurrency, disable unbounded retries, inspect dependency rate limits and escalate.

**Upgrade/rollback:** snapshot job definitions and state, test scheduler-version compatibility and DST behavior, roll back code without corrupting durable run history.

## 13. Lab and assessment
[Complete Chapter 083 Lab](labs/083-scheduling-background-jobs-reliable-task-automation-sre-dbre-lab.md) provides executable \`sched\`, \`asyncio\`, APScheduler 3.x, SQLite run ledger, idempotent claims, bounded retry, recovery, automated tests, incident drills, runbooks and a 100-point assessment.

**Next proposed:** Chapter 084 — Python Configuration Management, Secrets and Environment Automation.
