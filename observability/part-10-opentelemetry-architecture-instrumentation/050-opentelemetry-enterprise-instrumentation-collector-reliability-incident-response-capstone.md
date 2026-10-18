# Chapter 050 — OpenTelemetry Enterprise Instrumentation, Collector Reliability and Incident Response Capstone

**Part 10 — OpenTelemetry Architecture and Instrumentation: FINAL CAPSTONE**  
**Audience:** SRE/DBRE, observability architects and on-call platform teams.  
**Prerequisites:** Chapters 046–049, Python 3.10+, Kubernetes fundamentals.

## 1. Capstone mission

Design and validate a production-style OpenTelemetry stack across application SDKs, OTLP, agent/gateway Collectors, three signals, tail sampling, security, resilience and incident response. Distinguish design attestation from live observed evidence.

## 2. Architecture

```text
Kubernetes APIs -> HTTP clients -> PostgreSQL
    |                  |
  SDK traces / metrics / logs
    | W3C traceparent and safe attributes
    v
  OTel agent -> trace-ID-aware gateway routing
    |                   |
    |       memory_limiter -> tail_sampling -> batch
    |                   |
    +----------> authenticated OTLP exporters
                        |
                traces / metrics / logs backends
                        |
             Grafana + independent service SLIs
```

The Collector does not guarantee durable or exactly-once telemetry. Preserve independent application request/error/latency measurements: sampled traces and missing logs can bias SLOs.

## 3. Acceptance objectives

| Capability | Staging acceptance evidence |
|---|---|
| SDK | version pinned; HTTP and DB spans emitted |
| Context | W3C propagation across sync and async boundaries |
| Metrics | correct units, bounded cardinality, independent SLIs |
| Logs | safe severity/body, trace ID correlation |
| Collector | all three pipelines, health, memory and queues |
| Tail sampling | error/latency policy and trace affinity |
| Security | TLS/auth, PII redaction, approved RBAC |
| Recovery | exporter outage drill, restore and rollback |

## 4. Staging reference configuration

Use the version-pinned Collector configuration from Chapters 048–049. Validate component compatibility before deploying. Route spans by trace ID to a tail-sampling gateway; monitor decision wait, active trace count, memory and export refusals. Secure OTLP listeners and exporters with TLS, authentication and NetworkPolicy. For Kubernetes use image digests, least privilege, readiness, controlled rollout and safe resource limits.

## 5. Production SRE/DBRE incident simulation

A PostgreSQL-backed API experiences p95 latency spikes during a deploy. The SDK loses context in an async worker, a tail-sampling gateway is resharded during autoscaling, and the backend throttles exporters with 429. Collector queues grow; memory limiter rejects spans and some traces are incomplete.

**Investigation:** verify user impact from independent service metrics; identify SDK/propagation regression; inspect Collector accepted/refused counters, exporter failures, queue depth and memory; validate trace-affinity routing and tail-sampling decisions; contain PII exposure; restore version-pinned config; verify three-signal recovery and rollback. Record an RCA, owners, timelines and follow-up actions.

## 6. Executable offline capstone gate

The following is **synthetic acceptance metadata**. Boolean flags and numbers are illustrative; the script does not measure real telemetry or prove runtime security.

### healthy.json

```json
{
  "owner": "observability-sre",
  "environment": "staging",
  "change_id": "OBS-050",
  "sdk_version_pinned": true,
  "collector_version_pinned": true,
  "signals": [
    "traces",
    "metrics",
    "logs"
  ],
  "resource_attributes": [
    "service.name",
    "service.version",
    "deployment.environment.name"
  ],
  "propagation_tested": true,
  "trace_affinity_tested": true,
  "tail_sampling_reviewed": true,
  "collector_queue_reviewed": true,
  "backpressure_reviewed": true,
  "privacy_redaction_tested": true,
  "tls_auth_tested": true,
  "cardinality_reviewed": true,
  "independent_slo_tested": true,
  "incident_drill_completed": true,
  "restore_tested": true,
  "rollback_tested": true,
  "observed_export_success_percent": 99,
  "minimum_export_success_percent": 98,
  "trace_completeness_percent": 95,
  "minimum_trace_completeness_percent": 90,
  "collector_memory_mib": 500,
  "collector_memory_budget_mib": 768,
  "production_delete": false
}
```

