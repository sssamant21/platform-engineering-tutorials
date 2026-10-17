# Chapter 003 — Observability Architecture, Data Models and Telemetry Governance

**Part 01 — Observability Fundamentals**  
**Audience:** SRE/DBRE, platform engineers, data platform owners, security and compliance teams.  
**Prerequisites:** Chapters 001–002; Python 3.10+; basic JSON and Kubernetes familiarity.

## Outcomes

Design an enterprise telemetry architecture with explicit ownership, data contracts, privacy classification, retention, access boundaries, cardinality budgets, cost allocation, resiliency and evidence. Validate the architecture contract with executable offline tests.

## 1. Reference architecture

```text
Applications / EKS / AKS / GKE / databases / Jenkins
          | SDKs, exporters, agents
          v
     Edge OpenTelemetry Collectors
          | authentication, buffering
          v
       Regional gateways
          | tenant routing, redaction, sampling
          +--------+----------+-----------+
          |        |          |           |
       Metrics     Logs      Traces     Profiles
      Prometheus   Loki      Tempo      Profile backend
          |        |          |           |
          +--------+----------+-----------+
                   |
       Grafana / Alertmanager / on-call
                   |
     SLOs / incident command / RCA / COA
```

Each arrow is a trust and failure boundary. Backend choices are examples; the same governance principles apply to OpenSearch, Elasticsearch, Jaeger and other supported systems.

## 2. Architectural choices

| Decision | Option A | Option B | Tradeoff |
|---|---|---|---|
| Collection | node/sidecar agent | centralized gateway | blast radius versus management |
| Storage | self-hosted | managed | operations burden versus vendor dependency |
| Tenancy | dedicated backend | logical tenant | isolation versus cost |
| Resilience | in-memory retry | durable supported queue | complexity, disk, recovery |
| Trace sampling | head | tail | predictability versus retaining rare failures |
| Data location | regional | global | latency, compliance, cost |
| Retention | hot only | hot/cold tiers | investigation depth versus storage |

Document **why**, owner, cost, rollback and review date in an architecture decision record (ADR).

## 3. Telemetry data models

**Metric:** instrument name, unit, temporality, timestamp, value, bounded attributes and resource identity. Counters, gauges and histograms have different semantics; never derive request rates from an arbitrary gauge.

**Log:** event time, observed time, severity, body, service, environment, trace/span correlation and access classification. Log bodies may contain sensitive data even when labels are clean.

**Trace:** trace ID, span ID, parent ID, operation, start/end time, status, events, links and resource attributes. Span parent IDs are not guaranteed for roots or unsampled upstream context.

**Profile:** sampled stack, process/runtime metadata, CPU or memory measurement and symbolization context. Profile storage can reveal file paths or function names; control access.

**Resource model:** `service.name`, `service.namespace`, `deployment.environment.name`, cloud/cluster and workload identity; pin semantic convention versions where used.

## 4. Governance and classification

Classify telemetry before export:

| Class | Examples | Policy |
|---|---|---|
| Public/synthetic | test spans, fabricated IDs | normal lab handling |
| Internal operational | host names, service maps | access-controlled |
| Confidential | internal query details, sensitive payload metadata | strict minimization and RBAC |
| Restricted | credentials, tokens, PHI/PII | exclude or explicitly approved protected handling |

**Never rely solely on a downstream dashboard to hide restricted data.** Filter at source and approved Collector processing boundaries, and verify that copies are not retained in queues, logs, backups or debug exporters.

## 5. Cardinality, retention and cost

A metric with 20 routes, 5 status classes, 3 environments and 4 regions can yield **1,200 label combinations** before instances or histograms. Histograms can create multiple series per combination. Add request IDs and cardinality becomes unbounded.

Estimate:

```text
active_series ≈ product(distinct label values) × metric variants
ingest_cost ≈ bytes_per_sample × samples_per_second × retention
log_storage ≈ bytes_per_day × retention_days × replication_factor
trace_volume ≈ requests × sampled_fraction × spans_per_request
```

Use these for sizing estimates, not invoice forecasts without measured compression, overhead and backend pricing.

## 6. SRE/DBRE governance scenarios

- **Elasticsearch:** correlate search latency, thread-pool rejections, merge pressure, disk IOPS/throughput and query size; redact request bodies.
- **PostgreSQL:** monitor replication lag, WAL volume, checkpoint latency, locks and pool saturation; avoid raw SQL with credentials.
- **MongoDB:** monitor replica health, oplog window, cache pressure and storage latency; do not export patient documents.
- **Redis:** track CPU, command latency, blocked clients, evictions and memory fragmentation.
- **Kafka:** track consumer lag, broker availability, ISR changes, storage and rebalance events.
- **Kubernetes/Jenkins:** track pod readiness, OOMKilled, agent provisioning, build queue and deployment changes.

## 7. Executable governance contract lab

Directory:

```text
chapter003/
  fixtures/approved.json
  fixtures/rejected.json
  scripts/validate_contract.py
  tests/test_contract.py
```

