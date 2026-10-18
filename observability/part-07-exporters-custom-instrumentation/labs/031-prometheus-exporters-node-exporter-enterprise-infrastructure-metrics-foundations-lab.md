# Chapter 031 — Prometheus Exporters and Node Exporter Infrastructure Lab

**Part 07 — Exporters and Custom Instrumentation.** Python 3.10+ offline governance and optional isolated Docker Compose metrics stack.

## 1. Project layout

Copy the complete Compose, Prometheus YAML and four fixture/Python blocks from [Chapter 031](../031-prometheus-exporters-node-exporter-enterprise-infrastructure-metrics-foundations.md) into:

```text
chapter031/
  docker-compose.yml
  prometheus.yml
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/exporter_gate.py
  tests/test_exporter_gate.py
```

## 2. Offline validation

```bash
cd chapter031
python3 scripts/exporter_gate.py fixtures/healthy.json
if python3 scripts/exporter_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 26 tests PASS.

## 3. Optional local integration

```bash
docker compose config
docker compose run --rm --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose up -d
curl -fsS http://127.0.0.1:9100/metrics | head -n 20
curl -fsS http://127.0.0.1:9090/api/v1/targets
docker compose logs --tail=100 node-exporter
docker compose down
```

The containerized exporter does not provide full host visibility without reviewed host mounts/namespaces.

## 4. Twelve failure drills

1. Exporter process down.
2. Wrong scrape port.
3. Scrape timeout exceeds interval.
4. Metrics endpoint unavailable.
5. Collector missing.
6. Public bind address.
7. Missing security review.
8. Unbounded request ID label.
9. Series budget exceeded.
10. Missing target inventory.
11. Incorrect CPU rate query.
12. Missing rollback evidence.

## 5. DBRE incident tabletop

During Elasticsearch search slowness, a node has disk pressure but diskstats metrics disappear. Determine whether the collector is disabled, filesystem mount visibility is incomplete, or the scrape failed. Restore test metrics and validate a rollback.

## 6. Evidence

```text
UTC / operator / environment:
Exporter endpoint / scrape status:
CPU / memory / disk / network:
Healthy/degraded gate / 26 tests:
12 failure drills:
Optional Docker test / rollback / reviewer:
```

**Acceptance:** offline gate and 26 tests pass; live exporter scrape, host visibility and production security are separate acceptance gates.
