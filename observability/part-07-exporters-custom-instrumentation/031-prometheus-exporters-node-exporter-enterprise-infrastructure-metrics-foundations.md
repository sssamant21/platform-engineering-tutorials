# Chapter 031 — Prometheus Exporters, Node Exporter and Enterprise Infrastructure Metrics Foundations

**Part 07 — Exporters and Custom Instrumentation**  
**Audience:** SRE/DBRE, Kubernetes and infrastructure observability engineers.  
**Prerequisites:** Prometheus architecture/PromQL (Chapters 011–020), Linux, Docker, Python 3.10+.  
**Objective:** Deploy and secure Node Exporter, collect Linux infrastructure metrics, interpret CPU/memory/disk/network signals and validate production-style operational controls.

## 1. Prometheus exporter architecture

```text
Linux host /proc /sys / filesystem statistics
                     |
               Node Exporter
                 /metrics
                     |
              Prometheus scrape
                     |
         TSDB -> PromQL -> Grafana
                     |
          Alertmanager -> on-call
```

Exporters translate platform-specific measurements into Prometheus metrics. Node Exporter collects host-level Linux signals; it does not directly measure application SLIs. A scrape success (`up == 1`) proves endpoint reachability, not that every collector is healthy or the host is healthy.

## 2. Metric types and key Linux signals

| Metric | Type | Interpretation |
|---|---|---|
| `node_cpu_seconds_total` | counter | CPU time by mode/core |
| `node_memory_MemAvailable_bytes` | gauge | estimated memory available without swapping |
| `node_filesystem_avail_bytes` | gauge | filesystem space available to non-root |
| `node_filesystem_files_free` | gauge | free inodes |
| `node_disk_read_bytes_total` | counter | disk read throughput |
| `node_disk_written_bytes_total` | counter | disk write throughput |
| `node_network_receive_bytes_total` | counter | received bytes |
| `node_network_transmit_bytes_total` | counter | transmitted bytes |
| `node_load1` | gauge | 1-minute load average |

Counters need `rate()` or `increase()`; do not subtract raw counters across resets. Disk I/O counters and utilization are useful indicators but do not alone establish user-visible storage latency.

## 3. Safe local Docker lab

This example binds both ports to localhost and uses a test-only environment. Dockerized Node Exporter with no host namespace/filesystem mounts observes its container's view and **does not provide complete host metrics**. For real host monitoring, deploy Node Exporter with reviewed host mounts/namespaces and least privilege.

### docker-compose.yml

```yaml
services:
  node-exporter:
    image: prom/node-exporter:v1.8.2
    command:
      - --web.listen-address=:9100
    ports:
      - "127.0.0.1:9100:9100"
    networks: [lab]
  prometheus:
    image: prom/prometheus:v2.55.1
    command:
      - --config.file=/etc/prometheus/prometheus.yml
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "127.0.0.1:9090:9090"
    networks: [lab]
networks:
  lab: {}
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
scrape_configs:
  - job_name: node
    scrape_interval: 15s
    scrape_timeout: 10s
    static_configs:
      - targets: ["node-exporter:9100"]
        labels:
          cluster: lab
          environment: staging
```

### Commands

```bash
docker compose config
docker compose run --rm --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose up -d
curl -fsS http://127.0.0.1:9100/metrics | head -n 20
curl -fsS http://127.0.0.1:9090/api/v1/targets
curl -fsSG --data-urlencode 'query=up{job="node"}' http://127.0.0.1:9090/api/v1/query
docker compose logs --tail=100 node-exporter
docker compose down
```

Versions are pinned teaching examples; check upstream support/security advisories before production.

## 4. Essential PromQL

```promql
# Per-instance non-idle CPU proportion
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))

# Memory available fraction
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes

# Filesystem available fraction, excluding common virtual mounts
node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}
/
node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"}

# Disk read throughput
rate(node_disk_read_bytes_total[5m])

# Network receive throughput
rate(node_network_receive_bytes_total[5m])

# Target availability
up{job="node"}
```

