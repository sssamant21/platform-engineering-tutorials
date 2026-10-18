# Chapter 034 — Custom Prometheus Exporters, Python Instrumentation, Metric Design and Cardinality Control

**Part 07 — Exporters and Custom Instrumentation**  
**Audience:** SRE/DBRE, platform engineers and application developers.  
**Prerequisites:** Chapters 016–020 and 031–033, Python 3.10+, Prometheus fundamentals.

## 1. Architecture and operational goals

```text
Python service / custom collector
      |
prometheus_client registry
      |
localhost /metrics
      |
Prometheus scrape -> TSDB -> PromQL -> Grafana/Alertmanager
```

Prefer direct application instrumentation for app metrics; use a standalone exporter for systems without native metrics. Avoid placing expensive database queries inside scrape handlers. Design metrics around operational decisions, not every possible object.

## 2. Metric contract

| Type | Appropriate use | Pitfall |
|---|---|---|
| Counter | completed jobs, errors, requests | reset after restart |
| Gauge | queue depth, connections, capacity | stale if not refreshed |
| Histogram | latency/size distributions | buckets × labels amplify series |
| Summary | client-side quantile behavior varies | aggregation limits |

Use base units (seconds, bytes), clear help text, stable names and bounded labels. Prometheus histograms generate `_bucket`, `_sum` and `_count` series. For each unique label combination, a classic histogram with N explicit finite buckets typically generates N+3 time series (including +Inf bucket, sum and count). Estimate worst-case combinations before deploying.

## 3. Complete Python exporter

Create `requirements.txt`:

```text
prometheus-client==0.21.1
```

Create `exporter.py`:

```python
#!/usr/bin/env python3
"""Demo exporter: local only, bounded labels, no database credentials."""
import random,time
from prometheus_client import Counter,Gauge,Histogram,start_http_server
JOBS=Counter("dbre_jobs_total","Jobs processed",["result"])
DURATION=Histogram("dbre_job_duration_seconds","Job duration",["operation"],buckets=(.01,.05,.1,.5,1,5))
QUEUE=Gauge("dbre_queue_depth","Current queued work")
def process():
    start=time.monotonic()
    outcome="ok" if random.random()>.1 else "error"
    time.sleep(random.uniform(.01,.12))
    JOBS.labels(result=outcome).inc()
    DURATION.labels(operation="sync").observe(time.monotonic()-start)
    QUEUE.set(random.randint(0,20))
if __name__=="__main__":
    start_http_server(9108,addr="127.0.0.1")
    while True:
        process();time.sleep(1)
```

Run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python exporter.py
# in another terminal:
curl -fsS http://127.0.0.1:9108/metrics | grep -E '^dbre_'
```

This is a disposable synthetic exporter, not a production database probe. The demo binds to localhost and uses only fixed labels.

## 4. Prometheus scrape configuration

```yaml
scrape_configs:
  - job_name: custom-python
    scrape_interval: 15s
    scrape_timeout: 10s
    static_configs:
      - targets: ["127.0.0.1:9108"]
        labels:
          environment: staging
          cluster: lab
```

The target above works when Prometheus runs on the **same host/network namespace** as the Python process. If Prometheus runs in Docker, `127.0.0.1` refers to its own container; use an approved reachable address and network controls.

## 5. PromQL examples

```promql
sum by (result) (rate(dbre_jobs_total[5m]))
sum(rate(dbre_job_duration_seconds_count[5m]))
histogram_quantile(0.95, sum by (le) (rate(dbre_job_duration_seconds_bucket[5m])))
dbre_queue_depth
up{job="custom-python"}
```

Use `histogram_quantile` only with correct `le` bucket aggregation. A high p95 from a low-volume sample may be noisy; check counts and error budgets before paging.

## 6. Cardinality engineering

For metrics with independent label dimensions, approximate upper bound = product of allowed value counts, multiplied by bucket/summary expansion where relevant. Avoid user IDs, SQL text, trace IDs, pod UIDs, full URLs and timestamps. Track `scrape_samples_scraped`, `scrape_series_added` where available, active series, churn and ingestion cost. Include schema review in pull requests and explicit series budgets.

## 7. Security, reliability and deployment

Use least-privilege runtime, approved image dependencies, protected endpoints and private scrape networks. Do not include secrets or PII/PHI in labels. Instrumentation must fail safely without blocking business logic. Set reasonable timeouts for external data collection, and use dedicated exporter self-health signals. Validate restart behavior, counter resets, metric schema compatibility and rollback.

## 8. Executable offline metric-contract lab

The following JSON is synthetic governance metadata, not Prometheus native configuration. Its gate validates metric naming, types, labels, histogram buckets, series budgets and operational reviews; it does not verify actual scrape output.

Create:

```text
chapter034/
  exporter.py
  requirements.txt
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/metric_gate.py
  tests/test_metric_gate.py
