# Chapter 079 — Python Database Migrations, Schema Evolution and Operational Automation

**Part 08 — APIs, Networking and Databases | Python 3.11+ | SQLAlchemy 2 | Alembic | PostgreSQL**

## Outcomes
Design versioned schema changes using Alembic, SQLAlchemy and PostgreSQL; deploy backward-compatible expand–migrate–contract changes; assess online DDL lock risks; test upgrades and downgrades; automate migration gates; and operate incident-safe rollbacks. The companion lab provides an executable local SQLite smoke profile and an **explicitly opt-in disposable PostgreSQL profile** for database-specific validation.

## Architecture
\`\`\`text
Git migration review -> static checks -> disposable upgrade/downgrade tests
 -> preflight backups / compatibility / capacity / lock monitoring
 -> Alembic revision -> PostgreSQL transactional DDL where supported
 -> application dual-read/write / backfill / cutover
 -> contract after rollback window -> audit trail and SLO checks
\`\`\`

## 1. Migration fundamentals
A schema migration is a versioned change to tables, indexes, constraints, data shape or database objects. Application deployment and database migration are separate release steps. Use forward-only, reviewed revisions where rollback cannot be guaranteed; preserve compatibility until all old application versions are drained. Alembic stores applied revision state in \`alembic_version\`, but that table does not prove a migration's data correctness.

## 2. SQLAlchemy and Alembic
SQLAlchemy's \`MetaData\`, \`Table\`, \`Column\`, constraints and indexes describe schema. Alembic's \`env.py\` configures the migration context and \`target_metadata\`. \`alembic revision --autogenerate\` proposes changes, **not** a production-safe migration. Review inferred drops, renames, type changes, defaults, constraints and data transformations. Use \`alembic upgrade head\`, \`alembic current\`, \`alembic history\`, and \`alembic downgrade\` only with an approved rollback plan.

## 3. Expand–migrate–contract
Example: rename \`patients.full_name\` to \`display_name\`.
1. **Expand:** add nullable \`display_name\`; old clients continue using \`full_name\`.
2. **Migrate:** deploy compatible code, backfill in small idempotent batches with checkpoints, validate row counts and null ratios.
3. **Cutover:** switch reads to new column with feature flags; observe errors and replica lag.
4. **Contract:** only after old versions and rollback window are gone, enforce NOT NULL if justified, remove old reads/writes, and drop legacy column in a separately approved release.

Never combine a destructive drop with an application rollout that still needs the old column.

## 4. PostgreSQL online DDL and locks
PostgreSQL DDL takes locks, even when execution is fast. \`ALTER TABLE ADD COLUMN\` can be metadata-only for some defaults and versions but still takes an ACCESS EXCLUSIVE lock. \`CREATE INDEX CONCURRENTLY\` avoids blocking ordinary writes for much of its operation, but **cannot run inside a transaction block** and can leave an invalid index after failure. \`DROP INDEX CONCURRENTLY\` has restrictions too. Validate lock compatibility, disk headroom, index build time, replica lag and transaction age. Set approved \`lock_timeout\` and \`statement_timeout\`; do not increase global timeouts casually.

## 5. Data migrations and backfills
Use stable primary-key ranges and small transactions, avoid large OFFSET scans, checkpoint progress and throttle by replication lag/IOPS. Backfills should be idempotent, restartable and observable. Consider \`FOR UPDATE SKIP LOCKED\` only when work partitioning semantics support it. Record processed rows, errors and lag without logging PII.

## 6. Transactional DDL and downgrade limits
PostgreSQL supports transactional DDL for many operations, but not every command. SQLite has different DDL and locking behavior; its tests are smoke tests, not PostgreSQL proof. A downgrade may be structurally possible but unable to recover dropped data. For irreversible changes, favor restore or forward-fix plans, rehearsed backups and explicit approval rather than promising automatic rollback.

## 7. CI/CD and change governance
Pipeline stages: syntax/format/lint, Alembic history consistency, migration dry-run against disposable clone, upgrade test, app compatibility tests, downgrade test where reversible, performance/lock rehearsal, approval, production canary and post-deploy validation. Ensure only one migration runner per environment through orchestration/advisory locking; avoid concurrent Alembic upgrades from every app pod.

## 8. Production incidents
1. Long transaction blocks \`ALTER TABLE\` and queues writes.
2. New NOT NULL constraint fails on legacy null rows.
3. Autogenerate proposes dropping a renamed column.
4. Rolling deployment mixes old and new schema clients.
5. Backfill overloads WAL and replica lag.
6. \`CREATE INDEX CONCURRENTLY\` fails and leaves invalid index.
7. Index build runs out of disk space.
8. Migration retries after ambiguous commit.
9. Concurrent migration runners race.
10. Application uses a column before expansion completes.
11. Default expression rewrites a large table.
12. Constraint validation scans too much data.
13. Downgrade cannot restore dropped values.
14. PostgreSQL failover interrupts migration.
15. Schema drift exists between staging and production.
16. Alembic revision graph has multiple heads.
17. Secret exposure in migration logs.
18. A rollback deploy restores old code but not old schema.

## 9. Troubleshooting
| Signal | Cause | Response |
|---|---|---|
| Waiting DDL | Conflicting locks | Inspect \`pg_locks\` and blockers; cancel only by approval |
| Invalid index | Interrupted concurrent build | Inspect \`pg_index.indisvalid\`; approved cleanup/retry |
| Multiple Alembic heads | Parallel revision branches | Review and merge migration history |
| NOT NULL violation | Incomplete backfill | Validate data, resume safe batches |
| Replica lag | Large migration/WAL | Throttle backfill and monitor lag |
| Downgrade data loss | Destructive migration | Use restore/forward-fix strategy |
| Lock timeout | Migration lock budget exceeded | Retry during approved window after resolving blockers |
| Drift | Untracked schema changes | Compare catalog to versioned expected state |

## 10. Production runbooks
**Preflight:** confirm owner approval, current Alembic revision, tested backup/restore, replica health, free disk, active long transactions, expected locks, rollout compatibility and rollback decision points.

**Blocked migration:** stop additional runners, inspect lock graph and transaction age, cancel or defer only through incident procedure, then rerun on disposable clone.

**Failed concurrent index:** inspect validity, check disk/replica lag and plan approved drop/rebuild outside transaction.

**Backfill pressure:** pause or throttle worker, preserve checkpoint, confirm data consistency and restart with smaller batches.

**Rollback:** distinguish app rollback, schema downgrade, forward-fix and PITR; select based on reversibility, verify data and audit change.

## 11. Lab
[Chapter 079 — Alembic, Expand–Contract and Schema Migration SRE/DBRE Lab](labs/079-alembic-schema-migrations-expand-contract-sre-dbre-lab.md) includes full project files, Alembic revisions, automated smoke and PostgreSQL integration tests, incident drills, runbooks and a 100-point assessment.

**Next proposed:** Chapter 080 — Python APIs, Networking and Databases Production Integration Capstone.
