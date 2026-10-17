# Chapter 055 — Python Threading, Locks and Concurrent I/O

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.10+ | 6–8 hours**

## Objectives
Explain thread scheduling, the GIL, I/O concurrency, \`ThreadPoolExecutor\`, \`Future\`, \`threading.Lock\`, \`threading.Event\`, race conditions, bounded pools, cooperative cancellation, timeouts and safe concurrent SRE/DBRE telemetry collection.

## 1. Threading model and the GIL
A thread shares the process address space with other threads. This is useful for overlapping I/O waits, but introduces races around shared mutable state. In standard CPython builds the global interpreter lock generally prevents simultaneous execution of Python bytecode by multiple threads; it does **not** make application-level read-modify-write operations logically atomic. Threading is usually a good fit for network and file I/O, not a default way to accelerate CPU-bound Python code. Free-threaded Python builds have different guarantees; always synchronize shared state.

## 2. Creating threads
\`\`\`python
from threading import Thread
def read_status(): print("synthetic status")
worker = Thread(target=read_status, name="status-reader")
worker.start()
worker.join(timeout=1)
if worker.is_alive():
    raise TimeoutError("worker still running")
\`\`\`

\`join(timeout)\` returns even if the thread is still running. It does not terminate the worker. Avoid unmanaged daemon threads for operations requiring cleanup.

## 3. ThreadPoolExecutor
\`\`\`python
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = [pool.submit(read_status) for _ in range(3)]
    for future in as_completed(futures):
        print(future.result())
\`\`\`

The executor manages worker reuse and shutdown. \`future.result(timeout=...)\` bounds how long the caller waits for that result; it does **not** interrupt the running task. A \`with\` executor waits for running work during shutdown.

## 4. Race conditions and Lock
\`\`\`python
from threading import Lock
lock = Lock()
count = 0
def increment():
    global count
    with lock:
        count += 1
\`\`\`

The lock protects a multi-step invariant, not just one bytecode operation. Keep critical sections short; never hold a lock while making slow network calls. Use separate counters or queues when contention is high. Prefer immutable task inputs and results to shared mutable dictionaries.

## 5. Cooperative cancellation with Event
\`\`\`python
from threading import Event
stop = Event()
def work():
    if stop.is_set():
        return
    # perform a bounded read-only step
\`\`\`

A stop event is advisory: the worker must check it. It cannot kill a thread blocked indefinitely in a socket call. Real adapters require connect/read timeouts, overall deadlines and a shutdown policy.

## 6. Whole-batch deadlines
The lab computes a monotonic deadline and passes remaining time to \`Future.result\`. This is different from a per-task timeout. If a deadline is exceeded, pending futures are cancelled and the cooperative stop flag is set. The executor still waits for running tasks to finish. The lab's simulated delays are capped at 50 ms; production I/O adapters must independently enforce bounded waits.

## 7. Operational architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka targets
    -> strict metric and service validation
    -> bounded ThreadPoolExecutor (1..8 workers)
    -> read-only worker + cooperative cancellation
    -> Lock-protected started/completed/failed counters
    -> Future results collected against batch deadline
    -> deterministic, sanitized JSON summary
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag (seconds) | 30 | 120 |
| Elasticsearch | search_latency (milliseconds) | 200 | 500 |
| Kafka | consumer_lag (messages) | 1,000 | 10,000 |

All values and thresholds are synthetic.

## 8. Thread-safety and reliability design
Avoid using one SQLite connection across arbitrary worker threads. Avoid sharing cursors, mutable ORM sessions, HTTP clients without documented thread-safety or authentication refresh state. Prefer one adapter per worker or a documented thread-safe pool. Bound outstanding tasks and avoid unbounded \`executor.map\` ingestion. Record queue length, worker utilization, failure rate, deadline expirations and tail latency.

## 9. Troubleshooting
| Symptom | Likely cause | Mitigation |
|---|---|---|
| Counter mismatch | Unprotected shared mutation | Guard invariant with Lock |
| Process hangs on exit | Running worker blocked | Set I/O timeout and cooperative stop |
| Pool starvation | Too few workers / slow I/O | Profile, bound tasks, tune capacity |
| Excessive threads | Unbounded submission | Set max_workers and task cap |
| Deadline ignored | Assuming result timeout kills thread | Enforce adapter I/O timeout |
| Deadlock | Nested locks or waiting inside worker | Audit lock ordering and dependencies |
| Non-deterministic output | Completion-order aggregation | Sort results before reporting |
| Secret leakage | Logging task payloads | Use sanitized fixed labels |

## 10. Production runbooks
**Thread pool saturation:** inspect active/queued tasks and upstream latency, pause new submissions, restore bounded pool capacity and verify downstream health.

**Deadlock:** capture thread stacks, identify lock order or future-wait cycles, roll back unsafe changes and rerun deterministic concurrency tests.

**Timeout incident:** distinguish waiting deadline from I/O timeout, set cooperative stop, cancel pending futures, and verify running workers eventually exit.

**Metric corruption:** disable automated decisions, audit shared-state ownership, add lock-protected snapshots and replay synthetic fixtures.

**Rollback:** restore prior worker settings and adapter implementation, run race and timeout tests, and compare sorted reports.

## 11. Hands-on lab
[Chapter 055 — Thread-Safe Concurrent Telemetry Lab](labs/055-threading-locks-concurrent-io-sre-dbre-lab.md) provides executable code, tests, timeout simulations, production runbooks and a 100-point assessment.

**Next:** Chapter 056 — Python Multiprocessing and Process Pools (provisional).
