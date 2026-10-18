# Chapter 049 — OpenTelemetry Collector Reliability, Scaling, Tail Sampling and Advanced Processing

**Part 10 — OpenTelemetry Architecture and Instrumentation**  
**Audience:** SRE/DBRE and platform observability owners.  
**Prerequisites:** Chapters 046–048, Collector components, Kubernetes networking.

## 1. Objectives

Design reliable OTel Collector pipelines at scale, compare head/tail sampling, preserve trace affinity, model memory and queue capacity, manage retry/backpressure, sanitize telemetry and perform controlled recovery.

## 2. Architecture

```text
Apps + SDKs -> agent Collectors
                     |
           trace-ID-aware routing
                     |
          gateway Collector replicas
           memory_limiter -> tail_sampling -> batch
                     |
          authenticated OTLP exporters
                     |
               tracing backend
            independent SLI metrics
```

Tail sampling needs the **whole trace at one sampling decision point**. Ordinary round-robin load balancing across tail-sampling gateways can split traces and produce incomplete decisions. Use a version-compatible trace-ID-aware routing design, and test behavior during resharding, scaling and restarts.

## 3. Head vs tail sampling

| Aspect | Head sampling | Tail sampling |
|---|---|---|
| Decision | before trace completion | after observing spans |
| Cost | lower memory | buffer + decision overhead |
| Error/latency capture | may miss rare failures | can retain based on status/latency |
| Routing | simpler | trace affinity required |
| Failure | irreversible early drops | incomplete traces, cache eviction |

Sampling is lossy by design. Keep independent unsampled or appropriately aggregated application counters/histograms for SLOs.

## 4. Tail-sampling Collector example

**Version-sensitive, staging-only sketch:** verify the chosen contrib Collector build supports each processor and policy.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 128
  tail_sampling:
    decision_wait: 30s
    num_traces: 50000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 1000
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
      processors: [memory_limiter, tail_sampling, batch]
      exporters: [debug]
