# Chapter 112 — Enterprise Python API Services, Contracts and Data Access Integration

**Part 12 — Enterprise Capstone Projects | Chapter 112/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/112-enterprise-python-api-contracts-data-access-sre-dbre-lab.md) · [Offline executable project](labs/112/README.md)

## Learning objectives

Design reliable Python REST APIs with explicit request/response contracts, validation, authentication/authorization, idempotency, transactions, connection pooling, timeout budgets, caching, search projections and observability. Compare PostgreSQL, Elasticsearch/OpenSearch, MongoDB and Redis adapters and failure semantics. Implement and test a standard-library **offline API simulator** while designing separately approved live integration paths.

## Architecture

```text
Clients -> Ingress/WAF/TLS -> Python API replicas
                   |       AuthN / AuthZ / rate limit / request IDs
                   |       schema validation / versioned REST contract
                   v
             domain service + deadline + idempotency
                |          |           |         |
        PostgreSQL     Search       MongoDB     Redis
        authoritative  projection   documents   TTL cache
                |
       transactional outbox / CDC -> index projection and cache invalidation
                |
     OTel spans + JSON logs + Prometheus RED/USE -> SLO alerting
```

**Ownership:** A transactional write to PostgreSQL is not automatically atomic with Elasticsearch indexing or Redis cache updates. Production integrations should use an outbox, CDC, replay/reconciliation and idempotent consumers where required. The offline simulator performs an in-memory sequential projection to illustrate behavior, **not distributed transaction guarantees**.

## 1. REST contracts and API versioning

Define resource-oriented routes such as `POST /v1/records`, `GET /v1/records/{id}` and `GET /v1/search?q=...`. Use consistent JSON schema, status codes, error envelopes, pagination, ETags or revision preconditions, deprecation policy and backward-compatible changes. OpenAPI 3.1 with reviewed request/response schemas and generated contract tests is recommended for production; the lab validates a limited handcrafted schema.

| Case | Typical status | Client behavior |
|---|---:|---|
| Create | 201 | Record canonical response |
| Successful read | 200 | Honor cache policy |
| Invalid request | 422 | Correct request, do not retry blindly |
| Unauthorized/forbidden | 401/403 | Reauthenticate/request access |
| Missing resource | 404 | Resolve ID or lifecycle |
| Revision/idempotency conflict | 409 | Reconcile current state |
| Dependency unavailable/pool exhausted | 503 | Bounded retry if safe |
| Rate limited | 429 | Honor `Retry-After` and backoff |

## 2. Validation and error handling

Validate path IDs, field types, length limits, numeric bounds, Unicode/control characters, query parameters and body size **before** calling adapters. Treat `bool` separately from `int` in Python. Never concatenate untrusted SQL; use parameterized queries. Limit search query complexity, pagination depth and output size. Return stable machine-readable errors without leaking credentials, SQL statements or stack traces.

## 3. Authentication, authorization and tenancy

At the edge, validate issuer, audience, signature, expiration, scopes and tenant context using reviewed OIDC/OAuth2 libraries and trusted JWKS; rotate signing keys. Apply authorization at the service/domain boundary, not only in a gateway. Enforce row-level or tenant filters consistently across PostgreSQL, Elasticsearch, MongoDB and Redis. Audit privileged writes with trace/request IDs and privacy-safe fields.

**Lab limitation:** `role="reader"/"writer"` is a teaching-only authorization switch; it is not authentication, token verification, tenancy isolation or a secure identity implementation.

## 4. PostgreSQL adapter and transactions

Use a reviewed driver (`psycopg` or `asyncpg` as appropriate), prepared/parameterized statements, schema migrations, transactions, isolation levels, optimistic concurrency and a connection pool. Budget total connections as `replicas × max_pool_size + workers + admin reserve`; configure pool acquisition, statement and transaction timeouts. Avoid holding transactions open across remote calls. Use a transactional outbox for durable cross-system event propagation.