```

### fixtures/healthy.json

```json
{
  "service": "dbre-collector",
  "owner": "dbre",
  "environment": "staging",
  "metrics": [
    {
      "name": "dbre_jobs_total",
      "type": "counter",
      "labels": [
        "result"
      ]
    },
    {
      "name": "dbre_job_duration_seconds",
      "type": "histogram",
      "labels": [
        "operation"
      ],
      "buckets": [
        0.01,
        0.05,
        0.1,
        0.5,
        1,
        5
      ]
    },
    {
      "name": "dbre_queue_depth",
      "type": "gauge",
      "labels": []
    }
  ],
  "allowed_labels": [
    "result",
    "operation"
  ],
  "series_budget": 500,
  "estimated_series": 36,
  "reviewed": true,
  "security_reviewed": true,
  "load_tested": true,
  "rollback_tested": true,
  "runbook": "https://example.org/runbooks/custom-exporter",
  "endpoint_bind": "127.0.0.1",
  "scrape_interval_seconds": 15,
  "scrape_timeout_seconds": 10
}
```

### fixtures/degraded.json

```json
{
  "service": "dbre-collector",
  "owner": "dbre",
  "environment": "staging",
  "metrics": [
    {
      "name": "dbre_jobs_total",
      "type": "counter",
      "labels": [
        "result",
        "user_id"
      ]
    },
    {
      "name": "dbre_job_duration_seconds",
      "type": "histogram",
      "labels": [
        "operation"
      ],
      "buckets": [
        1,
        0.5
      ]
    },
    {
      "name": "dbre_queue_depth",
      "type": "gauge",
      "labels": []
    }
  ],
  "allowed_labels": [
    "result",
    "operation"
  ],
  "series_budget": 500,
  "estimated_series": 10000,
  "reviewed": true,
  "security_reviewed": false,
  "load_tested": true,
  "rollback_tested": true,
  "runbook": "https://example.org/runbooks/custom-exporter",
  "endpoint_bind": "0.0.0.0",
  "scrape_interval_seconds": 15,
  "scrape_timeout_seconds": 10
}
```

### scripts/metric_gate.py

```python
#!/usr/bin/env python3
"""Offline metric-contract validator, not a Prometheus runtime evaluator."""
import json,re,sys
from pathlib import Path
NAME=re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
TYPES={"counter","gauge","histogram"}
ALLOWED={"result","operation","service","environment","cluster","region"}
def validate(p):
    e=[]
    if not isinstance(p,dict): return ["policy must be object"]
    for k in ("service","owner","environment","runbook"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    for k in ("reviewed","security_reviewed","load_tested","rollback_tested"):
        if p.get(k) is not True: e.append("unverified "+k)
    if p.get("endpoint_bind")!="127.0.0.1": e.append("unsafe local bind")
    interval=p.get("scrape_interval_seconds");timeout=p.get("scrape_timeout_seconds")
    if type(interval) is not int or type(timeout) is not int or not 0<timeout<interval<=300: e.append("invalid scrape timing")
    allowed=p.get("allowed_labels")
    if not isinstance(allowed,list) or not set(allowed).issubset(ALLOWED): e.append("unsafe label allowlist");allowed=[]
    metrics=p.get("metrics")
    if not isinstance(metrics,list) or not metrics: e.append("missing metrics");metrics=[]
    names=set()
    for i,m in enumerate(metrics):
        tag="metric "+str(i)
        if not isinstance(m,dict): e.append(tag+" invalid");continue
        n=m.get("name");t=m.get("type");labels=m.get("labels")
        if not isinstance(n,str) or not NAME.fullmatch(n) or n in names: e.append(tag+" invalid name")
        else: names.add(n)
        if t not in TYPES: e.append(tag+" invalid type")
        if t=="counter" and isinstance(n,str) and not n.endswith("_total"): e.append(tag+" counter suffix")
        if t=="histogram" and isinstance(n,str) and not n.endswith("_seconds"): e.append(tag+" histogram unit")
        if not isinstance(labels,list) or len(labels)!=len(set(labels)) or not set(labels).issubset(allowed): e.append(tag+" unsafe labels")
        if t=="histogram":
            buckets=m.get("buckets")
            if not isinstance(buckets,list) or not buckets or any(type(v) not in (int,float) or v<=0 for v in buckets) or buckets!=sorted(set(buckets)): e.append(tag+" invalid buckets")
    budget=p.get("series_budget");estimated=p.get("estimated_series")
    if type(budget) is not int or budget<=0 or type(estimated) is not int or estimated<0: e.append("invalid series budget")
    elif estimated>budget: e.append("series budget exceeded")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 metric_gate.py fixtures/healthy.json")
    try: findings=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit(str(exc))
    print(json.dumps({"status":"FAIL" if findings else "PASS","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_metric_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from metric_gate import validate
class MetricTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def bad(self,change):
        p=copy.deepcopy(self.p);exec(change,{},{"p":p});self.assertTrue(validate(p))
    def test_healthy(self): self.assertEqual(validate(self.p),[])
    def test_degraded(self): self.assertTrue(validate(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(validate(None))
    def test_01_owner(self): self.bad("p[\"owner\"]=\"\"")
    def test_02_review(self): self.bad("p[\"reviewed\"]=False")
    def test_03_security(self): self.bad("p[\"security_reviewed\"]=False")
    def test_04_load(self): self.bad("p[\"load_tested\"]=False")
    def test_05_rollback(self): self.bad("p[\"rollback_tested\"]=False")
    def test_06_bind(self): self.bad("p[\"endpoint_bind\"]=\"0.0.0.0\"")
    def test_07_interval(self): self.bad("p[\"scrape_interval_seconds\"]=0")
    def test_08_timeout(self): self.bad("p[\"scrape_timeout_seconds\"]=15")
    def test_09_allowlist(self): self.bad("p[\"allowed_labels\"].append(\"request_id\")")
    def test_10_missing_metrics(self): self.bad("p[\"metrics\"]=[]")
    def test_11_bad_name(self): self.bad("p[\"metrics\"][0][\"name\"]=\"bad-name\"")
    def test_12_duplicate_name(self): self.bad("p[\"metrics\"][1][\"name\"]=\"dbre_jobs_total\"")
    def test_13_type(self): self.bad("p[\"metrics\"][0][\"type\"]=\"summary2\"")
    def test_14_counter_suffix(self): self.bad("p[\"metrics\"][0][\"name\"]=\"dbre_jobs\"")
    def test_15_histogram_unit(self): self.bad("p[\"metrics\"][1][\"name\"]=\"dbre_job_duration\"")
    def test_16_unsafe_label(self): self.bad("p[\"metrics\"][0][\"labels\"].append(\"user_id\")")
    def test_17_duplicate_label(self): self.bad("p[\"metrics\"][0][\"labels\"].append(\"result\")")
    def test_18_buckets_unsorted(self): self.bad("p[\"metrics\"][1][\"buckets\"]=[1,0.5]")
    def test_19_buckets_duplicate(self): self.bad("p[\"metrics\"][1][\"buckets\"]=[1,1]")
    def test_20_buckets_negative(self): self.bad("p[\"metrics\"][1][\"buckets\"]=[-1,1]")
    def test_21_budget(self): self.bad("p[\"series_budget\"]=0")
    def test_22_over_budget(self): self.bad("p[\"estimated_series\"]=9000")
    def test_23_missing_runbook(self): self.bad("p[\"runbook\"]=\"\"")
    def test_24_negative_estimate(self): self.bad("p[\"estimated_series\"]=-1")
if __name__=="__main__": unittest.main()
```

### Run offline tests

```bash
cd chapter034
python3 scripts/metric_gate.py fixtures/healthy.json
if python3 scripts/metric_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe metric contract accepted"; exit 1
else
  echo "PASS: unsafe contract rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, **27 authored tests** pass.

## 9. Twenty-four exercises

1. Install prometheus-client.
2. Define a bounded counter.
3. Define a gauge.
4. Define a duration histogram.
5. Explain buckets and quantiles.
6. Start localhost metrics server.
7. Inspect /metrics.
8. Configure Prometheus scrape.
9. Query counter rate.
10. Query histogram rate.
11. Calculate histogram_quantile.
12. Identify reset semantics.
13. Measure queue depth.
14. Review instrumentation overhead.
15. Review label allowlist.
16. Estimate histogram series.
17. Review multiprocess instrumentation risks.
18. Protect metrics endpoint.
19. Add exporter self-health.
20. Simulate load spike.
21. Review cardinality growth.
22. Run healthy policy gate.
23. Reject degraded policy.
24. Run 27 tests and rollback.

## 10. Twenty-four failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 1 | Exporter process crashes | Inspect metric registry, scrape target, labels, process and recent deployment |
| 2 | Endpoint unreachable | Inspect metric registry, scrape target, labels, process and recent deployment |
| 3 | Wrong scrape port | Inspect metric registry, scrape target, labels, process and recent deployment |
| 4 | Counter reset after restart | Inspect metric registry, scrape target, labels, process and recent deployment |
| 5 | Unbounded request ID label | Inspect metric registry, scrape target, labels, process and recent deployment |
| 6 | Per-user metrics explosion | Inspect metric registry, scrape target, labels, process and recent deployment |
| 7 | Histogram buckets unsorted | Inspect metric registry, scrape target, labels, process and recent deployment |
| 8 | Histogram cardinality too high | Inspect metric registry, scrape target, labels, process and recent deployment |
| 9 | Gauge never updated | Inspect metric registry, scrape target, labels, process and recent deployment |
| 10 | Metric name collision | Inspect metric registry, scrape target, labels, process and recent deployment |
| 11 | Counter suffix missing | Inspect metric registry, scrape target, labels, process and recent deployment |
| 12 | Incorrect units | Inspect metric registry, scrape target, labels, process and recent deployment |
| 13 | High instrumentation CPU | Inspect metric registry, scrape target, labels, process and recent deployment |
| 14 | Slow collection | Inspect metric registry, scrape target, labels, process and recent deployment |
| 15 | Exporter exposes credentials | Inspect metric registry, scrape target, labels, process and recent deployment |
| 16 | Metrics endpoint public | Inspect metric registry, scrape target, labels, process and recent deployment |
| 17 | Prometheus scrape timeout | Inspect metric registry, scrape target, labels, process and recent deployment |
| 18 | Stale series | Inspect metric registry, scrape target, labels, process and recent deployment |
| 19 | Unexpected missing metric | Inspect metric registry, scrape target, labels, process and recent deployment |
| 20 | Metric label churn | Inspect metric registry, scrape target, labels, process and recent deployment |
| 21 | Duplicate registration | Inspect metric registry, scrape target, labels, process and recent deployment |
| 22 | Multiprocess aggregation error | Inspect metric registry, scrape target, labels, process and recent deployment |
| 23 | SLO latency misleading | Inspect metric registry, scrape target, labels, process and recent deployment |
| 24 | Rollback not documented | Inspect metric registry, scrape target, labels, process and recent deployment |

## 11. Eight production runbooks

1. Exporter unavailable: check process, bind, /metrics and scrape target.
2. Cardinality explosion: inspect labels, active series, churn and scrape samples.
3. Histogram mismatch: review buckets, unit, observation count and rate windows.
4. Counter reset: use rate/increase and verify process restarts.
5. Performance regression: profile instrumentation overhead and expensive callbacks.
6. Security incident: restrict endpoint, sanitize labels and rotate leaked credentials.
7. Metric schema migration: dual-publish carefully, update queries and dashboards, then remove old names.
8. Rollback: restore approved code, verify scrape and alert behavior, archive evidence.

## 12. SRE/DBRE incident simulation

A Python collector for PostgreSQL queue processing adds `query_text` and `request_id` labels. Prometheus active series surge, scrape latency rises and SLO dashboards become stale. Roll back the instrumentation, restore bounded labels and compare series and scrape duration before/after. Use synthetic data only.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| Metric semantics and naming | 20 |
| Python exporter and PromQL | 20 |
| Cardinality, security and performance | 20 |
| Offline gate and 27 tests | 20 |
| Troubleshooting and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: bounded labels, approved registry schema, secure endpoint, cost budget, tests and rollback.

## 14. Evidence

```text
UTC / owner / environment:
Exporter version / Python dependency:
Metrics names / types / label values:
Series estimate / observed series:
Scrape and query verification:
Healthy/degraded gate / 27 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 034 custom exporter lab](labs/034-custom-prometheus-exporters-python-instrumentation-metric-design-cardinality-control-lab.md).

**Next:** Chapter 035 — Enterprise Exporter Integration, Metrics Governance and Production Readiness Capstone.
