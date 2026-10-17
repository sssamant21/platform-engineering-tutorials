# Chapter 004 — Observability Instrumentation Strategy, Sampling and Telemetry Quality

**Part 01 — Observability Fundamentals**  
**Audience:** SRE, DBRE, platform engineering, service owners and observability platform teams.  
**Prerequisites:** Chapters 001–003; Python 3.10+; basic HTTP and telemetry concepts.

## Objectives

Create an instrumentation plan for metrics, logs, traces and profiles; choose sampling strategies, enforce data quality and cardinality budgets, and validate telemetry completeness using executable synthetic tests. Distinguish instrumentation quality from downstream backend availability.

## 1. Instrumentation as a production interface

Observability is a product of **signal quality × context quality × delivery reliability × investigation usability**. A perfectly available backend is not useful if request errors are misclassified or span attributes lack service identity.

Define a contract per service:

| Area | Required contract |
|---|---|
| Ownership | service, team, on-call and escalation |
| SLIs | eligible events, good events, latency threshold |
| Metrics | names, units, instrument type, bounded dimensions |
| Logs | timestamp, severity, event, service, trace_id |
| Traces | parent context, span name, status, resource attributes |
| Profiles | runtime, sampling policy, sensitive symbol controls |
| Quality | completeness, freshness, correlation, drop/loss budget |
| Governance | classification, retention, regional routing, RBAC |
| Change | versioned schema, rollout, rollback, tests |

## 2. Instrumentation patterns

**Automatic instrumentation** gives rapid HTTP/DB/client spans but may omit domain-specific success criteria. **Manual instrumentation** adds business SLIs, critical spans and application error classification, at the cost of developer maintenance. Use both deliberately.

### API example

```text
GET /patients/{id}/summary
   -> HTTP server span
      -> authorization span
      -> search service client span
         -> Elasticsearch search span
      -> response serialization span
```

Use the **route template**, never raw patient IDs, as a metric label. Sensitive request/response payloads should not enter logs, spans, metric labels or baggage.

### Database and platform examples

- Elasticsearch: query latency histograms, threadpool rejections, disk IOPS, shard pressure; redact raw query bodies.
- PostgreSQL: transaction success, WAL lag, lock waits, connection saturation and checkpoints.
- MongoDB: operation latency, replication lag, WiredTiger cache and oplog window.
- Redis: command latency, blocked clients, evictions and CPU saturation.
- Kafka: producer/consumer latency, consumer lag, rebalances and ISR health.
- Jenkins/Kubernetes: queue time, agent provisioning, deployment readiness, container OOM and throttling.

## 3. Metric design and naming

Counters represent monotonic event totals between resets. Gauges represent instantaneous measurements. Histograms support latency distributions and SLO-threshold counting when bucket boundaries align with objectives. Record base units and distinguish **request outcome** from infrastructure health.

Avoid labels: trace_id, span_id, user_id, patient_id, request_id, raw URL, arbitrary SQL or document keys.

## 4. Sampling strategies

| Strategy | Mechanism | Strength | Risk |
|---|---|---|---|
| Always-on | all traces | complete context | cost and overload |
| Parent-based head | sampling decision at entry | low overhead | rare errors may be missed |
| Probability head | random representative traces | predictable rate | biased small cohorts |
| Tail sampling | decision after trace completion | keep slow/error traces | buffer/latency/memory |
| Adaptive | dynamic policy | controls volume | governance and comparability |

Sampling probability does not imply every small cohort has that exact observed percentage. Tail sampling requires a routing architecture that sends all spans for a trace to the same decision point. Trace sampling must not silently alter metrics-based SLO accounting.

## 5. Telemetry quality SLIs

```text
completeness = received_records / expected_records
drop_rate = dropped_records / (received_records + dropped_records)
correlation_rate = correctly_correlated_logs / eligible_logs
freshness = ingestion_time - event_time
cardinality = product(distinct values of metric dimensions)
```

Define how expected records are estimated; a sampled trace stream cannot be treated as an exhaustive request count. Monitor Collector refusal, exporter failures, queue saturation and scrape absence. Alert on **missing telemetry**, not only on reported application errors.

## 6. Pipeline design

```text
Application SDK / runtime agent
   | structured logs, histograms, spans, profiles
   v
Edge Collector (auth, memory guard, batch)
   |
Regional Collector gateway (routing, filtering, sampling)
   +------ metrics backend
   +------ logs backend
   +------ traces backend
   +------ profiles backend (where supported)
   |
Dashboards / SLO / alerting / incident review
```

Place privacy controls at the source and approved pipeline boundaries. Collector processor/exporter availability and syntax vary by distribution and version; pin and test configuration.

## 7. Executable instrumentation quality lab

Create:

```text
chapter004/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/quality_gate.py
  tests/test_quality_gate.py
```

### fixtures/healthy.json

