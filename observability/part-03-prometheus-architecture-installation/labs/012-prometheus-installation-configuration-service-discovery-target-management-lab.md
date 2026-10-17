# Chapter 012 — Prometheus Installation, Service Discovery and Target Management Lab

**Scope:** Disposable local Docker Compose training environment. Requires Docker and Python 3.10+.

## 1. Prepare

Copy the seven complete configuration and code blocks from [Chapter 012](../012-prometheus-installation-configuration-service-discovery-target-management.md) into:

```text
chapter012/
  compose.yaml
  prometheus.yml
  targets/services.json
  demo/Dockerfile
  demo/metrics_server.py
  scripts/validate_targets.py
  tests/test_discovery.py
```

## 2. Validate and deploy

```bash
cd chapter012
python3 scripts/validate_targets.py targets/services.json
python3 -m unittest discover -s tests -v
docker compose config --quiet
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  prom/prometheus:v2.55.1 check config /etc/prometheus/prometheus.yml
docker compose up -d --build
docker compose ps
```

Wait 15–30 seconds for scrapes, then:

```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS 'http://127.0.0.1:9090/api/v1/targets'
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=up'
```

## 3. Twelve failure-injection drills

1. Stop exporter and observe DOWN.
2. Restart exporter and verify UP.
3. Change file-SD target to an invalid port.
4. Reject an invalid host.
5. Reject duplicate targets.
6. Reject an extra high-cardinality label.
7. Reject a missing owner/team.
8. Reject empty target groups.
9. Inspect scrape timeout failures.
10. Test absence query.
11. Compare target relabeling and metric relabeling.
12. Document a rollback for a bad config.

Do not run fault injections against production. Preserve a clean baseline and capture before/after evidence.

## 4. Production review

Review service discovery RBAC, TLS/auth, HA, TSDB capacity, retention, missing-target alerting, sample limits and owner mapping. Document the difference between training stack success and production readiness.

## 5. Evidence

```text
UTC / operator / Docker and Prometheus versions:
Target policy validation:
12 unit tests:
Promtool config check:
Compose validation:
Two targets UP:
12 failure drills:
Security and retention review:
Rollback / RCA / COA:
```

## 6. Cleanup

```bash
docker compose down
```

Named volumes are preserved. Never use `down -v` without explicit permission to delete training data.