Filter devices and mountpoints to avoid misleading aggregate alerts. For missing targets, `up == 0` cannot detect an expected target that has vanished from service discovery; maintain an expected-target inventory or independent availability probe.

## 5. Security, capacity and operations

Restrict exporter endpoints to trusted monitoring networks; use approved TLS/auth termination when needed. Avoid public exposure of host telemetry. Review exporter versions, container privileges, host filesystem mounts and enabled collectors. Monitor `scrape_duration_seconds`, `scrape_samples_scraped`, sample ingestion and active-series growth. Keep labels bounded; never add request IDs, raw SQL, PHI/PII or volatile host identifiers as metric labels.

## 6. Executable offline governance lab

The following JSON is **synthetic deployment policy metadata**, not Prometheus YAML. Its Python gate validates local binding, scrape timing, approved collectors, series budget and review evidence; it does not query a running exporter.

Create:

```text
chapter031/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/exporter_gate.py
  tests/test_exporter_gate.py
```

### fixtures/healthy.json

```json
{
  "environment": "staging",
  "owner": "platform-sre",
  "job": "node",
  "exporter": "node_exporter",
  "version_reviewed": true,
  "security_reviewed": true,
  "scrape_verified": true,
  "inventory_verified": true,
  "rollback_tested": true,
  "capacity_baseline_reviewed": true,
  "labels": [
    "job",
    "instance",
    "cluster",
    "environment"
  ],
  "scrape_interval_seconds": 15,
  "scrape_timeout_seconds": 10,
  "port": 9100,
  "bind_address": "127.0.0.1",
  "tls_termination": "approved-ingress-or-private-network",
  "collectors": [
    "cpu",
    "meminfo",
    "filesystem",
    "diskstats",
    "netdev",
    "loadavg"
  ],
  "metric_budget_series": 20000,
  "observed_series": 12000,
  "cardinality_reviewed": true,
  "runbook": "https://example.org/runbooks/node-exporter"
}
```

### fixtures/degraded.json

```json
{
  "environment": "staging",
  "owner": "platform-sre",
  "job": "node",
  "exporter": "node_exporter",
  "version_reviewed": true,
  "security_reviewed": false,
  "scrape_verified": false,
  "inventory_verified": true,
  "rollback_tested": true,
  "capacity_baseline_reviewed": true,
  "labels": [
    "job",
    "instance",
    "cluster",
    "environment",
    "request_id"
  ],
  "scrape_interval_seconds": 15,
  "scrape_timeout_seconds": 30,
  "port": 9100,
  "bind_address": "0.0.0.0",
  "tls_termination": "approved-ingress-or-private-network",
  "collectors": [
    "cpu",
    "meminfo",
    "filesystem",
    "diskstats",
    "netdev",
    "loadavg",
    "unsafe-custom"
  ],
  "metric_budget_series": 20000,
  "observed_series": 50000,
  "cardinality_reviewed": true,
  "runbook": "https://example.org/runbooks/node-exporter"
}
```

### scripts/exporter_gate.py

