# Chapter 011 — Prometheus Architecture and Deployment Hands-on Lab

**Scope:** Local Docker Compose training stack with a synthetic Python exporter. No production deployment. Requires Docker Compose plugin and Python 3.10+.

## Prepare files

Copy the five complete configuration/code blocks from [Chapter 011](../011-prometheus-architecture-data-model-scraping-production-deployment-fundamentals.md) into:

```text
chapter011/
  compose.yaml
  prometheus.yml
  demo/
    Dockerfile
    metrics_server.py
  tests/
    test_lab.py
```

## Validate

```bash
cd chapter011
python3 -m unittest discover -s tests -v
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

After 15–30 seconds:

```bash
curl --fail --silent http://127.0.0.1:9090/-/ready
curl --fail --silent 'http://127.0.0.1:9090/api/v1/query?query=up'
curl --fail --silent 'http://127.0.0.1:9090/api/v1/targets'
```

Expected: two scrape targets UP and ten static tests passing.

## Twelve hands-on failure drills

1. Stop the demo exporter with `docker compose stop demo`; observe `up{job="demo"} == 0`.
2. Restart demo with `docker compose start demo`; confirm recovery.
3. Change demo port in an isolated copy; inspect scrape errors.
4. Set an incorrect metrics path; inspect HTTP status.
5. Explain DNS discovery failure.
6. Explain TLS handshake failure.
7. Explain authentication failure.
8. Explain duplicate target labels.
9. Identify unbounded label risk.
10. Explain counter reset behavior.
11. Explain retention/disk pressure.
12. Design an absence alert for missing targets.

Use a disposable local stack for drills; do not alter production configuration.

## PromQL acceptance

```promql
up
scrape_duration_seconds{job="demo"}
demo_uptime_seconds
rate(demo_requests_total[2m])
```

## Cleanup

```bash
docker compose down
```

Do not use `-v` unless intentional deletion of the training TSDB volume is approved.

## Evidence

```text
UTC / operator / Docker version:
Prometheus image version:
10 static tests:
Compose validation:
Prometheus readiness:
Target count and up status:
PromQL screenshots or query output:
12 drills and recovery:
Security/retention/HA review:
RCA / COA / reviewer:
```

**Acceptance:** two targets scrape, static tests pass, negative exporter failure is observed and recovery documented. Production validation is separate.
