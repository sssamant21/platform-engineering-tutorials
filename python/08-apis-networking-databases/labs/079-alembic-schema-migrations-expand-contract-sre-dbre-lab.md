# Chapter 079 — Alembic, Expand–Contract and Schema Migration SRE/DBRE Lab

**Python 3.11+ | SQLAlchemy 2.x | Alembic | SQLite smoke tests | Optional disposable PostgreSQL**

## Safety and project layout
The default tests create a temporary SQLite file and never touch external databases. The optional PostgreSQL profile is **explicitly opt-in** and must use a dedicated disposable database/role. Never use production or shared staging. The lab demonstrates reversible expansion and backfill; the destructive contract phase is a reviewed exercise, not automatically executed.

\`\`\`text
ch079/
  requirements.txt
  alembic.ini
  env.py
  versions/
    0001_create_patients.py
    0002_expand_display_name.py
  migration_ops.py
  test_migrations.py
\`\`\`

## 1. requirements.txt
\`\`\`text
SQLAlchemy>=2.0,<3
alembic>=1.13,<2
psycopg[binary]>=3.2,<4
\`\`\`
Use hash-pinned, reviewed versions in production.

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
The database URL is set programmatically in tests. Do not put production DSNs in this file.

## 3. env.py
\`\`\`python
"""Alembic environment; database URL supplied by approved caller."""
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
target_metadata = None

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    with engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    ).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
\`\`\`

## 4. versions/0001_create_patients.py
\`\`\`python
"""Create patients base schema.

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
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
    )

def downgrade():
    op.drop_table("patients")
\`\`\`

## 5. versions/0002_expand_display_name.py
\`\`\`python
"""Expand schema with backward-compatible display_name.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        "patients",
        sa.Column("display_name", sa.String(length=120), nullable=True),
    )

def downgrade():
    op.drop_column("patients", "display_name")
\`\`\`
Downgrading revision 0002 **drops data stored only in display_name**. The lab tests downgrade only before meaningful new-column data exists, or on a disposable database. A production downgrade requires explicit data-loss assessment.

## 6. migration_ops.py
\`\`\`python
"""Idempotent bounded backfill and safe migration checks."""
from __future__ import annotations

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

class MigrationError(RuntimeError): pass

def make_engine(url: str) -> Engine:
    if not isinstance(url, str) or not url:
        raise ValueError("database URL required")
    return create_engine(url, pool_pre_ping=True)

def seed_legacy(engine: Engine, *, count: int = 25) -> None:
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("invalid count")
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO patients(id,full_name) VALUES (:id,:name)"),
            [{"id":i, "name":f"Patient-{i}"} for i in range(1,count+1)],
        )

def backfill(engine: Engine, *, batch_size: int = 10) -> int:
    """Bounded, restartable primary-key backfill; each batch commits."""
    if type(batch_size) is not int or not 1 <= batch_size <= 1000:
        raise ValueError("invalid batch size")
    if "display_name" not in {c["name"] for c in inspect(engine).get_columns("patients")}:
        raise MigrationError("expand migration not applied")
    updated = 0
    last_id = 0
    while True:
        with engine.begin() as conn:
            rows = conn.execute(text("""
                SELECT id FROM patients
                WHERE id > :last_id AND display_name IS NULL
                ORDER BY id LIMIT :limit
            """), {"last_id":last_id,"limit":batch_size}).scalars().all()
            if not rows:
                break
            conn.execute(text("""
                UPDATE patients SET display_name=full_name
                WHERE id IN :ids AND display_name IS NULL
            """).bindparams(__import__("sqlalchemy").bindparam("ids", expanding=True)),
            {"ids":rows})
            updated += len(rows)
            last_id = rows[-1]
    return updated

def validate_expansion(engine: Engine) -> tuple[int,int]:
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM patients")).scalar_one()
        missing = conn.execute(
            text("SELECT COUNT(*) FROM patients WHERE display_name IS NULL")
        ).scalar_one()
        return int(total),int(missing)

def require_disposable_postgres() -> str:
    if os.environ.get("CH079_ALLOW_DESTRUCTIVE_TESTS") != "YES":
        raise MigrationError("destructive PostgreSQL tests not approved")
    url = os.environ.get("CH079_TEST_PG_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        raise MigrationError("explicit psycopg SQLAlchemy URL required")
    return url
\`\`\`

## 7. test_migrations.py
\`\`\`python
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from migration_ops import (
    MigrationError, backfill, make_engine, require_disposable_postgres,
    seed_legacy, validate_expansion,
)

def config_for(url: str) -> Config:
    cfg = Config(str(Path(__file__).with_name("alembic.ini")))
    cfg.set_main_option("script_location", str(Path(__file__).parent))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg

class SQLiteMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.url="sqlite:///" + str(Path(self.temp.name)/"lab.db")
        self.engine=make_engine(self.url)
        self.cfg=config_for(self.url)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_upgrade_backfill_idempotency(self):
        command.upgrade(self.cfg,"0001")
        seed_legacy(self.engine,count=25)
        command.upgrade(self.cfg,"head")
        self.assertEqual(backfill(self.engine,batch_size=7),25)
        self.assertEqual(backfill(self.engine,batch_size=7),0)
        self.assertEqual(validate_expansion(self.engine),(25,0))

    def test_expand_keeps_old_column(self):
        command.upgrade(self.cfg,"head")
        cols={c["name"] for c in inspect(self.engine).get_columns("patients")}
        self.assertEqual(cols,{"id","full_name","display_name"})

    def test_revision_tracking(self):
        command.upgrade(self.cfg,"head")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),"0002")

    def test_safe_downgrade_on_empty_database(self):
        command.upgrade(self.cfg,"head")
        command.downgrade(self.cfg,"0001")
        cols={c["name"] for c in inspect(self.engine).get_columns("patients")}
        self.assertEqual(cols,{"id","full_name"})

    def test_invalid_batch_size(self):
        with self.assertRaises(ValueError):
            backfill(self.engine,batch_size=0)

    def test_requires_expand_first(self):
        command.upgrade(self.cfg,"0001")
        with self.assertRaises(MigrationError):
            backfill(self.engine)

    def test_legacy_write_compatibility(self):
        command.upgrade(self.cfg,"head")
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO patients(id,full_name) VALUES (1,'Legacy')"))
        self.assertEqual(validate_expansion(self.engine),(1,1))

    def test_guard(self):
        with patch.dict(os.environ,{"CH079_ALLOW_DESTRUCTIVE_TESTS":"NO"},clear=True):
            with self.assertRaises(MigrationError):
                require_disposable_postgres()

@unittest.skipUnless(
    os.environ.get("CH079_ALLOW_DESTRUCTIVE_TESTS")=="YES"
    and bool(os.environ.get("CH079_TEST_PG_URL")),
    "requires approved disposable PostgreSQL and explicit guard",
)
class PostgreSQLMigrationTests(unittest.TestCase):
    """Requires a dedicated EMPTY disposable database; Alembic uses public schema."""
    @classmethod
    def setUpClass(cls):
        cls.url=require_disposable_postgres()
        cls.cfg=config_for(cls.url)
        cls.engine=make_engine(cls.url)
        command.upgrade(cls.cfg,"head")

    @classmethod
    def tearDownClass(cls):
        # DROP TABLE via downgrade: only in verified dedicated empty test DB.
        try:
            command.downgrade(cls.cfg,"base")
        finally:
            cls.engine.dispose()

    def setUp(self):
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE patients"))

    def test_postgres_expand_backfill(self):
        seed_legacy(self.engine,count=12)
        self.assertEqual(backfill(self.engine,batch_size=5),12)
        self.assertEqual(validate_expansion(self.engine),(12,0))

    def test_postgres_idempotent_resume(self):
        seed_legacy(self.engine,count=5)
        self.assertEqual(backfill(self.engine,batch_size=2),5)
        self.assertEqual(backfill(self.engine,batch_size=2),0)

if __name__=="__main__":
    unittest.main()
\`\`\`

## 8. Execute
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q env.py migration_ops.py test_migrations.py versions
python -m unittest -v test_migrations.py
\`\`\`
The default run executes local SQLite smoke tests and skips PostgreSQL. For a **verified empty disposable PostgreSQL database**, set \`CH079_TEST_PG_URL\` to a SQLAlchemy psycopg URL and \`CH079_ALLOW_DESTRUCTIVE_TESTS=YES\`; then run the same test command. PostgreSQL tests use the public schema and downgrade to base: **never run on any database containing valuable objects**. Avoid pasting real credentials into shell history. Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_migrations.py\`.

## 9. Online DDL PostgreSQL extension (not automated)
Only on disposable PostgreSQL:
\`\`\`sql
-- Must be outside an explicit transaction block:
CREATE INDEX CONCURRENTLY IF NOT EXISTS patients_full_name_idx ON patients(full_name);
-- Inspect invalid indexes after interrupted concurrent builds:
SELECT indexrelid::regclass, indisvalid FROM pg_index WHERE NOT indisvalid;
\`\`\`
Review locks, free disk and rollback path. Concurrent index creation is not executed by the default lab. Use \`lock_timeout\` and \`statement_timeout\` under approved test settings.

## 10. Incident drills
1. Run upgrade to head and inspect Alembic version.
2. Seed old schema then expand.
3. Backfill in small primary-key batches.
4. Rerun backfill; verify idempotency.
5. Verify old clients can still write \`full_name\`.
6. Downgrade empty test database and inspect columns.
7. Block backfill before expand; verify failure.
8. Reject invalid batch size.
9. Simulate migration runner race (guided).
10. Create a long transaction that blocks DDL (guided).
11. Interrupt \`CREATE INDEX CONCURRENTLY\` and inspect validity (guided).
12. Measure WAL/replica lag during backfill (guided).
13. Simulate NOT NULL validation failure (guided).
14. Test Alembic multiple heads resolution (guided).
15. Review a misleading autogenerate rename/drop (guided).
16. Simulate failover during migration (guided).
17. Reconcile ambiguous migration commit (guided).
18. Rehearse app rollback without schema downgrade (guided).
19. Verify backup/restore plan (guided).
20. Record change evidence and post-deploy SLO (guided).

## 11. CI template
\`\`\`yaml
name: chapter-079-migrations
on: workflow_dispatch
jobs:
  sqlite-smoke:
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
          test -f alembic.ini
          test -f env.py
          test -f migration_ops.py
          test -f test_migrations.py
          test -f versions/0001_create_patients.py
          test -f versions/0002_expand_display_name.py
      - name: Install
        run: python -m pip install -r requirements.txt
      - name: Smoke tests
        run: python -m unittest -v test_migrations.py
\`\`\`
This is a template, not an enabled pipeline. Extract Markdown code blocks, pin reviewed action SHAs/dependency hashes and run only in approved CI.

## 12. Runbooks
**Preflight:** verify migration history, backups, compatibility, lock budget, replica lag and change approval.

**Blocked DDL:** inspect blockers and xact age, stop duplicate runners, resolve through approved incident process.

**Backfill overload:** pause, preserve checkpoint, throttle and verify counts.

**Invalid concurrent index:** inspect \`pg_index\`, schedule approved cleanup/rebuild.

**Rollback:** distinguish app rollback, safe downgrade, forward-fix and PITR; rehearse and document data-loss risks.

## 13. 100-point assessment
| Area | Points |
|---|---:|
| Alembic revision management | 20 |
| Expand–migrate–contract safety | 20 |
| Idempotent backfill and validation | 20 |
| PostgreSQL online DDL and locking | 15 |
| Automated tests and incident response | 15 |
| CI, rollback and governance | 10 |

**Pass:** at least 90/100 with tests independently executed. SQLite smoke tests do not validate PostgreSQL online DDL or locking. Publishing this lab does not establish execution.
