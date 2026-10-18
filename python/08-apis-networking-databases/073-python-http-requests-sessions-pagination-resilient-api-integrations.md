# Chapter 073 — Python HTTP Requests, Sessions, Pagination and Resilient API Integrations

**Part 08 — APIs, Networking and Databases | Python 3.11+ | 10–14 hours**

## Outcomes
Build reliable SRE/DBRE HTTP integrations using \`requests.Session\`, connection pooling, cursor pagination, explicit timeouts, bounded retries with backoff, rate-limit handling, and a circuit breaker. Test each failure mode against a real disposable loopback HTTP service without cloud credentials.

## Architecture
\`\`\`text
synthetic DBRE collector
  -> trusted endpoint + scoped credential provider
  -> requests.Session + HTTPAdapter(pool_connections, pool_maxsize, pool_block)
  -> GET /v1/telemetry?cursor=...&limit=...
  -> bounded retries: 429/502/503/504 + Retry-After
  -> cursor validation + duplicate detection + page and item limits
  -> schema validation + sanitized metrics
  -> circuit breaker: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
\`\`\`

## 1. requests and sessions
\`requests.get\` is convenient for isolated calls. \`requests.Session\` reuses connection pools, cookies and default headers, reducing repeated TCP/TLS handshakes. Configure \`HTTPAdapter(pool_connections=..., pool_maxsize=..., pool_block=True)\` to bound connections under concurrency. Close sessions with a context manager. A \`Session\` is not a guarantee of thread safety; prefer one session per worker or externally synchronize shared mutable state. Keep sensitive headers scoped to trusted origins.

## 2. Timeouts and deadlines
\`requests\` accepts a timeout tuple \`(connect_seconds, read_seconds)\`. These are socket phase/inactivity timeouts, **not** a strict end-to-end deadline. Implement an application-level budget and consider streaming response limits for large bodies. Never omit timeouts in production. Distinguish \`ConnectTimeout\`, \`ReadTimeout\`, \`ConnectionError\`, \`HTTPError\` and invalid JSON.

## 3. Retries, backoff and idempotency
Only retry safe/idempotent operations under an explicit policy. A \`GET\` may be retried for transient 429/502/503/504 and connection errors; a POST requires documented idempotency semantics or a server-supported idempotency key. Use exponential backoff, bounded delay, jitter and an overall attempt cap. \`Retry-After\` can be seconds or an HTTP date; cap it to a safe operational budget. Avoid nested automatic retries in adapters and application code; choose one owner of retry policy. The lab disables adapter-level retries and implements observable application-level retries.

## 4. Cursor pagination
A cursor is opaque and must not be interpreted as an offset unless documented. Validate its type and length, detect repeated cursors, cap pages and total items, and deduplicate stable resource identifiers if required. Use a snapshot/version contract where supported to avoid missing/duplicated items during concurrent changes. Treat cursor strings as potentially sensitive and avoid logging them. Do not concatenate raw user-supplied URLs.

## 5. Circuit breakers
A circuit breaker protects an unhealthy upstream: CLOSED permits calls, OPEN rejects quickly, HALF_OPEN allows a limited probe after cooldown. Count defined transient failures, not every 4xx. Successful probes reset failure counts; failed probes reopen. A breaker is not a substitute for timeouts, rate limiting or retry budgets. Use a monotonic clock; in distributed systems, local breakers may not coordinate globally.

## 6. Rate limiting
A \`429\` response signals the caller should slow down. Parse \`Retry-After\` conservatively, cap wait, use jitter, limit concurrent requests and respect provider quotas. Track \`429\` frequency and retry amplification. Use a token bucket or shared distributed limiter if many workers target one quota.

## 7. Security and observability
Always use HTTPS and verify certificates for remote services. Allowlist scheme, host and path; disable redirects unless targets are reviewed; avoid SSRF and credentials in query strings. Redact authorization headers, cookies, cursors and raw response bodies. Emit only safe route templates, status classes, attempt counts and elapsed time. The lab allows HTTP **only on 127.0.0.1** for its disposable server.

## 8. Production SRE/DBRE scenarios
1. PostgreSQL replication telemetry API returns \`503\` twice, then recovers.
2. Elasticsearch shard-health endpoint returns \`429\` under heavy polling.
3. Kafka consumer lag endpoint paginates through multiple cursors.
4. A pagination bug repeats the same cursor indefinitely.
5. Upstream fails repeatedly, opening a circuit breaker.
6. Cooldown elapses and a successful half-open probe restores traffic.
7. \`401\` or \`403\` indicates auth/scope failure; no blind retry.
8. A response body is too large; reject before JSON parsing.
9. Invalid metric value NaN/negative or malformed identifier; reject contract.
10. TLS certificate expires; fix trust rather than disable verification.
11. Shared session saturates connection pool; bound concurrency and inspect wait time.
12. Concurrent updates change page membership; use snapshot/cursor contract.
13. Retry-After is huge or invalid; cap or reject conservatively.
14. Gateway redirects to another host; prevent token leakage.

## 9. Troubleshooting
| Symptom | Likely cause | Safe action |
|---|---|---|
| Pool exhaustion | More workers than pool slots | Bound concurrency, size pools |
| Repeated 429 | Quota exceeded | Reduce polling, bounded Retry-After |
| Retry storm | Layered retries and no jitter | One retry owner, cap attempts |
| Cursor loop | Repeated continuation token | Detect and abort |
| Inconsistent pages | Mutable dataset | Snapshot/version contract |
| OPEN breaker | Sustained upstream failures | Inspect error budget, probe after cooldown |
| 401/403 | Credential or RBAC drift | Rotate/repair scope; no blind retry |
| Read timeout | Slow upstream or payload | Measure latency and cap response |
| SSL error | CA/hostname/cert issue | Repair trust chain, never bypass |

## 10. Production runbooks
**Retry storm:** reduce client concurrency, disable duplicate retry layers, set budgets and monitor 429/5xx and upstream saturation.

**Circuit OPEN:** confirm transient failures, check health/SLO, let cooldown pass, permit one controlled probe and escalate if repeated.

**Pagination corruption:** halt ingestion, preserve sanitized cursor sequence, verify stable ordering and snapshot semantics, reconcile duplicates before resuming.

**Pool pressure:** inspect active workers, blocked pool acquisitions and socket states; right-size per-worker pools and rate limits.

**Credential/TLS incident:** revoke or rotate compromised credentials, restore trust and verify approved host policies.

**Rollback:** restore approved client/retry policy, rerun loopback tests and production canaries, verify SLO and record change approval.

## 11. Lab
[Chapter 073 — Resilient HTTP Sessions and Pagination SRE/DBRE Lab](labs/073-resilient-http-sessions-pagination-sre-dbre-lab.md) includes complete client/server Python code, automated tests, deterministic fault injection, incident drills, a CI template and a 100-point acceptance rubric.

**Next proposed:** Chapter 074 — Python Async HTTP Clients and Concurrent API Operations.