```python
#!/usr/bin/env python3
"""Offline Node Exporter deployment policy gate, not live Prometheus validation."""
import json,sys
from pathlib import Path
ALLOWED={"job","instance","cluster","environment","region","team"}
COLLECTORS={"cpu","meminfo","filesystem","diskstats","netdev","loadavg","filefd","uname","time","stat","vmstat","pressure"}
def check(p):
    e=[]
    if not isinstance(p,dict): return ["manifest must be object"]
    for k in ("environment","owner","job","exporter","runbook"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    if p.get("exporter")!="node_exporter": e.append("wrong exporter")
    for k in ("version_reviewed","security_reviewed","scrape_verified","inventory_verified","rollback_tested","capacity_baseline_reviewed","cardinality_reviewed"):
        if p.get(k) is not True: e.append("unverified "+k)
    labels=p.get("labels")
    if not isinstance(labels,list) or not {"job","instance","cluster","environment"}.issubset(labels) or not set(labels).issubset(ALLOWED): e.append("unsafe labels")
    interval=p.get("scrape_interval_seconds");timeout=p.get("scrape_timeout_seconds")
    if type(interval) is not int or type(timeout) is not int or not 0<timeout<interval<=300: e.append("invalid scrape timing")
    if p.get("port")!=9100: e.append("unexpected port")
    if p.get("bind_address")!="127.0.0.1": e.append("nonlocal lab bind")
    if p.get("tls_termination")!="approved-ingress-or-private-network": e.append("missing transport review")
    collectors=p.get("collectors")
    if not isinstance(collectors,list) or not {"cpu","meminfo","filesystem","diskstats","netdev"}.issubset(collectors) or not set(collectors).issubset(COLLECTORS): e.append("unsafe collectors")
    budget=p.get("metric_budget_series");observed=p.get("observed_series")
    if type(budget) is not int or budget<=0 or type(observed) is not int or observed<0: e.append("invalid series budget")
    elif observed>budget: e.append("series budget exceeded")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 exporter_gate.py fixtures/healthy.json")
    try: issues=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit("input error: "+str(exc))
    print(json.dumps({"status":"FAIL" if issues else "PASS","issues":issues},indent=2))
    sys.exit(bool(issues))
```

