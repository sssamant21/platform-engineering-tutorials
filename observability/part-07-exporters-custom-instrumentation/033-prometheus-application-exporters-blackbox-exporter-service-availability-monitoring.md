# Chapter 033 — Prometheus Application Exporters, Blackbox Exporter and Service Availability Monitoring

**Part 07 — Exporters and Custom Instrumentation**  
**Audience:** Enterprise SRE/DBRE, platform engineering and application on-call.  
**Prerequisites:** Chapters 026–032, Prometheus/PromQL, Docker Compose, Python 3.10+.  
**Objective:** Build active HTTP availability probes, distinguish exporter and target failures, and operate secure synthetic monitoring with actionable alerts.

## 1. Architecture and failure domains

```text
Synthetic HTTP target -> Blackbox Exporter /probe
                                  |
                           Prometheus scrape
                                  |
                        probe_success / duration
                                  |
                         SLO / alert rules
                                  |
                       Alertmanager -> on-call
```

**Critical distinction:** `up{job="blackbox-http"}` means Prometheus scraped Blackbox Exporter; `probe_success` indicates whether the target passed the configured probe. A 200 response may still miss broken user journeys. Combine blackbox probes with application RED metrics, traces and real user monitoring.

## 2. Probe design and reliability

| Metric | Meaning | Action |
|---|---|---|
| `probe_success` | 1 if probe passed, else 0 | investigate availability |
| `probe_duration_seconds` | end-to-end probe duration | investigate latency |
| `probe_http_status_code` | observed HTTP status | check endpoint contract |
| `probe_dns_lookup_time_seconds` | DNS lookup timing | investigate resolver |
| `probe_http_duration_seconds` | HTTP phase durations by `phase` | isolate network/server delays |
| `up` | exporter scrape succeeded | inspect monitoring pipeline |

Blackbox supports HTTP, TCP, ICMP and DNS probes. ICMP may require additional privileges; don't enable them blindly. Limit probe target selection to an approved inventory and network path.

## 3. Complete disposable local lab

The following lab probes the root path of a Python HTTP server; it returns HTTP 200. This is an intentionally basic synthetic target, **not** a real application health check. The offline policy fixture later uses a hypothetical `/healthz` endpoint; it is separate from the Compose target.

### docker-compose.yml

```yaml
services:
  demo-app:
    image: python:3.12-alpine
    command: ["python","-m","http.server","8080"]
    networks: [lab]
  blackbox:
    image: prom/blackbox-exporter:v0.25.0
    command: ["--config.file=/etc/blackbox/blackbox.yml"]
    volumes: ["./blackbox.yml:/etc/blackbox/blackbox.yml:ro"]
    ports: ["127.0.0.1:9115:9115"]
    networks: [lab]
  prometheus:
    image: prom/prometheus:v2.55.1
    volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml:ro"]
    ports: ["127.0.0.1:9090:9090"]
    networks: [lab]
networks:
  lab: {}
```

### blackbox.yml

```yaml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_status_codes: [200]
      preferred_ip_protocol: ip4
      follow_redirects: false
```

### prometheus.yml

```yaml
global:
  scrape_interval: 30s
scrape_configs:
  - job_name: blackbox-http
    metrics_path: /probe
    scrape_timeout: 10s
    params:
      module: [http_2xx]
    static_configs:
      - targets: [http://demo-app:8080/]
        labels: {service: demo-app, environment: staging}
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox:9115
```

### Run

```bash
docker compose config
docker compose up -d
curl -fsSG --data-urlencode 'module=http_2xx' --data-urlencode 'target=http://demo-app:8080/' http://127.0.0.1:9115/probe | grep -E 'probe_success|probe_duration_seconds|probe_http_status_code'
curl -fsSG --data-urlencode 'query=probe_success' http://127.0.0.1:9090/api/v1/query
curl -fsSG --data-urlencode 'query=up{job="blackbox-http"}' http://127.0.0.1:9090/api/v1/query
docker compose logs --tail=100 blackbox
docker compose down
```

