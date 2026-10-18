# Chapter 021 — Grafana Installation, Provisioning and Dashboard Foundations Lab

**Part 05 — Grafana Dashboards and Visualization.** Offline Python 3.10+ governance validation; optional Docker Compose with approved local Prometheus.

## 1. Project structure

Copy the complete Compose, datasource, provider, dashboard, gate and test blocks from [Chapter 021](../021-grafana-architecture-installation-data-sources-enterprise-dashboard-foundations.md) into:

```text
chapter021/
  docker-compose.yml
  .env                            # local only; do not commit
  provisioning/datasources/prometheus.yml
  provisioning/dashboards/provider.yml
  provisioning/dashboards/json/sre-foundations.json
  dashboards/sre-foundations.json
  scripts/dashboard_gate.py
  tests/test_dashboard_gate.py
```

Copy `dashboards/sre-foundations.json` to the provisioning `json/` folder.

## 2. Offline gate

```bash
cd chapter021
python3 scripts/dashboard_gate.py dashboards/sre-foundations.json provisioning/datasources/prometheus.yml provisioning/dashboards/provider.yml
python3 -m unittest discover -s tests -v
```

Expected: PASS and 20 tests PASS.

## 3. Optional isolated Docker deployment

```bash
printf 'GRAFANA_ADMIN_PASSWORD=%s\n' 'replace-with-strong-local-secret' > .env
chmod 600 .env
docker compose config
docker compose up -d
curl -fsS http://127.0.0.1:3000/api/health
docker compose logs --tail=100 grafana
```

Prometheus at the configured URL must exist for live panels. Verify Docker host routing; do not expose port 3000 publicly. After the lab, `docker compose down` stops containers; `down -v` deletes the local Grafana data volume and should only be used after confirming no data is needed.

## 4. Twelve negative drills

1. Invalid dashboard UID.
2. Duplicate panel ID.
3. Missing panel title.
4. Missing PromQL expression.
5. Wrong datasource UID.
6. Excessively long query.
7. Unexpected datasource URL.
8. Provisioning set editable.
9. Missing datasource proxy mode.
10. Refresh too aggressive.
11. Missing dashboard panels.
12. Prometheus unreachable (optional network drill).

## 5. Production SRE/DBRE tabletop

A Grafana dashboard shows no PostgreSQL targets after a datasource change. Investigate UID drift, network reachability, variable selection, scrape target inventory, RBAC and dashboard provisioning. Restore a known-good provisioned dashboard and document incident ownership.

## 6. Evidence and acceptance

```text
UTC / operator / environment:
Dashboard and datasource UIDs:
Local port and auth policy:
Gate result / 20 tests:
12 negative drills:
Optional Grafana health and Prometheus reachability:
RCA / rollback / reviewer:
```

**Acceptance:** offline governance gate and 20 tests pass; dashboard identity, access boundaries and no-data behavior are understood. Live deployment is not implied.
