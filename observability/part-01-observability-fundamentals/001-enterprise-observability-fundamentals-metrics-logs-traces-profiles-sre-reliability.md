# Chapter 001 — Enterprise Observability Fundamentals: Metrics, Logs, Traces, Profiles and SRE Reliability Engineering

**Part 01 — Observability Fundamentals**  
**Audience:** SRE, DBRE, DevOps, platform engineering, incident commanders.  
**Prerequisites:** Python 3.10+, terminal, Git; Docker optional.

## Learning objectives

Explain monitoring versus observability, choose telemetry signals, distinguish service health from host health, design cardinality-safe instrumentation, calculate an availability SLI, identify trace/log correlation, and validate a synthetic production incident using an executable local lab.

## 1. Monitoring versus observability

Monitoring answers predetermined questions: is the service up, is disk usage above a threshold, and did an alert fire? Observability enables investigating unfamiliar failure modes by combining high-quality telemetry and system context. Both require instrumentation, ownership, retention, access control and actionable response.

**Four core signals:**
- **Metrics:** aggregated measurements over time, e.g. request rate, latency histogram, errors, queue length, PostgreSQL replication lag, Redis CPU.
- **Logs:** discrete events with timestamps, severity, service, environment and correlation identifiers. Avoid PHI/PII, credentials and high-cardinality log labels.
- **Traces:** parent-child spans representing requests across services; trace IDs connect gateway, API, database and queue work.
- **Profiles:** sampled CPU, allocation and other resource activity revealing code-level hotspots; protect stack frames and symbol data.

Additional context: events, exemplars, service catalog, deploy markers, topology and runbook links.

## 2. Architecture and telemetry flow

```text
App/API/DB/Kubernetes/Jenkins
      | metrics logs traces profiles
      v
 OpenTelemetry SDK / exporters / agents
      |
 Collector receivers -> processors -> exporters
      |               |           |
 Prometheus         Loki        Tempo/Jaeger
      |               |           |
      +------------ Grafana ------+
                        |
             Alertmanager / on-call
                        |
            SLOs, incidents, RCA/COA
```

OpenTelemetry instrumentation and collection are vendor-neutral building blocks; exporters and backends have different data models, retention and capabilities. Prometheus is a metric monitoring system, not a universal telemetry database.

## 3. Golden signals and USE methodology

For a request-serving service, measure **latency, traffic, errors and saturation**. For infrastructure, apply **utilization, saturation and errors (USE)**. Examples:

| Workload | User-facing SLI | Supporting diagnostic |
|---|---|---|
| API | successful requests / eligible requests | p95 latency, CPU throttling |
| Elasticsearch | successful searches / eligible searches | search latency, rejections, disk IOPS |
| PostgreSQL | successful transactions / attempts | WAL lag, locks, checkpoints |
| MongoDB | successful operations / attempts | replication lag, cache eviction |
| Redis | successful commands / attempts | CPU, blocked clients, evictions |
| Kafka | delivered messages / expected | consumer lag, ISR shrink |
| Jenkins | successful eligible CI operations | queue wait, agent provisioning |

Avoid confusing high CPU utilization with an actual customer-impacting outage; correlate with error and latency SLIs.

## 4. Cardinality and data hygiene

Do not attach user ID, patient ID, request ID, raw SQL, full URL or arbitrary trace ID as metric labels. Use bounded labels such as service, environment, route template, operation and status class. Request/trace IDs belong in access-controlled logs or spans. Apply sampling, retention and RBAC to manage cost and risk.

## 5. SLI, SLO and error-budget arithmetic

For event-based availability:

```text
SLI = good_events / eligible_events
bad_events = eligible_events - good_events
allowed_bad_events = floor(eligible_events × (1 - target))
remaining_budget = allowed_bad_events - bad_events
```

Example: 10,000 eligible requests, 9,990 good requests, target 99.9%. SLI = 99.9%, bad = 10, allowed = 10, remaining = 0. A passing SLO with zero remaining budget requires careful change policy. The eligible-event definition must be approved and must not silently exclude failures.

For latency, define the threshold and measure the fraction of eligible requests below it. A p95 latency chart alone is not an error-budget accounting method.

## 6. Hands-on architecture

The local lab reads **synthetic JSON** telemetry representing an Elasticsearch-backed patient search API, detects degraded availability and latency, and checks signal correlation. It does not contact production or process patient data.

Directory:

```text
chapter001/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/assess.py
  tests/test_assess.py
```

Create `scripts/assess.py`:

```python
#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

def assess(d):
    errors = []
    for key in ("service", "environment", "trace_id", "log_correlation_id"):
        if not isinstance(d.get(key), str) or not d[key].strip():
            errors.append(f"missing {key}")
    for key in ("eligible", "good", "latency_p95_ms", "latency_slo_ms"):
        if type(d.get(key)) is not int or d[key] < 0:
            errors.append(f"invalid {key}")
    if errors:
        return errors
    if d["eligible"] == 0 or d["good"] > d["eligible"] or d["latency_slo_ms"] == 0:
        return ["invalid denominator, counts or latency threshold"]
    if not isinstance(d.get("slo_target"), (float, int)) or isinstance(d.get("slo_target"), bool) or not 0 < d["slo_target"] < 1:
        return ["invalid slo_target"]
    if d["trace_id"] != d["log_correlation_id"]:
        errors.append("log/trace correlation mismatch")
    bad = d["eligible"] - d["good"]
    budget = math.floor(d["eligible"] * (1 - d["slo_target"]) + 1e-9)
    if bad > budget:
        errors.append(f"availability budget exceeded: bad={bad}, allowed={budget}")
    if d["latency_p95_ms"] > d["latency_slo_ms"]:
        errors.append("p95 latency diagnostic threshold breached")
    return errors

if __name__ == "__main__":
    issues = assess(json.loads(Path(sys.argv[1]).read_text()))
    print("HEALTHY SYNTHETIC FIXTURE" if not issues else "DEGRADED SYNTHETIC FIXTURE")
    for issue in issues:
        print("-", issue)
    sys.exit(bool(issues))
```