### tests/test_exporter_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from exporter_gate import check
class ExporterTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        p=copy.deepcopy(self.p);f(p);return check(p)
    def test_healthy(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda p:p.update(owner="")))
    def test_runbook(self): self.assertTrue(self.mutate(lambda p:p.update(runbook="")))
    def test_exporter(self): self.assertTrue(self.mutate(lambda p:p.update(exporter="other")))
    def test_version(self): self.assertTrue(self.mutate(lambda p:p.update(version_reviewed=False)))
    def test_security(self): self.assertTrue(self.mutate(lambda p:p.update(security_reviewed=False)))
    def test_scrape(self): self.assertTrue(self.mutate(lambda p:p.update(scrape_verified=False)))
    def test_inventory(self): self.assertTrue(self.mutate(lambda p:p.update(inventory_verified=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda p:p.update(rollback_tested=False)))
    def test_baseline(self): self.assertTrue(self.mutate(lambda p:p.update(capacity_baseline_reviewed=False)))
    def test_cardinality_review(self): self.assertTrue(self.mutate(lambda p:p.update(cardinality_reviewed=False)))
    def test_labels(self): self.assertTrue(self.mutate(lambda p:p["labels"].append("request_id")))
    def test_missing_labels(self): self.assertTrue(self.mutate(lambda p:p.update(labels=["job"])))
    def test_interval(self): self.assertTrue(self.mutate(lambda p:p.update(scrape_interval_seconds=0)))
    def test_timeout(self): self.assertTrue(self.mutate(lambda p:p.update(scrape_timeout_seconds=15)))
    def test_port(self): self.assertTrue(self.mutate(lambda p:p.update(port=80)))
    def test_bind(self): self.assertTrue(self.mutate(lambda p:p.update(bind_address="0.0.0.0")))
    def test_tls(self): self.assertTrue(self.mutate(lambda p:p.update(tls_termination="none")))
    def test_collectors(self): self.assertTrue(self.mutate(lambda p:p["collectors"].append("unsafe-custom")))
    def test_missing_collectors(self): self.assertTrue(self.mutate(lambda p:p.update(collectors=["cpu"])))
    def test_budget(self): self.assertTrue(self.mutate(lambda p:p.update(metric_budget_series=0)))
    def test_over_budget(self): self.assertTrue(self.mutate(lambda p:p.update(observed_series=50000)))
    def test_negative_series(self): self.assertTrue(self.mutate(lambda p:p.update(observed_series=-1)))
    def test_valid_optional_collector(self): self.assertEqual(self.mutate(lambda p:p["collectors"].append("pressure")),[])
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter031
python3 scripts/exporter_gate.py fixtures/healthy.json
if python3 scripts/exporter_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded exporter manifest accepted"; exit 1
else
  echo "PASS: degraded exporter manifest rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, **26 automated unit tests pass**. This is policy validation, not live scrape verification.

## 7. Twenty-four hands-on exercises

1. Map exporter pull architecture.
2. Install Node Exporter in isolated lab.
3. Check /metrics endpoint.
4. Review collector flags.
5. Scrape with Prometheus.
6. Verify up metric.
7. Review CPU counters.
8. Calculate CPU utilization.
9. Review meminfo gauges.
10. Inspect filesystem free bytes.
11. Inspect disk read/write counters.
12. Inspect disk saturation context.
13. Review network counters.
14. Inspect load average.
15. Inspect PSI where available.
16. Identify missing target.
17. Check scrape duration.
18. Review scrape sample counts.
19. Review cardinality budget.
20. Review instance relabeling.
21. Design Linux SRE dashboard.
22. Run healthy governance gate.
23. Reject degraded manifest.
24. Run 26 tests and document rollback.

## 8. Twenty-four production failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 01 | Node exporter not reachable | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 02 | Exporter process crashed | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 03 | Prometheus target down | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 04 | Wrong target port | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 05 | Firewall blocked | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 06 | Wrong scrape scheme | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 07 | TLS verification failure | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 08 | Scrape timeout | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 09 | Metrics path wrong | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 10 | Collector disabled | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 11 | Filesystem metric absent | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 12 | CPU counter reset | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 13 | High CPU utilization | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 14 | Memory pressure | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 15 | Disk space low | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 16 | Disk I/O latency high | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 17 | Network drops | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 18 | Too many series | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 19 | Request ID label explosion | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 20 | High scrape duration | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 21 | Exporter version mismatch | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 22 | Node reboot | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 23 | Prometheus missing target | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |
| 24 | Stale dashboard metrics | Check exporter endpoint, Prometheus target, collector, labels and host telemetry |

## 9. Eight production runbooks

**A. Exporter down:** Check process/container status, port, endpoint, scrape target and logs.

**B. Scrape failure:** Review target discovery, scheme, auth, timeout, network policy and Prometheus scrape errors.

**C. CPU saturation:** Compare rate(node_cpu_seconds_total), load, steal, throttling and workload context.

**D. Memory pressure:** Inspect MemAvailable, swap, PSI, OOM kills and application behavior.

**E. Disk exhaustion:** Review filesystem available bytes, inode availability, mounts and safe cleanup ownership.

**F. Disk I/O pressure:** Inspect diskstats rates, latency from node_disk_* counters and application wait times.

**G. Cardinality incident:** Identify label churn, collectors, relabeling, scrape samples and series budget.

**H. Rollback:** Revert exporter config/version, validate endpoint, scrape health and dashboards.

## 10. SRE/DBRE incident simulation

An Elasticsearch data node reports high disk utilization and search latency. Prometheus still shows `up == 1`, but Node Exporter diskstats are absent due to a collector/configuration change. Investigate exporter collector health, mount visibility, filesystem/device filters and workload latency separately. Restore approved collection in staging and validate dashboards, alerts and rollback.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Exporter architecture and metrics | 20 |
| Local deployment and PromQL | 20 |
| Security and cardinality controls | 20 |
| Offline governance and 26 tests | 20 |
| Troubleshooting, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: local-only lab ports, reviewed exporter security, known target inventory, bounded labels, scrape validation and rollback evidence.

## 12. Evidence worksheet

```text
UTC / operator / environment:
Node Exporter and Prometheus versions:
Scrape target / up / collector metrics:
CPU / memory / disk / network baseline:
Series count / scrape samples:
Healthy/degraded gate / 26 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 031 executable Node Exporter lab](labs/031-prometheus-exporters-node-exporter-enterprise-infrastructure-metrics-foundations-lab.md).

**Next:** Chapter 032 — Prometheus Database Exporters, PostgreSQL Monitoring and Custom Exporter Integration.