```json
{
  "service": "search-api",
  "environment": "staging",
  "owner": "platform-sre",
  "expected_events": 10000,
  "received_events": 9998,
  "dropped_events": 2,
  "correlated_logs": 9980,
  "eligible_logs": 9990,
  "freshness_p95_seconds": 12,
  "max_freshness_p95_seconds": 30,
  "min_completeness": 0.999,
  "min_correlation": 0.998,
  "max_drop_rate": 0.001,
  "metric_labels": {"service": 1, "route": 20, "status_class": 5, "environment": 3},
  "max_series": 500,
  "sampling": {"strategy": "parent_based_head", "probability": 0.1},
  "sensitive_fields": [],
  "schema_version": "1.0"
}
```

### fixtures/degraded.json

```json
{
  "service": "search-api",
  "environment": "staging",
  "owner": "",
  "expected_events": 10000,
  "received_events": 9000,
  "dropped_events": 1000,
  "correlated_logs": 8000,
  "eligible_logs": 9000,
  "freshness_p95_seconds": 120,
  "max_freshness_p95_seconds": 30,
  "min_completeness": 0.999,
  "min_correlation": 0.998,
  "max_drop_rate": 0.001,
  "metric_labels": {"service": 1, "patient_id": 1000000},
  "max_series": 500,
  "sampling": {"strategy": "probability_head", "probability": 1.5},
  "sensitive_fields": ["authorization"],
  "schema_version": ""
}
```

### scripts/quality_gate.py

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

FORBIDDEN = {"patient_id", "user_id", "trace_id", "span_id", "request_id", "email", "authorization", "token"}
STRATEGIES = {"always_on", "parent_based_head", "probability_head", "tail"}

def check(data):
    errors = []
    for key in ("service", "environment", "owner", "schema_version"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"missing {key}")
    for key in ("expected_events", "received_events", "dropped_events", "correlated_logs", "eligible_logs"):
        if type(data.get(key)) is not int or data[key] < 0:
            errors.append(f"invalid {key}")
    if errors and any(x.startswith("invalid ") for x in errors):
        return errors
    expected, received, dropped = (data[k] for k in ("expected_events", "received_events", "dropped_events"))
    correlated, eligible_logs = data["correlated_logs"], data["eligible_logs"]
    if expected <= 0 or eligible_logs <= 0 or received > expected or correlated > eligible_logs:
        errors.append("invalid event/log denominator or counts")
    else:
        for key in ("min_completeness", "min_correlation", "max_drop_rate"):
            val = data.get(key)
            if type(val) not in (int, float) or not 0 <= val <= 1:
                errors.append(f"invalid threshold {key}")
        if not any(e.startswith("invalid threshold") for e in errors):
            if received / expected < data["min_completeness"]:
                errors.append("telemetry completeness below threshold")
            if correlated / eligible_logs < data["min_correlation"]:
                errors.append("log correlation below threshold")
            if dropped / max(received + dropped, 1) > data["max_drop_rate"]:
                errors.append("telemetry drop rate above threshold")
    freshness, limit = data.get("freshness_p95_seconds"), data.get("max_freshness_p95_seconds")
    if type(freshness) not in (int, float) or type(limit) not in (int, float) or freshness < 0 or limit <= 0:
        errors.append("invalid freshness")
    elif freshness > limit:
        errors.append("telemetry freshness SLO breached")
    labels, max_series = data.get("metric_labels"), data.get("max_series")
    if not isinstance(labels, dict) or not labels or type(max_series) is not int or max_series <= 0:
        errors.append("invalid label contract")
    else:
        series = 1
        for key, count in labels.items():
            if key.lower() in FORBIDDEN:
                errors.append(f"forbidden label: {key}")
            if type(count) is not int or count <= 0:
                errors.append(f"invalid label cardinality: {key}")
            else:
                series *= count
        if series > max_series:
            errors.append(f"metric cardinality budget exceeded: {series} > {max_series}")
    sampling = data.get("sampling")
    if not isinstance(sampling, dict) or sampling.get("strategy") not in STRATEGIES:
        errors.append("invalid sampling strategy")
    else:
        prob = sampling.get("probability")
        if type(prob) not in (int, float) or not 0 <= prob <= 1:
            errors.append("invalid sampling probability")
    sensitive = data.get("sensitive_fields")
    if not isinstance(sensitive, list) or any(not isinstance(x, str) for x in sensitive):
        errors.append("invalid sensitive_fields")
    elif sensitive:
        errors.append("sensitive fields must be removed before export")
    return errors

if __name__ == "__main__":
    errors = check(json.loads(Path(sys.argv[1]).read_text()))
    print("QUALITY GATE PASS: synthetic fixture" if not errors else "QUALITY GATE FAIL")
    for error in errors:
        print("-", error)
    sys.exit(bool(errors))
```

Run:

```bash
python3 scripts/quality_gate.py fixtures/healthy.json
if python3 scripts/quality_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded telemetry accepted"; exit 1
else
  echo "PASS: degraded telemetry rejected"
