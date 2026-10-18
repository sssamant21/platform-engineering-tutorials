# Chapter 077 — Python PostgreSQL Transactions, Isolation and Reliable Database Operations

**Part 08 — APIs, Networking and Databases | Python 3.11+ | psycopg 3 | SRE/DBRE**

## Objectives
Implement safe PostgreSQL transactions in Python using psycopg 3, understand MVCC and isolation levels, use savepoints, diagnose locks and deadlocks, handle SQLSTATE 40001 and 40P01, design idempotent retries, and operate database workloads safely during failover and contention.

## Architecture
\`\`\`text
Python worker -> psycopg 3 connection -> explicit transaction
  -> parameterized SQL -> PostgreSQL MVCC snapshots and row locks
  -> COMMIT or ROLLBACK
  -> SQLSTATE classification -> bounded whole-transaction retry (only if safe)
  -> idempotency ledger + reconciliation for ambiguous commits
\`\`\`

## 1. Transaction semantics
A transaction groups changes into an atomic unit. PostgreSQL provides atomicity, consistency, isolation and durability subject to configured durability and replication semantics. A successful COMMIT confirms the server accepted the transaction; a client-side network error during COMMIT can leave the outcome **unknown**. Never blindly repeat an externally visible write after an ambiguous outcome. Use a stable idempotency key and query the authoritative database before replay.

With psycopg 3, \`with psycopg.connect(dsn) as conn:\` manages commit/rollback and closes the connection. Explicit \`with conn.transaction():\` creates a transaction or savepoint according to connection state; avoid mixing implicit transactions and explicit transaction blocks unintentionally. psycopg defaults to non-autocommit, so even SELECT can start a transaction. Keep transactions short and close idle-in-transaction sessions.

## 2. MVCC
PostgreSQL Multi-Version Concurrency Control lets readers observe consistent row versions while writers create new versions. Visibility depends on snapshots and isolation level. Long-lived snapshots delay cleanup of dead tuples, increasing bloat and vacuum pressure. Monitor \`pg_stat_activity.xact_start\`, \`backend_xmin\`, wait events and autovacuum. A row version visible to one transaction may not be visible to another.

## 3. Isolation levels
| Isolation | Snapshot/behavior | Operational risk |
|---|---|---|
| READ COMMITTED | New snapshot per statement | Nonrepeatable reads; application must handle concurrent changes |
| REPEATABLE READ | Stable transaction snapshot | Serialization failures can occur under conflicting updates |
| SERIALIZABLE | Serializable Snapshot Isolation | SQLSTATE 40001; retry complete safe transaction |
| READ UNCOMMITTED | Treated as READ COMMITTED by PostgreSQL | No dirty reads despite name |

Isolation is not a substitute for uniqueness constraints, conditional updates or application idempotency. PostgreSQL's REPEATABLE READ prevents phantoms within the transaction snapshot, unlike some generic SQL descriptions.

## 4. Locks and deadlocks
\`SELECT ... FOR UPDATE\` obtains row locks. Two transactions locking resources in opposite order can deadlock; PostgreSQL detects a cycle and aborts one transaction with SQLSTATE \`40P01\`. Use a consistent lock order, short transactions and targeted indexes. \`lock_timeout\` bounds waiting for locks; \`statement_timeout\` bounds statement execution. Do not kill sessions without operational authorization.

## 5. Savepoints
\`SAVEPOINT name\`, \`ROLLBACK TO SAVEPOINT name\`, and \`RELEASE SAVEPOINT name\` allow a transaction to recover from a local error without aborting all prior work. psycopg's nested \`conn.transaction()\` can manage savepoints. Savepoints do not commit independently; an outer rollback still undoes all changes.

## 6. Safe retries
Retry the **entire transaction**, not just the last failed statement, for retryable \`40001\` and \`40P01\`. Use a small attempt cap, jitter, deadline and metrics. Do not retry arbitrary \`OperationalError\` or unknown commit outcomes. Keep non-database side effects (emails, Kafka publishes, HTTP calls) outside retried blocks or use transactional outbox patterns. Preserve stable idempotency keys across retries. SQLSTATE \`23505\` unique violations are usually business conflicts, not automatically retryable.

## 7. psycopg 3 patterns
\`\`\`python
import psycopg
from psycopg import IsolationLevel
from psycopg.rows import dict_row

with psycopg.connect(TEST_DSN, connect_timeout=3, row_factory=dict_row) as conn:
    conn.isolation_level = IsolationLevel.READ_COMMITTED
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM account WHERE id = %s FOR UPDATE", (account_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError("account missing")
\`\`\`
This is a conceptual excerpt: use a disposable test database and configure TLS verification and scoped credentials. Avoid changing isolation level while a transaction is active.

## 8. PostgreSQL production observability
Inspect \`pg_stat_activity\`, \`pg_locks\`, \`pg_stat_database.deadlocks\`, \`pg_stat_statements\` where installed, transaction age and \`pg_blocking_pids(pid)\`. Track SQLSTATE classes, retry attempts, lock wait duration, serialization failures, connection utilization and idempotency conflicts without exposing parameters or PII. Never log raw DSNs or customer identifiers.

## 9. Production incident simulations
1. Concurrent updates to the same account.
2. READ COMMITTED sees a changed value on a later statement.
3. REPEATABLE READ retains snapshot across statements.
4. SERIALIZABLE conflict raises 40001.
5. Opposite lock ordering produces 40P01.
6. Nested savepoint recovers from a unique violation.
7. Outer rollback undoes released savepoint changes.
8. Long transaction blocks vacuum cleanup.
9. Lock timeout aborts a blocked statement.
10. Statement timeout cancels slow SQL.
11. Network loss during COMMIT causes ambiguous outcome.
12. Duplicate request is safely deduplicated by idempotency key.
13. Nonretryable 23505 is classified correctly.
14. Failover disconnects an in-flight transaction.
15. Retry storm overloads the primary.
16. Transactional outbox prevents duplicate Kafka side effects.
17. Connection pool holds idle-in-transaction sessions.
18. Replica lag causes stale reads after a write.

## 10. Troubleshooting matrix
| Symptom | SQLSTATE/Signal | Response |
|---|---|---|
| Serialization conflict | 40001 | Retry whole safe transaction with bounded jitter |
| Deadlock | 40P01 | Enforce lock order; bounded whole-transaction retry |
| Unique violation | 23505 | Resolve business/idempotency conflict |
| Lock timeout | 55P03 | Inspect blockers, shorten transactions |
| Statement timeout | 57014 | Optimize query or approved budget |
| Connection failure | 08xxx | Determine commit outcome before replay |
| Idle in transaction | \`pg_stat_activity\` | Close transactions, set session timeouts |
| Bloat and vacuum lag | Long \`backend_xmin\` | Investigate long snapshots and vacuum |

## 11. Runbooks
**Deadlock storm:** capture SQLSTATE, identify conflicting statements and lock order, limit retries, inspect \`pg_locks\` and deploy consistent lock ordering.

**Serialization failures:** verify isolation and retry eligibility, cap whole-transaction attempts, reduce contention and confirm no external side effects.

**Ambiguous COMMIT:** stop blind replay, query idempotency ledger on primary, reconcile transaction outcome and record evidence.

**Long transaction:** inspect \`xact_start\`, blockers and backend state; coordinate termination only through approved incident/change procedure.

**Failover:** validate new primary, TLS and connection pool health; reconcile uncertain writes and resume through canary operations.

**Rollback:** restore approved isolation, retry and timeout policies, rerun tests and production canaries, verify SLO and record change approval.

## 12. Lab
[Chapter 077 — PostgreSQL Transactions, Isolation and Reliability SRE/DBRE Lab](labs/077-postgresql-transactions-isolation-reliability-sre-dbre-lab.md) contains complete psycopg 3 source, an explicitly gated disposable PostgreSQL test profile, automated integration tests, fault injection, runbooks and a 100-point assessment. PostgreSQL is required for the live integration tests; they are not represented as SQLite-equivalent.

**Next proposed:** Chapter 078 — Python Database Query Performance, Batching and Streaming Results.
