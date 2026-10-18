# Chapter 032 — Prometheus Database Exporters, PostgreSQL Monitoring and Custom Exporter Integration

**Part 07 — Exporters and Custom Instrumentation**  
**Audience:** SRE/DBRE, PostgreSQL administrators and observability engineers.  
**Prerequisites:** Chapter 031, PostgreSQL basics, Prometheus, Python 3.10+, optional Docker.  
**Objective:** Deploy PostgreSQL exporter metrics safely, analyze DB reliability signals, add reviewed custom queries, and validate privilege, performance and cardinality controls.

## 1. Database exporter architecture

```text
PostgreSQL stats catalogs/views
        |
read-only monitoring role
        |
postgres_exporter /metrics
        |
Prometheus scrape and TSDB
        |
PromQL -> Grafana -> Alertmanager
        |
DBRE incident triage and recovery
```

Postgres Exporter exposes PostgreSQL operational metrics to Prometheus. It does not replace query tracing, SQL plan inspection or PostgreSQL logs. A successful exporter scrape is not proof the database is healthy. Exporter metrics vary with exporter and PostgreSQL versions; verify actual metric names in `/metrics`.

## 2. Important PostgreSQL signals

| Area | Data source | Why it matters |
|---|---|---|
| Availability | exporter `pg_up` and Prometheus `up` | distinguish exporter from DB reachability |
| Connections | `pg_stat_activity`, `pg_stat_database` | saturation, pooling, long transactions |
| Transactions | `pg_stat_database` | commits, rollbacks, deadlocks |
| Storage | `pg_database_size`, filesystem | growth, free space, I/O |
| Replication | `pg_stat_replication`, `pg_stat_wal_receiver` | lag, receive/replay health |
| WAL | WAL/archiver stats | durability and archive backlog |
| Vacuum | `pg_stat_user_tables` | dead tuples, autovacuum |
| Query performance | `pg_stat_statements` when enabled | expensive statements and workload |

Cumulative PostgreSQL counters can reset; use rate/increase with care and account for database restarts or statistics resets.

## 3. Safe local PostgreSQL exporter lab

The following Compose stack is **local-only**, uses a throwaway password for demonstration and is not production-ready. Real deployments must use secret management, TLS, least-privilege monitoring roles, network policy and supported image versions.

### docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: lab-only-change-me
      POSTGRES_DB: observability
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d observability"]
      interval: 5s
      timeout: 3s
      retries: 20
    networks: [lab]
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    environment:
      DATA_SOURCE_NAME: "postgresql://postgres:lab-only-change-me@postgres:5432/observability?sslmode=disable"
    ports:
      - "127.0.0.1:9187:9187"
    depends_on:
      postgres:
        condition: service_healthy
    networks: [lab]
  prometheus:
    image: prom/prometheus:v2.55.1
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "127.0.0.1:9090:9090"
    networks: [lab]
networks:
  lab: {}
```

**Security distinction:** The lab uses the PostgreSQL superuser for convenience only. Do **not** carry this pattern into staging or production. The acceptance gate below requires a reviewed monitoring role; the Compose example is a disposable demonstration and does not satisfy that production gate.

### prometheus.yml

```yaml
global:
  scrape_interval: 30s
scrape_configs:
  - job_name: postgres
    scrape_timeout: 10s
    static_configs:
      - targets: ["postgres-exporter:9187"]
        labels:
          cluster: lab
          environment: staging