fi
```

### tests/test_quality_gate.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from quality_gate import check

class QualityTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_healthy(self):
        self.assertEqual(check(self.fixture("healthy.json")), [])

    def test_degraded(self):
        self.assertTrue(check(self.fixture("degraded.json")))

    def test_drop_rate(self):
        d = self.fixture("healthy.json")
        d["dropped_events"] = 100
        self.assertTrue(check(d))

    def test_correlation(self):
        d = self.fixture("healthy.json")
        d["correlated_logs"] = 5000
        self.assertTrue(check(d))

    def test_sensitive_label(self):
        d = self.fixture("healthy.json")
        d["metric_labels"]["patient_id"] = 1
        self.assertTrue(check(d))

    def test_sampling(self):
        d = self.fixture("healthy.json")
        d["sampling"]["probability"] = 2
        self.assertTrue(check(d))

    def test_freshness(self):
        d = self.fixture("healthy.json")
        d["freshness_p95_seconds"] = 120
        self.assertTrue(check(d))

    def test_missing_owner(self):
        d = self.fixture("healthy.json")
        d["owner"] = ""
        self.assertTrue(check(d))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 8. Twenty-four hands-on exercises

1. Define service instrumentation owner.
2. Document service and environment resource attributes.
3. Choose automatic instrumentation coverage.
4. Define manual business SLI instrumentation.
5. Design bounded HTTP route labels.
6. Select counter/gauge/histogram instruments.
7. Define latency bucket boundaries.
8. Create structured log correlation schema.
9. Define trace parent/child boundaries.
10. Review async message propagation.
11. Define CPU profiling guardrails.
12. Compare head and tail sampling.
13. Define sampling probability.
14. Define telemetry completeness SLI.
15. Define telemetry drop-rate SLI.
16. Define telemetry freshness SLI.
17. Define log correlation SLI.
18. Calculate metric cardinality budget.
19. Create healthy synthetic fixture.
20. Create degraded synthetic fixture.
21. Execute positive gate.
22. Execute negative gate.
23. Run eight automated tests.
24. Write an instrumentation quality review.

## 9. Twenty failure scenarios

| # | Failure | Diagnostic |
|---|---|---|
| 01 | Missing owner | service catalog |
| 02 | Wrong metric unit | schema |
| 03 | Counter used as gauge | instrument type |
| 04 | Unbounded route labels | cardinality |
| 05 | Patient IDs in metrics | privacy |
| 06 | Secrets in span attributes | redaction |
| 07 | Missing log trace IDs | correlation |
| 08 | Broken async context | propagation |
| 09 | Excessive head sampling | cost |
| 10 | Too little sampling | blind spots |
| 11 | Tail-sampling queue pressure | capacity |
| 12 | Collector dropped records | loss |
| 13 | Delayed telemetry | freshness |
| 14 | Incomplete ingestion | completeness |
| 15 | Duplicate counters | double counting |
| 16 | Wrong event denominator | SLI correctness |
| 17 | Schema version drift | compatibility |
| 18 | Missing Kubernetes resource attrs | enrichment |
| 19 | Profile symbol exposure | access control |
| 20 | Debug exporter in production | governance |

## 10. Eight production runbooks

**A. Instrumentation regression:** Compare release diff, semantic conventions, instrument units and metrics before/after deployment; revert if SLI accounting breaks.

**B. Collector telemetry loss:** Check refused/dropped counts, queue saturation, exporter errors, retry policy and backend availability; quantify visibility gap.

**C. Trace/log correlation failure:** Inspect context propagation, log enrichment, span parenting and sampling; avoid sensitive identifiers.

**D. Cardinality explosion:** Identify new labels, block unbounded dimensions, estimate series growth and verify alert continuity.

**E. Sampling blind spot:** Compare error/slow trace retention, sampling policy and backend cost; use staged changes.

**F. Telemetry freshness incident:** Check event clocks, queue delay, batching, backend ingest and dashboard time windows.

**G. Privacy incident:** Stop offending instrumentation, restrict access, identify downstream copies and engage security/privacy response.

**H. Instrumentation acceptance failure:** Freeze rollout, assign owner, run negative tests and require independent review.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Instrumentation strategy and architecture | 20 |
| Metrics/logs/traces/profiles semantics | 20 |
| Sampling and telemetry quality | 20 |
| Security, cardinality and governance | 20 |
| Executable tests, runbooks and evidence | 20 |
| **Total** | **100** |

Suggested pass 85/100, with mandatory gates for no restricted data export, bounded labels, positive/negative quality checks, eight unit tests and defined ownership. Synthetic validation does not prove production telemetry quality.

## 12. Evidence worksheet

```text
UTC / service / owner:
Instrumentation plan and semantic version:
Metric types and units:
Log/trace correlation:
Sampling policy:
Completeness/drop/freshness thresholds:
Cardinality/privacy:
Healthy fixture:
Degraded fixture:
Eight tests:
Incident scenarios:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 004 hands-on lab](labs/004-observability-instrumentation-strategy-sampling-telemetry-quality-lab.md).

**Next:** Chapter 005 — Observability Fundamentals Production Readiness and Reliability Capstone.
