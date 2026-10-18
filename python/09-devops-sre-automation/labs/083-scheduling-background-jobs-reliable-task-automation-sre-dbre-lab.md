# Chapter 083 — Scheduling, Background Jobs and Reliable Task Automation Lab

**Python 3.11+ | SQLite | sched | asyncio | APScheduler 3.x**

## Safety, files and prerequisites
This is a disposable, local-only scheduler simulation. It does not launch production cron jobs or alter system services. Code blocks are complete source files; extract them into one \`ch083/\` directory before execution.

\`\`\`text
ch083/
  requirements.txt
  scheduler_lab.py
  test_scheduler_lab.py
\`\`\`

### requirements.txt
\`\`\`text
APScheduler>=3.10,<4
\`\`\`
APScheduler 3.x is explicitly required; version 4 APIs differ. For production, pin a reviewed exact version and dependency hashes.

## scheduler_lab.py
\`\`\`python
"""Local-only reliable job ledger and scheduler demonstration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sched
import sqlite3
import time
from typing import Callable

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  run_key TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK(status IN ('running','succeeded','failed')),
  owner TEXT NOT NULL,
  lease_until REAL NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  result TEXT,
  updated_at TEXT NOT NULL
);
"""

class LeaseBusy(RuntimeError): pass
class PermanentFailure(RuntimeError): pass
class TransientFailure(RuntimeError): pass

def connect(path: Path) -> sqlite3.Connection:
    conn=sqlite3.connect(path,timeout=2,isolation_level=None)
    conn.execute("PRAGMA busy_timeout=2000")
    conn.execute(SCHEMA)
    return conn

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def claim(conn: sqlite3.Connection, run_key: str, owner: str,
          *, now: float, lease_seconds: float=30) -> bool:
    """Claim a run; False means already completed. Lease expiry permits recovery.

    SQLite BEGIN IMMEDIATE serializes writers on this local database. This is not
    a distributed fencing protocol and is unsafe for non-idempotent external effects.
    """
    if not run_key or len(run_key)>128 or not owner or len(owner)>64:
        raise ValueError("invalid run key or owner")
    if lease_seconds<=0 or lease_seconds>3600:
        raise ValueError("invalid lease")
    conn.execute("BEGIN IMMEDIATE")
    try:
        row=conn.execute(
            "SELECT status,owner,lease_until FROM jobs WHERE run_key=?",
            (run_key,)
        ).fetchone()
        if row and row[0]=="succeeded":
            conn.execute("COMMIT")
            return False
        if row and row[0]=="running" and row[2]>now:
            raise LeaseBusy("job lease still active")
        if row:
            conn.execute("""
              UPDATE jobs SET status='running',owner=?,lease_until=?,
              attempts=attempts+1,updated_at=? WHERE run_key=?
            """,(owner,now+lease_seconds,utc_now(),run_key))
        else:
            conn.execute("""
              INSERT INTO jobs(run_key,status,owner,lease_until,attempts,updated_at)
              VALUES (?,'running',?,?,1,?)
            """,(run_key,owner,now+lease_seconds,utc_now()))
        conn.execute("COMMIT")
        return True
    except Exception:
        conn.execute("ROLLBACK")
        raise

def finish(conn: sqlite3.Connection, run_key: str, owner: str,
           result: str, *, now: float) -> bool:
    """Conditional completion while the worker still owns an unexpired lease."""
    cur=conn.execute("""
      UPDATE jobs SET status='succeeded',result=?,lease_until=0,updated_at=?
      WHERE run_key=? AND owner=? AND status='running' AND lease_until>?
    """,(result,utc_now(),run_key,owner,now))
    return cur.rowcount==1

def fail(conn: sqlite3.Connection, run_key: str, owner: str,
         *, now: float) -> bool:
    cur=conn.execute("""
      UPDATE jobs SET status='failed',lease_until=0,updated_at=?
      WHERE run_key=? AND owner=? AND status='running' AND lease_until>?
    """,(utc_now(),run_key,owner,now))
    return cur.rowcount==1

def run_idempotent(conn: sqlite3.Connection, run_key: str, owner: str,
                   operation: Callable[[], str], *, now: float) -> str:
    if not claim(conn,run_key,owner,now=now):
        return "duplicate"
    try:
        result=operation()
        if not isinstance(result,str):
            raise PermanentFailure("operation must return a string")
        if not finish(conn,run_key,owner,result,now=now):
            raise LeaseBusy("lease lost before commit")
        return "succeeded"
    except Exception:
        fail(conn,run_key,owner,now=now)
        raise

def retry_transient(fn: Callable[[], str], *, attempts: int=3,
                    delay: Callable[[float],None]=time.sleep) -> str:
    if type(attempts) is not int or not 1<=attempts<=5:
        raise ValueError("invalid retry budget")
    for index in range(attempts):
        try:
            return fn()
        except TransientFailure:
            if index+1==attempts:
                raise
            delay(min(0.2,0.01*(2**index)))
    raise AssertionError("unreachable")

def sched_demo() -> list[str]:
    """Deterministic in-memory scheduling with an injected virtual clock."""
    clock=[0.0]
    def advance(seconds: float) -> None:
        clock[0]+=seconds
    queue=sched.scheduler(timefunc=lambda:clock[0],delayfunc=advance)
    events=[]
    queue.enter(3,1,events.append,argument=("third",))
    queue.enter(1,1,events.append,argument=("first",))
    queue.run()
    return events

async def asyncio_demo() -> list[int]:
    semaphore=asyncio.Semaphore(2)
    results=[]
    async def worker(n: int) -> None:
        async with semaphore:
            await asyncio.sleep(0)
            results.append(n)
    await asyncio.gather(*(worker(n) for n in range(4)))
    return sorted(results)

def apscheduler_demo() -> str:
    """Inspect a pinned APScheduler 3.x job without starting background threads."""
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler=BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: None, trigger="interval", seconds=60, id="ch083-heartbeat",
        replace_existing=True,max_instances=1,coalesce=True,
        misfire_grace_time=30,
    )
    jobs=scheduler.get_jobs()
    return jobs[0].id

def summarize(conn: sqlite3.Connection) -> dict:
    rows=conn.execute("SELECT status,COUNT(*) FROM jobs GROUP BY status").fetchall()
    return dict(rows)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--database",type=Path,required=True)
    parser.add_argument("--run-key",default="local-demo-001")
    args=parser.parse_args()
    if not args.database.parent.is_dir():
        parser.error("database parent directory must exist")
    with connect(args.database) as conn:
        outcome=run_idempotent(
            conn,args.run_key,"local-worker",
            lambda:"verified",now=time.time()
        )
        print(json.dumps({"outcome":outcome,"counts":summarize(conn)},sort_keys=True))
\`\`\`

## test_scheduler_lab.py
\`\`\`python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scheduler_lab import (
    LeaseBusy,PermanentFailure,TransientFailure,apscheduler_demo,
    asyncio_demo,claim,connect,fail,finish,retry_transient,
    run_idempotent,sched_demo,summarize,
)

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.db=Path(self.temp.name)/"jobs.db"
        self.conn=connect(self.db)
    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_sched_order(self):
        self.assertEqual(sched_demo(),["first","third"])
    def test_asyncio_bounded_tasks(self):
        self.assertEqual(asyncio.run(asyncio_demo()),[0,1,2,3])
    def test_apscheduler_three_api(self):
        self.assertEqual(apscheduler_demo(),"ch083-heartbeat")
    def test_claim(self):
        self.assertTrue(claim(self.conn,"job-1","worker",now=100))
    def test_active_lease_denies_overlap(self):
        claim(self.conn,"job-1","worker-a",now=100)
        with self.assertRaises(LeaseBusy):
            claim(self.conn,"job-1","worker-b",now=101)
    def test_expired_lease_recovery(self):
        claim(self.conn,"job-1","worker-a",now=100,lease_seconds=5)
        self.assertTrue(claim(self.conn,"job-1","worker-b",now=106))
    def test_stale_owner_cannot_finish(self):
        claim(self.conn,"job-1","worker-a",now=100,lease_seconds=5)
        claim(self.conn,"job-1","worker-b",now=106)
        self.assertFalse(finish(self.conn,"job-1","worker-a","bad",now=107))
        self.assertTrue(finish(self.conn,"job-1","worker-b","ok",now=107))
    def test_success_idempotent(self):
        self.assertEqual(run_idempotent(self.conn,"job-1","worker",lambda:"ok",now=100),"succeeded")
        self.assertEqual(run_idempotent(self.conn,"job-1","worker",lambda:"again",now=101),"duplicate")
    def test_failed_job_recoverable(self):
        with self.assertRaises(PermanentFailure):
            run_idempotent(self.conn,"job-1","worker",lambda:(_ for _ in ()).throw(PermanentFailure()),now=100)
        self.assertEqual(run_idempotent(self.conn,"job-1","worker",lambda:"ok",now=101),"succeeded")
    def test_invalid_run_key(self):
        with self.assertRaises(ValueError):
            claim(self.conn,"","worker",now=100)
    def test_invalid_lease(self):
        with self.assertRaises(ValueError):
            claim(self.conn,"job","worker",now=100,lease_seconds=0)
    def test_finish_requires_owner(self):
        claim(self.conn,"job","worker",now=100)
        self.assertFalse(finish(self.conn,"job","stranger","bad",now=101))
    def test_finish_requires_unexpired_lease(self):
        claim(self.conn,"job","worker",now=100,lease_seconds=1)
        self.assertFalse(finish(self.conn,"job","worker","late",now=102))
    def test_fail_conditional(self):
        claim(self.conn,"job","worker",now=100)
        self.assertTrue(fail(self.conn,"job","worker",now=101))
    def test_summary(self):
        run_idempotent(self.conn,"job","worker",lambda:"ok",now=100)
        self.assertEqual(summarize(self.conn),{"succeeded":1})
    def test_retry_transient(self):
        calls=[]
        def fn():
            calls.append(1)
            if len(calls)<3: raise TransientFailure()
            return "ok"
        self.assertEqual(retry_transient(fn,delay=lambda _:None),"ok")
        self.assertEqual(len(calls),3)
    def test_retry_exhaustion(self):
        with self.assertRaises(TransientFailure):
            retry_transient(lambda:(_ for _ in ()).throw(TransientFailure()),attempts=2,delay=lambda _:None)
    def test_permanent_not_retried(self):
        with self.assertRaises(PermanentFailure):
            retry_transient(lambda:(_ for _ in ()).throw(PermanentFailure()))
    def test_invalid_retry_budget(self):
        with self.assertRaises(ValueError):
            retry_transient(lambda:"ok",attempts=0)
    def test_sql_parameter_binding(self):
        key="' OR 1=1 --"
        self.assertTrue(claim(self.conn,key,"worker",now=100))
        self.assertEqual(summarize(self.conn),{"running":1})

if __name__=="__main__":
    unittest.main()
\`\`\`

## Run locally
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q scheduler_lab.py test_scheduler_lab.py
python -m unittest -v test_scheduler_lab.py
mkdir -p ./ch083-workspace
python scheduler_lab.py --database ./ch083-workspace/jobs.db
python scheduler_lab.py --database ./ch083-workspace/jobs.db
# First run: succeeded; second: duplicate
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`New-Item -ItemType Directory -Force ch083-workspace\`, \`py -m unittest -v test_scheduler_lab.py\`.

## Incident drills
**Automated:** schedule ordering; asyncio fan-out; APScheduler configuration; active lease contention; expired lease recovery; stale owner rejection; duplicate replay; permanent failure; transient retry; retry exhaustion; invalid run key; invalid lease; invalid retry budget; conditional completion; SQL injection-safe binding.

**Guided only:** DST skip/repeat; clock skew; multiple scheduler nodes; database crash during commit; ambiguous external side effect; persistent PostgreSQL job store; Kubernetes CronJob duplicate execution; missed-run catch-up storm; stuck lease recovery; poison queue; graceful SIGTERM; telemetry alerts.

## Production limitations
The SQLite ledger demonstrates transactional claims on one local database. A lease expiry can allow a second worker while the first is still executing. \`finish\` validates owner and expiry but **does not implement a monotonically increasing fencing token**. Do not use this lab to control destructive or externally non-idempotent operations. APScheduler's in-memory job store is deliberately not persisted; only the business run ledger is persisted. The lab does not start the APScheduler background scheduler or verify real cron/DST behavior.

## CI template (not installed)
\`\`\`yaml
name: chapter-083-scheduler
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m pip install -r requirements.txt
      - run: python -m unittest -v test_scheduler_lab.py
\`\`\`
Extract source files into the expected working directory, pin reviewed dependency versions and action SHAs, then enable in approved CI.

## Troubleshooting and runbooks
**Missed jobs:** compare UTC due timestamp with last-success watermark and scheduler status; bounded catch-up only. **Duplicates:** reconcile by run key, verify side effects, suspend unsafe writers. **Stuck lease:** verify owner health, expiry and protected-resource fencing before recovery. **Retry storm:** reduce workers and backoff, quarantine poison jobs. **Scheduler upgrade:** verify APScheduler major version and restore definitions from version-controlled configuration.

## 100-point final assessment
| Category | Points |
|---|---:|
| sched and asyncio timing | 15 |
| Cron/APScheduler concepts and version safety | 15 |
| SQLite job persistence and idempotency | 25 |
| Lease handling, recovery and concurrency limitations | 20 |
| Retry policy and incident exercises | 10 |
| Tests, observability and runbooks | 15 |
| **Total** | **100** |

Pass target ≥90 with independently executed tests and explicit documentation of production limitations. Publishing the Markdown does not mean tests or CI ran.
