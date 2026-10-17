# Chapter 057 — Python AsyncIO and Asynchronous I/O

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.11+ | 6–8 hours**

## Objectives
Explain the event loop, coroutines, \`async\`/\`await\`, task scheduling, \`asyncio.gather\`, structured concurrency with \`TaskGroup\`, deadlines, cancellation, \`asyncio.Semaphore\`, asynchronous context managers and safe operational resource cleanup. Implement an executable offline SRE/DBRE telemetry collector.

## 1. The event loop and cooperative scheduling
\`asyncio\` runs many waiting operations in a single event-loop thread by allowing coroutines to suspend at \`await\` points. Unlike threads, coroutine switches are normally cooperative. This is useful for high-concurrency I/O-bound tasks, but a blocking \`time.sleep()\`, synchronous database query or CPU-heavy loop inside a coroutine stalls the event loop.

\`\`\`python
import asyncio

async def check_status() -> str:
    await asyncio.sleep(0.01)
    return "synthetic-ok"

if __name__ == "__main__":
    print(asyncio.run(check_status()))
\`\`\`

\`asyncio.run\` creates and closes the event loop. Do not call it inside an already running loop; in notebooks, \`await\` the coroutine instead.

## 2. Coroutines, tasks and gather
Calling an \`async def\` function produces a coroutine object; it does not run until awaited or scheduled. \`asyncio.create_task\` schedules a coroutine. \`asyncio.gather\` waits for multiple awaitables and returns results in input order, even if completion order differs. By default, when one awaitable fails, \`gather\` propagates that failure but does not necessarily cancel all sibling tasks. This makes explicit lifecycle management important.

## 3. TaskGroup and structured concurrency
Python 3.11 introduced \`asyncio.TaskGroup\`. It scopes child tasks so the parent does not exit the group until they finish or are cancelled and cleaned up. On a non-cancellation failure, remaining siblings are cancelled and exceptions are grouped in an \`ExceptionGroup\`.

\`\`\`python
async with asyncio.TaskGroup() as group:
    first = group.create_task(check_status())
    second = group.create_task(check_status())
print(first.result(), second.result())
\`\`\`

Do not swallow \`asyncio.CancelledError\` without correctly restoring cancellation semantics; cleanup should generally run in \`finally\` or \`__aexit__\`.

## 4. Timeouts and cancellation
\`asyncio.timeout(seconds)\` defines a scope-level deadline. When reached, it cancels the current task and raises \`TimeoutError\` outside the timeout context. This is cooperative cancellation: a coroutine that blocks the event loop or suppresses cancellation can defeat expected deadlines. Use driver-level connect/read timeouts in addition to an overall operation deadline.

## 5. Semaphore-based concurrency limits
\`asyncio.Semaphore(N)\` bounds the number of tasks simultaneously inside a critical I/O section. It does **not** bound the number of task objects created. The lab also caps submitted targets at 100. For unbounded streams, use a bounded queue and a fixed worker pool rather than creating one task per item.

## 6. Async resource lifecycle
\`async with\` invokes \`__aenter__\` and \`__aexit__\`. Async context managers can release connections, semaphores and sessions even when a task is cancelled. Cleanup that itself awaits can be cancelled again; production designs should establish explicit shutdown deadlines and test cleanup under cancellation.

\`\`\`python
class Session:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        return False
\`\`\`

## 7. Async generators and streaming
\`async for\` consumes an asynchronous iterator, and \`async def\` with \`yield\` defines an async generator. Use \`contextlib.aclosing\` to ensure cleanup when breaking early from a generator. For pipelines, bounded queues provide backpressure between producers and consumers.

## 8. SRE/DBRE architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka targets
  -> strict input validation and task cap
  -> asyncio event loop
  -> TaskGroup (structured lifetime)
  -> Semaphore (bounded active polling)
  -> AsyncResource (async with cleanup)
  -> timeout scope + cooperative cancellation
  -> sorted sanitized JSON report
\`\`\`

| System | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

All fixtures and thresholds are synthetic; the lab performs no external network or database operations.

## 9. Troubleshooting
| Symptom | Cause | Response |
|---|---|---|
| Event loop stalls | Blocking call in coroutine | Use native async I/O or bounded \`to_thread\` |
| Unawaited coroutine warning | Coroutine created but not scheduled | Await or schedule |
| Orphan tasks | Tasks created without ownership | Use TaskGroup |
| Timeout not respected | Blocking I/O or cancellation suppressed | Driver timeouts and cooperative cleanup |
| Memory spike | Unbounded task creation | Queue and task cap |
| Connection leak | Missing async context manager | Use \`async with\` and test cancellation |
| Unexpected ExceptionGroup | TaskGroup sibling failure | Inspect grouped exceptions and fix source |
| Non-deterministic report | Completion-order output | Sort results |

## 10. Production runbooks
**Event-loop stall:** inspect task stacks, blocking calls and event-loop lag; move synchronous I/O to dedicated threads or use async drivers.

**Task storm:** pause ingestion, reduce concurrency, enforce bounded queue and task budgets, monitor active tasks and memory.

**Timeout incident:** distinguish connection/read timeout from operation deadline, ensure cancellation propagates and validate resource cleanup.

**Partial failure:** fail closed on TaskGroup errors, quarantine invalid telemetry, avoid publishing partial healthy reports.

**Rollback:** restore last known-good concurrency limits and async adapter, run cancellation tests and replay synthetic fixtures.

## 11. Hands-on lab
[Chapter 057 — AsyncIO SRE/DBRE Lab](labs/057-asyncio-asynchronous-io-sre-dbre-lab.md) includes executable code, automated tests, cancellation/timeout simulations, production runbooks and a 100-point assessment.

**Next:** Chapter 058 — Python AsyncIO Queues, Backpressure and Streaming Pipelines (provisional).
