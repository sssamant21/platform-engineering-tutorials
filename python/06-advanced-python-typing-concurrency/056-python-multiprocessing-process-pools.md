# Chapter 056 — Python Multiprocessing and Process Pools

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.10+ | 6–8 hours**

## Learning objectives
Understand processes versus threads, CPU-bound workloads, \`multiprocessing.Process\`, \`ProcessPoolExecutor\`, pickling and serialization boundaries, worker isolation, process startup methods, task budgets, futures, timeouts, worker failure recovery and safe SRE/DBRE reporting.

## 1. Threads versus processes
Threads share process memory and often suit I/O-bound work. Separate processes have independent Python interpreters and address spaces; CPU-bound Python code can use multiple cores, subject to platform scheduling, container CPU quotas and serialization overhead. More processes are not automatically faster. Measure workload size, startup overhead, memory pressure, interprocess transfer and queueing.

## 2. multiprocessing.Process
\`\`\`python
from multiprocessing import Process
def cpu_task():
    print("synthetic CPU work")
if __name__ == "__main__":
    process = Process(target=cpu_task)
    process.start()
    process.join(timeout=5)
    if process.is_alive():
        process.terminate()
        process.join()
\`\`\`
A process is not a thread. It does not automatically share mutable Python objects. \`terminate()\` is abrupt and may leave locks, queues and external state inconsistent; it is a last-resort safety measure, not a normal shutdown mechanism.

## 3. ProcessPoolExecutor
\`\`\`python
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

def square(n: int) -> int:
    return n * n

if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=2, mp_context=get_context("spawn")) as pool:
        futures = [pool.submit(square, x) for x in (2, 3, 4)]
        print([future.result() for future in futures])
\`\`\`

Keep submitted worker functions defined at module top level so they can be imported and pickled. Protect process-pool entrypoints with \`if __name__ == "__main__":\`, especially on Windows and when using spawn. Interactive shells and notebooks may not provide an importable \`__main__\`; run the lab as normal files.

## 4. Serialization and isolation
Pool tasks cross a serialization boundary. Arguments and return values must be picklable; lambdas, nested functions, open sockets, locks and live database connections are usually unsuitable. Never unpickle untrusted input. Prefer small immutable dataclasses or primitive data-transfer objects, validated before dispatch. Avoid copying large datasets into every task.

## 5. Start methods
\`spawn\` starts a fresh interpreter and is supported on Windows and POSIX. \`forkserver\` is available on supported POSIX systems. \`fork\` can be unsafe when inheriting a multithreaded parent with locked resources; do not use it casually in SRE tools. Platform defaults vary by Python version. The lab explicitly allows spawn or forkserver when supported.

## 6. CPU-bound workloads
The lab uses repeated SHA-256 hashing to simulate CPU-heavy, deterministic telemetry fingerprinting. This is a teaching workload, **not** cryptographic signing or a benchmark proving process pools outperform threads. Workers classify synthetic PostgreSQL, Elasticsearch and Kafka metrics and return sanitized results.

## 7. Deadlines and process lifecycle
\`future.result(timeout=seconds)\` limits the caller's wait, **not** the worker's execution. \`future.cancel()\` only cancels tasks that have not started. The \`with ProcessPoolExecutor(...)\` context waits for running tasks to finish, even after a timeout is raised. The lab uses bounded task iteration counts; production systems requiring a hard execution deadline must use process termination or an external supervisor with verified cleanup semantics. Python 3.14 adds \`terminate_workers()\` and \`kill_workers()\`; availability depends on interpreter version.

## 8. SRE/DBRE architecture
\`\`\`text
synthetic telemetry job fixtures
  -> strict schema and resource-budget validation
  -> bounded ProcessPoolExecutor (1..4 workers)
  -> spawn-isolated CPU hashing + severity classification
  -> pickled immutable JobResult objects
  -> monotonic batch deadline and failure propagation
  -> sorted deterministic JSON report (no worker PIDs or secrets)
\`\`\`

| System | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

Thresholds are synthetic, not production SLO policy.

## 9. Failure modes and troubleshooting
| Symptom | Cause | Response |
|---|---|---|
| Worker cannot start | Missing main guard or non-importable module | Run from .py with main guard |
| Pickling error | Lambda or unpicklable argument | Use top-level functions and DTOs |
| BrokenProcessPool | Worker exited unexpectedly | Fail batch, inspect exit reason, restart safely |
| High RSS | Too many workers or large arguments | Reduce pool and transfer size |
| Timeout but process persists | Future timeout is not termination | Use bounded jobs or supervisor |
| Slow performance | Startup/IPC overhead dominates | Benchmark and increase task granularity |
| Non-deterministic results | Completion-order aggregation | Sort before output |
| Corrupt data | Missing validation | Validate before serialization |

## 10. Production runbooks
**Worker crash:** stop accepting new jobs, inspect exit codes and resource limits, restart a fresh pool, and replay only safe idempotent work.

**CPU saturation:** inspect per-core utilization, cgroup quotas, process count and run queue; reduce workers or workload size.

**Memory pressure:** examine process RSS and input copying, reduce parallelism, and avoid shipping huge objects between workers.

**Timeout:** identify whether tasks are running or queued, cancel pending work, and use a supervisor if hard termination is required.

**Serialization failure:** inspect DTO schemas and importability; do not use pickle for untrusted input.

**Rollback:** restore previous worker budget and start method, rerun the offline suite and compare checksums.

## 11. Lab
[Chapter 056 — Process Pool SRE/DBRE Lab](labs/056-multiprocessing-process-pools-sre-dbre-lab.md) provides executable source, tests, failure simulations, runbooks and a 100-point assessment.

**Next:** Chapter 057 — Python AsyncIO and Asynchronous I/O (provisional).
