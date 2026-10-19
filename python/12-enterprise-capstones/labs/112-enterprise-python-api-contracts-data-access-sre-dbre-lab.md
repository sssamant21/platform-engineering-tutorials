# Chapter 112 — Enterprise API Contracts and Data Access SRE/DBRE Lab

[Offline API](112/api_lab.py) · [Unit tests](112/test_api_lab.py) · [Project guide](112/README.md)

## Scenario

A Python Kubernetes API integrates PostgreSQL authoritative records, Elasticsearch search projections, MongoDB documents and Redis cache. A deployment introduces pool exhaustion, stale cache and inconsistent search results. Diagnose safely in an offline simulation; design real production controls separately.

## Lab 1 — Run

```bash
cd python/12-enterprise-capstones/labs/112
python -m compileall -q api_lab.py test_api_lab.py
python -m unittest -v test_api_lab.py
python api_lab.py --dry-run
```

## Lab 2 — API and identity

Exercise POST/GET/search, exact-field validation, role denial, revision conflicts, stable HTTP error codes and idempotency-key replay. Specify OpenAPI 3.1 contracts and a production OIDC/JWT verification design with issuer/audience and tenant isolation. The lab role flag is not real authentication.

## Lab 3 — Data adapters

Test PostgreSQL-style bounded pool and optimistic revision updates; search query bounds and projection; MongoDB-style document validation; Redis TTL and defensive copying. Design a transactional outbox and replay/reconciliation workflow: the lab's inline projections are not atomic across real stores.

## Lab 4 — Timeout and observability

Check end-to-end timeout budgets, error counts and p99; design OTel spans, RED/USE Prometheus metrics, structured log redaction and SLO burn-rate alerts. Analyze HPA replica scaling against aggregate DB connection limits.

## Production incident simulations

| # | Scenario | Operational response |
|---|---|---|
| 1 | Invalid API payload | Check contract/version rollout |
| 2 | Injection-like path | Reject and verify parameterized SQL |
| 3 | Authentication failure | Validate token trust and policy |
| 4 | Tenant isolation failure | Contain and audit |
| 5 | PostgreSQL pool exhaustion | Bound replicas and pool size |
| 6 | PostgreSQL lock wait | Inspect blocked sessions |
| 7 | PostgreSQL serialization failure | Retry only safe transactions |
| 8 | Uncertain DB commit | Verify result before replay |
| 9 | Elasticsearch 429 | Reduce fanout and backoff |
| 10 | Elasticsearch disk bottleneck | Inspect IOPS and shard size |
| 11 | Search projection drift | Replay outbox and reconcile |
| 12 | Search alias regression | Restore previous alias |
| 13 | MongoDB primary election | Validate write concern |
| 14 | MongoDB pool pressure | Inspect connection wait |
| 15 | MongoDB schema drift | Validate/migrate documents |
| 16 | Redis stampede | Singleflight and origin protection |
| 17 | Redis stale cache | Repair invalidation |
| 18 | Redis evictions | Inspect memory and TTL |
| 19 | API p99 spike | Correlate traces and pools |
| 20 | Event-loop blocking | Isolate blocking work |
| 21 | Deadline cascade | Propagate bounded timeouts |
| 22 | Retry storm | Cap attempts and jitter |
| 23 | Idempotency collision | Check request fingerprint |
| 24 | Duplicate write | Use durable deduplication |
| 25 | OTel outage | Protect app, flag missing evidence |
| 26 | Prometheus label explosion | Remove high-cardinality labels |
| 27 | Kubernetes OOM | Inspect memory/limits |
| 28 | HPA DB overload | Cap aggregate connections |
| 29 | Unsafe migration | Halt release and rollback |
| 30 | Cross-store inconsistency | Reconcile authoritative state |

## Runbooks

**API security:** restrict compromised identity, validate authorization and preserve privacy-safe audit evidence.

**PostgreSQL:** inspect `pg_stat_activity`, locks and pool waits; protect reserved connections.

**Elasticsearch:** inspect search rejections, query fanout, fetch latency and disk IOPS; lower pressure and verify SLO.

**MongoDB:** inspect replica state, pool wait and uncertain writes; reconcile before retrying.

**Redis:** protect source DB, bound misses and restore cache invalidation.

**Rollback:** stop canary, restore immutable artifact, verify migration compatibility and monitor error budget.

## Final assessment (100 points)

| Domain | Points |
|---|---:|
| API contracts and validation | 20 |
| Authentication and idempotency | 15 |
| PostgreSQL pools and transactions | 20 |
| Elasticsearch, MongoDB and Redis adapters | 20 |
| Observability and incident runbooks | 15 |
| Automated tests and validation | 10 |
| **Total** | **100** |

Pass at 90+ with locally executed tests, no-write evidence, an outbox/reconciliation design and reviewed rollback.

**Validation:** Offline test code published; exact committed execution, CI, real datastore integration and security/production acceptance pending.
