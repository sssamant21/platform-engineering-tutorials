# Chapter 026 — Prometheus Alertmanager Installation and Notification Routing Lab

**Part 06 — Alertmanager and Alert Engineering.** Local Docker Compose with synthetic alerts and internal webhook, plus offline Python 3.10+ governance tests.

## 1. Files

Copy the complete Docker Compose, Prometheus config, rules, Alertmanager config, webhook, fixtures and Python scripts from [Chapter 026](../026-prometheus-alertmanager-architecture-installation-notification-routing-fundamentals.md) into:

```text
chapter026/
  docker-compose.yml
  prometheus.yml
  rules.yml
  alertmanager.yml
  webhook.py
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/policy_gate.py
  tests/test_policy_gate.py
```

## 2. Offline validation

```bash
cd chapter026
python3 scripts/policy_gate.py fixtures/healthy.json
if python3 scripts/policy_gate.py fixtures/degraded.json; then exit 1; fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and 24 tests PASS.

## 3. Optional local integration

```bash
docker compose config
docker compose run --rm --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose run --rm --entrypoint promtool prometheus check rules /etc/prometheus/rules.yml
docker compose run --rm --entrypoint amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
docker compose up -d
curl -fsS http://127.0.0.1:9090/api/v1/alerts
curl -fsS http://127.0.0.1:9093/api/v2/alerts
docker compose logs -f webhook
```

Allow at least the pending period and notification grouping delay. Verify receiver `dbre-test` in the webhook log. Stop with `docker compose down`; do not send synthetic alerts to production receivers.

## 4. Twelve failure drills

1. Prometheus Alertmanager target wrong.
2. Invalid Alertmanager YAML.
3. Receiver missing.
4. Child route receiver wrong.
5. Grouping omits cluster.
6. Repeat interval zero.
7. Broad silence.
8. Unsafe inhibition equality.
9. Unbounded label cardinality.
10. Webhook container unavailable.
11. Resolved event not delivered.
12. Alertmanager HA peer unavailable (tabletop).

## 5. DBRE incident tabletop

An expected PostgreSQL exporter disappears during failover, but `up == 0` does not detect it because the target is absent from discovery. Design a separate expected-target inventory alert. Test routing, missing-series handling, silence expiration and recovery notification using staging-only receivers.

## 6. Evidence

```text
UTC / operator / environment:
Prometheus rule status:
Alertmanager route / receiver / webhook receipt:
Healthy/degraded gate / 24 tests:
12 failure drills:
Silence and inhibition review:
Rollback / reviewer / score:
```

**Acceptance:** offline tests pass and degraded fixture fails. Live notification delivery and HA remain separate integration gates.
