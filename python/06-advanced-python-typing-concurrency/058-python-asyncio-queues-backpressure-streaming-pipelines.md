# Chapter 058 — Python AsyncIO Queues, Backpressure and Streaming Pipelines

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.11+ | 6–8 hours**

## Learning outcomes
Design producer–consumer systems with \`asyncio.Queue\`, bounded memory, cooperative backpressure, correct \`task_done()\` / \`join()\` accounting, task cancellation, structured concurrency and graceful shutdown. Build an offline SRE/DBRE telemetry pipeline with deterministic reports and explicit failure policies.

## 1. Why queues matter for operations
An SRE poller may collect telemetry faster than a downstream analyzer or exporter can consume it. Without backpressure, the number of pending objects grows until the process exhausts memory. A bounded queue converts overload into producer waiting and makes capacity observable. Queue size is not a rate limit: set both concurrency and arrival-rate policies in production.

## 2. Queue API and invariants
\`\`\`python
import asyncio
q = asyncio.Queue(maxsize=2)
await q.put("item")       # blocks when full
item = await q.get()      # blocks when empty
try:
    process(item)
finally:
    q.task_done()         # exactly once for every successful get()
await q.join()            # waits for unfinished task count to reach zero
\`\`\`
Calling \`task_done()\` too many times raises \`ValueError\`; calling it too few times makes \`join()\` hang. \`join()\` confirms acknowledgement, **not** successful processing: if a worker acknowledges failed work, your application must separately record that failure and avoid publishing a misleading success report.

## 3. Producer and consumer
A producer validates and enqueues immutable events. A consumer obtains events, processes them, records results and acknowledges every acquired item in a \`finally\` block. Keep the queue bounded and limit the number of consumer tasks. \`asyncio.Queue\` is designed for async tasks in one event loop; it is **not thread-safe** and must not be shared directly with OS threads.

## 4. Backpressure and fairness
\`await queue.put(item)\` suspends the producer when the queue reaches \`maxsize\`. This bounds queued items, but not items currently being processed, input already loaded into memory or downstream buffers. The lab uses an in-memory list capped at 100 items; a true large-scale streaming adapter should ingest incrementally with bounded parsing, byte limits and a fixed worker pool.

## 5. Structured concurrency with TaskGroup
Python 3.11 \`asyncio.TaskGroup\` scopes worker tasks and cancels siblings when a worker fails. The lab places producer activity inside the same TaskGroup scope; producer validation failures cause the group to cancel consumers and wait for cleanup. TaskGroup reports worker failures through \`ExceptionGroup\`. The lab does not emit a partial report when a failure occurs.

## 6. Graceful shutdown
After producing all data, enqueue **one unique shutdown token per consumer**, await \`queue.join()\`, and let the TaskGroup wait for workers to exit. The lab uses a private singleton sentinel, compared with \`is\`. Every sentinel acquired by a worker is acknowledged. Do not enqueue shutdown tokens before producers finish. On error, rely on TaskGroup cancellation rather than attempting a normal sentinel drain of an incomplete pipeline.

## 7. Cancellation and timeouts
\`asyncio.timeout\` provides an overall operation deadline. On expiry, tasks are cancelled cooperatively and the outer scope raises \`TimeoutError\`. Avoid swallowing \`CancelledError\`. An async worker performing blocking synchronous I/O can still stall the loop. Use async drivers, per-request network timeouts and controlled shutdown budgets.

## 8. Async queue lifecycle and Python versions
Python 3.13 introduced \`Queue.shutdown()\`, including immediate shutdown semantics; these APIs are not available in Python 3.11. This lab deliberately uses portable sentinels for Python 3.11+. For \`shutdown(immediate=True)\`, understand that it can release \`join()\` even if work was not completed, so it must not be treated as proof of successful processing.

## 9. SRE/DBRE architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka readings
   -> strict schema validation
   -> producer (await queue.put)
   -> bounded asyncio.Queue (maxsize 1..32)
   -> 1..8 async consumers
   -> acknowledgement via task_done
   -> queue.join + sentinel shutdown
   -> TaskGroup + overall timeout
   -> deterministic sanitized JSON summary
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

All readings and thresholds are synthetic. The lab has no live infrastructure connections or writes.

## 10. Production capacity planning
Monitor queue depth, enqueue wait duration, oldest-item age, consumer utilization, processing rate, dropped/failed count and end-to-end latency. Use Little's Law as a sanity check for stable systems: average in-flight work ≈ arrival rate × average time in system. For example, 20 events/s with 0.25 s end-to-end latency implies roughly five events in the system on average. This does not determine safe burst capacity by itself.

## 11. Troubleshooting
| Symptom | Likely cause | Recovery |
|---|---|---|
| Producer stalled | Queue full, consumers too slow | Check depth and downstream latency |
| \`queue.join()\` hangs | Missing \`task_done()\` | Audit every successful \`get()\` |
| \`task_done()\` raises | Duplicate acknowledgement | Ensure exactly one call |
| Silent data loss | Acknowledging failed processing | Fail closed and record failure |
| Task leak | Workers not awaited | Use TaskGroup |
| Memory spike | Unbounded input or task creation | Bound input, queue and workers |
| Deadline exceeded | Slow consumer or blocking I/O | Inspect lag and enforce timeouts |
| Incomplete shutdown | Missing sentinel | Send one token per consumer |

## 12. Production runbooks
**Queue saturation:** identify the slow stage, reduce intake, validate consumer health, adjust bounded concurrency and replay only safe idempotent events.

**Stuck join:** inspect unfinished-task accounting and blocked consumers, stop new production, recover missing acknowledgements in a controlled test, and restart a known-good version.

**Cancellation storm:** inspect upstream deadlines, avoid suppressing cancellation, ensure async cleanup and reduce overloaded fan-out.

**Telemetry schema failure:** quarantine invalid input, fail the batch, fix exporter contract and replay synthetic fixtures before production rollout.

**Rollback:** restore previous queue capacity, consumer count and code; rerun backpressure, cancellation and shutdown tests.

## 13. Hands-on lab
[Chapter 058 — Async Queue and Backpressure SRE/DBRE Lab](labs/058-asyncio-queues-backpressure-streaming-sre-dbre-lab.md) includes complete executable source, tests, failure injection, runbooks and a 100-point assessment.

**Next:** Chapter 059 — Advanced AsyncIO Synchronization and Resilient Concurrency (provisional).