Check current supported image versions and security fixes before deploying outside the lab.

## 4. PromQL and alert design

```promql
probe_success{job="blackbox-http"} == 0
avg_over_time(probe_success{job="blackbox-http"}[30m])
max_over_time(probe_duration_seconds{job="blackbox-http"}[5m])
up{job="blackbox-http"} == 0
```

For a synthetic availability SLO, define eligible checks, exclusions, expected targets and measurement interval. **Missing probes are not successful probes**: separately alert on absent expected targets, scrape failure and inventory mismatch. Use multi-location probing for critical services and avoid treating a single vantage point as global availability.

## 5. Secure probing and SSRF controls

The `/probe?target=...` endpoint can cause outbound requests. Never expose it as an unrestricted public proxy. Restrict caller access, target inventory and network egress; deny metadata and internal management endpoints. Review redirects, DNS rebinding, credentials, TLS verification and notification payloads. The Python gate below is a policy check only; production SSRF prevention requires network-level controls.

## 6. Offline policy gate with automated tests

This synthetic JSON is not native Blackbox Exporter YAML. The gate validates approved target names, label cardinality, timing, SLO settings and review evidence; it **does not execute HTTP requests**.

Create:

```text
chapter033/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/probe_gate.py
  tests/test_probe_gate.py
```

### fixtures/healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "module": "http_2xx",
  "probe_timeout_seconds": 5,
  "scrape_timeout_seconds": 10,
  "scrape_interval_seconds": 30,
  "allowed_targets": [
    "http://demo-app:8080/healthz"
  ],
  "targets": [
    "http://demo-app:8080/healthz"
  ],
  "labels": [
    "job",
    "instance",
    "service",
    "environment"
  ],
  "runbook": "https://example.org/runbooks/http-probe",
  "reviewed": true,
  "network_policy_reviewed": true,
  "ssrf_reviewed": true,
  "synthetic_alert_tested": true,
  "rollback_tested": true,
  "latency_slo_ms": 500,
  "availability_slo": 0.999,
  "observed_series": 500,
  "series_budget": 2000
}
```

### fixtures/degraded.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "module": "http_2xx",
  "probe_timeout_seconds": 12,
  "scrape_timeout_seconds": 10,
  "scrape_interval_seconds": 30,
  "allowed_targets": [
    "http://demo-app:8080/healthz"
  ],
  "targets": [
    "http://169.254.169.254/latest/meta-data/"
  ],
  "labels": [
    "job",
    "instance",
    "service",
    "environment",
    "user_id"
  ],
  "runbook": "https://example.org/runbooks/http-probe",
  "reviewed": true,
  "network_policy_reviewed": true,
  "ssrf_reviewed": false,
  "synthetic_alert_tested": true,
  "rollback_tested": true,
  "latency_slo_ms": 500,
  "availability_slo": 0.999,
  "observed_series": 5000,
  "series_budget": 2000
}
```

### scripts/probe_gate.py

