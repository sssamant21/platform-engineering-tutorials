# Chapter 002 — Observability Signals, Telemetry Pipelines and Context Propagation

**Part 01 — Observability Fundamentals**  
**Audience:** SRE/DBRE, platform engineering, application developers and security engineers.  
**Prerequisites:** Chapter 001, Python 3.10+, shell, basic HTTP concepts.  
**Goal:** Design reliable, privacy-aware collection and correlation of metrics, logs, traces and profiles across production services.

## 1. Learning objectives

After this chapter you can:
1. Describe the four telemetry signals and the boundaries between instrumentation, collection and storage.
2. Design an OpenTelemetry Collector pipeline with receivers, processors, exporters and connectors.
3. Explain W3C Trace Context (`traceparent`, `tracestate`) and baggage propagation.
4. Correlate logs with trace/span IDs without putting identifiers into high-cardinality metric labels.
5. Classify sampling, batching, queueing, retry and backpressure failure modes.
6. Enforce redaction, retention, tenancy, resource attributes and trust boundaries.
7. Run a safe Python standard-library lab with positive and negative tests.

## 2. Signals and their roles

| Signal | Typical record | Investigation question | Cardinality / security concern |
|---|---|---|---|
| Metrics | counters, gauges, histograms | Is error rate rising? | labels must be bounded |
| Logs | timestamp, severity, event, trace_id | What happened? | credentials/PII/PHI redaction |
| Traces | span_id, parent_id, duration | Where is latency spent? | sensitive span attributes |
| Profiles | CPU or allocation samples | Which code consumes resources? | symbols, paths, stack privacy |

**Production example:** A patient-search API calls Elasticsearch. Request latency spikes; a histogram reveals p95 regression, logs show storage timeout warnings, traces identify the Elasticsearch span, and a CPU profile rules out application CPU as the primary bottleneck. Storage IOPS/latency and query fan-out remain separate diagnostic evidence.

## 3. Telemetry pipeline reference architecture

```text
Kubernetes API / application / databases / Jenkins
            | OTLP gRPC/HTTP, scrape, logs
            v
     edge agent / SDK exporters
            |
            v
   OpenTelemetry Collector gateway
   receiver -> processors -> exporter
       |          |            |
       |      batch, memory    +--> metrics backend
       |      filtering        +--> logs backend
       |      resource         +--> trace backend
       |      attributes       +--> profile backend (if supported)
       |
  auth, mTLS, quotas, tenant routing
```

Collector component names and supported signals vary by distribution/version. Pin tested Collector versions and confirm the availability of each receiver, processor and exporter. Use agent and gateway topology when appropriate: local collection reduces app coupling; gateway policies centralize routing and governance.

### Receiver, processor, exporter, connector

- **Receiver:** ingests OTLP or other supported formats.
- **Processor:** transforms, batches, filters, limits memory, enriches resource context.
- **Exporter:** sends data to an authorized backend.
- **Connector:** bridges pipelines, e.g. span-derived metrics, when supported.
- **Extension:** service-level capabilities such as health checks and authentication, depending on distribution.

## 4. Context propagation and correlation

A W3C `traceparent` header has four dash-separated fields:

```text
version-trace-id-parent-id-trace-flags
00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

The trace ID is 16 bytes (32 hex characters); the parent ID is 8 bytes (16 hex characters). IDs must not be all zero. Version 00 uses a two-hex-character flags field. A new span has its own span ID and references the propagated parent span ID. The `01` flag indicates sampled, but the receiving service must still apply its configured sampling/security policy.

**Propagation rules:**
- Accept trace context only at defined trust boundaries and validate syntax.
- Preserve correlation across synchronous HTTP and asynchronous messaging when appropriate.
- Do not blindly trust baggage from public clients; never place credentials or patient identifiers in baggage.
- Add trace ID/span ID to structured logs in an access-controlled store.
- Do **not** use raw trace IDs as metric labels.

## 5. Resource and semantic attributes

Common useful resource attributes include `service.name`, `service.namespace`, `deployment.environment.name`, `cloud.region` and Kubernetes namespace/pod context. Pin semantic convention versions for instrumentation and document renames. Avoid embedding customer or patient IDs in metric dimensions.

## 6. Reliability design: batching, queueing, retry and sampling

| Control | Benefit | Failure mode / tradeoff |
|---|---|---|
| Batching | lower exporter overhead | delayed visibility |
| Memory limiter | bounded collector memory | refused/dropped data under pressure |
| Retry/backoff | handles transient backend failures | backlog if sustained outage |
| Persistent queue (supported exporters) | survives collector restarts | disk pressure and operational complexity |
| Head sampling | predictable cost | rare errors may be missed |
| Tail sampling | retain interesting traces | stateful processing, latency and memory |
| Cardinality controls | stable metric storage cost | overly broad filtering hides incidents |

Use explicit loss budgets and telemetry-health alerts. No telemetry pipeline guarantees zero loss without end-to-end durability design and tests.

## 7. Example Collector configuration (illustrative)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
      http:
        endpoint: 127.0.0.1:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
    spike_limit_mib: 64
  batch:
    timeout: 5s
    send_batch_size: 512

exporters:
  debug:
    verbosity: basic

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
```