Create `fixtures/healthy.json`:

```json
{"service":"patient-search-api","environment":"staging","trace_id":"demo-trace-001","log_correlation_id":"demo-trace-001","eligible":10000,"good":9995,"slo_target":0.999,"latency_p95_ms":150,"latency_slo_ms":300}
```

Create `fixtures/degraded.json`:

```json
{"service":"patient-search-api","environment":"staging","trace_id":"demo-trace-002","log_correlation_id":"different-id","eligible":10000,"good":9800,"slo_target":0.999,"latency_p95_ms":950,"latency_slo_ms":300}
```

Run:

```bash
python3 scripts/assess.py fixtures/healthy.json
if python3 scripts/assess.py fixtures/degraded.json; then
  echo "FAIL: degradation not detected"; exit 1
else
  echo "PASS: degradation detected"
fi
```

## 7. Automated tests

Create `tests/test_assess.py`:

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess import assess

class Tests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_healthy(self):
        self.assertEqual(assess(self.load("healthy.json")), [])

    def test_degraded(self):
        self.assertTrue(assess(self.load("degraded.json")))

    def test_invalid_counts(self):
        d = self.load("healthy.json")
        d["good"] = 10001
        self.assertTrue(assess(d))

    def test_missing_trace_correlation(self):
        d = self.load("healthy.json")
        d["log_correlation_id"] = "other"
        self.assertTrue(assess(d))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 8. Twenty hands-on exercises

1. Define monitoring and observability.
2. Classify metrics, logs, traces and profiles.
3. Draw the telemetry pipeline.
4. Identify service owners.
5. Define an API availability SLI.
6. Define latency SLI and threshold.
7. Calculate an error budget.
8. Choose bounded metric labels.
9. Identify sensitive telemetry fields.
10. Define log correlation keys.
11. Define span attributes and trace sampling.
12. Identify CPU profiling use cases.
13. Select Elasticsearch IOPS diagnostics.
14. Select PostgreSQL replication diagnostics.
15. Select Redis saturation diagnostics.
16. Create healthy synthetic fixture.
17. Create degraded synthetic fixture.
18. Execute positive and negative checks.
19. Execute automated tests.
20. Produce an incident evidence summary.

## 9. Twelve failure scenarios

| Failure | Investigation |
|---|---|
| Missing metrics | scrape/discovery/permissions |
| Missing logs | collector routing |
| Broken trace propagation | context headers |
| Metric cardinality explosion | label design |
| Sensitive identifiers in labels | privacy incident |
| Alert noise | ownership and SLO policy |
| Silent telemetry outage | heartbeat/absence alert |
| Collector backpressure | queue/retry/storage |
| High Elasticsearch latency | search/IOPS/queue |
| PostgreSQL WAL lag | replication/checkpoints |
| Redis CPU saturation | command mix and single-thread behavior |
| Budget burn with healthy host CPU | request path analysis |

## 10. Six production runbooks

**A. Telemetry outage:** Validate source, agent, collector, backend, time synchronization and ingestion gaps; declare visibility degradation.

**B. API SLO breach:** Identify eligible events, latency, errors, recent deploys, traces and database dependencies; mitigate and preserve timeline.

**C. Cardinality/cost spike:** Identify new labels, limit ingestion safely, preserve required forensic data and revert instrumentation.

**D. Elasticsearch search slowness:** Correlate slowlog, queue rejections, disk throughput/IOPS and query patterns; reduce load and escalate capacity.

**E. Database replication lag:** Inspect write rate, storage, WAL/oplog, replica resource pressure and recovery objectives.

**F. Broken trace/log correlation:** Verify context propagation, trace IDs, sampling, logger enrichment and privacy constraints.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Theory and signal selection | 20 |
| Architecture and privacy | 20 |
| SLI/SLO and error-budget math | 20 |
| Runnable lab and automated tests | 20 |
| Troubleshooting/runbooks/evidence | 20 |
| **Total** | **100** |

Passing recommendation: 85/100, with mandatory privacy, correlation and synthetic negative-test gates. **A synthetic pass is not proof of a live production monitoring deployment.**

## 12. Evidence template

```text
UTC / service / owner:
Telemetry architecture:
Signals and bounded labels:
SLI/SLO/error budget:
Healthy fixture result:
Degraded fixture result:
Unit tests:
Incident hypotheses:
Runbook references:
Score / gaps / RCA / COA / reviewer:
```

**Companion:** [Chapter 001 executable lab](labs/001-enterprise-observability-fundamentals-metrics-logs-traces-profiles-sre-reliability-lab.md).

**Next:** Chapter 002 — Observability Signals, Telemetry Pipelines and Context Propagation.
