# Chapter 005 — Observability Fundamentals Production Readiness and Reliability Capstone

**Part 01 — Observability Fundamentals (Final Capstone)**  
**Audience:** SRE/DBRE, platform engineering, application owners, incident commanders.  
**Prerequisites:** Chapters 001–004, Python 3.10+, basic metrics/logs/traces and SLO arithmetic.

## Mission and acceptance

Build an enterprise observability acceptance plan for a synthetic patient-search API backed by Elasticsearch, PostgreSQL, Redis and Kafka. Validate **service SLOs**, **telemetry pipeline reliability**, **trace/log correlation**, **privacy and cardinality controls**, and **incident readiness**. This is a local, offline synthetic lab: passing does not certify production.

## 1. Reference architecture

```text
API Gateway -> patient-search-api -> Elasticsearch
                         |         -> PostgreSQL
                         |         -> Redis
                         |         -> Kafka
                         v
       OpenTelemetry SDKs / exporters / agents
                         |
               Regional Collector gateway
           auth -> redact -> memory -> batch
                  /         |         \
              metrics      logs       traces
            Prometheus     Loki      Tempo
                  \         |         /
                    Grafana / alerts
                          |
                   SLO + on-call
                          |
                   RCA / COA / DR
```

The architecture must specify owner, trust boundaries, data region, tenant isolation, collection failure modes, backpressure, recovery and cost. Collector capabilities vary by distribution and version; test pinned versions before staging deployment.

## 2. End-to-end acceptance checklist

| Domain | Acceptance criterion | Evidence |
|---|---|---|
| Ownership | service and telemetry pipeline owners assigned | service catalog |
| Availability | good/eligible events and SLO defined | metric/SLI spec |
| Latency | latency-good events or threshold documented | histogram design |
| Metrics | bounded labels and valid units | cardinality review |
| Logs | structured, correlated, privacy-filtered | synthetic sample |
| Traces | valid W3C context and useful span tree | trace review |
| Profiles | opt-in, access-controlled | profiling policy |
| Pipeline | completeness, freshness and drops tracked | collector SLIs |
| Security | restricted data excluded, encryption/RBAC | control checklist |
| Incident response | alert routing and runbooks tested | tabletop |
| Resilience | queue/retry/DR behavior defined | failure drill |
| FinOps | retention and series budget approved | cost worksheet |

## 3. SLI, SLO and error budgets

```text
availability = good_requests / eligible_requests
allowed_bad = floor(eligible_requests × (1 - slo_target))
remaining = allowed_bad - (eligible_requests - good_requests)
pipeline_completeness = received_telemetry / expected_telemetry
pipeline_drop_rate = dropped_telemetry / (received_telemetry + dropped_telemetry)
correlation = correlated_logs / eligible_logs
```

Choose eligible requests explicitly. For a 99.9% SLO and 100,000 eligible requests, 100 failures exhaust the event-count budget. Event-count budgets do not replace time-window burn-rate policies. Traces are often sampled; do not use sampled trace counts as the denominator for unsampled availability SLIs.

## 4. Production failure hypotheses

**Scenario A — Elasticsearch search slowness:** p95 latency increases with disk queue depth, IOPS pressure and search thread-pool rejections. Correlate metrics with trace spans and slowlog summaries; inspect query page size and shard sizing before scaling.

**Scenario B — PostgreSQL replication lag:** replication delay increases after write burst; correlate WAL generation, replay lag, storage and network diagnostics.

**Scenario C — Redis saturation:** single-threaded command execution pressure, high CPU and blocked clients cause request tail latency; examine command mix and upstream retry storm.

**Scenario D — Kafka lag:** consumer lag rises after rebalance or downstream slowness; correlate partitions, ISR, processing time and retry behavior.

**Scenario E — telemetry outage:** Collector queue saturates; alerts based solely on application metrics may become silent. Maintain missing-data alerts and independent health signals.

## 5. Executable acceptance gate

Create:

```text
chapter005/
  fixtures/approved.json
  fixtures/rejected.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

### fixtures/approved.json

```json
{
  "service": "patient-search-api",
  "environment": "staging",
  "service_owner": "app-sre",
  "telemetry_owner": "platform-sre",
  "eligible_requests": 100000,
  "good_requests": 99950,
  "slo_target": 0.999,
  "expected_telemetry": 10000,
  "received_telemetry": 9998,
  "dropped_telemetry": 2,
  "eligible_logs": 1000,
  "correlated_logs": 999,
  "freshness_p95_seconds": 10,
  "max_freshness_p95_seconds": 30,
  "metric_labels": {"service": 1, "route": 20, "status_class": 5, "environment": 3},
  "max_series": 500,
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
  "log_trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "sensitive_fields": [],
  "approved_region": "us-east-1",
  "export_region": "us-east-1",
  "retention_days": 14,
  "max_retention_days": 30,
  "rbac_reviewed": true,
  "encrypted": true,
  "oncall_routed": true,
  "runbook_reviewed": true
}
```

### fixtures/rejected.json

```json
{
  "service": "patient-search-api",
  "environment": "staging",
  "service_owner": "",
  "telemetry_owner": "",
  "eligible_requests": 100000,
  "good_requests": 98000,
  "slo_target": 0.999,
  "expected_telemetry": 10000,
  "received_telemetry": 9000,
  "dropped_telemetry": 1000,
  "eligible_logs": 1000,
  "correlated_logs": 500,
  "freshness_p95_seconds": 120,
  "max_freshness_p95_seconds": 30,
  "metric_labels": {"service": 1, "patient_id": 1000000},
  "max_series": 500,
  "traceparent": "00-00000000000000000000000000000000-0000000000000000-01",
  "log_trace_id": "not-a-trace",
  "sensitive_fields": ["authorization", "patient_id"],
  "approved_region": "us-east-1",
  "export_region": "us-west-2",
  "retention_days": 90,
  "max_retention_days": 30,
  "rbac_reviewed": false,
  "encrypted": false,
  "oncall_routed": false,
  "runbook_reviewed": false
}
```

### scripts/acceptance.py

```python
#!/usr/bin/env python3
import json
import math
import re
import sys
from pathlib import Path

TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
FORBIDDEN = {"patient_id", "user_id", "trace_id", "span_id", "request_id", "email", "token", "authorization"}

def check(d):
    errors = []
    for key in ("service", "environment", "service_owner", "telemetry_owner"):
        if not isinstance(d.get(key), str) or not d[key].strip():
            errors.append(f"missing {key}")
    for key in ("eligible_requests", "good_requests", "expected_telemetry", "received_telemetry", "dropped_telemetry", "eligible_logs", "correlated_logs"):
        if type(d.get(key)) is not int or d[key] < 0:
            errors.append(f"invalid {key}")
    if any(e.startswith("invalid ") for e in errors):
        return errors
    eligible, good = d["eligible_requests"], d["good_requests"]
    target = d.get("slo_target")
    if eligible == 0 or good > eligible or type(target) not in (int, float) or not 0 < target < 1:
        errors.append("invalid SLO counts/target")
    else:
        allowed = math.floor(eligible * (1 - target) + 1e-9)
        if eligible - good > allowed:
            errors.append(f"availability SLO exceeded: bad={eligible-good}, allowed={allowed}")
    expected, received, dropped = (d[k] for k in ("expected_telemetry", "received_telemetry", "dropped_telemetry"))
    if expected == 0 or received > expected or received + dropped > expected:
        errors.append("invalid telemetry counts")
    elif received / expected < 0.999 or dropped / max(received + dropped, 1) > 0.001:
        errors.append("telemetry loss/completeness threshold breached")
    logs, correlated = d["eligible_logs"], d["correlated_logs"]
    if logs == 0 or correlated > logs or correlated / logs < 0.998:
        errors.append("log correlation threshold breached")
    freshness, max_freshness = d.get("freshness_p95_seconds"), d.get("max_freshness_p95_seconds")
    if type(freshness) not in (int, float) or type(max_freshness) not in (int, float) or freshness < 0 or max_freshness <= 0:
        errors.append("invalid freshness")
    elif freshness > max_freshness:
        errors.append("telemetry freshness breached")
    labels, budget = d.get("metric_labels"), d.get("max_series")
    if not isinstance(labels, dict) or not labels or type(budget) is not int or budget <= 0:
        errors.append("invalid metric contract")
    else:
        series = 1
        for name, value in labels.items():
            if name.lower() in FORBIDDEN:
                errors.append(f"forbidden metric label: {name}")
            if type(value) is not int or value <= 0:
                errors.append(f"invalid cardinality: {name}")
            else:
                series *= value
        if series > budget:
            errors.append(f"metric series budget exceeded: {series} > {budget}")
    tp = d.get("traceparent")
    match = TP.fullmatch(tp) if isinstance(tp, str) else None
    if not match or int(match[1], 16) == 0 or int(match[2], 16) == 0:
        errors.append("invalid traceparent")
    elif d.get("log_trace_id") != match[1]:
        errors.append("trace/log correlation mismatch")
    sensitive = d.get("sensitive_fields")
    if not isinstance(sensitive, list) or any(not isinstance(x, str) for x in sensitive):
        errors.append("invalid sensitive_fields")
    elif sensitive:
        errors.append("sensitive fields in export")
    if not isinstance(d.get("approved_region"), str) or not d["approved_region"] or d.get("export_region") != d["approved_region"]:
        errors.append("unapproved export region")
    retention, limit = d.get("retention_days"), d.get("max_retention_days")
    if type(retention) is not int or type(limit) is not int or not 0 < retention <= limit:
        errors.append("invalid retention")
    for key in ("rbac_reviewed", "encrypted", "oncall_routed", "runbook_reviewed"):
        if d.get(key) is not True:
            errors.append(f"missing required control: {key}")
    return errors