```

### Commands

```bash
docker compose config
docker compose run --rm --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose up -d
curl -fsS http://127.0.0.1:9187/metrics | head -n 25
curl -fsSG --data-urlencode 'query=up{job="postgres"}' http://127.0.0.1:9090/api/v1/query
curl -fsSG --data-urlencode 'query=pg_up' http://127.0.0.1:9090/api/v1/query
docker compose logs --tail=100 postgres-exporter
docker compose down
```

Pinned image tags are teaching examples; check upstream advisories and version compatibility before production.

## 4. Least-privilege monitoring role

A reviewed PostgreSQL deployment can use a dedicated login role with `pg_monitor` and narrower grants where possible. Validate the required privileges for the selected exporter version and custom queries.

```sql
CREATE ROLE metrics_reader LOGIN PASSWORD 'replace-with-secret-manager-value';
GRANT pg_monitor TO metrics_reader;
ALTER ROLE metrics_reader SET statement_timeout = '5s';
```

Provision credentials securely, avoid logging DSNs, use TLS, and limit connections. **Never put real passwords into Git.**

## 5. PromQL and DBRE triage

```promql
up{job="postgres"}
pg_up
rate(pg_stat_database_xact_commit[5m])
rate(pg_stat_database_xact_rollback[5m])
rate(pg_stat_database_deadlocks[5m])
```

These metric names depend on exporter mappings and PostgreSQL version. Validate names and label sets against the deployed `/metrics` endpoint. For capacity, compare sessions to configured connection limits and consider PgBouncer pooling, idle-in-transaction sessions, and replica lag.

## 6. Custom exporter queries: operational guardrails

Custom queries can increase database load. Prefer built-in metrics and low-cost aggregate queries. Require explicit review of SQL text, query plan, timeout, privilege scope, metric type and label cardinality. Avoid per-row, per-user, raw SQL text, patient identifiers and other unbounded labels. Custom query configuration differs across exporter versions; verify supported `queries.yaml` or extension mechanisms before use.

Illustrative read-only SQL:

```sql
SELECT count(*) AS sessions FROM pg_stat_activity;
SELECT pg_database_size(current_database()) AS bytes;
```

These are **SQL examples**, not a complete version-specific custom-query mapping.

## 7. Executable offline governance lab

The JSON below is **synthetic exporter policy metadata**, not native exporter configuration. The Python gate checks approved secret references, read-only query declarations, bounded labels, timeouts and series budgets. Its SQL checks are heuristic and **must not be used as a security boundary**; enforce database read-only privileges.

Create:

```text
chapter032/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/db_exporter_gate.py
  tests/test_db_exporter_gate.py