### capstone_gate.py

```python
"""Offline synthetic OTel capstone acceptance gate. No cluster access."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 for k,req in (("signals",{"traces","metrics","logs"}),("resource_attributes",{"service.name","service.version","deployment.environment.name"})):
  v=p.get(k)
  if not isinstance(v,list) or not req.issubset(v):e.append("missing "+k)
 for k in ["sdk_version_pinned","collector_version_pinned","propagation_tested","trace_affinity_tested","tail_sampling_reviewed","collector_queue_reviewed","backpressure_reviewed","privacy_redaction_tested","tls_auth_tested","cardinality_reviewed","independent_slo_tested","incident_drill_completed","restore_tested","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe action")
 for k in ("observed_export_success_percent","minimum_export_success_percent","trace_completeness_percent","minimum_trace_completeness_percent"):
  v=p.get(k)
  if type(v) is not int or not 0<=v<=100:e.append("invalid "+k)
 for a,b in (("observed_export_success_percent","minimum_export_success_percent"),("trace_completeness_percent","minimum_trace_completeness_percent")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and x<y:e.append("acceptance threshold missed "+a)
 for k in ("collector_memory_mib","collector_memory_budget_mib"):
  v=p.get(k)
  if type(v) is not int or v<=0:e.append("invalid "+k)
 if type(p.get("collector_memory_mib")) is int and type(p.get("collector_memory_budget_mib")) is int and p["collector_memory_mib"]>p["collector_memory_budget_mib"]:e.append("memory budget exceeded")
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_capstone_gate.py

```python
import copy,json,unittest
from pathlib import Path
from capstone_gate import validate
class CapstoneTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_change_id(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_04_signals(self):
  p=copy.deepcopy(self.p);p["signals"]=["traces"];self.assertTrue(validate(p))
 def test_05_resource_attributes(self):
  p=copy.deepcopy(self.p);p["resource_attributes"]=["service.name"];self.assertTrue(validate(p))
 def test_06_sdk_version_pinned(self):
  p=copy.deepcopy(self.p);p["sdk_version_pinned"]=False;self.assertTrue(validate(p))
 def test_07_collector_version_pinned(self):
  p=copy.deepcopy(self.p);p["collector_version_pinned"]=False;self.assertTrue(validate(p))
 def test_08_propagation_tested(self):
  p=copy.deepcopy(self.p);p["propagation_tested"]=False;self.assertTrue(validate(p))
 def test_09_trace_affinity_tested(self):
  p=copy.deepcopy(self.p);p["trace_affinity_tested"]=False;self.assertTrue(validate(p))
 def test_10_tail_sampling_reviewed(self):
  p=copy.deepcopy(self.p);p["tail_sampling_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_collector_queue_reviewed(self):
  p=copy.deepcopy(self.p);p["collector_queue_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_backpressure_reviewed(self):
  p=copy.deepcopy(self.p);p["backpressure_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_privacy_redaction_tested(self):
  p=copy.deepcopy(self.p);p["privacy_redaction_tested"]=False;self.assertTrue(validate(p))
 def test_14_tls_auth_tested(self):
  p=copy.deepcopy(self.p);p["tls_auth_tested"]=False;self.assertTrue(validate(p))
 def test_15_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_independent_slo_tested(self):
  p=copy.deepcopy(self.p);p["independent_slo_tested"]=False;self.assertTrue(validate(p))
 def test_17_incident_drill_completed(self):
  p=copy.deepcopy(self.p);p["incident_drill_completed"]=False;self.assertTrue(validate(p))
 def test_18_restore_tested(self):
  p=copy.deepcopy(self.p);p["restore_tested"]=False;self.assertTrue(validate(p))
 def test_19_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_20_observed_export_success_percent(self):
  p=copy.deepcopy(self.p);p["observed_export_success_percent"]=50;self.assertTrue(validate(p))
 def test_21_minimum_export_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_export_success_percent"]=101;self.assertTrue(validate(p))
 def test_22_trace_completeness_percent(self):
  p=copy.deepcopy(self.p);p["trace_completeness_percent"]=50;self.assertTrue(validate(p))
 def test_23_minimum_trace_completeness_percent(self):
  p=copy.deepcopy(self.p);p["minimum_trace_completeness_percent"]=101;self.assertTrue(validate(p))
 def test_24_collector_memory_mib(self):
  p=copy.deepcopy(self.p);p["collector_memory_mib"]=1000;self.assertTrue(validate(p))
 def test_25_collector_memory_budget_mib(self):
  p=copy.deepcopy(self.p);p["collector_memory_budget_mib"]=0;self.assertTrue(validate(p))
 def test_26_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter050 && cd chapter050
# Save blocks as healthy.json, capstone_gate.py, test_capstone_gate.py
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Expected PASS and **28 authored Python tests**.

## 7. Twenty-four hands-on exercises

1. Inventory application telemetry.
2. Pin SDK versions.
3. Pin Collector versions.
4. Validate three signals.
5. Validate resource conventions.
6. Trace HTTP server spans.
7. Trace HTTP client spans.
8. Trace PostgreSQL spans.
9. Verify W3C propagation.
10. Verify async propagation.
11. Inspect baggage privacy.
12. Validate histogram units.
13. Audit metric cardinality.
14. Validate Collector receiver.
15. Validate memory limiter.
16. Validate batch/exporter.
17. Measure queue depth.
18. Test exporter retry.
19. Verify trace affinity.
20. Verify tail sampling.
21. Run synthetic incident.
22. Test recovery and restore.
23. Run acceptance tests.
24. Document rollback.

## 8. Twenty-four production failures

1. **Missing service.name:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
2. **Traceparent not propagated:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
3. **Async spans disconnected:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
4. **Duplicate auto/manual spans:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
5. **SQL bind values exposed:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
6. **Baggage contains PII:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
7. **Metric cardinality surge:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
8. **Wrong histogram units:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
9. **Collector receiver unreachable:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
10. **TLS auth failure:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
11. **Exporter 429:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
12. **Queue overflow:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
13. **Memory limiter refuses spans:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
14. **Collector OOM:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
15. **Tail sampler loses traces:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
16. **Trace affinity broken:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
17. **Error sampling misses incident:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
18. **Log trace correlation absent:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
19. **Metrics missing during outage:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
20. **Exporter success below SLO:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
21. **Collector health check fails:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
22. **Backend persistence fails:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
23. **Restore test fails:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.
24. **Rollback incomplete:** investigate SDK, Collector, sampling, exporter, backend, privacy and rollback evidence.

## 9. Eight production runbooks

1. **No traces:** inspect SDK provider, sampling, propagation, receiver and exporter..
2. **No metrics/logs:** inspect pipeline wiring, instrument registration and signal compatibility..
3. **Privacy incident:** stop unsafe attributes, restrict access, rotate exposed secrets and follow approved handling..
4. **Exporter outage:** inspect 429, TLS/auth, queue saturation, retries and independent SLOs..
5. **Tail sampling gaps:** inspect trace affinity, decision wait, cache pressure and replica changes..
6. **Collector OOM:** inspect limiter, batch, memory, queue and resource requests..
7. **Incident command:** preserve timestamps, impact, hypotheses, changes and recovery evidence..
8. **Rollback and DR:** restore pinned configs, verify synthetic three-signal delivery and compare RPO/RTO..

## 10. 100-point final assessment

| Domain | Points |
|---|---:|
| SDKs, context and three-signal instrumentation | 20 |
| Collector pipelines and scalability | 20 |
| Security, sampling and data governance | 20 |
| Offline tests and evidence | 20 |
| Incident response, DR and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory production acceptance requires witnessed end-to-end export, independent SLIs, privacy validation, load testing and rollback evidence.

## 11. Evidence worksheet

```text
UTC / owner / change ID / environment:
SDK and Collector versions:
Trace propagation and DB spans:
Metrics units/cardinality / logs correlation:
Collector accepted/refused / queue / memory:
Tail sampling decisions / affinity:
TLS/auth / redaction / independent SLIs:
Restore / rollback / incident timeline:
Offline gate / 28 tests / score:
```

**Companion:** [Chapter 050 enterprise capstone lab](labs/050-opentelemetry-enterprise-instrumentation-collector-reliability-incident-response-capstone-lab.md).

**Part 10 complete. Next:** Chapter 051 — Distributed Tracing Architecture with Jaeger and Grafana Tempo (Part 11).