if __name__ == "__main__":
    errors = check(json.loads(Path(sys.argv[1]).read_text()))
    print("CAPSTONE PASS: synthetic only" if not errors else "CAPSTONE FAIL")
    for error in errors:
        print("-", error)
    sys.exit(bool(errors))
```

Run:

```bash
python3 scripts/acceptance.py fixtures/approved.json
if python3 scripts/acceptance.py fixtures/rejected.json; then
  echo "FAIL: rejected fixture accepted"; exit 1
else
  echo "PASS: rejected fixture denied"
fi
```

### tests/test_acceptance.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acceptance import check

class CapstoneTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_approved(self):
        self.assertEqual(check(self.fixture("approved.json")), [])

    def test_rejected(self):
        self.assertTrue(check(self.fixture("rejected.json")))

    def test_availability(self):
        d = self.fixture("approved.json")
        d["good_requests"] = 99000
        self.assertTrue(check(d))

    def test_telemetry_loss(self):
        d = self.fixture("approved.json")
        d["dropped_telemetry"] = 100
        self.assertTrue(check(d))

    def test_correlation(self):
        d = self.fixture("approved.json")
        d["log_trace_id"] = "f" * 32
        self.assertTrue(check(d))

    def test_sensitive_label(self):
        d = self.fixture("approved.json")
        d["metric_labels"]["patient_id"] = 1
        self.assertTrue(check(d))

    def test_region(self):
        d = self.fixture("approved.json")
        d["export_region"] = "us-west-2"
        self.assertTrue(check(d))

    def test_oncall(self):
        d = self.fixture("approved.json")
        d["oncall_routed"] = False
        self.assertTrue(check(d))

    def test_retention(self):
        d = self.fixture("approved.json")
        d["retention_days"] = 365
        self.assertTrue(check(d))

    def test_freshness(self):
        d = self.fixture("approved.json")
        d["freshness_p95_seconds"] = 100
        self.assertTrue(check(d))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 6. Twenty-four hands-on acceptance exercises

1. Define service/telemetry owners.
2. Draw end-to-end telemetry topology.
3. Identify trust boundaries.
4. Document signal data models.
5. Define API availability SLI.
6. Calculate SLO error budget.
7. Define latency SLI.
8. Select bounded metric labels.
9. Define log redaction policy.
10. Validate W3C traceparent.
11. Validate log/trace correlation.
12. Define profile security policy.
13. Define Collector queue/loss SLI.
14. Define telemetry freshness SLI.
15. Document sampling tradeoffs.
16. Document approved export region.
17. Document retention and cost budgets.
18. Review RBAC and encryption.
19. Review on-call routing.
20. Create approved fixture.
21. Create rejected fixture.
22. Execute positive/negative checks.
23. Run ten automated tests.
24. Produce acceptance evidence and incident action plan.

## 7. Twenty production failure drills

| # | Failure | Primary response |
|---|---|---|
| 01 | Elasticsearch disk IOPS saturation | correlate search/IO |
| 02 | Elasticsearch thread-pool rejections | inspect load/query |
| 03 | PostgreSQL replication lag | WAL/replay/storage |
| 04 | MongoDB replication delay | oplog/cache/network |
| 05 | Redis CPU saturation | command mix |
| 06 | Kafka consumer lag | partition/consumer |
| 07 | Kubernetes pod OOM | memory/limits |
| 08 | Jenkins agent queue saturation | provisioning |
| 09 | Collector exporter timeout | retry/backend |
| 10 | Collector queue full | pressure/loss |
| 11 | Missing metrics | absence alert |
| 12 | Missing logs | pipeline |
| 13 | Broken trace propagation | context |
| 14 | Cardinality explosion | label rollback |
| 15 | PHI/PII leakage | security response |
| 16 | Cross-region telemetry export | route isolation |
| 17 | SLO burn spike | incident mitigation |
| 18 | Alert noise | policy/ownership |
| 19 | Missing on-call routing | escalation |
| 20 | Backup/restore telemetry gap | DR validation |

## 8. Eight production runbooks

**A. API SLO burn:** Validate denominator, error and latency trends, recent changes, dependencies and mitigation; communicate impact and preserve evidence.

**B. Elasticsearch search latency:** Correlate search slowlogs, query sizes, IOPS/throughput, disk latency and rejection counters; prioritize safe workload reduction.

**C. PostgreSQL/Redis/Kafka dependency degradation:** Separate user impact from infrastructure diagnostics; trace critical path, throttle/retry safely, escalate to owner.

**D. Telemetry pipeline outage:** Check Collector health, exporter failures, queue utilization, dropped records, backend availability and independent missing-data alerts.

**E. Sensitive telemetry incident:** Stop offending export, restrict access, preserve evidence, identify downstream copies and invoke privacy/security response.

**F. Cardinality and FinOps incident:** Identify new dimensions, cap or roll back, estimate ingestion/storage impact and document change review.

**G. SLO and alerting false positives:** Audit SLI definition, sample completeness, time windows and alert thresholds; avoid disabling critical alerts blindly.

**H. Production readiness review:** Collect ownership, schema, privacy, retention, on-call, runbook, DR and acceptance evidence; reject unsupported sign-off.

## 9. 100-point capstone scorecard

| Domain | Points |
|---|---:|
| Architecture and ownership | 20 |
| SLIs/SLOs and signal correctness | 20 |
| Telemetry quality and correlation | 20 |
| Privacy, security, cardinality and FinOps | 20 |
| Tests, incident drills and evidence | 20 |
| **Total** | **100** |

Recommended pass: 85/100 with mandatory gates for SLO correctness, synthetic negative-test rejection, sensitive-data exclusion, bounded labels, regional routing, encryption, on-call and ten automated tests.

## 10. Evidence package

```text
UTC / service / service owner / telemetry owner:
Topology and trust boundaries:
SLI/SLO and error budget:
Metric/log/trace/profile contracts:
Pipeline quality and sampling:
Privacy/region/retention/cost:
Approved fixture:
Rejected fixture:
Ten unit tests:
20 failure drills:
Eight runbooks:
Score / open risks / RCA / COA / reviewer:
```

**Companion:** [Chapter 005 capstone lab](labs/005-observability-fundamentals-production-readiness-reliability-capstone-lab.md).

**Next:** Chapter 006 — Linux Observability Architecture, CPU, Memory, Disk and Network Monitoring (Part 02).