The offline `MemoryPostgres` adapter models a bounded pool and revision-based optimistic updates; it does not provide ACID guarantees, SQL execution, crash recovery or concurrency safety.

## 5. Elasticsearch/OpenSearch adapter

Index denormalized search projections with versioned mappings and aliases. Query with explicit filters, bounded `size`, source filtering, request timeout and `search_after` for deep pagination. Handle partial results and retryable rejections with capped backoff/jitter; monitor shard fanout, query/fetch latency, disk IOPS and threadpool rejections. Do not use search results as proof of transactional consistency. The offline `MemorySearch` adapter supports bounded substring search only.

## 6. MongoDB adapter

Define collection schemas, indexes, tenant boundaries, retryable write semantics, read/write concerns, pool limits and driver timeouts. Understand replica elections, oplog and consistency. Use document validation and reject unexpected fields. The offline `MemoryMongo` adapter stores bounded JSON-like documents only; it does not simulate real MongoDB query semantics, transactions or replication.

## 7. Redis adapter

Use cache-aside with bounded TTL, namespaced keys, invalidation on updates, stampede prevention and clear failure policies. Monitor cache hit ratio, memory/evictions, hot keys and origin database pressure. Never assume cache persistence or atomicity matches PostgreSQL. The offline `MemoryRedis` adapter implements deterministic TTL and defensive copies but no real Redis server.

## 8. Timeouts, retries and idempotency

Use an end-to-end deadline encompassing pool acquisition, connect, query, serialization and any retries. Propagate cancellation and cap retry amplification. Retry only operations known to be safe or protected by server-side idempotency keys and durable deduplication. For uncertain writes, verify the commit outcome; do not blindly replay. The offline API requires an idempotency key on POST and prevents reuse with a different request fingerprint. Production deduplication must be durable and atomic across replicas.

## 9. Observability and reliability

Instrument HTTP request count, error rate, duration histograms, inflight requests, pool wait, backend timeout/error classification, cache hit ratio, search rejections and transaction conflicts. Use OTel spans across API/adapters, W3C context propagation and redacted structured logs. Apply RED for requests and USE for resources; define SLO eligible events and burn-rate alerts. Avoid per-user or per-request Prometheus labels. The offline `Telemetry` class counts requests and 5xx and reports a simple sample percentile; it does not export Prometheus/OTLP.

## 10. Production incident troubleshooting

**PostgreSQL pool exhaustion:** inspect pool wait, active sessions, locks, slow SQL and aggregate replica pools; shed load before scaling replicas.

**Elasticsearch 429/search slowness:** inspect threadpool rejections, shard fanout, page size, disk latency and fetch phase; narrow queries and apply bounded backoff.

**MongoDB primary election:** inspect driver retry semantics, write concern and uncertain commits; reconcile before replay.

**Redis stampede:** cap cache-miss concurrency, use TTL jitter/singleflight and protect PostgreSQL.

**API p99 regression:** correlate traces, pool wait, event-loop blocking, CPU throttling, search fetch latency and deployments.

**401/403 spike:** inspect token issuer/audience/key rotation, policy and tenant context without logging tokens.

**Inconsistent search projection:** replay outbox/CDC, compare source revision and repair index alias safely.

## 11. Lab and validation

The [full lab](labs/112-enterprise-python-api-contracts-data-access-sre-dbre-lab.md) and [offline project](labs/112/README.md) provide typed request validation, stable error envelopes, role gates, optimistic revisions, idempotency, bounded pools, search, MongoDB documents, Redis TTL, timeouts, request telemetry, automated tests and guided incidents.

**Security/validation boundary:** No HTTP server, real credentials, JWT verification, actual DB drivers, TLS, production network, durable transaction, real exporter or live writes are included. Exact committed test execution, CI, security review and staging integrations remain pending.

**Next:** Chapter 113 — Enterprise Python Event-Driven Workers, Kafka Integration and Reliable Data Pipelines.
