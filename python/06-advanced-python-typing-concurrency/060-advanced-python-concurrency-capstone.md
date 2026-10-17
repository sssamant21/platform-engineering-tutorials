# Chapter 060 — Advanced Python Concurrency Capstone

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.11+ | 8–12 hours**

## Capstone mission
Build a production-minded **offline** SRE/DBRE telemetry processor that integrates asynchronous orchestration, bounded producer–consumer queues, thread-pool I/O adapters, process-pool CPU workers, thread-safe observability, cancellation, deadlines and deterministic reporting. The lab does not contact or mutate PostgreSQL, Elasticsearch, Kafka or any other live service.

## Learning outcomes
1. Choose the correct concurrency model for I/O, CPU and orchestration.
2. Explain GIL limitations, process isolation and serialization costs.
3. Build bounded queue and worker lifecycles with correct acknowledgement.
4. Guard cross-thread counters with \`threading.Lock\`.
5. Use \`asyncio.Semaphore\`, \`TaskGroup\` and \`asyncio.timeout\` correctly.
6. Identify limits of cooperative cancellation and executor shutdown.
7. Test failure propagation, ordering, validation and resource budgets.
8. Design operational runbooks and an acceptance gate.

## 1. Architecture and ownership
\`\`\`text
strict synthetic telemetry fixtures
      |
      v
schema validation / duplicate detection / <=40 items
      |
      v
async producer -> bounded asyncio.Queue (1..16)
      |                    |
      |                    v
      |             TaskGroup consumers (1..4)
      |                    |
      |                    v
      |             asyncio.Semaphore
      |                    |
      |                    v
      |             ThreadPoolExecutor
      |             synthetic blocking I/O
      |             threading.Lock counters
      |                    |
      |                    v
      |             ProcessPoolExecutor
      |             spawn + pure CPU SHA-256
      |                    |
      |                    v
      |             deterministic results
      |                    |
      +------ queue.join / task_done / sentinels
                           |
                           v
                   sanitized JSON report
\`\`\`

## 2. Concurrency design decisions
**AsyncIO:** owns producer, queue, consumers and structured task lifetime. Asyncio tasks are cooperatively scheduled, not automatically parallel across cores.

**ThreadPoolExecutor:** isolates a synthetic blocking I/O adapter from the event loop. Worker functions may execute on different threads, so shared counters require a real \`threading.Lock\`.

**ProcessPoolExecutor:** isolates CPU-intensive deterministic hashing. Workers are top-level importable functions, and inputs/outputs are picklable dataclasses. Explicit \`spawn\` avoids inheriting multithreaded state through unsafe fork. Process startup and IPC overhead can dominate small workloads; benchmark before deploying.

**Queue:** \`asyncio.Queue(maxsize=N)\` bounds queued events. \`await queue.put\` applies backpressure. Every successful \`get\` receives exactly one \`task_done\` in \`finally\`. One private sentinel per consumer initiates normal shutdown.

**Semaphore:** caps simultaneous thread/process work. The semaphore does not limit already-created task count; input is separately capped.

## 3. Correctness and safety contracts
- Fail input validation before opening executors.
- Reject unknown engines, wrong metric units, nonfinite values and unsafe service names.
- Reject duplicate engine/service pairs and more than 40 events.
- Limit workers to 1–4 and queue size to 1–16.
- Use deterministic result sorting independent of scheduling.
- Keep worker functions pure and side-effect-free.
- Publish no partial report on TaskGroup failure.
- Report thread read/failure counts and peak queue depth.
- Never include credentials, network endpoints or worker PIDs in reports.

## 4. Deadlines, cancellation and limitations
\`asyncio.timeout\` cancels the current async scope cooperatively. It does **not** kill synchronous thread workers or process-pool workers. Executor context managers wait for running work at shutdown, potentially exceeding the apparent deadline. This capstone bounds input size and CPU iterations to limit normal work, but **does not provide a hard wall-clock execution guarantee**. Production systems requiring a hard kill need supervised subprocesses, driver-level I/O timeouts and tested termination/cleanup policies. Cancellation of \`run_in_executor\` futures does not stop already-running work.

## 5. Observability and reliability
Collect queue peak depth, accepted/processed event counts, thread I/O failures, task failures, end-to-end latency, per-stage duration, timeout rate, process worker restarts, memory RSS and CPU quota pressure. The sample reports a small safe subset; extend with Prometheus/OpenTelemetry in a real deployment. Synthetic warning/critical thresholds are for training, not production SLOs.

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

## 6. Failure modes
| Failure | Detection | Mitigation |
|---|---|---|
| Queue saturation | High depth, slow puts | Backpressure and capacity review |
| Unfinished queue work | join hangs | Ensure task_done exactly once |
| Race condition | Wrong thread counters | Lock shared invariant |
| Process startup failure | BrokenProcessPool / spawn error | Main guard, importable worker |
| Serialization failure | Pickling error | Immutable picklable DTOs |
| Worker crash | TaskGroup ExceptionGroup | Fail batch, rebuild pool |
| Deadline exceeded | TimeoutError | Bound adapters and supervise |
| Memory exhaustion | RSS/cgroup alerts | Reduce workers and task budgets |
| Partial output | Count mismatch | Reject batch, never report healthy |
| Credential exposure | Unexpected fields | Strict allowlist and redaction |

## 7. Production runbooks
**Queue overload:** pause intake, inspect producer and consumer rates, validate downstream health, reduce batch size, replay only idempotent telemetry.

**Thread race or I/O hang:** collect thread stacks, inspect lock scope and driver timeouts, restore a known-good adapter and rerun stress tests.

**Process crash or memory pressure:** inspect worker exit codes, RSS, cgroup limits and pickling errors; restart a fresh pool and lower concurrency.

**Cancellation/timeout:** inspect active tasks and executor workers, enforce external hard-stop policy where needed, and verify cleanup.

**Corrupt telemetry:** quarantine the source export, reject partial reports, validate schemas and replay offline fixtures.

**Rollback:** restore previous code and budgets, run full unit and integration tests, verify deterministic results, and resume scheduled operations only after acceptance.

## 8. Acceptance gates
See [Chapter 060 Capstone Lab](labs/060-advanced-python-concurrency-capstone-sre-dbre-lab.md) for complete executable source, tests, incident simulations and a 100-point rubric. Require at least 90/100, all safety tests passing, and independent verification of test execution before production promotion.

**Part 06 completion:** Chapter 060 completes Chapters 051–060.

**Next:** Chapter 061 — Python Testing Foundations with unittest and pytest (provisional).
