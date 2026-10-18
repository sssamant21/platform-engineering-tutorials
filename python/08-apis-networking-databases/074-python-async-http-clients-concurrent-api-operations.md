# Chapter 074 — Python Async HTTP Clients and Concurrent API Operations

**Part 08 — APIs, Networking and Databases | Python 3.11+ | 10–14 hours**

## Outcomes
Build production-aware asynchronous SRE/DBRE HTTP collectors with \`asyncio\`, \`httpx.AsyncClient\`, bounded concurrency, connection pools, explicit timeouts, safe retries, cancellation, rate limiting and backpressure. Validate behavior using a disposable loopback HTTP service and deterministic automated tests.

## Architecture
\`\`\`text
SRE scheduler -> bounded work queue -> N asyncio workers
    -> Semaphore (max in-flight requests)
    -> httpx.AsyncClient (pooled connections)
    -> timeout/retry/budget policy
    -> loopback synthetic PostgreSQL/Elasticsearch/Kafka HTTP API
    -> validated JSON -> structured results and counters
    -> cancellation/shutdown/drain
\`\`\`

## 1. asyncio fundamentals
\`async def\` creates a coroutine. \`await\` suspends it so the event loop can run other work. Use \`asyncio.create_task\`, \`TaskGroup\`, \`gather\`, \`Semaphore\`, \`Queue\` and \`asyncio.timeout\` deliberately. Concurrency is not parallel CPU execution: blocking synchronous calls in the event loop stall all tasks. Offload blocking code with \`asyncio.to_thread\` when appropriate and use separate workers/processes for CPU-bound workloads.

## 2. httpx and aiohttp
\`httpx.AsyncClient\` offers async requests, pooling, explicit timeout/connection limits, HTTP/2 where supported, and transport injection for tests. \`aiohttp.ClientSession\` is an alternative with a different API and connector configuration. Reuse clients for related calls; do not create a new client per request. Close clients via \`async with\`. Do not share mutable auth state indiscriminately.

## 3. Pooling and backpressure
Configure \`httpx.Limits(max_connections=N, max_keepalive_connections=M)\`. A semaphore limits in-flight application requests; pool limits cap connections. These protect different boundaries. A bounded \`asyncio.Queue(maxsize=...)\` prevents unbounded work accumulation. A queue may block producers; design shedding, expiry or admission control for overload. Expose queue depth, wait duration, active requests, error classes and drops with bounded-cardinality labels.

## 4. Timeouts, retries and deadlines
Configure connect, read, write and pool timeouts. Apply a total deadline using \`asyncio.timeout\` around the whole operation or batch. Retry only safe/idempotent requests and only documented transient statuses such as 429, 502, 503 and 504. Bound attempts, exponential backoff and jitter; respect bounded Retry-After when supported. Avoid retries from both transport and application layers. Cancellation should propagate; never swallow \`asyncio.CancelledError\` accidentally.

## 5. Cancellation and shutdown
Use \`TaskGroup\` for structured concurrency; when one task fails, sibling tasks are cancelled and an exception group is raised. \`asyncio.gather\` has different failure/cancellation behavior; choose intentionally. During shutdown, stop producers, drain or discard queue according to SLO, cancel workers, close sessions and report incomplete items. Protect critical cleanup with \`try/finally\` but do not suppress cancellation.

## 6. Rate limiting and fairness
Use semaphores for concurrency, token buckets for rate, and bounded queues for pending work. A semaphore alone is **not** a requests-per-second limiter. A per-client rate budget may be insufficient when multiple pods share one upstream quota. For multi-pod workloads, coordinate distributed quotas or conservative per-replica limits.

## 7. Security
For remote endpoints require HTTPS with certificate and hostname verification, trusted host/path allowlists, strict redirect handling and scoped credentials. Never log tokens, query secrets or raw response bodies. The lab intentionally permits only \`http://127.0.0.1\` and uses synthetic data; do not copy that exception into production.

## 8. Production incident simulations
1. PostgreSQL lag endpoint slows down; async read timeout prevents hangs.
2. Elasticsearch telemetry returns 503 then recovers with bounded retry.
3. Kafka lag API responds 429; throttle and avoid retry storms.
4. Pool exhaustion causes PoolTimeout; inspect connection limits.
5. Producer floods work queue; backpressure prevents memory blowup.
6. A worker is cancelled during sleep; cancellation propagates and resources close.
7. One TaskGroup task fails; siblings are cancelled predictably.
8. API responds with malformed JSON or wrong units; fail contract.
9. Event loop is blocked by \`time.sleep\`; replace with \`asyncio.sleep\`.
10. Request limit is exceeded; semaphore prevents concurrency spikes.
11. Global deadline expires; outstanding tasks are cancelled.
12. TLS certificate fails; repair trust, never disable verification.
13. Multiple pods exceed shared rate limit; coordinate quotas.
14. Unbounded retry loop amplifies outage; enforce attempt and time budgets.

## 9. Troubleshooting
| Symptom | Cause | Safe response |
|---|---|---|
| Event-loop lag | Blocking sync I/O or CPU work | Use async I/O, offload blocking calls |
| PoolTimeout | Pool saturation | Bound concurrency, inspect connection reuse |
| ReadTimeout | Slow upstream | Tune budgets based on SLO, reduce payload |
| 429 | Shared quota exceeded | Rate limiter, bounded backoff |
| Queue growth | Arrival rate > service rate | Bounded queue and load shedding |
| Cancelled tasks leak resources | Missing cleanup | Use \`async with\` and \`finally\` |
| Partial results | TaskGroup cancellation | Track completed/failed work and retry safely |
| TLS failure | Certificate or hostname | Repair trust, never bypass |
| High memory | Unbounded tasks/results | Batch, stream and cap work |

## 10. Production runbooks
**429/503 surge:** cap concurrent requests, reduce poll frequency, inspect upstream saturation, enforce retry budgets and restore known-good client settings.

**Queue overload:** inspect queue depth and service rate, pause producers or shed noncritical work, increase capacity only after identifying bottleneck.

**Cancellation incident:** inspect shutdown deadlines and task lifecycle, verify cleanup and ensure partial work is auditable.

**Pool exhaustion:** compare worker concurrency to connection limits, inspect keepalive reuse and identify slow consumers.

**Rollback:** restore approved client/concurrency settings, rerun synthetic integration tests, validate production SLO and document approval.

## 11. Lab
[Chapter 074 — Async HTTP and Concurrency SRE/DBRE Lab](labs/074-async-http-concurrency-sre-dbre-lab.md) contains complete \`httpx\` client and disposable loopback server, unit/integration tests, concurrency-limit assertions, retry and cancellation drills, CI template, runbooks and a 100-point acceptance rubric.

**Next proposed:** Chapter 075 — Python Socket Programming, DNS and Network Troubleshooting.
