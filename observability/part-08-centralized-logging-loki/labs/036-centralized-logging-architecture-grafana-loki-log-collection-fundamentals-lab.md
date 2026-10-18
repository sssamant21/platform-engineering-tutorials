# Chapter 036 — Loki Centralized Logging and Log Collection Hands-on Lab

**Part 08 — Centralized Logging with Loki.** Offline governance and optional disposable Loki/Alloy stack.

## 1. Project layout

Copy the complete blocks from [Chapter 036](../036-centralized-logging-architecture-grafana-loki-log-collection-fundamentals.md):

```text
chapter036/
  docker-compose.yml
  loki-config.yaml
  config.alloy
  logs/app.log
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/log_gate.py
  tests/test_log_gate.py
```

## 2. Offline policy validation

```bash
cd chapter036
python3 scripts/log_gate.py fixtures/healthy.json
if python3 scripts/log_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, 27 tests PASS.

## 3. Optional local logging integration

```bash
mkdir -p logs
printf '{"level":"info","message":"synthetic order processed","request_id":"req-001"}\n' > logs/app.log
docker compose config
docker compose up -d
curl -fsS http://127.0.0.1:3100/ready
curl -fsSG --data-urlencode 'query={service="orders-api"}' http://127.0.0.1:3100/loki/api/v1/query_range
docker compose logs --tail=100 alloy
docker compose down
```

## 4. Twelve failure drills

1. Loki unavailable.
2. Alloy source path wrong.
3. File unreadable.
4. Push endpoint wrong.
5. Log timestamp invalid.
6. Request ID promoted to stream label.
7. Stream budget exceeded.
8. Ingestion budget exceeded.
9. Retention not approved.
10. Redaction review missing.
11. RBAC review missing.
12. Rollback missing.

## 5. DBRE incident tabletop

During PostgreSQL query slowness, logs disappear after a cardinality regression. Restore stable stream labels, preserve correlation IDs in log bodies, validate ingestion and correlate with database/host metrics.

## 6. Evidence

```text
UTC / operator / environment:
Loki readiness / Alloy logs / query:
Healthy/degraded gate / 27 tests:
12 negative drills:
Stream and ingestion budgets:
Incident analysis / rollback / reviewer:
```

**Acceptance:** offline gate and tests pass; live ingestion, query behavior, redaction and access control require separate verification.
