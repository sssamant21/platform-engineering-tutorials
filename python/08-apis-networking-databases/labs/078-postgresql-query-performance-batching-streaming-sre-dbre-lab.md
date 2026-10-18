# Chapter 078 — PostgreSQL Query Performance, Batching and Streaming SRE/DBRE Lab

**Python 3.11+ | psycopg 3 | PostgreSQL 15+ | Explicitly approved disposable database**

## 1. Safety and topology
\`\`\`text
unittest -> psycopg 3 -> isolated disposable PostgreSQL
 -> ch078_lab.events table -> batch INSERT / COPY / named cursor
 -> EXPLAIN ANALYZE BUFFERS -> rollback and timeout validation
\`\`\`
The integration tests create and **drop** schema \`ch078_lab\`. They run only if both \`CH078_ALLOW_DESTRUCTIVE_TESTS=YES\` and \`CH078_TEST_DSN\` are present. The default test run performs offline guard/unit tests only. Do not use production or shared staging. Verify database, host, role, schema ownership and TLS before opting in. Use a dedicated test role/database.

## 2. requirements.txt
\`\`\`text
psycopg[binary]>=3.2,<4
\`\`\`
Use reviewed hash-pinned dependencies for production.

## 3. Complete source — pg_performance.py
\`\`\`python
"""Safe PostgreSQL query performance and bounded streaming lab."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Iterator

import psycopg
from psycopg.rows import dict_row

class LabError(RuntimeError): pass

@dataclass(frozen=True)
class Event:
    event_id: int
    source: str
    value: int

def test_dsn() -> str:
    if os.environ.get("CH078_ALLOW_DESTRUCTIVE_TESTS") != "YES":
        raise LabError("destructive-test guard not enabled")
    dsn = os.environ.get("CH078_TEST_DSN", "")
    if not dsn:
        raise LabError("disposable PostgreSQL DSN required")
    return dsn

def connect():
    return psycopg.connect(test_dsn(), connect_timeout=3, row_factory=dict_row)

def validate(event: Event) -> None:
    if not isinstance(event, Event):
        raise ValueError("Event required")
    if type(event.event_id) is not int or event.event_id <= 0:
        raise ValueError("invalid event id")
    if not isinstance(event.source, str) or not event.source or len(event.source) > 32:
        raise ValueError("invalid source")
    if type(event.value) is not int or event.value < 0:
        raise ValueError("invalid value")

def setup() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS ch078_lab")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ch078_lab.events (
                    event_id BIGINT PRIMARY KEY,
                    source TEXT NOT NULL,
                    value BIGINT NOT NULL CHECK(value >= 0)
                )
            """)
            cur.execute("TRUNCATE ch078_lab.events")
            cur.execute("CREATE INDEX IF NOT EXISTS events_source_idx ON ch078_lab.events(source)")

def teardown() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS ch078_lab CASCADE")

def batch_insert(events: Iterable[Event], *, batch_size: int = 100) -> int:
    if type(batch_size) is not int or not 1 <= batch_size <= 1000:
        raise ValueError("invalid batch size")
    count = 0
    batch: list[tuple[int, str, int]] = []
    with connect() as conn:
        with conn.cursor() as cur:
            for event in events:
                validate(event)
                batch.append((event.event_id, event.source, event.value))
                if len(batch) == batch_size:
                    cur.executemany(
                        "INSERT INTO ch078_lab.events(event_id,source,value) VALUES (%s,%s,%s)",
                        batch,
                    )
                    count += len(batch)
                    batch.clear()
            if batch:
                cur.executemany(
                    "INSERT INTO ch078_lab.events(event_id,source,value) VALUES (%s,%s,%s)",
                    batch,
                )
                count += len(batch)
    return count

def copy_insert(events: Iterable[Event]) -> int:
    """COPY with typed rows; commits only when entire stream succeeds."""
    count = 0
    with connect() as conn:
        with conn.cursor() as cur:
            with cur.copy(
                "COPY ch078_lab.events (event_id, source, value) FROM STDIN"
            ) as copy:
                for event in events:
                    validate(event)
                    copy.write_row((event.event_id, event.source, event.value))
                    count += 1
    return count

def stream_events(*, batch_size: int = 64) -> Iterator[Event]:
    """Named server-side cursor: keeps client batch bounded but holds snapshot."""
    if type(batch_size) is not int or not 1 <= batch_size <= 1000:
        raise ValueError("invalid batch size")
    with connect() as conn:
        with conn.cursor(name="ch078_stream") as cur:
            cur.itersize = batch_size
            cur.execute("SELECT event_id,source,value FROM ch078_lab.events ORDER BY event_id")
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    yield Event(int(row["event_id"]), row["source"], int(row["value"]))

def explain_source(source: str) -> list[str]:
    """EXPLAIN ANALYZE executes SELECT against isolated lab table."""
    if not isinstance(source, str) or len(source) > 32:
        raise ValueError("invalid source")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '3s'")
            cur.execute(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                "SELECT event_id FROM ch078_lab.events WHERE source = %s",
                (source,),
            )
            return [row["QUERY PLAN"] for row in cur.fetchall()]

def count_rows() -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM ch078_lab.events")
            return int(cur.fetchone()["n"])

def timeout_demo() -> None:
    """Demonstrate statement timeout; PostgreSQL raises QueryCanceled (57014)."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '50ms'")
            cur.execute("SELECT pg_sleep(0.2)")

def rollback_demo() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ch078_lab.events(event_id,source,value) VALUES (%s,%s,%s)",
                (999999, "rollback", 1),
            )
            raise LabError("simulate error before COMMIT")

if __name__ == "__main__":
    print("Run unittest against an approved disposable PostgreSQL database")
\`\`\`

## 4. Complete tests — test_pg_performance.py
\`\`\`python
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from psycopg import errors

from pg_performance import (
    Event, LabError, batch_insert, copy_insert, count_rows,
    explain_source, rollback_demo, setup, stream_events,
    teardown, test_dsn, timeout_demo, validate,
)

class OfflineTests(unittest.TestCase):
    def test_guard(self):
        with patch.dict(os.environ, {"CH078_ALLOW_DESTRUCTIVE_TESTS": "NO"}, clear=True):
            with self.assertRaises(LabError):
                test_dsn()
    def test_invalid_event_id(self):
        with self.assertRaises(ValueError):
            validate(Event(0,"pg",1))
    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            validate(Event(1,"pg",-1))
    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate(Event(1,"pg",True))
    def test_invalid_source(self):
        with self.assertRaises(ValueError):
            validate(Event(1,"",1))
    def test_invalid_batch_size(self):
        with self.assertRaises(ValueError):
            list(stream_events(batch_size=0))
            # stream_events is a generator: validation happens at iteration.
    def test_explain_source_invalid(self):
        with self.assertRaises(ValueError):
            explain_source("x"*33)

@unittest.skipUnless(
    os.environ.get("CH078_ALLOW_DESTRUCTIVE_TESTS") == "YES"
    and bool(os.environ.get("CH078_TEST_DSN")),
    "requires approved disposable PostgreSQL DSN and destructive-test guard",
)
class PostgreSQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup()
    @classmethod
    def tearDownClass(cls):
        teardown()
    def setUp(self):
        from pg_performance import connect
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE ch078_lab.events")

    def test_batch_insert(self):
        self.assertEqual(batch_insert((Event(i,"postgresql",i) for i in range(1,8)),batch_size=3),7)
        self.assertEqual(count_rows(),7)

    def test_copy_insert(self):
        self.assertEqual(copy_insert((Event(i,"kafka",i) for i in range(1,11))),10)
        self.assertEqual(count_rows(),10)

    def test_streaming_batches(self):
        batch_insert((Event(i,"es",i) for i in range(1,251)),batch_size=50)
        result=list(stream_events(batch_size=17))
        self.assertEqual(len(result),250)
        self.assertEqual(result[0].event_id,1)
        self.assertEqual(result[-1].event_id,250)

    def test_copy_rollback_on_invalid_row(self):
        def rows():
            yield Event(1,"pg",1)
            yield Event(2,"pg",-1)
        with self.assertRaises(ValueError):
            copy_insert(rows())
        self.assertEqual(count_rows(),0)

    def test_batch_rollback_on_duplicate(self):
        with self.assertRaises(errors.UniqueViolation):
            batch_insert([Event(1,"pg",1),Event(1,"pg",2)],batch_size=1)
        self.assertEqual(count_rows(),0)

    def test_explain_analyze_buffers(self):
        batch_insert([Event(1,"pg",1)])
        lines=explain_source("pg")
        plan="\\n".join(lines)
        self.assertIn("Execution Time",plan)
        self.assertIn("Buffers",plan)

    def test_statement_timeout(self):
        with self.assertRaises(errors.QueryCanceled) as caught:
            timeout_demo()
        self.assertEqual(caught.exception.sqlstate,"57014")

    def test_rollback(self):
        with self.assertRaises(LabError):
            rollback_demo()
        self.assertEqual(count_rows(),0)

    def test_parameterized_filter(self):
        batch_insert([Event(1,"pg",1)])
        self.assertTrue(explain_source("' OR 1=1 --"))
        self.assertEqual(count_rows(),1)

if __name__=="__main__":
    unittest.main()
\`\`\`

## 5. Run locally
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q pg_performance.py test_pg_performance.py
# Default offline guard/unit tests; PostgreSQL integration tests skipped.
python -m unittest -v test_pg_performance.py
\`\`\`
For an approved disposable database only:
\`\`\`bash
# Provision dedicated PostgreSQL test role/database and verify endpoint first.
export CH078_TEST_DSN='postgresql://test_user:REPLACE_ME@127.0.0.1:5432/ch078_disposable'
export CH078_ALLOW_DESTRUCTIVE_TESTS=YES
python -m unittest -v test_pg_performance.py
\`\`\`
Avoid storing real passwords in shell history; use a secret provider or restricted local environment file. For remote PostgreSQL enforce \`sslmode=verify-full\` and trusted root certificates. Windows PowerShell uses \`$env:CH078_TEST_DSN=...\` and \`$env:CH078_ALLOW_DESTRUCTIVE_TESTS="YES"\`.

## 6. Incident drills
1. Compare \`executemany\` versus COPY throughput with equal row counts.
2. Stream 250 rows in batches of 17; inspect bounded client batches.
3. Return invalid row mid-COPY; verify full rollback.
4. Trigger duplicate primary key during batched insert; verify rollback.
5. Run EXPLAIN ANALYZE BUFFERS and compare actual/estimated rows.
6. Inject statement timeout and classify SQLSTATE 57014.
7. Simulate failure before COMMIT and verify rollback.
8. Attempt SQL injection as bound source value.
9. Run huge eager fetch as a **disposable extension** and compare RSS.
10. Keep a named cursor open and observe \`xact_start\`.
11. Cause slow scan by removing index in disposable DB.
12. Compare keyset versus OFFSET pagination.
13. Measure COPY-induced WAL and replica lag in a disposable replica lab.
14. Examine temp-file spill in a controlled workload.
15. Simulate pool saturation under parallel exports.
16. Simulate network loss during COMMIT; reconcile batch IDs.
17. Observe stale planner stats after large inserts.
18. Test lock timeout against a deliberately blocked row.
19. Tune batch size for p95 latency and memory.
20. Roll back unsafe query/ingest settings and validate SLO.

Exercises 9–20 are guided extensions; the automated suite covers 1–8.

## 7. Diagnostic SQL (approved read-only use)
\`\`\`sql
SELECT pid, state, wait_event_type, wait_event,
       now()-xact_start AS transaction_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start;

SELECT datname, temp_files, temp_bytes, deadlocks
FROM pg_stat_database
ORDER BY temp_bytes DESC;

SELECT relname, n_live_tup, n_dead_tup, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
\`\`\`

## 8. CI template
\`\`\`yaml
name: chapter-078-postgresql
on: workflow_dispatch
jobs:
  offline:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify extracted files
        run: |
          test -f pg_performance.py
          test -f test_pg_performance.py
          test -f requirements.txt
      - name: Install
        run: python -m pip install -r requirements.txt
      - name: Guard tests
        run: python -m unittest -v test_pg_performance.OfflineTests
\`\`\`
Template only. Extract Markdown code blocks into source files, pin reviewed action SHAs and dependencies. Enable a separate disposable PostgreSQL CI service only after security review.

## 9. Runbooks
**Query regression:** capture sanitized EXPLAIN/BUFFERS, compare statistics and plans, validate indexes on isolated data before change.

**Memory pressure:** replace eager result materialization with named cursors, cap batch size and monitor transaction age.

**COPY lag:** throttle ingest, inspect WAL/checkpoints/replica lag and ensure downstream freshness.

**Timeouts:** distinguish connect, lock, statement and overall job deadlines; reconcile ambiguous writes.

**Rollback:** restore approved batch/query settings, rerun integration tests and verify memory, latency and replication SLOs.

## 10. 100-point assessment
| Category | Points |
|---|---:|
| Query plans and EXPLAIN ANALYZE BUFFERS | 20 |
| psycopg batch inserts and COPY | 20 |
| Named cursors and memory efficiency | 20 |
| Timeout/rollback safety | 15 |
| Integration tests and incident drills | 15 |
| Security, CI and runbooks | 10 |

**Pass:** at least 90/100 and independently executed PostgreSQL integration tests against a verified disposable database. Publishing the lab does not prove execution.