```

### fixtures/healthy.json

```json
{
  "environment": "staging",
  "owner": "dbre",
  "database": "postgresql",
  "exporter": "postgres_exporter",
  "version_reviewed": true,
  "least_privilege_reviewed": true,
  "secret_ref": "env:DATA_SOURCE_NAME",
  "scrape_verified": true,
  "rollback_tested": true,
  "sql_reviewed": true,
  "query_timeout_seconds": 5,
  "scrape_interval_seconds": 30,
  "scrape_timeout_seconds": 10,
  "labels": [
    "job",
    "instance",
    "cluster",
    "environment",
    "database"
  ],
  "metric_budget_series": 15000,
  "observed_series": 9000,
  "queries": [
    {
      "name": "db_sessions",
      "sql": "SELECT count(*) AS sessions FROM pg_stat_activity",
      "read_only": true,
      "returns_scalar": true
    },
    {
      "name": "db_size_bytes",
      "sql": "SELECT pg_database_size(current_database()) AS bytes",
      "read_only": true,
      "returns_scalar": true
    }
  ],
  "runbook": "https://example.org/runbooks/postgresql-exporter"
}
```

### fixtures/degraded.json

```json
{
  "environment": "staging",
  "owner": "dbre",
  "database": "postgresql",
  "exporter": "postgres_exporter",
  "version_reviewed": true,
  "least_privilege_reviewed": false,
  "secret_ref": "postgres://password@localhost",
  "scrape_verified": true,
  "rollback_tested": true,
  "sql_reviewed": true,
  "query_timeout_seconds": 40,
  "scrape_interval_seconds": 30,
  "scrape_timeout_seconds": 10,
  "labels": [
    "job",
    "instance",
    "cluster",
    "environment",
    "database",
    "query_text"
  ],
  "metric_budget_series": 15000,
  "observed_series": 25000,
  "queries": [
    {
      "name": "db_sessions",
      "sql": "DELETE FROM pg_stat_activity",
      "read_only": true,
      "returns_scalar": true
    },
    {
      "name": "db_size_bytes",
      "sql": "SELECT pg_database_size(current_database()) AS bytes",
      "read_only": true,
      "returns_scalar": true
    }
  ],
  "runbook": "https://example.org/runbooks/postgresql-exporter"
}
```

### scripts/db_exporter_gate.py

```python
#!/usr/bin/env python3
"""Offline DB exporter governance; SQL check is heuristic and not a SQL parser."""
import json,re,sys
from pathlib import Path
ALLOWED={"job","instance","cluster","environment","database","region","team"}
FORBIDDEN=re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY|CALL|DO)\b",re.I)
def check(p):
    e=[]
    if not isinstance(p,dict): return ["manifest must be object"]
    for k in ("environment","owner","database","exporter","runbook"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    if p.get("database")!="postgresql" or p.get("exporter")!="postgres_exporter": e.append("wrong exporter")
    for k in ("version_reviewed","least_privilege_reviewed","scrape_verified","rollback_tested","sql_reviewed"):
        if p.get(k) is not True: e.append("unverified "+k)
    secret=p.get("secret_ref")
    if not isinstance(secret,str) or not secret.startswith("env:"): e.append("unsafe secret reference")
    labels=p.get("labels")
    if not isinstance(labels,list) or not {"job","instance","cluster","environment","database"}.issubset(labels) or not set(labels).issubset(ALLOWED): e.append("unsafe labels")
    interval=p.get("scrape_interval_seconds");timeout=p.get("scrape_timeout_seconds");q=p.get("query_timeout_seconds")
    if type(interval) is not int or type(timeout) is not int or type(q) is not int or not 0<q<=timeout<interval<=300: e.append("invalid timing")
    budget=p.get("metric_budget_series");observed=p.get("observed_series")
    if type(budget) is not int or budget<=0 or type(observed) is not int or observed<0: e.append("invalid series budget")
    elif observed>budget: e.append("series budget exceeded")
    queries=p.get("queries")
    if not isinstance(queries,list) or not queries: e.append("missing queries");queries=[]
    seen=set()
    for i,query in enumerate(queries):
        prefix="query "+str(i)
        if not isinstance(query,dict): e.append(prefix+" invalid");continue
        name=query.get("name")
        if not isinstance(name,str) or not name or name in seen: e.append(prefix+" duplicate/missing name")
        else: seen.add(name)
        sql=query.get("sql")
        if not isinstance(sql,str) or not re.match(r"^\s*SELECT\b",sql,re.I) or FORBIDDEN.search(sql) or ";" in sql:
            e.append(prefix+" unsafe SQL")
        if query.get("read_only") is not True or query.get("returns_scalar") is not True: e.append(prefix+" unreviewed query")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 db_exporter_gate.py fixtures/healthy.json")
    try: findings=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit("input error: "+str(exc))
    print(json.dumps({"status":"FAIL" if findings else "PASS","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_db_exporter_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from db_exporter_gate import check
class DBExporterTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        p=copy.deepcopy(self.p);f(p);return check(p)
    def test_healthy(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda p:p.update(owner="")))
    def test_runbook(self): self.assertTrue(self.mutate(lambda p:p.update(runbook="")))
    def test_exporter(self): self.assertTrue(self.mutate(lambda p:p.update(exporter="other")))
    def test_version(self): self.assertTrue(self.mutate(lambda p:p.update(version_reviewed=False)))
    def test_privilege(self): self.assertTrue(self.mutate(lambda p:p.update(least_privilege_reviewed=False)))
    def test_scrape(self): self.assertTrue(self.mutate(lambda p:p.update(scrape_verified=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda p:p.update(rollback_tested=False)))
    def test_sql_review(self): self.assertTrue(self.mutate(lambda p:p.update(sql_reviewed=False)))
    def test_secret(self): self.assertTrue(self.mutate(lambda p:p.update(secret_ref="plaintext")))
    def test_labels(self): self.assertTrue(self.mutate(lambda p:p["labels"].append("query_text")))
    def test_missing_labels(self): self.assertTrue(self.mutate(lambda p:p.update(labels=["job"])))
    def test_timeout(self): self.assertTrue(self.mutate(lambda p:p.update(scrape_timeout_seconds=30)))
    def test_query_timeout(self): self.assertTrue(self.mutate(lambda p:p.update(query_timeout_seconds=20)))
    def test_interval(self): self.assertTrue(self.mutate(lambda p:p.update(scrape_interval_seconds=0)))
    def test_budget(self): self.assertTrue(self.mutate(lambda p:p.update(metric_budget_series=0)))
    def test_over_budget(self): self.assertTrue(self.mutate(lambda p:p.update(observed_series=20000)))
    def test_no_queries(self): self.assertTrue(self.mutate(lambda p:p.update(queries=[])))
    def test_duplicate(self): self.assertTrue(self.mutate(lambda p:p["queries"][1].update(name="db_sessions")))
    def test_delete(self): self.assertTrue(self.mutate(lambda p:p["queries"][0].update(sql="DELETE FROM users")))
    def test_select_delete(self): self.assertTrue(self.mutate(lambda p:p["queries"][0].update(sql="SELECT 1; DELETE FROM users")))
    def test_not_readonly(self): self.assertTrue(self.mutate(lambda p:p["queries"][0].update(read_only=False)))
    def test_not_scalar(self): self.assertTrue(self.mutate(lambda p:p["queries"][0].update(returns_scalar=False)))
    def test_valid_new_query(self): self.assertEqual(self.mutate(lambda p:p["queries"].append({"name":"db_up","sql":"SELECT 1 AS up","read_only":True,"returns_scalar":True})),[])
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter032
python3 scripts/db_exporter_gate.py fixtures/healthy.json
if python3 scripts/db_exporter_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded exporter manifest accepted"; exit 1
else
  echo "PASS: degraded exporter manifest rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **26 automated tests pass**.

## 8. Twenty-four hands-on exercises

1. Explain DB exporter pull model.
2. Configure dedicated monitoring role.
3. Review pg_monitor permissions.
4. Configure environment-secret DSN.
5. Start PostgreSQL lab container.
6. Start postgres_exporter.
7. Inspect /metrics endpoint.
8. Configure Prometheus scrape job.
9. Validate up metric.
10. Inspect pg_stat_activity.
11. Inspect connection saturation.
12. Inspect transaction counters.
13. Inspect deadlocks.
14. Inspect database size.
15. Inspect replication lag signals.
16. Review WAL activity.
17. Design read-only custom query.
18. Set statement timeout.
19. Check query execution cost.
20. Review metric cardinality.
21. Review exporter auth failures.
22. Run healthy policy gate.
23. Reject degraded fixture.
24. Run 26 tests and rollback.

## 9. Twenty-four production failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 01 | Exporter cannot authenticate | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 02 | DSN secret malformed | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 03 | PostgreSQL unavailable | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 04 | Wrong exporter port | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 05 | Prometheus target down | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 06 | Exporter scrape timeout | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 07 | Slow custom query | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 08 | Monitoring role too privileged | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 09 | Monitoring role insufficient privileges | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 10 | pg_stat_activity unavailable | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 11 | pg_stat_database resets | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 12 | Connection exhaustion | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 13 | Long-running transaction | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 14 | Deadlock surge | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 15 | Replication lag | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 16 | WAL archive failure | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 17 | Disk pressure | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 18 | Autovacuum lag | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 19 | High-cardinality query labels | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 20 | Exporter version mismatch | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 21 | SQL permission denied | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 22 | TLS certificate mismatch | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 23 | Custom query blocks database | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |
| 24 | Missing target after failover | Check PostgreSQL health, exporter logs, DSN, privilege, scrape and query cost |

## 10. Eight production runbooks

**A. Exporter down:** Check exporter process, DSN, PostgreSQL connectivity, scrape endpoint and logs.

**B. Authentication failure:** Validate secret reference, role, password rotation, pg_hba.conf and TLS.

**C. Slow metrics query:** Inspect pg_stat_activity, query plans, statement_timeout and exporter scrape duration.

**D. Connection saturation:** Compare active/idle sessions, max_connections, pooling and workload demand.

**E. Replication lag:** Review replica replay/receive positions, WAL generation, network and downstream pressure.

**F. Vacuum pressure:** Inspect dead tuples, autovacuum activity, long transactions and storage growth.

**G. Metric cardinality:** Audit query labels, dynamic identifiers, scrape sample count and series budget.

**H. Rollback:** Revert exporter version/custom query, validate read-only access, scrape health and dashboards.

## 11. DBRE incident simulation

During PostgreSQL failover, the exporter reports `pg_up == 0` while the exporter endpoint itself remains scrapeable. A custom query begins timing out and replication lag rises. Distinguish exporter availability from database availability, validate monitoring credentials on the new primary, disable the expensive query and verify metrics recover. Run only in a disposable/staging environment.

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| PostgreSQL metrics and exporter architecture | 20 |
| Local deployment and PromQL | 20 |
| Least privilege, SQL cost and cardinality | 20 |
| Offline governance and 26 tests | 20 |
| Troubleshooting, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: least-privilege production design, safe secret handling, query timeouts, bounded labels, scrape evidence and rollback.

## 13. Evidence worksheet

```text
UTC / operator / environment:
PostgreSQL and exporter versions:
Monitoring role / grants / TLS:
Scrape target / up / pg_up:
Connection / replication / WAL / vacuum:
Custom query plan / timeout / series count:
Healthy/degraded gate / 26 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 032 executable PostgreSQL exporter lab](labs/032-prometheus-database-exporters-postgresql-monitoring-custom-exporter-integration-lab.md).

**Next:** Chapter 033 — Prometheus Application Exporters, Blackbox Exporter and Service Availability Monitoring.