Create `fixtures/approved.json`:

```json
{
  "service": "search-api",
  "environment": "staging",
  "owner": "platform-sre",
  "data_classification": "internal",
  "region": "us-east-1",
  "approved_regions": ["us-east-1"],
  "retention_days": {"metrics": 30, "logs": 14, "traces": 7, "profiles": 3},
  "max_retention_days": {"metrics": 90, "logs": 30, "traces": 14, "profiles": 7},
  "metric_labels": {"service": 1, "route": 20, "status_class": 5, "environment": 3},
  "series_budget": 500,
  "sample_interval_seconds": 30,
  "sensitive_fields": [],
  "tenant_isolation": true,
  "rbac_reviewed": true,
  "encryption_in_transit": true,
  "encryption_at_rest": true,
  "export_approved": true,
  "cost_center": "platform",
  "incident_contact": "sre-oncall"
}
```

Create `fixtures/rejected.json`:

```json
{
  "service": "search-api",
  "environment": "staging",
  "owner": "",
  "data_classification": "restricted",
  "region": "us-west-2",
  "approved_regions": ["us-east-1"],
  "retention_days": {"metrics": 180, "logs": 60, "traces": 30, "profiles": 14},
  "max_retention_days": {"metrics": 90, "logs": 30, "traces": 14, "profiles": 7},
  "metric_labels": {"service": 1, "patient_id": 100000, "trace_id": 1000000},
  "series_budget": 500,
  "sample_interval_seconds": 0,
  "sensitive_fields": ["authorization", "patient_id"],
  "tenant_isolation": false,
  "rbac_reviewed": false,
  "encryption_in_transit": false,
  "encryption_at_rest": false,
  "export_approved": false,
  "cost_center": "",
  "incident_contact": ""
}
```

Create `scripts/validate_contract.py`:

```python
#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

SIGNALS = ("metrics", "logs", "traces", "profiles")
FORBIDDEN = {"trace_id", "span_id", "request_id", "patient_id", "user_id", "email", "authorization", "token", "password"}

def validate(d):
    errors = []
    for key in ("service", "environment", "owner", "region", "cost_center", "incident_contact"):
        if not isinstance(d.get(key), str) or not d[key].strip():
            errors.append(f"{key} missing")
    if d.get("data_classification") not in ("public", "internal", "confidential", "restricted"):
        errors.append("invalid data_classification")
    regions = d.get("approved_regions")
    if not isinstance(regions, list) or not regions or d.get("region") not in regions:
        errors.append("region not approved")
    retention, maximum = d.get("retention_days"), d.get("max_retention_days")
    if not isinstance(retention, dict) or not isinstance(maximum, dict):
        errors.append("retention objects missing")
    else:
        for signal in SIGNALS:
            actual, limit = retention.get(signal), maximum.get(signal)
            if type(actual) is not int or type(limit) is not int or not 0 < actual <= limit:
                errors.append(f"invalid retention: {signal}")
    labels = d.get("metric_labels")
    series = 1
    if not isinstance(labels, dict) or not labels:
        errors.append("metric_labels must be nonempty object")
    else:
        for name, count in labels.items():
            if name.lower() in FORBIDDEN:
                errors.append(f"forbidden label: {name}")
            if type(count) is not int or count <= 0:
                errors.append(f"invalid cardinality: {name}")
            else:
                series *= count
    budget = d.get("series_budget")
    if type(budget) is not int or budget <= 0:
        errors.append("invalid series_budget")
    elif series > budget:
        errors.append(f"series budget exceeded: {series} > {budget}")
    interval = d.get("sample_interval_seconds")
    if type(interval) is not int or interval <= 0:
        errors.append("invalid sample interval")
    fields = d.get("sensitive_fields")
    if not isinstance(fields, list) or any(not isinstance(x, str) for x in fields):
        errors.append("sensitive_fields must be string list")
    elif fields:
        errors.append("sensitive fields must be removed before export")
    for key in ("tenant_isolation", "rbac_reviewed", "encryption_in_transit", "encryption_at_rest", "export_approved"):
        if d.get(key) is not True:
            errors.append(f"{key} must be true")
    return errors

if __name__ == "__main__":
    errors = validate(json.loads(Path(sys.argv[1]).read_text()))
    print("CONTRACT ACCEPTED: synthetic only" if not errors else "CONTRACT DENIED")
    for error in errors:
        print("-", error)
    sys.exit(bool(errors))
```

Run:

```bash
python3 scripts/validate_contract.py fixtures/approved.json
if python3 scripts/validate_contract.py fixtures/rejected.json; then
  echo "FAIL: rejected fixture accepted"; exit 1
else
  echo "PASS: unsafe contract rejected"
fi
```

## 8. Automated tests

Create `tests/test_contract.py`:

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_contract import validate

class GovernanceTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_approved(self):
        self.assertEqual(validate(self.fixture("approved.json")), [])

    def test_rejected(self):
        self.assertTrue(validate(self.fixture("rejected.json")))

    def test_region(self):
        d = self.fixture("approved.json")
        d["region"] = "unapproved"
        self.assertTrue(validate(d))

    def test_retention(self):
        d = self.fixture("approved.json")
        d["retention_days"]["logs"] = 365
        self.assertTrue(validate(d))

    def test_cardinality(self):
        d = self.fixture("approved.json")
        d["metric_labels"]["route"] = 1000
        self.assertTrue(validate(d))

    def test_sensitive_label(self):
        d = self.fixture("approved.json")
        d["metric_labels"]["patient_id"] = 1
        self.assertTrue(validate(d))

    def test_encryption(self):
        d = self.fixture("approved.json")
        d["encryption_in_transit"] = False
        self.assertTrue(validate(d))

    def test_owner(self):
        d = self.fixture("approved.json")
        d["owner"] = ""
        self.assertTrue(validate(d))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 9. Twenty-four hands-on exercises

1. Draw regional telemetry architecture.
2. Identify sources and signals.
3. Define agent/gateway trust boundaries.
4. Document Collector/backends ownership.
5. Choose self-hosted versus managed backends.
6. Define tenancy isolation model.
7. Define metrics data model.
8. Define structured log schema.
9. Define trace/span correlation.
10. Define profile access controls.
11. Pin semantic convention versions.
12. Classify telemetry sensitivity.
13. Design source-side redaction.
14. Define allowed data regions.
15. Define signal retention periods.
16. Calculate metric label cardinality.
17. Estimate trace and log volume.
18. Define billing and cost center.
19. Define on-call and telemetry SLO.
20. Create approved JSON contract.
21. Create rejected JSON contract.
22. Run positive and negative validation.
23. Run eight automated unit tests.
24. Publish architecture decision and governance review.

## 10. Twenty failure scenarios

| # | Failure | Response |
|---|---|---|
| 01 | Missing telemetry owner | assign RACI |
| 02 | Unauthorized region export | block route |
| 03 | Unbounded patient ID labels | remove and investigate |
| 04 | Excess retention | policy gate |
| 05 | No tenant isolation | deny |
| 06 | RBAC not reviewed | security review |
| 07 | No encryption in transit | stop export |
| 08 | No encryption at rest | storage control |
| 09 | Collector OOM | memory/queue |
| 10 | Gateway saturation | scale and diagnose |
| 11 | Backend outage | retries/loss |
| 12 | Duplicate metric scrape | discovery |
| 13 | Semantic convention drift | version |
| 14 | Missing trace correlation | propagation |
| 15 | Sensitive log body | redact |
| 16 | Profile symbol exposure | access |
| 17 | Series budget exceeded | label control |
| 18 | Missing cost allocation | FinOps |
| 19 | Telemetry SLO blind spot | missing-data alert |
| 20 | Debug exporter enabled in prod | remove |

## 11. Eight production runbooks

**A. Unauthorized data export:** Disable affected pipeline, preserve access evidence, identify downstream copies and engage security/privacy owners.

**B. Cardinality explosion:** Identify new label dimensions, limit ingestion safely, revert instrumentation and review billing impact.

**C. Collector/gateway overload:** Inspect CPU/memory, queue, exporter latency, retry and dropped-record counters; protect high-priority signals.

**D. Backend outage:** Validate ingestion gaps, persistent queue limits, alerting, recovery and data-loss reporting.

**E. Sensitive telemetry exposure:** Quarantine access, stop offending instrumentation, assess retention/backups and follow incident process.

**F. Cross-region routing failure:** Verify region policy, network path, tenant identity, DNS and exporter configuration.

**G. Schema/version drift:** Compare semantic conventions and collector versions, revert incompatible changes and retest.

**H. Cost/retention anomaly:** Audit storage growth, series counts, retention and cost tags; document approved optimization.

## 12. 100-point acceptance

| Domain | Points |
|---|---:|
| Architecture and reliability boundaries | 20 |
| Signal data models and correlation | 20 |
| Privacy, tenancy and regional governance | 20 |
| Cardinality, retention and FinOps | 20 |
| Lab tests, troubleshooting and evidence | 20 |
| **Total** | **100** |

Suggested pass: 85/100 with mandatory gates for ownership, approved region, no restricted fields in exported fixtures, bounded labels, encryption, tenant isolation, positive/negative validation and eight automated tests. Synthetic fixture approval is not live security compliance evidence.

## 13. Evidence worksheet

```text
UTC / service / owner:
Architecture diagram / ADR:
Collector and backend versions:
Signal schemas and classification:
Region/tenancy/access:
Retention/cardinality/cost:
Approved fixture:
Rejected fixture:
Eight automated tests:
20 failure scenarios:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 003 hands-on lab](labs/003-observability-architecture-data-models-telemetry-governance-lab.md).

**Next:** Chapter 004 — Observability Instrumentation Strategy, Sampling and Telemetry Quality.