This localhost-only debug exporter is **not a production backend**. Configuration syntax depends on the Collector distribution/version. Debug output can expose sensitive telemetry; use synthetic data and never enable verbose debug in production without approval.

## 8. Executable local context validation lab

Create:

```text
chapter002/
  fixtures/
    valid.json
    invalid.json
  scripts/
    validate_context.py
  tests/
    test_context.py
```

### fixtures/valid.json

```json
{
  "service_name": "search-api",
  "environment": "staging",
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
  "log_trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "metric_labels": {"service": "search-api", "environment": "staging", "route": "/search/{id}"},
  "baggage": {"experiment": "synthetic"},
  "collector_queue_utilization": 0.35,
  "collector_dropped_records": 0,
  "batch_size": 512
}
```

### fixtures/invalid.json

```json
{
  "service_name": "search-api",
  "environment": "staging",
  "traceparent": "00-00000000000000000000000000000000-0000000000000000-01",
  "log_trace_id": "not-a-valid-id",
  "metric_labels": {"patient_id": "synthetic-patient", "trace_id": "bad", "service": "search-api"},
  "baggage": {"authorization": "synthetic-do-not-use"},
  "collector_queue_utilization": 0.99,
  "collector_dropped_records": 20,
  "batch_size": 0
}
```

### scripts/validate_context.py

```python
#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

TRACEPARENT = re.compile(r"^(?P<version>[0-9a-f]{2})-(?P<trace>[0-9a-f]{32})-(?P<parent>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$")
FORBIDDEN_LABELS = {"trace_id", "span_id", "request_id", "user_id", "patient_id", "email"}
FORBIDDEN_BAGGAGE = {"authorization", "cookie", "password", "token", "patient_id", "user_id"}

def validate(data):
    errors = []
    for key in ("service_name", "environment"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"missing {key}")
    value = data.get("traceparent")
    match = TRACEPARENT.fullmatch(value) if isinstance(value, str) else None
    if not match:
        errors.append("invalid W3C traceparent")
    else:
        if match["version"] != "00":
            errors.append("lab supports traceparent version 00 only")
        if int(match["trace"], 16) == 0 or int(match["parent"], 16) == 0:
            errors.append("trace/span IDs cannot be zero")
        if data.get("log_trace_id") != match["trace"]:
            errors.append("log trace ID does not match propagated trace ID")
    labels = data.get("metric_labels")
    if not isinstance(labels, dict):
        errors.append("metric_labels must be an object")
    else:
        for key, val in labels.items():
            if key.lower() in FORBIDDEN_LABELS:
                errors.append(f"forbidden metric label: {key}")
            if not isinstance(val, str):
                errors.append(f"non-string metric label: {key}")
    baggage = data.get("baggage")
    if not isinstance(baggage, dict):
        errors.append("baggage must be an object")
    else:
        for key in baggage:
            if key.lower() in FORBIDDEN_BAGGAGE:
                errors.append(f"sensitive baggage key: {key}")
    q = data.get("collector_queue_utilization")
    if type(q) not in (int, float) or not 0 <= q <= 1:
        errors.append("queue utilization must be 0..1")
    elif q >= 0.90:
        errors.append("collector queue saturation")
    dropped = data.get("collector_dropped_records")
    if type(dropped) is not int or dropped < 0:
        errors.append("invalid dropped-record count")
    elif dropped > 0:
        errors.append(f"collector dropped {dropped} records")
    size = data.get("batch_size")
    if type(size) is not int or size <= 0 or size > 8192:
        errors.append("invalid batch_size")
    return errors

if __name__ == "__main__":
    problems = validate(json.loads(Path(sys.argv[1]).read_text()))
    print("CONTEXT VALID: synthetic fixture" if not problems else "CONTEXT REJECTED")
    for problem in problems:
        print("-", problem)
    sys.exit(bool(problems))
```

Run:

```bash
python3 scripts/validate_context.py fixtures/valid.json
if python3 scripts/validate_context.py fixtures/invalid.json; then
  echo "FAIL: unsafe fixture accepted"; exit 1
else
  echo "PASS: unsafe fixture rejected"
fi
```

### tests/test_context.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_context import validate

class ContextTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_valid(self):
        self.assertEqual(validate(self.fixture("valid.json")), [])

    def test_invalid(self):
        self.assertTrue(validate(self.fixture("invalid.json")))

    def test_trace_mismatch(self):
        data = self.fixture("valid.json")
        data["log_trace_id"] = "f" * 32
        self.assertTrue(validate(data))

    def test_forbidden_metric_label(self):
        data = self.fixture("valid.json")
        data["metric_labels"]["user_id"] = "synthetic"
        self.assertTrue(validate(data))

    def test_collector_backpressure(self):
        data = self.fixture("valid.json")
        data["collector_queue_utilization"] = 0.95
        self.assertTrue(validate(data))

    def test_sensitive_baggage(self):
        data = self.fixture("valid.json")
        data["baggage"]["token"] = "synthetic"
        self.assertTrue(validate(data))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 9. Twenty-four hands-on exercises

1. Classify the four telemetry signals.
2. Draw the SDK/agent/gateway/backend pipeline.
3. Identify receiver/processor/exporter ownership.
4. Explain OTLP gRPC and HTTP endpoints.
5. Pin Collector distribution and version.
6. Review localhost debug exporter limitations.
7. Define batch/queue/backpressure SLOs.
8. Explain head versus tail sampling.
9. Review metric cardinality limits.
10. Design bounded metric labels.
11. Parse W3C traceparent.
12. Identify trace and parent IDs.
13. Propagate context across HTTP services.
14. Design async message context propagation.
15. Add trace IDs to structured logs.
16. Identify sensitive baggage keys.
17. Define service and environment attributes.
18. Define telemetry tenant boundaries.
19. Create valid synthetic fixture.
20. Create unsafe synthetic fixture.
21. Execute positive validation.
22. Execute negative validation.
23. Run six automated unit tests.
24. Document an SRE incident correlation report.

## 10. Twenty failure scenarios

| # | Failure | Diagnostic |
|---|---|---|
| 01 | Collector not reachable | endpoint and network |
| 02 | OTLP protocol mismatch | gRPC versus HTTP |
| 03 | Receiver authentication rejected | identity and TLS |
| 04 | Backend exporter timeout | retry and latency |
| 05 | Collector OOM | memory limiter |
| 06 | Queue saturation | queue utilization |
| 07 | Dropped telemetry | exporter counters |
| 08 | Batch delay too high | flush timeout |
| 09 | Trace context absent | instrumentation |
| 10 | Invalid traceparent | header validation |
| 11 | Broken parent-child spans | propagation |
| 12 | Missing log trace ID | logging enrichment |
| 13 | Metric cardinality spike | label audit |
| 14 | Sensitive baggage propagation | privacy response |
| 15 | PHI in span attributes | redaction |
| 16 | Missing Kubernetes resource attributes | enrichment |
| 17 | Tail-sampling memory pressure | sampling policy |
| 18 | Duplicate metrics | scrape/SDK overlap |
| 19 | Telemetry clock skew | time synchronization |
| 20 | Inconsistent semantic conventions | version alignment |

## 11. Eight production runbooks

**A. OTLP ingestion outage:** Check receiver endpoints, TLS, firewall, SDK retry, Collector health and dropped-record counters; preserve incident timeline.

**B. Collector memory/backpressure:** Inspect queue utilization, exporter latency, batch sizing and memory limiter; scale only after identifying the bottleneck.

**C. Broken trace correlation:** Validate traceparent, middleware instrumentation, async propagation and log enrichment; use synthetic identifiers.

**D. Sensitive telemetry leak:** Restrict access, stop offending instrumentation, assess retention and downstream exports, invoke security/privacy response.

**E. Cardinality explosion:** Identify unbounded labels, roll back instrumentation, measure ingestion impact and avoid discarding required evidence.

**F. Backend outage:** Use bounded retries and supported durable queues; alert on loss and verify recovery/backfill limitations.

**G. Sampling blind spot:** Compare sampling policies with error traces, evaluate tail-sampling cost and adjust with a controlled experiment.

**H. Version/schema drift:** Check Collector and SDK versions, semantic convention changes and exporter compatibility; roll back to pinned versions.

## 12. 100-point acceptance

| Domain | Points |
|---|---:|
| Signal selection and pipeline architecture | 20 |
| Context propagation and log correlation | 20 |
| Security, privacy and cardinality | 20 |
| Executable lab and six automated tests | 20 |
| Troubleshooting, runbooks and evidence | 20 |
| **Total** | **100** |

Suggested pass 85/100, with mandatory gates for context validation, sensitive baggage exclusion, bounded metric labels, telemetry-loss detection and negative-test rejection. Real Collector deployment and end-to-end trace delivery require separate staging evidence.

## 13. Evidence worksheet

```text
UTC / service / owner:
Collector distribution/version:
Telemetry topology:
Signal/label/baggage policy:
Traceparent/log correlation:
Queue/retry/sampling policy:
Valid fixture:
Invalid fixture:
Six unit tests:
20 failure investigations:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 002 executable lab](labs/002-observability-signals-telemetry-pipelines-context-propagation-lab.md).

**Next:** Chapter 003 — Observability Architecture, Data Models and Telemetry Governance.
