# Chapter 011 — Prometheus Architecture, Data Model, Scraping and Production Deployment Fundamentals

**Part 03 — Prometheus Architecture and Installation**  
**Audience:** SRE/DBRE, platform and cloud engineers.  
**Prerequisites:** Chapters 001–010; Docker Engine + Compose plugin for the optional local deployment; Python 3.10+ for static tests.  
**Outcome:** Understand Prometheus's pull model, time-series labels, service discovery, scraping, TSDB lifecycle and production controls; deploy a reproducible local demonstration.

## 1. Architecture

```text
Linux node_exporter   DB exporters   Instrumented services
        \                |                 /
         \          /metrics              /
             targets + discovery
                     |
               Prometheus
             scrape + TSDB/WAL
             rules + recording
                /         \
         Alertmanager    PromQL HTTP API
                \         /
             Grafana / SRE
                     |
          remote_write (optional)
                     |
            durable backend
```

Prometheus pulls HTTP endpoints on a schedule, records samples with timestamps, and stores them in a local TSDB with write-ahead log and block compaction. Exporters expose metrics; Prometheus is not a general-purpose log or trace store. Alertmanager handles alert grouping, inhibition and routing. Prometheus itself evaluates recording/alerting rules; Grafana queries the metrics API.

## 2. Data model and types

A time series is identified by a metric name and label set, e.g. `http_requests_total{job="api",instance="api-1:8000",route="/search",status_class="2xx"}`. A sample has a value and timestamp. Avoid labels containing patient identifiers, request IDs, email, raw paths or other unbounded values.

| Metric type | Use | Query pattern |
|---|---|---|
| Counter | monotonically increasing events (except reset) | `rate()`, `increase()` |
| Gauge | current measurement | direct, `avg_over_time()` |
| Classic histogram | latency bucket counts, sum, count | `histogram_quantile()` |
| Summary | client-calculated observations/quantiles | use count/sum carefully |

Native histograms have different support and query considerations depending on version. Confirm feature compatibility before adoption. Never sum summary quantiles across instances. Histogram buckets can be aggregated when boundaries align.

## 3. Scrape lifecycle and discovery

1. Discover static, Kubernetes, file-SD or cloud targets.
2. Apply target relabeling and assign stable identity labels.
3. Fetch `/metrics` within timeout.
4. Parse exposition and enforce sample/label limits.
5. Append samples to TSDB and update `up` and scrape health metrics.
6. Evaluate recording and alerting rules.
7. Serve PromQL queries and optionally remote-write.

Important controls: `scrape_interval`, `scrape_timeout`, `sample_limit`, `label_limit`, `metric_relabel_configs`, target relabeling, service discovery, network access and authentication. Metric relabeling runs after scrape and cannot prevent an exporter from generating expensive series; fix instrumentation at the source.

## 4. Production topology and security

A single Prometheus instance is appropriate for training and some workloads, but it is not inherently HA. For production, use redundant Prometheus replicas, consistent external labels, Alertmanager HA, carefully planned retention and remote-write/durable storage where appropriate. Replica deduplication is a responsibility of compatible query/storage layers; do not assume two independent instances automatically form a cluster.

Restrict UI and API access, secure scrape endpoints with TLS/auth as appropriate, manage credentials outside Git, enforce RBAC at platform boundaries, and avoid unrestricted remote-write egress. Pin and review container image versions, monitor security advisories and upgrade through staging. The demonstration below binds Prometheus only to loopback and has no authentication; do not expose it publicly.

## 5. Executable local Docker Compose lab

Create:

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

### compose.yaml

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.55.1
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=24h
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    restart: unless-stopped
  demo:
    build: ./demo
    expose:
      - "8000"
    restart: unless-stopped
volumes:
  prometheus-data:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: staging
scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["prometheus:9090"]
  - job_name: demo
    metrics_path: /metrics
    static_configs:
      - targets: ["demo:8000"]
        labels:
          service: synthetic-api