```

Loopback is local-only; in a real multi-pod topology use approved network listeners, TLS/auth and a routing tier that hashes by trace ID. Avoid claiming the above sketch is production ready.

## 5. Capacity and scaling

Estimate active traces from incoming traces/second multiplied by decision wait, with a safety factor for late spans, skew and bursts. Size `num_traces`, memory limits and replicas from load tests rather than copying defaults. A bounded queue reduces transient failures but cannot guarantee exactly-once telemetry. Watch exporter failures, queue occupancy, refused spans, tail-sampling decisions, CPU and OOMs.

## 6. Advanced processing and security

Use attribute filtering/transform processors only when supported by the pinned Collector distribution. Remove credentials, patient identifiers and SQL bind values before export; control metric label cardinality; distinguish tail sampling from metrics aggregation; validate logs independently. Treat semantic convention upgrades as compatibility changes.

## 7. Executable offline reliability gate

The synthetic manifest below is **review metadata**. It does not configure a real Collector or prove trace affinity.

### healthy.json

```json
{
  "owner": "observability-sre",
  "environment": "staging",
  "trace_routing": "consistent-hash",
  "tail_sampling_enabled": true,
  "all_spans_same_gateway": true,
  "decision_wait_seconds": 30,
  "expected_trace_duration_seconds": 10,
  "num_traces": 50000,
  "estimated_active_traces": 20000,
  "replicas": 3,
  "replica_capacity_traces": 10000,
  "queue_capacity_batches": 3000,
  "estimated_peak_batches": 1500,
  "memory_limit_mib": 1024,
  "memory_limiter_mib": 768,
  "spike_limit_mib": 128,
  "error_sampling_enabled": true,
  "latency_sampling_enabled": true,
  "privacy_filter_reviewed": true,
  "cardinality_reviewed": true,
  "backpressure_reviewed": true,
  "collector_metrics_reviewed": true,
  "load_test_reviewed": true,
  "rollback_tested": true,
  "production_delete": false
}
```

### sampling_gate.py

```python
"""Offline tail-sampling design gate; does not configure a Collector."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("trace_routing")!="consistent-hash":e.append("unsafe trace routing")
 for k in ["tail_sampling_enabled","all_spans_same_gateway","error_sampling_enabled","latency_sampling_enabled","privacy_filter_reviewed","cardinality_reviewed","backpressure_reviewed","collector_metrics_reviewed","load_test_reviewed","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 for k in ("decision_wait_seconds","expected_trace_duration_seconds","num_traces","estimated_active_traces","replicas","replica_capacity_traces","queue_capacity_batches","estimated_peak_batches","memory_limit_mib","memory_limiter_mib","spike_limit_mib"):
  if type(p.get(k)) is not int or p[k]<=0:e.append("invalid "+k)
 for a,b in (("expected_trace_duration_seconds","decision_wait_seconds"),("estimated_peak_batches","queue_capacity_batches"),("memory_limiter_mib","memory_limit_mib"),("spike_limit_mib","memory_limiter_mib"),("estimated_active_traces","num_traces")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and x>=y:e.append("capacity exceeded "+a)
 if all(type(p.get(k)) is int for k in ("estimated_active_traces","replicas","replica_capacity_traces")):
  if p["estimated_active_traces"]>p["replicas"]*p["replica_capacity_traces"]:e.append("fleet capacity exceeded")
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_sampling_gate.py

```python
import copy,json,unittest
from pathlib import Path
from sampling_gate import validate
class SamplingTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_invalid_object(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_trace_routing(self):
  p=copy.deepcopy(self.p);p["trace_routing"]="round-robin";self.assertTrue(validate(p))
 def test_04_tail_sampling_enabled(self):
  p=copy.deepcopy(self.p);p["tail_sampling_enabled"]=False;self.assertTrue(validate(p))
 def test_05_all_spans_same_gateway(self):
  p=copy.deepcopy(self.p);p["all_spans_same_gateway"]=False;self.assertTrue(validate(p))
 def test_06_error_sampling_enabled(self):
  p=copy.deepcopy(self.p);p["error_sampling_enabled"]=False;self.assertTrue(validate(p))
 def test_07_latency_sampling_enabled(self):
  p=copy.deepcopy(self.p);p["latency_sampling_enabled"]=False;self.assertTrue(validate(p))
 def test_08_privacy_filter_reviewed(self):
  p=copy.deepcopy(self.p);p["privacy_filter_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_backpressure_reviewed(self):
  p=copy.deepcopy(self.p);p["backpressure_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_collector_metrics_reviewed(self):
  p=copy.deepcopy(self.p);p["collector_metrics_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_load_test_reviewed(self):
  p=copy.deepcopy(self.p);p["load_test_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_14_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
 def test_15_decision_wait_seconds(self):
  p=copy.deepcopy(self.p);p["decision_wait_seconds"]=1;self.assertTrue(validate(p))
 def test_16_num_traces(self):
  p=copy.deepcopy(self.p);p["num_traces"]=100;self.assertTrue(validate(p))
 def test_17_estimated_active_traces(self):
  p=copy.deepcopy(self.p);p["estimated_active_traces"]=60000;self.assertTrue(validate(p))
 def test_18_replicas(self):
  p=copy.deepcopy(self.p);p["replicas"]=0;self.assertTrue(validate(p))
 def test_19_replica_capacity_traces(self):
  p=copy.deepcopy(self.p);p["replica_capacity_traces"]=100;self.assertTrue(validate(p))
 def test_20_queue_capacity_batches(self):
  p=copy.deepcopy(self.p);p["queue_capacity_batches"]=100;self.assertTrue(validate(p))
 def test_21_memory_limit_mib(self):
  p=copy.deepcopy(self.p);p["memory_limit_mib"]=256;self.assertTrue(validate(p))
 def test_22_memory_limiter_mib(self):
  p=copy.deepcopy(self.p);p["memory_limiter_mib"]=64;self.assertTrue(validate(p))
 def test_23_spike_limit_mib(self):
  p=copy.deepcopy(self.p);p["spike_limit_mib"]=900;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter049 && cd chapter049
# Save blocks as healthy.json, sampling_gate.py, test_sampling_gate.py
python3 sampling_gate.py healthy.json
python3 -m unittest -v test_sampling_gate.py
```

Expected PASS and **25 authored Python tests**.

## 8. Twenty-four hands-on exercises

1. Identify high-cardinality spans.
2. Measure trace arrival rate.
3. Measure trace duration p99.
4. Select head vs tail sampling.
5. Design error sampling.
6. Design latency sampling.
7. Set decision wait.
8. Set trace cache capacity.
9. Choose trace ID affinity.
10. Deploy load balancing exporter.
11. Plan gateway replicas.
12. Model uneven hash distribution.
13. Inspect memory limiter.
14. Inspect batch queue.
15. Review exporter retry.
16. Review persistent storage queue.
17. Define attribute filter.
18. Test PII removal.
19. Measure dropped spans.
20. Measure accepted spans.
21. Simulate exporter 429.
22. Simulate gateway restart.
23. Run offline unit tests.
24. Document rollback.

## 9. Twenty-four failure scenarios

1. **Spans split across gateways:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
2. **Trace routing uses round robin:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
3. **Decision wait too short:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
4. **Decision wait too long:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
5. **Trace cache overflow:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
6. **Memory limiter rejects:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
7. **Collector OOM:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
8. **Uneven hash skew:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
9. **Scale-down loses traces:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
10. **Exporter returns 429:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
11. **Exporter 401:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
12. **Persistent queue fills:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
13. **Retry amplifies outage:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
14. **Tail sampling hides errors:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
15. **Latency policy misses slow trace:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
16. **Cardinality explosion:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
17. **PII filter misconfigured:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
18. **Batch processor pressure:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
19. **Clock skew:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
20. **Collector CPU throttled:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
21. **Unassigned gateway:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
22. **Backend query misses trace:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
23. **Self-metrics unavailable:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.
24. **Rollback causes gaps:** investigate trace affinity, sampler cache, memory, queues, export and SLO evidence.

## 10. Eight production runbooks

1. **Missing complete traces:** verify all spans route by trace ID to same tail-sampling instance..
2. **Tail sampler pressure:** review decision wait, trace cache capacity, span arrival rate and memory..
3. **Scaling incident:** inspect hash distribution, gateway replica count and disruption behavior..
4. **Exporter outage:** inspect retry/queue saturation, 429, credentials and TLS..
5. **Data loss:** compare accepted/refused/exporter counters and backend persisted traces..
6. **Sampling bias:** retain independent request metrics; review error and latency policies..
7. **Privacy:** stop unsafe attributes, validate filtering and coordinate approved incident response..
8. **Rollback:** restore versioned routing and sampling policy, validate trace continuity and SLOs..

## 11. SRE/DBRE game day

A PostgreSQL-backed API shows intermittent 10-second latency while gateway Collectors scale from three to five replicas. Tail-sampling decisions become incomplete, exporter 429s increase and memory limiter refuses spans. Compare independent p95/error metrics, inspect trace routing and decision wait, rightsize queues, stage a stable trace-affinity topology and roll back on increased telemetry loss.

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| Sampling theory and trace affinity | 20 |
| Capacity, queues and scaling | 20 |
| Advanced processing and privacy | 20 |
| Offline gate and automated tests | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires witnessed load tests, end-to-end trace completeness, privacy tests and recovery evidence.

**Companion:** [Chapter 049 lab](labs/049-opentelemetry-collector-reliability-scaling-tail-sampling-advanced-processing-lab.md).

**Next:** Chapter 050 — OpenTelemetry Enterprise Instrumentation, Collector Reliability and Incident Response Capstone.
