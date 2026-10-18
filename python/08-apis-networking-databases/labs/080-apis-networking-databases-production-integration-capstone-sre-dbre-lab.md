# Chapter 080 — APIs, Networking and Databases Production Integration Capstone SRE/DBRE Lab

**Python 3.11+ | httpx | asyncio | SQLAlchemy 2 | Alembic | psycopg 3 optional**

## Project and execution contract
Build a loopback-only asynchronous collector that ingests service metrics from a synthetic HTTP endpoint into an Alembic-managed SQL database. SQLite runs by default; PostgreSQL is an opt-in disposable integration profile. All source files below are complete code blocks: extract each into the named file before executing. No GitHub Actions workflow is installed or enabled by this Markdown publication.

\`\`\`text
ch080/
  requirements.txt
  alembic.ini
  env.py
  versions/0001_observations.py
  collector.py
  test_capstone.py
\`\`\`

## 1. requirements.txt
\`\`\`text
httpx>=0.27,<1
SQLAlchemy>=2.0,<3
alembic>=1.13,<2
psycopg[binary]>=3.2,<4
\`\`\`
Pin exact reviewed dependency versions and hashes before deployment.

## 2. alembic.ini
\`\`\`ini
[alembic]
script_location = .
prepend_sys_path = .
sqlalchemy.url = sqlite:///placeholder.db
[loggers]
keys = root
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = WARN
formatter = generic
[formatter_generic]
format = %(levelname)s %(message)s
\`\`\`

## 3. env.py
\`\`\`python
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
target_metadata = None

def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    with engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    ).connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
\`\`\`

## 4. versions/0001_observations.py
\`\`\`python
"""Create operational observations.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "observations",
        sa.Column("event_id", sa.String(length=80), primary_key=True),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value >= 0", name="ck_observation_nonnegative"),
    )
    op.create_index("ix_observations_service", "observations", ["service"])

def downgrade():
    op.drop_index("ix_observations_service", table_name="observations")
    op.drop_table("observations")
\`\`\`
**Downgrade drops all observation data.** Only exercise on disposable databases. In production use an approved compatible forward-fix or backup/restore plan.

## 5. collector.py
\`\`\`python
"""Bounded, idempotent loopback API-to-database ingestion capstone."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import QueuePool

MAX_BODY = 4096

class ValidationError(ValueError):
    pass

class UpstreamError(RuntimeError):
    pass

@dataclass(frozen=True)
class Observation:
    event_id: str
    service: str
    value: int

@dataclass(frozen=True)
class Summary:
    attempted: int
    succeeded: int
    duplicates: int
    failed: int

def validate_payload(raw: bytes) -> Observation:
    if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
        raise ValidationError("invalid response size")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValidationError("invalid JSON") from exc
    if not isinstance(data, dict) or set(data) != {"event_id", "service", "value"}:
        raise ValidationError("unexpected JSON schema")
    event_id, service, value = data["event_id"], data["service"], data["value"]
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 80:
        raise ValidationError("invalid event_id")
    if not isinstance(service, str) or not 1 <= len(service) <= 64:
        raise ValidationError("invalid service")
    if type(value) is not int or value < 0:
        raise ValidationError("invalid value")
    return Observation(event_id, service, value)

def sqlite_engine(path: Path) -> Engine:
    return create_engine(
        "sqlite+pysqlite:///" + str(path.resolve()),
        poolclass=QueuePool, pool_size=2, max_overflow=0,
        pool_timeout=0.2, pool_pre_ping=True,
    )

def store(engine: Engine, item: Observation) -> bool:
    """Atomic insert, unique-key duplicate check, payload-conflict rejection."""
    if not isinstance(item, Observation):
        raise TypeError("Observation required")
    # Validate even for directly constructed Observation objects.
    validate_payload(json.dumps({
        "event_id": item.event_id, "service": item.service, "value": item.value
    }).encode())
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO observations(event_id,service,value)
                VALUES (:id,:service,:value)
            """), {"id":item.event_id, "service":item.service, "value":item.value})
        return True
    except IntegrityError:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT service,value FROM observations WHERE event_id=:id
            """), {"id":item.event_id}).mappings().first()
        if row is None or row["service"] != item.service or row["value"] != item.value:
            raise ValidationError("idempotency key conflict")
        return False

def export_batches(engine: Engine, *, size: int = 20):
    """Keyset pagination with bounded fetch size and short transactions."""
    if type(size) is not int or not 1 <= size <= 1000:
        raise ValueError("invalid batch size")
    last_id = ""
    while True:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT event_id,service,value FROM observations
                WHERE event_id > :last ORDER BY event_id LIMIT :size
            """), {"last":last_id,"size":size}).mappings().all()
        if not rows:
            break
        for row in rows:
            yield Observation(row["event_id"], row["service"], int(row["value"]))
        last_id = rows[-1]["event_id"]

def _loopback_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise ValueError("capstone fixture allows loopback HTTP only")
    if parsed.username or parsed.password or not parsed.port:
        raise ValueError("invalid fixture URL")

async def fetch_one(client: httpx.AsyncClient, url: str, token: str, *,
                    attempts: int = 3) -> Observation:
    _loopback_url(url)
    if not isinstance(token, str) or not token or attempts not in range(1, 6):
        raise ValueError("invalid token or retry budget")
    for index in range(attempts):
        try:
            response = await client.get(
                url, headers={"Authorization": "Bearer " + token},
            )
            if response.status_code in (429, 502, 503, 504):
                if index + 1 < attempts:
                    await asyncio.sleep(min(0.1, 0.01 * (2 ** index)))
                    continue
                raise UpstreamError("transient HTTP error exhausted")
            if response.status_code != 200:
                raise UpstreamError("nonretryable HTTP response")
            return validate_payload(response.content)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if index + 1 == attempts:
                raise UpstreamError("transport retries exhausted") from exc
            await asyncio.sleep(min(0.1, 0.01 * (2 ** index)))
    raise AssertionError("unreachable")

async def collect(urls: list[str], engine: Engine, token: str, *,
                  concurrency: int = 3) -> Summary:
    if type(concurrency) is not int or not 1 <= concurrency <= 20:
        raise ValueError("invalid concurrency")
    if len(urls) > 100:
        raise ValueError("too many fixture URLs")
    for url in urls:
        _loopback_url(url)
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(1.0, connect=0.5), limits=limits, trust_env=False,
    ) as client:
        async def worker(url):
            async with sem:
                try:
                    item = await fetch_one(client, url, token)
                    # Synchronous SQL is deliberate for the tiny lab. For production,
                    # offload blocking database calls or use a suitable async driver.
                    return "inserted" if store(engine, item) else "duplicate"
                except (UpstreamError, ValidationError, httpx.HTTPError):
                    return "failed"
        results = await asyncio.gather(*(worker(url) for url in urls))
    return Summary(
        attempted=len(results),
        succeeded=results.count("inserted"),
        duplicates=results.count("duplicate"),
        failed=results.count("failed"),
    )
\`\`\`

## 6. test_capstone.py
\`\`\`python
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from collector import (
    Observation, UpstreamError, ValidationError, collect,
    export_batches, fetch_one, sqlite_engine, store, validate_payload,
)

@contextmanager
def fixture_http():
    counts = {}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            counts[self.path] = counts.get(self.path, 0) + 1
            if self.headers.get("Authorization") != "Bearer lab-token":
                self.send_response(401)
                self.end_headers()
                return
            if self.path == "/unavailable":
                self.send_response(503)
                self.end_headers()
                return
            if self.path == "/flaky" and counts[self.path] == 1:
                self.send_response(503)
                self.end_headers()
                return
            if self.path == "/invalid":
                body = b"{not json"
            elif self.path == "/oversized":
                body = b"x" * 5000
            else:
                event_id = self.path.strip("/") or "default"
                body = json.dumps({
                    "event_id":event_id,"service":"postgresql","value":42
                }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1",0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), counts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def migration_config(url: str) -> Config:
    cfg = Config(str(Path(__file__).with_name("alembic.ini")))
    cfg.set_main_option("script_location", str(Path(__file__).parent))
    cfg.set_main_option("sqlalchemy.url", url.replace("%","%%"))
    return cfg

class CapstoneTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "capstone.db"
        self.url = "sqlite:///" + str(self.path)
        self.cfg = migration_config(self.url)
        command.upgrade(self.cfg, "head")
        self.engine = sqlite_engine(self.path)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_migration_version(self):
        with self.engine.connect() as conn:
            self.assertEqual(
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                "0001",
            )

    def test_idempotent_insert(self):
        item = Observation("e1","postgresql",42)
        self.assertTrue(store(self.engine,item))
        self.assertFalse(store(self.engine,item))

    def test_conflicting_duplicate(self):
        store(self.engine,Observation("e1","postgresql",42))
        with self.assertRaises(ValidationError):
            store(self.engine,Observation("e1","postgresql",99))

    def test_rollback_on_constraint(self):
        with self.assertRaises(ValidationError):
            store(self.engine,Observation("bad","postgresql",-1))
        self.assertEqual(list(export_batches(self.engine)),[])

    def test_parameterized_event_id(self):
        item = Observation("' OR 1=1 --","postgresql",1)
        store(self.engine,item)
        self.assertEqual(list(export_batches(self.engine)),[item])

    def test_bounded_export(self):
        for i in range(25):
            store(self.engine,Observation("id-%03d" % i,"postgresql",i))
        self.assertEqual(len(list(export_batches(self.engine,size=7))),25)

    def test_invalid_batch_size(self):
        with self.assertRaises(ValueError):
            list(export_batches(self.engine,size=0))

    def test_payload_validation(self):
        for raw in (b"not-json",b"[]",b'{"value":1}',b"x"*5000):
            with self.assertRaises(ValidationError):
                validate_payload(raw)

    def test_http_collect(self):
        with fixture_http() as (base, _):
            result = asyncio.run(collect(
                [base+"/e1",base+"/e2"],self.engine,"lab-token",concurrency=2
            ))
        self.assertEqual((result.attempted,result.succeeded,result.failed),(2,2,0))

    def test_duplicate_http_replay(self):
        with fixture_http() as (base, _):
            first = asyncio.run(collect([base+"/e1"],self.engine,"lab-token"))
            second = asyncio.run(collect([base+"/e1"],self.engine,"lab-token"))
        self.assertEqual(first.succeeded,1)
        self.assertEqual(second.duplicates,1)

    def test_transient_retry(self):
        with fixture_http() as (base, counts):
            result = asyncio.run(collect([base+"/flaky"],self.engine,"lab-token"))
        self.assertEqual(result.succeeded,1)
        self.assertEqual(counts["/flaky"],2)

    def test_exhausted_retry(self):
        with fixture_http() as (base, counts):
            result = asyncio.run(collect([base+"/unavailable"],self.engine,"lab-token"))
        self.assertEqual(result.failed,1)
        self.assertEqual(counts["/unavailable"],3)

    def test_unauthorized_not_retried(self):
        with fixture_http() as (base, counts):
            result = asyncio.run(collect([base+"/e1"],self.engine,"bad-token"))
        self.assertEqual(result.failed,1)
        self.assertEqual(counts["/e1"],1)

    def test_malformed_and_oversized(self):
        with fixture_http() as (base, _):
            result = asyncio.run(collect(
                [base+"/invalid",base+"/oversized"],self.engine,"lab-token"
            ))
        self.assertEqual(result.failed,2)

    def test_reject_external_network(self):
        with self.assertRaises(ValueError):
            asyncio.run(collect(
                ["https://example.com/metrics"],self.engine,"lab-token"
            ))

    def test_concurrency_validation(self):
        with self.assertRaises(ValueError):
            asyncio.run(collect([],self.engine,"lab-token",concurrency=0))

    def test_empty_batch(self):
        result=asyncio.run(collect([],self.engine,"lab-token"))
        self.assertEqual(result.attempted,0)

    def test_downgrade_on_empty_disposable_database(self):
        command.downgrade(self.cfg,"base")
        self.assertNotIn("observations",inspect(self.engine).get_table_names())

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 7. Execute default lab
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q collector.py env.py test_capstone.py versions
python -m unittest -v test_capstone.py
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_capstone.py\`. The HTTP fixture binds only to 127.0.0.1. If local loopback is prohibited by workstation policy, run on an approved development machine.

## 8. Optional PostgreSQL / psycopg 3 integration
**Disposable database only.** These checks are not run by the default suite. Explicitly verify the PostgreSQL host, database, user, privileges and TLS configuration. Never run on production or shared staging.

\`\`\`python
# Save as optional_postgres.py. Run only after verifying the isolated test DSN.
import os
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from alembic.config import Config

if os.environ.get("CH080_ALLOW_DESTRUCTIVE_TESTS") != "YES":
    raise RuntimeError("explicit destructive-test opt-in required")
url = os.environ.get("CH080_TEST_PG_URL", "")
if not url.startswith("postgresql+psycopg://"):
    raise RuntimeError("SQLAlchemy psycopg test URL required")
# Only a verified EMPTY dedicated disposable PostgreSQL database.
cfg = Config("alembic.ini")
cfg.set_main_option("sqlalchemy.url", url.replace("%","%%"))
command.upgrade(cfg,"head")
engine = create_engine(
    url, pool_size=2, max_overflow=0, pool_timeout=1,
    pool_pre_ping=True, connect_args={"connect_timeout":3},
)
try:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO observations(event_id,service,value)
            VALUES (:id,:service,:value)
        """), {"id":"pg-canary","service":"postgresql","value":42})
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT value FROM observations WHERE event_id=:id"),
            {"id":"pg-canary"},
        ).scalar_one() == 42
finally:
    engine.dispose()
# Intentionally NO automatic downgrade: review and clean up disposable DB manually.
\`\`\`
For remote PostgreSQL, enforce \`sslmode=verify-full\` and approved CA roots. The optional code is a smoke test for PostgreSQL connectivity and schema migration, not a full deadlock/serialization/COPY performance test. Production-grade bulk loading, async DB calls and concurrent migrations are extensions.

## 9. Production hardening checklist
- Replace the synthetic loopback fixture with approved HTTPS endpoints, trust store, secret manager and egress allowlist.
- Validate bearer token rotation, SNI/hostname, DNS and certificate expiry.
- Use bounded work queues, request deadlines, jittered backoff and rate-limit-aware admission.
- Offload blocking SQL calls from the event loop or adopt a reviewed async PostgreSQL driver.
- Add OpenTelemetry traces and Prometheus metrics with redaction and sampling.
- Add PostgreSQL \`INSERT ... ON CONFLICT\` and immutable idempotency records for concurrent writers.
- Add migration serialization, expand–contract compatibility tests and backup restore rehearsals.
- Add PostgreSQL COPY, named cursor and SQLSTATE 40001/40P01 tests on disposable infrastructure.
- Reconcile unknown COMMIT outcomes; never retry writes blindly.
- Run a security review and validate SLOs before production use.

## 10. Incident simulation matrix
| Drill | Automation |
|---|---|
| Successful HTTP ingestion | Automated |
| HTTP 503 recovery | Automated |
| Persistent 503 retry exhaustion | Automated |
| HTTP 401 fail-fast | Automated |
| Invalid JSON and oversized body | Automated |
| Duplicate event replay | Automated |
| Conflicting idempotency key | Automated |
| Bounded keyset export | Automated |
| Migration upgrade/downgrade on disposable SQLite | Automated |
| SQL injection value binding | Automated |
| TLS certificate mismatch | Guided |
| DNS outage and network policy | Guided |
| Database pool exhaustion | Guided |
| PostgreSQL deadlock / 40001 | Guided |
| Ambiguous COMMIT reconciliation | Guided |
| Alembic migration race | Guided |
| COPY-induced WAL/replica lag | Guided |
| Large result set and named cursor | Guided |
| Credential rotation | Guided |
| Disaster recovery and rollback | Guided |

## 11. CI workflow template
\`\`\`yaml
name: chapter-080-capstone
on: workflow_dispatch
jobs:
  local-integration:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify extracted lab
        run: |
          test -f collector.py
          test -f test_capstone.py
          test -f env.py
          test -f alembic.ini
          test -f versions/0001_observations.py
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Test loopback integration
        run: python -m unittest -v test_capstone.py
\`\`\`
**Template only:** extract files into a runnable directory, pin reviewed action SHAs and dependency hashes, and enable through normal CI review. No workflow was deployed by this publication.

## 12. Runbooks
**API incident:** distinguish 401, 429, 5xx, timeout and DNS/TLS failures; cap fan-out and retries, validate upstream health, roll back unsafe concurrency.

**DB incident:** check pool budget, transaction age, SQLSTATE, locks, \`pg_stat_activity\`, WAL and replica lag; reconcile ambiguous writes by event ID.

**Migration incident:** stop duplicate runners, inspect Alembic head and PostgreSQL blockers, use approved compatible rollback or forward-fix.

**Security incident:** revoke exposed tokens, verify redacted logs, restore TLS trust and audit access.

**Recovery:** restore approved config, rerun smoke and PostgreSQL canaries, verify latency, error budget, memory and data correctness; document RCA and follow-up owners.

## 13. Final 100-point assessment
| Area | Points |
|---|---:|
| Secure HTTP and asyncio concurrency | 20 |
| SQLAlchemy, transactions and idempotency | 20 |
| Alembic migration and schema safety | 15 |
| PostgreSQL/psycopg operational design | 15 |
| Bounded batching and streaming | 10 |
| Automated tests and fault injection | 10 |
| Observability, runbooks and rollback | 10 |
| **Total** | **100** |

**Acceptance:** score ≥90, all default tests pass, PostgreSQL profile validated on a verified disposable database, no secrets in logs, and operational sign-off for any production adaptation. Publishing the Markdown is not evidence that tests or production checks were executed.