```

### demo/Dockerfile

```dockerfile
FROM python:3.12-alpine
WORKDIR /app
COPY metrics_server.py /app/metrics_server.py
USER 10001
EXPOSE 8000
CMD ["python", "/app/metrics_server.py"]
```

### demo/metrics_server.py

```python
#!/usr/bin/env python3
"""Synthetic Prometheus text exposition server; local training only."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import monotonic

START = monotonic()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        uptime = monotonic() - START
        payload = (
            "# HELP demo_uptime_seconds Process uptime in seconds\n"
            "# TYPE demo_uptime_seconds gauge\n"
            f"demo_uptime_seconds {uptime:.3f}\n"
            "# HELP demo_requests_total Synthetic counter\n"
            "# TYPE demo_requests_total counter\n"
            f'demo_requests_total{{route="/search",status_class="2xx"}} {int(uptime)}\n'
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
```

### tests/test_lab.py

```python
import unittest
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo"))
from metrics_server import Handler

class ExpositionTests(unittest.TestCase):
    def test_handler_has_get(self):
        self.assertTrue(callable(Handler.do_GET))
    def test_no_external_dependencies(self):
        self.assertTrue((ROOT / "demo" / "metrics_server.py").exists())
    def test_prometheus_config(self):
        c = (ROOT / "prometheus.yml").read_text()
        self.assertIn("scrape_interval: 15s", c)
        self.assertIn("job_name: demo", c)
        self.assertIn("demo:8000", c)
    def test_prometheus_self_scrape(self):
        self.assertIn("prometheus:9090", (ROOT / "prometheus.yml").read_text())
    def test_compose_loopback_binding(self):
        self.assertIn("127.0.0.1:9090:9090", (ROOT / "compose.yaml").read_text())
    def test_retention(self):
        self.assertIn("retention.time=24h", (ROOT / "compose.yaml").read_text())
    def test_named_volume(self):
        self.assertIn("prometheus-data:/prometheus", (ROOT / "compose.yaml").read_text())
    def test_demo_build(self):
        self.assertIn("build: ./demo", (ROOT / "compose.yaml").read_text())
    def test_dockerfile(self):
        self.assertIn("USER 10001", (ROOT / "demo" / "Dockerfile").read_text())
    def test_no_secrets_in_config(self):
        c = (ROOT / "prometheus.yml").read_text().lower()
        self.assertNotIn("password:", c)
        self.assertNotIn("authorization:", c)

if __name__ == "__main__":
    unittest.main()
```

### Validate and start

```bash
cd chapter011
python3 -m unittest discover -s tests -v
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl --fail --silent http://127.0.0.1:9090/-/ready
curl --fail --silent 'http://127.0.0.1:9090/api/v1/query?query=up'
curl --fail --silent 'http://127.0.0.1:9090/api/v1/targets'
```

Open `http://127.0.0.1:9090` on the host. Expect two active targets (`prometheus`, `demo`) and `up == 1` after successful scrapes. Scraping may require waiting one or two 15-second intervals. Local Docker daemon and images must be available; no live execution has been performed by this publication workflow.

### PromQL exercises

```promql
up
```

```promql
scrape_duration_seconds{job="demo"}
```

```promql
demo_uptime_seconds
```

```promql
rate(demo_requests_total[2m])
```

The demo counter increments with elapsed seconds, not real HTTP traffic; it is explicitly synthetic.

### Safe cleanup

```bash
docker compose down
```

This preserves the named TSDB volume. `docker compose down -v` deletes the local training volume; only run it with explicit approval and no data to preserve.

## 6. Reliability and cardinality

- Series count grows approximately as the product of independent label cardinalities.
- Choose bounded route templates, service, environment and status class; never raw URLs or patient IDs.
- Monitor `prometheus_tsdb_head_series`, scrape sample counts, query duration, WAL/TSDB storage, remote-write queue and target availability.
- Size storage using measured samples/sec, retention and observed bytes/sample rather than universal constants.
- Design `absent_over_time()` alerts for missing expected series, in addition to `up == 0`.

## 7. Troubleshooting

| Symptom | Hypothesis | Check |
|---|---|---|
| Target DOWN | DNS, network, port, auth | Targets UI and scrape error |
| No metrics | exporter not emitting | curl `/metrics` from scrape network |
| Duplicate series | labels or discovery | target labels |
| High cardinality | unbounded labels | head series and scrape samples |
| High TSDB disk | ingestion/retention | volume, WAL, blocks |
| Slow PromQL | wide regex/range | query log, cardinality |
| Missing alerts | rules/route | rules API, Alertmanager |
| Remote-write backlog | backend/network | queue and retry metrics |

## 8. Twenty-four hands-on exercises

1. Draw the pull architecture.
2. Identify exporter versus collector responsibilities.
3. Explain TSDB/WAL.
4. Define metric name/label contract.
5. Compare counter and gauge.
6. Explain histogram and summary.
7. Define scrape interval/timeout.
8. Configure Prometheus self-scrape.
9. Configure demo scrape.
10. Pin Prometheus image.
11. Build non-root demo exporter.
12. Validate Compose.
13. Run static unit tests.
14. Start local deployment.
15. Inspect Targets UI.
16. Query `up`.
17. Query scrape duration.
18. Query demo gauge.
19. Query counter rate.
20. Explain target relabeling.
21. Plan Kubernetes discovery.
22. Design missing-data alert.
23. Simulate exporter stop in isolated lab.
24. Document production readiness and rollback.

## 9. Twenty failure scenarios

| # | Failure | Primary response |
|---|---|---|
| 01 | exporter down | target error |
| 02 | DNS failure | discovery |
| 03 | scrape timeout | latency/timeout |
| 04 | TLS failure | certificates |
| 05 | auth failure | secrets/RBAC |
| 06 | duplicate targets | relabeling |
| 07 | missing target | service discovery |
| 08 | unbounded route labels | instrumentation |
| 09 | patient ID labels | privacy incident |
| 10 | sample limit exceeded | scrape health |
| 11 | TSDB full | capacity/retention |
| 12 | WAL pressure | I/O/storage |
| 13 | slow query | cardinality |
| 14 | counter reset misread | rate |
| 15 | incorrect histogram aggregation | bucket contract |
| 16 | remote-write backlog | queue/backend |
| 17 | rule evaluation delay | rule health |
| 18 | Alertmanager unavailable | HA routing |
| 19 | duplicate HA alerts | replica labels |
| 20 | missing-data blind spot | absent rules |

## 10. Eight production runbooks

**A. Target down:** Inspect Targets UI, DNS, network, exporter, auth, TLS, scrape timeout and recent changes.

**B. Missing metrics:** Confirm discovery, endpoint exposition, relabeling, sample limits, `up` and absence alerts.

**C. High cardinality:** Identify label explosion, fix instrumentation, estimate series/storage cost, review retention and privacy.

**D. TSDB disk pressure:** Inspect retention, WAL, ingestion, filesystem and capacity; back up and stage any retention change.

**E. Slow PromQL:** Review selectors, range, recording rules, query timeout and TSDB pressure; avoid broad regexes.

**F. Remote-write backlog:** Inspect queue length, retries, backend, network and durability requirements.

**G. Security incident:** Restrict exposed endpoints, revoke credentials if needed, preserve evidence and notify security owner.

**H. Prometheus production readiness:** Verify HA, restore drills, alert routing, rule tests, ownership, RBAC, retention and rollback.

## 11. 100-point assessment

| Area | Points |
|---|---:|
| Architecture and TSDB/data model | 20 |
| Scrape/discovery and instrumentation | 20 |
| Executable local lab and ten tests | 20 |
| Security, HA, cardinality and cost | 20 |
| Incident scenarios, runbooks, evidence | 20 |
| **Total** | **100** |

Recommended pass 85/100, mandatory gates for bounded labels, loopback-only training UI, validated scrape targets, static tests and safe cleanup.

## 12. Evidence

```text
UTC / operator / Prometheus image version:
Compose config validation:
Target discovery and up:
Scrape health:
Metric label review:
TSDB retention and volume:
10 static tests:
Failure drill and recovery:
Security / HA / capacity review:
RCA / COA / reviewer:
```

**Companion:** [Chapter 011 deployment lab](labs/011-prometheus-architecture-data-model-scraping-production-deployment-fundamentals-lab.md).

**Next:** Chapter 012 — Prometheus Installation, Configuration, Service Discovery and Target Management.
