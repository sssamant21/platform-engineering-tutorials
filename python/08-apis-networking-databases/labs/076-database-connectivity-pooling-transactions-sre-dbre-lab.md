# Chapter 076 — Database Connectivity, Pooling and Transactions SRE/DBRE Lab

**Python 3.11+ | SQLAlchemy 2.x | SQLite default | Optional PostgreSQL/psycopg 3**

## Architecture and safety
\`\`\`text
pytest/unittest -> SQLAlchemy Engine (QueuePool, size=2, overflow=0, timeout=0.1)
 -> SQLite file in TemporaryDirectory -> parameterized SQL / commit / rollback
optional PostgreSQL -> psycopg3 + QueuePool -> disposable, explicitly approved DB
\`\`\`
No production database, cloud credentials or external network access is required for default tests. The optional PostgreSQL section must be run only against an isolated test database. SQLite's concurrency and transaction behavior differs from PostgreSQL.

## Files
\`\`\`text
ch076/
  requirements.txt
  db_lab.py
  test_db_lab.py
\`\`\`

## 1. requirements.txt
\`\`\`text
SQLAlchemy>=2.0,<3
\`\`\`
Optional PostgreSQL: \`python -m pip install 'psycopg[binary]>=3.2,<4'\`. Use an approved lockfile and hashes for production.

## 2. Complete application — db_lab.py
\`\`\`python
"""Disposable DB-API/SQLAlchemy pooling and transaction lab."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
import time
from typing import Callable

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as PoolTimeout
from sqlalchemy.pool import QueuePool

class LabError(RuntimeError):
    pass

@dataclass(frozen=True)
class Telemetry:
    engine: str
    service: str
    metric_value: float

def make_engine(db_path: Path, *, pool_size: int = 2, pool_timeout: float = 0.1) -> Engine:
    if type(pool_size) is not int or not 1 <= pool_size <= 10:
        raise ValueError("invalid pool size")
    if type(pool_timeout) not in (int, float) or not math.isfinite(pool_timeout) or pool_timeout <= 0:
        raise ValueError("invalid pool timeout")
    if not isinstance(db_path, Path):
        raise TypeError("Path required")
    return create_engine(
        "sqlite+pysqlite:///" + str(db_path.resolve()),
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=0,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,
        connect_args={"timeout": 0.5},
    )

def initialize(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY,
                engine TEXT NOT NULL,
                service TEXT NOT NULL,
                metric_value REAL NOT NULL CHECK (metric_value >= 0),
                UNIQUE(engine, service)
            )
        """))

def upsert(engine: Engine, item: Telemetry) -> None:
    if not isinstance(item, Telemetry):
        raise TypeError("Telemetry required")
    if item.engine not in ("postgresql", "elasticsearch", "kafka"):
        raise ValueError("invalid engine")
    if not isinstance(item.service, str) or not item.service or len(item.service) > 64:
        raise ValueError("invalid service")
    if type(item.metric_value) not in (int, float) or not math.isfinite(item.metric_value) or item.metric_value < 0:
        raise ValueError("invalid metric")
    # SQLite-specific syntax. PostgreSQL uses INSERT ... ON CONFLICT DO UPDATE.
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO telemetry (engine, service, metric_value)
            VALUES (:engine, :service, :value)
            ON CONFLICT(engine, service) DO UPDATE SET metric_value=excluded.metric_value
        """), {"engine": item.engine, "service": item.service, "value": item.metric_value})

def get_value(engine: Engine, service: str) -> float | None:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT metric_value FROM telemetry WHERE service = :service"),
            {"service": service},
        ).scalar_one_or_none()
    return None if result is None else float(result)

def transaction_rollback(engine: Engine) -> None:
    """Raise after an insert; engine.begin must roll it back."""
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO telemetry (engine, service, metric_value)
            VALUES (:engine, :service, :value)
        """), {"engine": "postgresql", "service": "must-rollback", "value": 1})
        raise LabError("simulated failure before commit")

def pool_timeout_drill(engine: Engine) -> bool:
    """Exhaust one-slot QueuePool, then verify checkout timeout."""
    with engine.connect():
        try:
            with engine.connect():
                pass
        except PoolTimeout:
            return True
    return False

def retry_safe_operation(operation: Callable[[], object], *, attempts: int = 3,
                         sleep: Callable[[float], None] = time.sleep) -> object:
    """Retry only explicitly identified transient connection/checkout failures.

    Do NOT use this helper for writes after ambiguous commit or arbitrary SQL errors.
    """
    if type(attempts) is not int or not 1 <= attempts <= 5:
        raise ValueError("invalid attempts")
    for index in range(attempts):
        try:
            return operation()
        except (PoolTimeout, OperationalError):
            if index + 1 == attempts:
                raise LabError("transient operation exhausted") from None
            sleep(min(0.1, 0.01 * (2 ** index)))
    raise AssertionError("unreachable")

def dbapi_parameterization_example(db_path: Path, service: str) -> int:
    """Demonstrate PEP 249 qmark placeholders using sqlite3 directly."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM telemetry WHERE service = ?", (service,)
        ).fetchone()
    return int(row[0])

if __name__ == "__main__":
    print("Run python -m unittest -v test_db_lab.py for disposable integration tests")
\`\`\`

## 3. Complete tests — test_db_lab.py
\`\`\`python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as PoolTimeout

from db_lab import (
    LabError, Telemetry, dbapi_parameterization_example, get_value,
    initialize, make_engine, pool_timeout_drill, retry_safe_operation,
    transaction_rollback, upsert,
)

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "lab.sqlite"
        self.engine = make_engine(self.path, pool_size=1, pool_timeout=0.05)
        initialize(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_insert_and_read(self):
        upsert(self.engine, Telemetry("postgresql", "pg-replica", 12))
        self.assertEqual(get_value(self.engine, "pg-replica"), 12)

    def test_upsert_idempotent(self):
        upsert(self.engine, Telemetry("kafka", "consumer", 10))
        upsert(self.engine, Telemetry("kafka", "consumer", 20))
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM telemetry")).scalar_one(), 1)
        self.assertEqual(get_value(self.engine, "consumer"), 20)

    def test_transaction_commit(self):
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO telemetry(engine,service,metric_value) VALUES (:e,:s,:v)"),
                         {"e":"postgresql","s":"committed","v":1})
        self.assertEqual(get_value(self.engine,"committed"),1)

    def test_transaction_rollback(self):
        with self.assertRaises(LabError):
            transaction_rollback(self.engine)
        self.assertIsNone(get_value(self.engine, "must-rollback"))

    def test_parameterized_injection_attempt(self):
        upsert(self.engine, Telemetry("postgresql", "normal", 5))
        payload = "' OR 1=1 --"
        self.assertEqual(dbapi_parameterization_example(self.path, payload), 0)
        self.assertEqual(dbapi_parameterization_example(self.path, "normal"), 1)

    def test_sqlalchemy_parameterized_injection_attempt(self):
        upsert(self.engine, Telemetry("kafka", "worker", 5))
        self.assertIsNone(get_value(self.engine, "' OR 1=1 --"))

    def test_pool_timeout(self):
        self.assertTrue(pool_timeout_drill(self.engine))

    def test_pool_recovery(self):
        self.assertTrue(pool_timeout_drill(self.engine))
        self.assertEqual(get_value(self.engine, "unknown"), None)

    def test_pool_budget(self):
        self.assertEqual(self.engine.pool.size(), 1)
        self.assertEqual(self.engine.pool.overflow(), 0)

    def test_invalid_pool_size(self):
        for size in (0, 11, True):
            with self.assertRaises(ValueError):
                make_engine(self.path, pool_size=size)

    def test_invalid_pool_timeout(self):
        for timeout in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                make_engine(self.path, pool_timeout=timeout)

    def test_invalid_metric(self):
        for value in (-1, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                upsert(self.engine, Telemetry("postgresql", "pg", value))

    def test_invalid_engine(self):
        with self.assertRaises(ValueError):
            upsert(self.engine, Telemetry("mysql", "db", 1))

    def test_retry_success(self):
        calls = []
        def operation():
            calls.append(1)
            if len(calls) == 1:
                raise PoolTimeout("synthetic pool exhaustion")
            return "recovered"
        self.assertEqual(retry_safe_operation(operation, sleep=lambda _: None), "recovered")
        self.assertEqual(len(calls), 2)

    def test_retry_exhaustion(self):
        calls = []
        def operation():
            calls.append(1)
            raise PoolTimeout("synthetic pool exhaustion")
        with self.assertRaises(LabError):
            retry_safe_operation(operation, attempts=2, sleep=lambda _: None)
        self.assertEqual(len(calls), 2)

    def test_no_retry_for_business_failure(self):
        calls = []
        def operation():
            calls.append(1)
            raise ValueError("permanent application failure")
        with self.assertRaises(ValueError):
            retry_safe_operation(operation)
        self.assertEqual(len(calls), 1)

    def test_retry_invalid_budget(self):
        with self.assertRaises(ValueError):
            retry_safe_operation(lambda: None, attempts=0)

    def test_rollback_after_constraint_violation(self):
        upsert(self.engine, Telemetry("postgresql", "pg", 5))
        with self.assertRaises(Exception):
            with self.engine.begin() as conn:
                conn.execute(text("INSERT INTO telemetry(engine,service,metric_value) VALUES (:e,:s,:v)"),
                             {"e":"postgresql","s":"pg","v":6})
        self.assertEqual(get_value(self.engine, "pg"), 5)

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 4. Execute
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q db_lab.py test_db_lab.py
python -m unittest -v test_db_lab.py
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_db_lab.py\`.

## 5. Optional PostgreSQL profile — psycopg 3 and SQLAlchemy
**Only for an explicitly approved disposable database.** Never point these examples at production.

\`\`\`bash
python -m pip install 'psycopg[binary]>=3.2,<4'
# Supply a secret-managed test DSN through the environment.
# Use sslmode=verify-full and an approved root certificate for remote TLS.
\`\`\`
\`\`\`python
import os
import psycopg
from sqlalchemy import create_engine, text

dsn = os.environ["CH076_TEST_POSTGRES_DSN"]  # disposable test DB only
with psycopg.connect(dsn, connect_timeout=3) as conn:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout = '3s'")
        cur.execute("SELECT %s::int + 1", (41,))
        assert cur.fetchone()[0] == 42

# psycopg3 SQLAlchemy dialect and bounded QueuePool.
engine = create_engine(
    "postgresql+psycopg://" + os.environ["CH076_TEST_PG_URL_COMPONENTS"],
    pool_size=2, max_overflow=0, pool_timeout=1,
    pool_pre_ping=True, connect_args={"connect_timeout": 3},
)
with engine.begin() as conn:
    assert conn.execute(text("SELECT :value + 1"), {"value": 41}).scalar_one() == 42
engine.dispose()
\`\`\`
Do not concatenate untrusted DSN components; the second example expects an operator-controlled SQLAlchemy URL string in \`CH076_TEST_PG_URL_COMPONENTS\` without a scheme, not user input. Prefer \`sqlalchemy.engine.URL.create\` and secret-provider integration in production. For PostgreSQL pool capacity, calculate \`replicas × processes × (pool_size + max_overflow)\`, including rolling deployment overlap.

## 6. CI template
\`\`\`yaml
name: chapter-076-db
on: workflow_dispatch
jobs:
  sqlite-lab:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify extracted source
        run: |
          test -f db_lab.py
          test -f test_db_lab.py
          test -f requirements.txt
      - name: Install
        run: python -m pip install -r requirements.txt
      - name: Test
        run: python -m unittest -v test_db_lab.py
\`\`\`
This is a template only. Extract code blocks to files, pin reviewed action commit SHAs and dependency hashes, then validate on an approved runner.

## 7. Production incident drills
1. QueuePool exhausted with one connection checked out.
2. Connection returned after checkout failure.
3. SQL parameter injection attempt blocked.
4. Transaction committed on success.
5. Transaction rolled back on exception.
6. Duplicate unique key causes rollback.
7. Idempotent upsert updates one row.
8. Invalid telemetry metric rejected.
9. Transient pool error recovered after bounded retry.
10. Repeated transient error exhausts retry budget.
11. Business failure is not retried.
12. PostgreSQL \`max_connections\` pressure (runbook).
13. Stale connection after failover (runbook).
14. SQLSTATE 40001/40P01 whole-transaction retry design.
15. Ambiguous commit: reconcile before replay.
16. Long transaction blocks VACUUM.
17. Lock and statement timeout policy.
18. Credential/TLS failure and approved rotation.

## 8. Runbooks
**Pool exhaustion:** identify checked-out connections, slow transactions and total pool capacity across pods. Reduce concurrency and restore approved pool sizing.

**Deadlock/serialization:** classify SQLSTATE; retry the complete idempotent transaction with bounded jitter, not an arbitrary SQL statement.

**Failover:** confirm primary endpoint and TLS trust, invalidate stale pools, reconcile ambiguous writes and verify read/write canaries.

**Security:** revoke exposed credentials, verify parameterization and RBAC, inspect audit logs and never log DSNs.

**Rollback:** revert connection/pool/retry configuration, rerun isolated tests and production canaries, confirm latency/error SLO.

## 9. 100-point assessment
| Area | Points |
|---|---:|
| DB-API and psycopg concepts | 15 |
| SQLAlchemy QueuePool and capacity | 20 |
| Transaction commit/rollback | 20 |
| Parameterization and secret safety | 15 |
| Automated tests and failure injection | 20 |
| Runbooks, timeouts and CI | 10 |

**Pass:** at least 90/100 and mandatory tests executed independently. SQLite tests do not validate PostgreSQL-specific SQLSTATE, TLS or isolation semantics. GitHub publication is not test execution evidence.