```python
#!/usr/bin/env python3
"""Offline blackbox probe deployment gate; no network requests or real probes."""
import json,sys
from pathlib import Path
LABELS={"job","instance","service","environment","cluster","region"}
def validate(p):
    e=[]
    if not isinstance(p,dict): return ["policy must be object"]
    for k in ("owner","environment","runbook"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    for k in ("reviewed","network_policy_reviewed","ssrf_reviewed","synthetic_alert_tested","rollback_tested"):
        if p.get(k) is not True: e.append("gate failed "+k)
    if p.get("module")!="http_2xx": e.append("unapproved module")
    for k in ("probe_timeout_seconds","scrape_timeout_seconds","scrape_interval_seconds"):
        if type(p.get(k)) is not int: e.append("invalid "+k)
    a=p.get("probe_timeout_seconds");b=p.get("scrape_timeout_seconds");c=p.get("scrape_interval_seconds")
    if all(type(v) is int for v in (a,b,c)) and not 0<a<b<c<=300: e.append("unsafe timing")
    allow=p.get("allowed_targets");targets=p.get("targets")
    if not isinstance(allow,list) or not allow or not isinstance(targets,list) or not targets: e.append("missing targets")
    elif any(not isinstance(t,str) or t not in allow or not t.startswith("http://demo-app:8080/") for t in targets): e.append("unapproved probe target")
    labels=p.get("labels")
    if not isinstance(labels,list) or not {"job","instance","service","environment"}.issubset(labels) or not set(labels).issubset(LABELS): e.append("unsafe labels")
    slo=p.get("availability_slo")
    if type(slo) not in (int,float) or not 0<slo<1: e.append("invalid availability SLO")
    latency=p.get("latency_slo_ms")
    if type(latency) is not int or latency<=0: e.append("invalid latency SLO")
    observed=p.get("observed_series");budget=p.get("series_budget")
    if type(observed) is not int or type(budget) is not int or observed<0 or budget<=0: e.append("invalid series budget")
    elif observed>budget: e.append("series budget exceeded")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 probe_gate.py fixtures/healthy.json")
    try: errors=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit(str(exc))
    print(json.dumps({"status":"FAIL" if errors else "PASS","errors":errors},indent=2))
    sys.exit(bool(errors))
```

