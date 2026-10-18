# Chapter 076 — Python Database Connectivity and Connection Pooling Fundamentals

**Part 08 — APIs, Networking and Databases | Python 3.11+ | SRE/DBRE operations**

## Learning objectives
Explain Python DB-API 2.0 (PEP 249), PostgreSQL connectivity with psycopg 3, SQLAlchemy Engine and QueuePool, transaction boundaries, safe parameterized SQL, pool saturation, connect/read timeouts, retry safety, connection lifecycle, and incident response. Run the companion lab with built-in SQLite for deterministic offline testing, plus an **optional disposable PostgreSQL** integration profile.

## 1. Architecture
\`\`\`text
API/worker -> bounded work admission -> SQLAlchemy Engine / QueuePool
  -> connection checkout (pool_timeout)
  -> psycopg driver (connect_timeout, TCP/TLS)
  -> PostgreSQL (statement_timeout, lock_timeout, idle_in_transaction_session_timeout)
  -> commit/rollback -> pool reset-on-return -> check-in
  -> safe metrics: pool wait, checked-out count, SQLSTATE, query duration
\`\`\`
The local default profile uses SQLite for reproducible DB-API and transaction tests. SQLite differs from PostgreSQL in concurrency, isolation, SQLSTATE and pooling; do not interpret SQLite tests as proof of PostgreSQL production readiness.

## 2. DB-API 2.0
PEP 249 defines \`connect()\`, connection objects, cursors, \`execute()\`, \`fetchone()\`, \`fetchall()\`, \`commit()\`, \`rollback()\`, exception classes and driver metadata such as \`paramstyle\` and \`threadsafety\`. Placeholder syntax varies by driver: psycopg uses \`%s\` for bound **values**, SQLite uses \`?\`, and SQLAlchemy \`text()\` uses named binds like \`:patient_id\`. Never concatenate user values into SQL. SQL identifiers cannot generally be bound as values; use allowlists or psycopg's \`sql.Identifier\`.

## 3. psycopg 3
Install \`psycopg[binary]\` for local labs, or use the deployment-approved build in production. Connect with a trusted DSN and \`connect_timeout\`, then configure \`statement_timeout\`, \`lock_timeout\`, and idle-in-transaction timeout at role/database/session scope. Use \`with psycopg.connect(...) as conn:\` for transaction commit/rollback and connection cleanup; manage cursors with \`with conn.cursor() as cur:\`. Bind parameters using \`cur.execute("SELECT ... WHERE id = %s", (id_value,))\`. Use TLS verification such as \`sslmode=verify-full\` and an approved CA trust configuration for remote PostgreSQL.

## 4. SQLAlchemy Engine and pools
The Engine owns a dialect, connection management and pool. \`QueuePool(pool_size=N, max_overflow=M, pool_timeout=S, pool_pre_ping=True, pool_recycle=...)\` bounds resource use. Maximum concurrent DB connections per process can reach \`N + M\`; multiply by processes, pods and rollout overlap when calculating total server load. \`pool_pre_ping\` detects stale connections at checkout but does not make an in-flight transaction safe to replay. \`pool_recycle\` limits connection age at checkout; it does not terminate an active long query. SQLAlchemy \`engine.begin()\` commits on success and rolls back on exception. \`engine.connect()\` does not imply automatic commit. A pool timeout means a connection could not be checked out within its budget; distinguish it from PostgreSQL connect timeout and SQL statement timeout.

## 5. Transactions and isolation
Transactions guarantee atomicity of grouped writes. Use explicit boundaries and keep them short; avoid network calls inside open transactions. Understand PostgreSQL READ COMMITTED, REPEATABLE READ and SERIALIZABLE, plus MVCC snapshots, deadlocks and serialization failures. A retryable SQLSTATE (\`40001\` serialization failure or \`40P01\` deadlock) may justify retrying the **entire transaction** with a bounded budget when its external side effects are safe. Never blindly retry a transaction after an ambiguous network failure; commit may have succeeded. Use idempotency keys and reconciliation.

## 6. SQL injection and secrets
Use driver bind parameters for values, allowlist schema/table names, apply least-privilege DB roles and separate read-only from writer identities. Never log connection strings with passwords, raw SQL containing PII, full query parameters or credentials. Load secrets from approved providers; rotate without exposing them to process listings. Use parameterized \`text()\` statements in SQLAlchemy.

## 7. Timeouts and reliability
Enforce budgets at several layers: client admission timeout, pool checkout timeout, driver connection timeout, PostgreSQL statement/lock timeout and overall request deadline. Align these with service SLOs and upstream budgets. A large pool is not a fix for a slow database; increasing connections can amplify lock contention and CPU pressure. Monitor \`pg_stat_activity\`, wait events, \`pg_stat_statements\` where enabled, locks, deadlocks and application pool utilization.

## 8. Production incident simulations
1. PostgreSQL max_connections exhausted by too many pods.
2. SQLAlchemy QueuePool timeout due to leaked checkout.
3. Database restart invalidates idle pooled connections.
4. Long transaction blocks VACUUM and causes bloat.
5. Lock wait exceeds \`lock_timeout\`.
6. Query exceeds \`statement_timeout\`.
7. Transaction deadlock (SQLSTATE 40P01).
8. Serialization conflict (40001).
9. Ambiguous commit after TCP reset; avoid blind replay.
10. SQL injection attempt against a patient identifier.
11. Wrong credentials or expired certificate.
12. DNS resolution and network timeout to RDS/Aurora.
13. Read replica lag makes a fresh read stale.
14. Connection pool multiplied across Kubernetes replicas.
15. Session state leaked between pooled connections.
16. Rolling deployment doubles connections temporarily.

## 9. Troubleshooting
| Symptom | Diagnose | Action |
|---|---|---|
| QueuePool timeout | Checked-out/overflow count, request concurrency | Find leaks and slow transactions; bound admission |
| Too many connections | \`pg_stat_activity\`, replicas × pool | Reduce pools and excess workers |
| 40001/40P01 | SQLSTATE, transaction scope | Bounded retry of safe full transaction |
| Slow checkout | Pool saturation | Reduce query/transaction time |
| Stale connection | Restart/failover, network idle timeout | Pre-ping, recycle, reconnect safely |
| 28P01 | Authentication | Verify identity and rotate credential |
| 57014 | Statement cancelled | Optimize SQL, tune approved timeout |
| 55P03 | Lock not available | Inspect blockers, reduce lock duration |
| Connection refused | Listener, endpoint, network policy | Restore service path; avoid retry storm |

## 10. Runbooks
**Pool exhaustion:** check pod count × (pool_size + max_overflow), active checkouts, slow queries, blocked transactions and DB connection ceiling. Restore a safe pool budget and rollback unapproved scaling.

**Transaction failures:** classify SQLSTATE, verify idempotency, retry entire safe transaction with bounded backoff; never repeat unknown committed external actions.

**Failover:** confirm new primary endpoint, DNS/TLS, stale pool invalidation, reconnect and transaction reconciliation before resuming writes.

**Security:** revoke exposed credentials, review audit logs, enforce least privilege and parameterization, validate TLS.

**Rollback:** restore previous pool, timeout and retry settings; rerun synthetic and approved PostgreSQL canaries, verify latency/error SLO and document change.

## 11. Companion lab and acceptance
[Chapter 076 — Database Connectivity, Pooling and Transactions SRE/DBRE Lab](labs/076-database-connectivity-pooling-transactions-sre-dbre-lab.md) contains complete executable Python, unit/integration tests, a SQLite default profile, optional PostgreSQL profile, fault injection, runbooks and a 100-point assessment. The PostgreSQL profile requires an explicit disposable database and is **not** run automatically.

**Next proposed:** Chapter 077 — Python PostgreSQL Transactions, Isolation and Reliable Database Operations.
