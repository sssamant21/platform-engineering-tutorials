# Chapter 012 — Prometheus Installation, Configuration, Service Discovery and Target Management

**Part 03 — Prometheus Architecture and Installation**  
**Audience:** SRE, DBRE, platform and Kubernetes operators. **Prerequisites:** Chapters 001–011; Docker Compose; Python 3.10+.  
**Goal:** Deploy a reproducible training Prometheus, safely manage target discovery and validate scrape health, configuration and operational changes.

## 1. Architecture and discovery lifecycle

```text
Inventory / Kubernetes API / cloud metadata / file-SD
                     |
           target discovery groups
                     |
          target relabeling pipeline
                     |
        scrape scheduler / HTTP /metrics
                     |
       scrape-time metric relabeling
                     |
            WAL -> TSDB blocks
                     |
      PromQL / recording rules / alerts
```

Prometheus supports static targets, file-based discovery, Kubernetes discovery and other integrations. A discovered target is not necessarily healthy. Track discovery, scrape success, sample limits, label contracts and endpoint ownership separately.

## 2. Installation approaches

| Option | Typical use | Operational considerations |
|---|---|---|
| Binary + systemd | Linux VMs | dedicated user, immutable config, persistent storage, systemd hardening |
| Docker Compose | isolated training/staging | pinned image, named volume, loopback UI, controlled lifecycle |
| Kubernetes manifests | small Kubernetes installations | RBAC, PVC, config reload, pod security |
| Prometheus Operator | Kubernetes production | ServiceMonitor/PodMonitor CRDs, selector policies, tenancy |
| Managed Prometheus | cloud-scale teams | billing, remote-write, vendor limits, IAM |

Production installations require release pinning, vulnerability review, HA and DR planning, retention/capacity modeling, TLS, authentication or private network enforcement, backups where needed, SLO ownership and tested rollback.

## 3. Configuration hierarchy

`global.scrape_interval` sets the default polling interval. `scrape_timeout` must not exceed the effective interval. Jobs can override these values. `external_labels` identify replicas/regions for federation or remote-write, but they are not a substitute for safe target identity.

`relabel_configs` operate on discovered target labels **before** scraping. `metric_relabel_configs` operate on metric samples **after** scraping and do not eliminate exporter generation overhead. `file_sd_configs` watches JSON/YAML target files and updates discovered groups without requiring full Prometheus restarts.

## 4. Target labels, security and cardinality

Prefer bounded `environment`, `service`, `team`, `job` and `instance`. Never include raw user IDs, patient IDs, email addresses, request IDs, arbitrary URLs or secrets in labels. Ensure labels are consistent across discovery mechanisms and preserve meaningful ownership. Apply target and sample limits; review changes for duplicate time series.

For service discovery, ensure the Prometheus service account has only the Kubernetes API permissions it needs. Restrict exporter exposure, protect scrape authentication credentials outside Git, and verify TLS certificate rotation.

## 5. Complete local executable lab

Create the following tree:

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

### compose.yaml

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.55.1
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=24h
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./targets:/etc/prometheus/targets:ro
      - prometheus-data:/prometheus
    ports:
      - "127.0.0.1:9090:9090"
    restart: unless-stopped
  demo:
    build: ./demo
    expose:
      - "8000"
volumes:
  prometheus-data:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s
scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["prometheus:9090"]
  - job_name: discovered-services
    file_sd_configs:
      - files:
          - /etc/prometheus/targets/*.json
        refresh_interval: 15s
    relabel_configs:
      - source_labels: [__address__]
        regex: "(.*)"
        target_label: endpoint
        replacement: "$1"
```

### targets/services.json

```json
[
  {
    "targets": ["demo:8000"],
    "labels": {
      "environment": "staging",
      "service": "synthetic-api",
      "team": "platform-sre"
    }
  }
]
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
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import monotonic
START = monotonic()
class Metrics(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = (
            "# HELP demo_uptime_seconds Synthetic exporter uptime\n"
            "# TYPE demo_uptime_seconds gauge\n"
            f"demo_uptime_seconds {monotonic() - START:.3f}\n"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Metrics).serve_forever()
```

### scripts/validate_targets.py

```python
#!/usr/bin/env python3
"""Validate bounded file-SD JSON without PyYAML or external dependencies."""
import json
import re
import sys
from pathlib import Path
ALLOWED_LABELS = {"environment", "service", "team"}
TARGET = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.-]*:[0-9]{1,5}$")
LABEL = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")

def validate(doc):
    problems = []
    if not isinstance(doc, list) or not doc:
        return ["target groups must be a nonempty array"]
    seen = set()
    for idx, group in enumerate(doc):
        if not isinstance(group, dict) or set(group) != {"targets", "labels"}:
            problems.append(f"group {idx}: expected targets and labels")
            continue
        targets, labels = group["targets"], group["labels"]
        if not isinstance(targets, list) or not targets or len(targets) > 100:
            problems.append(f"group {idx}: invalid target list")
        else:
            for target in targets:
                if not isinstance(target, str) or not TARGET.fullmatch(target):
                    problems.append(f"group {idx}: invalid target")
                elif not 1 <= int(target.rsplit(":", 1)[1]) <= 65535:
                    problems.append(f"group {idx}: invalid port")
                elif target in seen:
                    problems.append(f"group {idx}: duplicate target")
                else:
                    seen.add(target)
        if not isinstance(labels, dict) or set(labels) != ALLOWED_LABELS:
            problems.append(f"group {idx}: labels must be environment/service/team")
        else:
            for key, value in labels.items():
                if not isinstance(value, str) or not LABEL.fullmatch(value):
                    problems.append(f"group {idx}: invalid {key} label")
    return problems

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 validate_targets.py targets/services.json")
    try:
        problems = validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError, ValueError) as error:
        sys.exit(f"invalid JSON: {error}")
    for problem in problems:
        print(problem)
    print("FILE-SD PASS" if not problems else "FILE-SD FAIL")
    sys.exit(bool(problems))
```

### tests/test_discovery.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_targets import validate

class DiscoveryTests(unittest.TestCase):
    def doc(self):
        return json.loads((ROOT / "targets" / "services.json").read_text())
    def test_valid(self): self.assertEqual(validate(self.doc()), [])
    def test_empty(self): self.assertTrue(validate([]))
    def test_missing_labels(self):
        d = self.doc()
        del d[0]["labels"]
        self.assertTrue(validate(d))
    def test_unbounded_label(self):
        d = self.doc()
        d[0]["labels"]["request_id"] = "123"
        self.assertTrue(validate(d))
    def test_invalid_port(self):
        d = self.doc()
        d[0]["targets"] = ["demo:99999"]
        self.assertTrue(validate(d))
    def test_duplicate_target(self):
        d = self.doc()
        d[0]["targets"].append("demo:8000")
        self.assertTrue(validate(d))
    def test_invalid_host(self):
        d = self.doc()
        d[0]["targets"] = ["http://demo:8000"]
        self.assertTrue(validate(d))
    def test_missing_team(self):
        d = self.doc()
        del d[0]["labels"]["team"]
        self.assertTrue(validate(d))
    def test_invalid_label(self):
        d = self.doc()
        d[0]["labels"]["team"] = "a space"
        self.assertTrue(validate(d))
    def test_excessive_targets(self):
        d = self.doc()
        d[0]["targets"] = [f"demo-{i}:8000" for i in range(101)]
        self.assertTrue(validate(d))
    def test_scrape_timeout(self):
        c = (ROOT / "prometheus.yml").read_text()
        self.assertIn("scrape_timeout: 10s", c)
    def test_compose_loopback(self):
        c = (ROOT / "compose.yaml").read_text()
        self.assertIn("127.0.0.1:9090:9090", c)

if __name__ == "__main__":
    unittest.main()
```

### Validation and startup

```bash
cd chapter012
python3 scripts/validate_targets.py targets/services.json
python3 -m unittest discover -s tests -v
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS 'http://127.0.0.1:9090/api/v1/targets'
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=up'
```

Expect two scrape targets (`prometheus` and `discovered-services`) after 15–30 seconds. File-SD target label `endpoint` is copied from `__address__`; this is deliberately a simple relabel example. The validator is a bounded educational policy, not a full Prometheus configuration parser.

### Configuration and discovery changes

1. Edit `targets/services.json` in a disposable local stack, retaining valid JSON and bounded labels.
2. Run `python3 scripts/validate_targets.py targets/services.json`.
3. Observe target changes after file-SD refresh; inspect `/api/v1/targets`.
4. To change `prometheus.yml`, validate using a matching `promtool` binary or image, then restart/reload according to approved deployment process.
5. For production changes, require peer review, GitOps rollout, pre/post health checks and rollback.

Example matching image validation:

```bash
docker run --rm -v "$PWD/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  prom/prometheus:v2.55.1 \
  promtool check config /etc/prometheus/prometheus.yml
```

If the container image's entrypoint is Prometheus, specify `--entrypoint /bin/promtool` instead:

```bash
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  prom/prometheus:v2.55.1 check config /etc/prometheus/prometheus.yml
```

The second form is the recommended explicit command.

### Safe shutdown

```bash
docker compose down
```

This preserves the named training TSDB volume. Do not use `down -v` without confirming that deleting local metrics is acceptable.

## 6. PromQL for target management

```promql
up
```

```promql
scrape_duration_seconds{job="discovered-services"}
```

```promql
scrape_samples_scraped{job="discovered-services"}
```

```promql
absent_over_time(up{job="discovered-services"}[5m])
```

`up == 0` catches discovered targets with failed scrapes; `absent_over_time` catches missing expected series, provided labels and discovery expectations are stable. Test both cases.

## 7. Twenty-four hands-on exercises

1. Compare binary, Compose and Operator installation.
2. Design production deployment topology.
3. Define scrape interval and timeout.
4. Explain file-SD lifecycle.
5. Explain target relabeling.
6. Explain metric relabeling.
7. Build bounded label policy.
8. Create local Compose stack.
9. Configure Prometheus self-scrape.
10. Create JSON target group.
11. Build non-root demo exporter.
12. Validate target JSON.
13. Run 12 unit tests.
14. Validate Compose configuration.
15. Run promtool config check.
16. Start Prometheus and exporter.
17. Query Targets API.
18. Query `up`.
19. Query scrape duration.
20. Change file-SD target safely.
21. Simulate exporter outage.
22. Detect missing target.
23. Restore target and verify recovery.
24. Document change ticket, rollback and evidence.

## 8. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | malformed config | promtool |
| 02 | scrape timeout too long | config validation |
| 03 | target DOWN | Targets API |
| 04 | target absent | file-SD/discovery |
| 05 | invalid JSON | policy validator |
| 06 | wrong port | connectivity |
| 07 | wrong metrics path | HTTP 404 |
| 08 | TLS mismatch | certificate |
| 09 | auth failure | secret/RBAC |
| 10 | duplicate target | labels |
| 11 | cardinality explosion | labels |
| 12 | scrape sample limit | scrape metrics |
| 13 | stale file-SD file | refresh/path |
| 14 | Kubernetes RBAC denied | service account |
| 15 | service discovery overload | API/watch |
| 16 | exporter crashes | process logs |
| 17 | storage fills | TSDB/retention |
| 18 | missing-data alert absent | alert rules |
| 19 | unsafe public UI | network controls |
| 20 | rollback unavailable | change process |

## 9. Eight production runbooks

**A. Installation failure:** Check image/binary version, config validation, permissions, storage and service logs.

**B. Scrape target DOWN:** Inspect discovery, DNS, network, TLS/auth, timeout and endpoint response.

**C. Target missing:** Inspect file-SD paths, Kubernetes selectors, service discovery health and absence alerts.

**D. Duplicate series:** Compare target label sets, external labels, relabeling and exporter identities.

**E. Cardinality regression:** Identify unbounded labels, fix instrumentation, enforce label policy and estimate TSDB impact.

**F. Configuration rollout:** Validate with promtool, review Git diff, stage, deploy, monitor and rollback.

**G. Security exposure:** Restrict UI/exporters, rotate exposed credentials, preserve evidence and escalate.

**H. Production readiness:** Verify HA, retention, backups/DR, RBAC, alert routing, runbook ownership and capacity.

## 10. 100-point acceptance

| Area | Points |
|---|---:|
| Installation architecture and lifecycle | 20 |
| Scrape and file-SD configuration | 20 |
| Executable lab and 12 tests | 20 |
| Security, cardinality and target governance | 20 |
| Runbooks, troubleshooting and evidence | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory gates: valid config, bounded labels, two targets UP, negative test rejection, safe cleanup and documented rollback.

## 11. Evidence checklist

```text
UTC / operator / Prometheus version:
Promtool validation:
Docker Compose config:
Target JSON validator:
12 automated tests:
Targets API and up:
Discovery change and recovery:
Security/retention/HA review:
RCA / COA / approver:
```

**Companion:** [Chapter 012 executable lab](labs/012-prometheus-installation-configuration-service-discovery-target-management-lab.md).

**Next:** Chapter 013 — Prometheus TSDB, WAL, Retention, Compaction and Storage Capacity Engineering.