### tests/test_probe_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from probe_gate import validate
class ProbeTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def bad(self,change):
        p=copy.deepcopy(self.p);exec(change,{},{"p":p});self.assertTrue(validate(p))
    def test_healthy(self): self.assertEqual(validate(self.p),[])
    def test_degraded(self): self.assertTrue(validate(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(validate(None))
    def test_01_owner(self): self.bad("p[\"owner\"]=\"\"")
    def test_02_review(self): self.bad("p[\"reviewed\"]=False")
    def test_03_network(self): self.bad("p[\"network_policy_reviewed\"]=False")
    def test_04_ssrf(self): self.bad("p[\"ssrf_reviewed\"]=False")
    def test_05_synthetic(self): self.bad("p[\"synthetic_alert_tested\"]=False")
    def test_06_rollback(self): self.bad("p[\"rollback_tested\"]=False")
    def test_07_module(self): self.bad("p[\"module\"]=\"tcp_connect\"")
    def test_08_probe_timeout(self): self.bad("p[\"probe_timeout_seconds\"]=12")
    def test_09_scrape_timeout(self): self.bad("p[\"scrape_timeout_seconds\"]=30")
    def test_10_interval(self): self.bad("p[\"scrape_interval_seconds\"]=0")
    def test_11_missing_targets(self): self.bad("p[\"targets\"]=[]")
    def test_12_metadata_endpoint(self): self.bad("p[\"targets\"]=[\"http://169.254.169.254/\"]")
    def test_13_external_endpoint(self): self.bad("p[\"targets\"]=[\"https://example.com\"]")
    def test_14_label_explosion(self): self.bad("p[\"labels\"].append(\"user_id\")")
    def test_15_missing_labels(self): self.bad("p[\"labels\"]=[\"job\"]")
    def test_16_availability_(self): self.bad("p[\"availability_slo\"]=1")
    def test_17_latency_(self): self.bad("p[\"latency_slo_ms\"]=0")
    def test_18_series_budget(self): self.bad("p[\"series_budget\"]=0")
    def test_19_series_overrun(self): self.bad("p[\"observed_series\"]=10000")
    def test_20_missing_runbook(self): self.bad("p[\"runbook\"]=\"\"")
    def test_21_missing_environment(self): self.bad("p[\"environment\"]=\"\"")
    def test_22_invalid_timing_type(self): self.bad("p[\"probe_timeout_seconds\"]=\"5\"")
    def test_23_invalid_observed(self): self.bad("p[\"observed_series\"]=-1")
    def test_24_no_allowlist(self): self.bad("p[\"allowed_targets\"]=[]")
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter033
python3 scripts/probe_gate.py fixtures/healthy.json
if python3 scripts/probe_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded policy accepted"; exit 1
else
  echo "PASS: degraded policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **27 authored tests** pass.

## 7. Twenty-four hands-on exercises

1. Understand exporters vs active probes.
2. Run local HTTP service.
3. Configure Blackbox Exporter.
4. Create HTTP 2xx module.
5. Configure Prometheus multi-target relabeling.
6. Inspect /probe response.
7. Inspect probe_success.
8. Measure probe_duration_seconds.
9. Inspect DNS phase.
10. Inspect TLS phase for HTTPS targets.
11. Compare HTTP 2xx and TCP probes.
12. Define synthetic availability SLI.
13. Define probe latency SLO.
14. Design probe_success alert.
15. Test failing HTTP status.
16. Test DNS failure.
17. Test connection refusal.
18. Test timeout.
19. Test target allowlist.
20. Review SSRF threat.
21. Review egress network policy.
22. Review cardinality.
23. Run healthy/degraded policy checks.
24. Run 27 tests and rollback.

## 8. Twenty-four failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 1 | Probe returns 404 | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 2 | Probe returns 500 | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 3 | Connection refused | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 4 | DNS lookup fails | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 5 | TLS chain invalid | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 6 | Certificate expired | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 7 | HTTP redirect unexpected | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 8 | Probe timeout | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 9 | Scrape timeout | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 10 | Blackbox exporter down | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 11 | Prometheus scrape down | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 12 | Target removed from inventory | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 13 | IPv6-only target | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 14 | Wrong module | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 15 | Probe blocked by firewall | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 16 | Service healthy but dependency down | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 17 | Synthetic check misses user journey | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 18 | Latency SLO exceeded | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 19 | Probe cardinality explosion | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 20 | Internal metadata SSRF risk | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 21 | Unapproved external target | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 22 | Wrong service label | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 23 | Alert not routed | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |
| 24 | Recovery notification missing | Inspect probe metrics, exporter scrape, DNS/TLS, route and target inventory |

## 9. Eight operational runbooks

1. **HTTP probe failure:** verify probe_success, HTTP status, application health and upstream dependencies.
2. **DNS failure:** inspect resolver, target hostname, network policy and service discovery.
3. **TLS failure:** inspect certificate validity, chain, SNI and endpoint scheme.
4. **Timeout:** compare probe_timeout, scrape_timeout, service latency and network RTT.
5. **Exporter unavailable:** inspect process, configuration, /metrics, scrape health and restart.
6. **False positive:** validate probe location, redirects, target expectations and response codes.
7. **SSRF/security:** block unapproved target, restrict /probe access and egress, rotate compromised secrets.
8. **Rollback:** restore reviewed config, validate scrape/probe, test synthetic alert and document recovery.

## 10. SRE/DBRE incident tabletop

A Kubernetes-hosted API returns 200 on `/healthz`, but PostgreSQL connections are exhausted and users see 5xx on real requests. Design a representative synthetic user-journey probe and compare it with application error ratios, traces and database exporter metrics. During the drill, disable the target to observe `probe_success`, then remove it from discovery to test the independent missing-target detection plan.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Blackbox architecture and probe design | 20 |
| Local lab and PromQL | 20 |
| SSRF/security and cardinality | 20 |
| Offline policy gate and 27 tests | 20 |
| Incident troubleshooting and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory: approved target inventory, restricted probe access, target failure vs exporter failure differentiation, missing-target policy, rollback and evidence.

## 12. Evidence worksheet

```text
UTC / owner / environment:
Target / module / Blackbox version:
up / probe_success / HTTP status / duration:
Probe location / availability SLO / missing targets:
SSRF and network policy review:
Healthy/degraded gate / 27 tests:
Incident simulation / rollback / reviewer / score:
```

**Companion:** [Chapter 033 Blackbox Exporter lab](labs/033-prometheus-application-exporters-blackbox-exporter-service-availability-monitoring-lab.md).

**Next:** Chapter 034 — Custom Prometheus Exporters, Python Instrumentation, Metric Design and Cardinality Control.
