# Chapter 033 — Blackbox Exporter and Service Availability Hands-on Lab

**Part 07 — Exporters and Custom Instrumentation.** Disposable Docker HTTP probe, offline policy validation, optional staging drills.

## 1. Materialize the lab

Copy all complete blocks from [Chapter 033](../033-prometheus-application-exporters-blackbox-exporter-service-availability-monitoring.md) into:

```text
chapter033/
  docker-compose.yml
  blackbox.yml
  prometheus.yml
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/probe_gate.py
  tests/test_probe_gate.py
```

## 2. Offline acceptance

```bash
cd chapter033
python3 scripts/probe_gate.py fixtures/healthy.json
if python3 scripts/probe_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected healthy PASS, degraded FAIL and 27 tests PASS.

## 3. Optional Docker integration

```bash
docker compose config
docker compose up -d
curl -fsSG --data-urlencode 'module=http_2xx' --data-urlencode 'target=http://demo-app:8080/' http://127.0.0.1:9115/probe
curl -fsSG --data-urlencode 'query=probe_success' http://127.0.0.1:9090/api/v1/query
docker compose down
```

Only localhost ports are published. Do not enable public access to the `/probe` endpoint.

## 4. Twelve failure drills

1. Stop demo-app and observe failed probe.
2. Stop blackbox and observe scrape failure.
3. Change target to a nonexistent host.
4. Configure incorrect HTTP status expectations.
5. Reduce probe timeout.
6. Make scrape timeout shorter than probe timeout.
7. Attempt unapproved target in policy fixture.
8. Attempt metadata endpoint in fixture.
9. Add high-cardinality user ID label.
10. Exceed series budget.
11. Disable SSRF review.
12. Remove rollback approval.

## 5. DBRE incident simulation

An API health endpoint passes while PostgreSQL is unavailable. Compare `probe_success`, application 5xx and database availability. Improve the synthetic journey and document how alerts distinguish service and telemetry failure.

## 6. Evidence

```text
UTC / operator / environment:
Target and probe module:
probe_success / up / probe_duration_seconds:
Healthy/degraded gate / 27 tests:
12 negative drills:
Incident analysis / rollback / reviewer:
```

**Acceptance:** offline gate and tests pass; live probe and synthetic paging require separate integration verification.
