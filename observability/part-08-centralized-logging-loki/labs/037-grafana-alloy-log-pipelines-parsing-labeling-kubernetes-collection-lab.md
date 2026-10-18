# Chapter 037 — Alloy Pipelines and Kubernetes Collection Lab

**Part 08 — Centralized Logging with Loki.** Copy all YAML/HCL, JSON and Python blocks from [Chapter 037](../037-grafana-alloy-log-pipelines-parsing-labeling-kubernetes-collection.md) into:

```text
chapter037/
  docker-compose.yml
  loki-config.yaml
  config.alloy
  logs/app.log
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/pipeline_gate.py
  tests/test_pipeline_gate.py
```

## Offline acceptance

```bash
cd chapter037
python3 scripts/pipeline_gate.py fixtures/healthy.json
if python3 scripts/pipeline_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected healthy PASS, degraded FAIL, 24 tests PASS.

## Local integration

```bash
mkdir -p logs
printf '{"level":"info","message":"synthetic checkout","trace_id":"trace-demo"}\n' > logs/app.log
docker compose config
docker compose up -d
curl -fsS http://127.0.0.1:3100/ready
curl -fsSG --data-urlencode 'query={service="orders-api"}' http://127.0.0.1:3100/loki/api/v1/query_range
docker compose down
```

## Twelve negative drills

1. Wildcard namespace. 2. Missing RBAC approval. 3. Missing tenant review. 4. Missing redaction review. 5. Pod UID label. 6. Request ID label. 7. Stream budget exceeded. 8. Ingestion budget exceeded. 9. Missing rollback. 10. Loki unavailable. 11. Alloy unavailable. 12. File source inaccessible.

## DBRE incident game day

After EKS node rotation, log collection stops and a volatile label change creates too many Loki streams. Restore stable labels, confirm source access and recover query results. Never test on production without an approved change.

## Evidence

```text
UTC / operator / environment:
Healthy/degraded gate / 24 tests:
Loki readiness / LogQL results:
RBAC / privacy / budgets:
12 drills / rollback / reviewer:
```

Actual Kubernetes log collection and sensitive-data redaction require separate verification.
