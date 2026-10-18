# Chapter 077 — PostgreSQL Transactions, Isolation and Reliability SRE/DBRE Lab

**Python 3.11+ | psycopg 3 | PostgreSQL 15+ | Disposable database required**

## Safety and topology
\`\`\`text
unittest -> psycopg3 -> explicitly approved disposable PostgreSQL
  -> transaction/savepoint/row-lock/idempotency tables in isolated test schema
  -> SQLSTATE classification + bounded whole-transaction retries
\`\`\`
**Never run against production or shared staging.** Tests create and drop objects in a dedicated, isolated schema. Provide a disposable database with a dedicated role. The script refuses to run unless \`CH077_ALLOW_DESTRUCTIVE_TESTS=YES\` and \`CH077_TEST_DSN\` are set. This is an educational guard, not proof of isolation; verify host/database/user manually. Use a TLS-verified connection for remote databases. Local Docker PostgreSQL is appropriate for learning.

## 1. requirements.txt
\`\`\`text
psycopg[binary]>=3.2,<4
\`\`\`

## 2. Complete application — pg_transactions.py
\`\`\`python
"""PostgreSQL transaction and retry exercises for an isolated test database."""
from __future__ import annotations

from dataclasses import dataclass
import os
import random
import time
from typing import Callable

import psycopg
from psycopg import errors
from psycopg.rows import dict_row

RETRYABLE_SQLSTATES = frozenset(("40001", "40P01"))

class LabError(RuntimeError): pass

@dataclass(frozen=True)
class Transfer:
    request_id: str
    source: int
    destination: int
    amount: int

def test_dsn() -> str:
    if os.environ.get("CH077_ALLOW_DESTRUCTIVE_TESTS") != "YES":
        raise LabError("set CH077_ALLOW_DESTRUCTIVE_TESTS=YES only for isolated DB")
    dsn = os.environ.get("CH077_TEST_DSN", "")
    if not dsn:
        raise LabError("CH077_TEST_DSN required")
    return dsn

def connect():
    return psycopg.connect(test_dsn(), connect_timeout=3, row_factory=dict_row)

def setup() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS ch077_lab")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ch077_lab.account (
                    id INTEGER PRIMARY KEY,
                    balance BIGINT NOT NULL CHECK (balance >= 0)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ch077_lab.transfer_ledger (
                    request_id TEXT PRIMARY KEY,
                    source_id INTEGER NOT NULL,
                    destination_id INTEGER NOT NULL,
                    amount BIGINT NOT NULL CHECK (amount > 0)
                )
            """)
            cur.execute("TRUNCATE ch077_lab.transfer_ledger, ch077_lab.account")
            cur.execute("INSERT INTO ch077_lab.account(id,balance) VALUES (1,1000),(2,1000)")

def teardown() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS ch077_lab CASCADE")

def transfer_once(conn, item: Transfer) -> bool:
    """Run within caller-owned transaction. Return False for exact duplicate."""
    if (not isinstance(item.request_id, str) or not item.request_id
            or len(item.request_id) > 80 or item.source == item.destination
            or type(item.source) is not int or type(item.destination) is not int
            or type(item.amount) is not int or item.amount <= 0):
        raise ValueError("invalid transfer")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source_id, destination_id, amount FROM ch077_lab.transfer_ledger WHERE request_id = %s",
            (item.request_id,),
        )
        existing = cur.fetchone()
        if existing is not None:
            if (existing["source_id"], existing["destination_id"], existing["amount"]) != (
                item.source, item.destination, item.amount
            ):
                raise LabError("idempotency key reused with different payload")
            return False
        # Lock accounts in deterministic order to avoid cyclic lock acquisition.
        cur.execute(
            "SELECT id,balance FROM ch077_lab.account WHERE id IN (%s,%s) ORDER BY id FOR UPDATE",
            (item.source, item.destination),
        )
        rows = cur.fetchall()
        if len(rows) != 2:
            raise LabError("missing account")
        balances = {row["id"]: row["balance"] for row in rows}
        if balances[item.source] < item.amount:
            raise LabError("insufficient funds")
        cur.execute(
            "UPDATE ch077_lab.account SET balance=balance-%s WHERE id=%s",
            (item.amount, item.source),
        )
        cur.execute(
            "UPDATE ch077_lab.account SET balance=balance+%s WHERE id=%s",
            (item.amount, item.destination),
        )
        cur.execute(
            "INSERT INTO ch077_lab.transfer_ledger(request_id,source_id,destination_id,amount) VALUES (%s,%s,%s,%s)",
            (item.request_id, item.source, item.destination, item.amount),
        )
        return True

def transfer_with_retry(item: Transfer, *, attempts: int = 3,
                        sleep: Callable[[float], None] = time.sleep) -> bool:
    """Retry whole transaction only for SQLSTATE 40001 or 40P01."""
    if type(attempts) is not int or not 1 <= attempts <= 5:
        raise ValueError("invalid attempts")
    for index in range(attempts):
        try:
            with connect() as conn:
                with conn.transaction():
                    return transfer_once(conn, item)
        except psycopg.Error as exc:
            if exc.sqlstate not in RETRYABLE_SQLSTATES or index + 1 == attempts:
                raise
            sleep(min(0.2, 0.02 * (2 ** index)) * random.uniform(0.5, 1.0))
    raise AssertionError("unreachable")

def balance(account_id: int) -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM ch077_lab.account WHERE id=%s", (account_id,))
            row = cur.fetchone()
            if row is None:
                raise LabError("missing account")
            return int(row["balance"])

def ledger_count() -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM ch077_lab.transfer_ledger")
            return int(cur.fetchone()["n"])

def savepoint_demo() -> int:
    """Catch unique violation within a savepoint; preserve outer transaction."""
    with connect() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("INSERT INTO ch077_lab.account(id,balance) VALUES (3,50)")
            try:
                with conn.transaction():  # nested SAVEPOINT
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO ch077_lab.account(id,balance) VALUES (3,99)")
            except errors.UniqueViolation:
                pass
    return balance(3)

def sqlstate_retryable(sqlstate: str | None) -> bool:
    return sqlstate in RETRYABLE_SQLSTATES

if __name__ == "__main__":
    print("Run the isolated PostgreSQL integration tests; never use production.")
\`\`\`

## 3. Complete integration tests — test_pg_transactions.py
\`\`\`python
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import psycopg
from psycopg import errors

from pg_transactions import (
    LabError, Transfer, balance, connect, ledger_count, savepoint_demo,
    setup, sqlstate_retryable, teardown, test_dsn, transfer_once,
    transfer_with_retry,
)

class GuardTests(unittest.TestCase):
    def test_missing_guard(self):
        with patch.dict(os.environ, {"CH077_ALLOW_DESTRUCTIVE_TESTS": "NO"}, clear=True):
            with self.assertRaises(LabError):
                test_dsn()
    def test_sqlstate_classification(self):
        self.assertTrue(sqlstate_retryable("40001"))
        self.assertTrue(sqlstate_retryable("40P01"))
        self.assertFalse(sqlstate_retryable("23505"))
        self.assertFalse(sqlstate_retryable(None))
    def test_invalid_retry_budget(self):
        with self.assertRaises(ValueError):
            transfer_with_retry(Transfer("x",1,2,1),attempts=0)

@unittest.skipUnless(
    os.environ.get("CH077_ALLOW_DESTRUCTIVE_TESTS") == "YES"
    and bool(os.environ.get("CH077_TEST_DSN")),
    "requires explicitly approved disposable PostgreSQL DSN and destructive-test guard",
)
class PostgreSQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup()
    @classmethod
    def tearDownClass(cls):
        teardown()

    def setUp(self):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE ch077_lab.transfer_ledger, ch077_lab.account")
                cur.execute("INSERT INTO ch077_lab.account(id,balance) VALUES (1,1000),(2,1000)")

    def test_transfer_commits(self):
        self.assertTrue(transfer_with_retry(Transfer("t1",1,2,100)))
        self.assertEqual((balance(1),balance(2)),(900,1100))
        self.assertEqual(ledger_count(),1)

    def test_idempotent_duplicate(self):
        item=Transfer("t2",1,2,100)
        self.assertTrue(transfer_with_retry(item))
        self.assertFalse(transfer_with_retry(item))
        self.assertEqual((balance(1),balance(2)),(900,1100))
        self.assertEqual(ledger_count(),1)

    def test_idempotency_payload_mismatch(self):
        transfer_with_retry(Transfer("t3",1,2,100))
        with self.assertRaises(LabError):
            transfer_with_retry(Transfer("t3",1,2,200))
        self.assertEqual(ledger_count(),1)

    def test_insufficient_funds_rolls_back(self):
        with self.assertRaises(LabError):
            transfer_with_retry(Transfer("t4",1,2,2000))
        self.assertEqual((balance(1),balance(2)),(1000,1000))
        self.assertEqual(ledger_count(),0)

    def test_missing_account_rolls_back(self):
        with self.assertRaises(LabError):
            transfer_with_retry(Transfer("t5",1,9,10))
        self.assertEqual(balance(1),1000)

    def test_savepoint(self):
        self.assertEqual(savepoint_demo(),50)

    def test_outer_rollback(self):
        with self.assertRaises(RuntimeError):
            with connect() as conn:
                with conn.transaction():
                    transfer_once(conn,Transfer("t6",1,2,10))
                    raise RuntimeError("abort outer transaction")
        self.assertEqual((balance(1),balance(2)),(1000,1000))
        self.assertEqual(ledger_count(),0)

    def test_parameterization(self):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS n FROM ch077_lab.transfer_ledger WHERE request_id=%s",
                            ("' OR 1=1 --",))
                self.assertEqual(cur.fetchone()["n"],0)

    def test_invalid_transfer(self):
        for item in (Transfer("",1,2,1),Transfer("bad",1,1,1),Transfer("bad",1,2,0)):
            with self.assertRaises(ValueError):
                transfer_with_retry(item)

    def test_read_committed_isolation(self):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW transaction_isolation")
                self.assertIn(cur.fetchone()["transaction_isolation"],
                              ("read committed","repeatable read","serializable"))

    def test_unique_violation_sqlstate(self):
        with connect() as conn:
            with conn.cursor() as cur:
                with self.assertRaises(errors.UniqueViolation) as caught:
                    cur.execute("INSERT INTO ch077_lab.account(id,balance) VALUES (1,1)")
                self.assertEqual(caught.exception.sqlstate,"23505")

if __name__=="__main__":
    unittest.main()
\`\`\`

## 4. Execute safely
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q pg_transactions.py test_pg_transactions.py
# Default: only guard/SQLSTATE tests run; live integration tests are skipped.
python -m unittest -v test_pg_transactions.py
\`\`\`
For a **disposable** PostgreSQL database, provision a dedicated test role/database with no other workloads. Review the DSN and verify the server identity before opting in:
\`\`\`bash
export CH077_TEST_DSN='postgresql://test_user:REPLACE_ME@127.0.0.1:5432/ch077_disposable'
export CH077_ALLOW_DESTRUCTIVE_TESTS=YES
python -m unittest -v test_pg_transactions.py
\`\`\`
Do not paste real passwords into shell history; use a local environment file with restrictive permissions or a secret manager. The example DSN contains a placeholder only. On Windows PowerShell, set environment variables with \`$env:CH077_TEST_DSN=...\` and \`$env:CH077_ALLOW_DESTRUCTIVE_TESTS="YES"\`.

## 5. Advanced concurrency exercises (isolated database only)
The core automated suite covers transactions, savepoints, rollback, idempotency and SQLSTATE classification. The following are **guided incident exercises** rather than automatically executed tests:

**Deadlock:** open two test connections; lock account 1 then 2 in session A, and account 2 then 1 in session B. Observe \`40P01\`, roll back and implement consistent lock ordering. Coordinate sessions to avoid indefinite waits and use \`SET LOCAL lock_timeout='2s'\`.

**Serialization failure:** set both transactions to SERIALIZABLE, read a shared invariant, then update conflicting rows; observe \`40001\` and retry the entire transaction. A conflict is workload-dependent; confirm SQLSTATE rather than assuming every run produces one.

**Isolation:** compare READ COMMITTED statement snapshots against REPEATABLE READ transaction snapshots with two connections.

**Ambiguous commit:** simulate client disconnect during COMMIT, query \`transfer_ledger\` by stable request ID before any replay. Do not infer success or failure solely from socket status.

**Long transaction:** inspect \`pg_stat_activity.xact_start\` and \`backend_xmin\`; validate vacuum impact only on disposable data.

## 6. Diagnostic SQL (read-only; run with authorization)
\`\`\`sql
SELECT pid, state, wait_event_type, wait_event, now()-xact_start AS xact_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start;

SELECT pid, pg_blocking_pids(pid) AS blockers
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

SELECT datname, deadlocks
FROM pg_stat_database
ORDER BY deadlocks DESC;
\`\`\`
Do not terminate sessions or alter global timeouts without approved change procedures.

## 7. CI template
\`\`\`yaml
name: chapter-077-postgresql
on: workflow_dispatch
jobs:
  guard-tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Require extracted files
        run: |
          test -f pg_transactions.py
          test -f test_pg_transactions.py
          test -f requirements.txt
      - name: Install
        run: python -m pip install -r requirements.txt
      - name: Guard tests only
        run: python -m unittest -v test_pg_transactions.GuardTests
\`\`\`
Template only. Extract source from Markdown, pin reviewed action SHAs and dependencies, and add a separate **explicitly authorized disposable PostgreSQL service** before enabling live integration tests.

## 8. Runbooks
**Deadlock/40001:** classify SQLSTATE, inspect lock ordering, bound whole-transaction retries and avoid external side effects.

**Ambiguous COMMIT:** query idempotency ledger, reconcile outcome, never blindly replay.

**Long snapshot:** inspect xact age and backend_xmin, coordinate safe cleanup and monitor vacuum.

**Failover:** reconnect to validated primary, reconcile in-flight transactions, verify read/write canaries.

**Rollback:** restore approved transaction/isolation/retry policy, rerun isolated tests and production canaries, confirm SLO.

## 9. 100-point assessment
| Area | Points |
|---|---:|
| psycopg transaction and MVCC concepts | 15 |
| Isolation levels and concurrency reasoning | 20 |
| Savepoints and rollback | 15 |
| Deadlocks, serialization and safe retries | 20 |
| Idempotency and ambiguous commit handling | 15 |
| Automated tests, runbooks and CI | 15 |

**Pass:** at least 90/100, with PostgreSQL integration tests run against a verified isolated database. Publication and skipped tests are not execution evidence.
