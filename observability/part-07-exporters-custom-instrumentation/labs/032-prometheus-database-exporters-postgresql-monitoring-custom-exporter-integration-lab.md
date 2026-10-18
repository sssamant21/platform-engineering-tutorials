# Chapter 032 — PostgreSQL Database Exporter and Custom Metrics Lab

**Part 07 — Exporters and Custom Instrumentation.** Python 3.10+ offline governance; optional disposable PostgreSQL/Prometheus Docker stack.

## 1. Project layout

Copy Compose, Prometheus YAML and four JSON/Python blocks from [Chapter 032](../032-prometheus-database-exporters-postgresql-monitoring-custom-exporter-integration.md) into:

```text
chapter032/
  docker-compose.yml
  prometheus.yml
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/db_exporter_gate.py
  tests/test_db_exporter_gate.py
```

## 2. Offline validation

```bash
cd chapter032
python3 scripts/db_exporter_gate.py fixtures/healthy.json
if python3 scripts/db_exporter_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 26 tests PASS.

## 3. Optional local integration

```bash
docker compose config
docker compose run --rm --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose up -d
curl -fsS http://127.0.0.1:9187/metrics | head -n 25
curl -fsS http://127.0.0.1:9090/api/v1/targets
docker compose logs --tail=100 postgres-exporter
docker compose down
```

The disposable Compose example uses a lab superuser; production requires a dedicated least-privilege role, TLS and secret management.

## 4. Twelve negative drills

1. Invalid DSN.
2. PostgreSQL down.
3. Exporter scrape timeout.
4. Monitoring role missing grants.
5. Monitoring role overly privileged.
6. Password exposed in source.
7. Custom query performs DELETE.
8. Custom query has multiple statements.
9. Query exceeds timeout.
10. Metric labels contain SQL text.
11. Metric series budget exceeded.
12. Exporter disappears during failover.

## 5. DBRE incident tabletop

A PostgreSQL primary fails over, exporter credentials fail on the new primary and a custom query causes additional load. Verify exporter versus database health, restore read-only credentials, remove expensive metrics and document rollback.

## 6. Evidence

```text
UTC / operator / environment:
PostgreSQL/exporter version:
Metrics endpoint / up / pg_up:
Monitoring grants / custom query review:
Healthy/degraded gate / 26 tests:
12 drills / optional Docker test:
Rollback / reviewer / score:
```

**Acceptance:** offline gate and 26 tests pass; live database monitoring and custom-query safety require separate integration review.
