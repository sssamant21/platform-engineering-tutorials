# Chapter 070 — Enterprise Application Performance Monitoring, Incident Response and Reliability Capstone

**Part 14 — Application Performance Monitoring: Final Capstone**  
**Audience:** SRE, DBRE, application platform engineers and incident commanders.  
**Prerequisites:** Chapters 066–069.

## Mission

Demonstrate end-to-end application performance monitoring using user-facing RED metrics, USE saturation, OpenTelemetry traces, service maps, runtime profiling, bounded load tests, error budgets and safe incident recovery.

## Architecture

```text
Users -> API -> PostgreSQL / Redis / Kafka
           |           |
         RED + USE + OTel spans
                   |
           OTel Collector -> Tempo / Loki / Prometheus
                   |
             Grafana / SLO alerts
                   |
          k6 + profiler + incident commander
                   |
             rollback and validation
```

## Acceptance matrix

| Area | Evidence |
|---|---|
| RED and SLO | availability, error rate, p95/p99 and throughput |
| Dependencies | PostgreSQL pool/locks, Redis latency and Kafka backlog |
| Tracing | W3C traceparent, service map and critical path |
| Runtime | CPU/wall time, heap/GC, thread and async waits |
| Load | requested vs achieved RPS, dropped iterations, saturation |
| Telemetry | Collector drops, sampling, logs and dashboards |
| Security | tenant isolation, sanitized spans and least privilege |
| Recovery | alert routing, incident timeline and approved rollback |

Sampled traces do not replace independent request counters. Do not average per-instance percentiles. Closed-loop load generators can hide latency cliffs; verify achieved arrival rates. Avoid recording raw SQL, patient identifiers or secrets.

## Production game day

After a deployment, API p95 rises above its 300 ms SLO and errors spike. PostgreSQL connection-pool waits, Redis hot-key latency and Kafka consumer lag increase. Autoscaling adds pods but does not resolve dependency saturation. k6 drops iterations, and the trace service map omits an asynchronous consumer. Establish a UTC incident timeline, compare independent RED metrics with sampled traces, profile CPU/heap, inspect Collector queues and restore a safe baseline through an approved rollback.

## Local executable offline gate

Save as `capstone_gate.py`. This checks a **synthetic** review, not real application telemetry.

```python
import json,sys
from pathlib import Path
REQUIRED=["red","use","trace_context","service_map","dependency_spans","logs","collector","sampling","cpu_profile","memory_profile","load_test","generator_health","slo","privacy","incident_command","rollback"]
def validate(d):
 if not isinstance(d,dict):return ["expected object"]
 errors=[]
 if d.get("environment") not in ("lab","staging"):errors.append("unsafe environment")
 if not isinstance(d.get("owner"),str) or not d["owner"].strip():errors.append("missing owner")
 if not isinstance(d.get("change_id"),str) or not d["change_id"].strip():errors.append("missing change_id")
 c=d.get("checks")
 if not isinstance(c,dict):errors.append("invalid checks");c={}
 for k in REQUIRED:
  if c.get(k) is not True:errors.append("unverified "+k)
 for a,b in (("p95_ms","p95_budget_ms"),("error_rate_percent","error_budget_percent")):
  x,y=d.get(a),d.get(b)
  if type(x) not in (int,float) or x<0 or type(y) not in (int,float) or y<0:errors.append("invalid "+a)
  elif x>y:errors.append("breach "+a)
 if d.get("destructive_change") is not False:errors.append("unsafe action")
 return errors
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))
```

Save `healthy.json`:

```json
{"owner":"enterprise-apm","change_id":"OBS-070","environment":"staging","p95_ms":180,"p95_budget_ms":300,"error_rate_percent":0.2,"error_budget_percent":1,"destructive_change":false,"checks":{"red":true,"use":true,"trace_context":true,"service_map":true,"dependency_spans":true,"logs":true,"collector":true,"sampling":true,"cpu_profile":true,"memory_profile":true,"load_test":true,"generator_health":true,"slo":true,"privacy":true,"incident_command":true,"rollback":true}}
```

Save `test_capstone_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from capstone_gate import validate
class AcceptanceTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_not_object(self):self.assertTrue(validate(None))
 def test_unsafe_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="production";self.assertTrue(validate(p))
 def test_missing_review(self):
  p=copy.deepcopy(self.p);p["checks"]["trace_context"]=False;self.assertTrue(validate(p))
 def test_latency_breach(self):
  p=copy.deepcopy(self.p);p["p95_ms"]=900;self.assertTrue(validate(p))
 def test_error_breach(self):
  p=copy.deepcopy(self.p);p["error_rate_percent"]=20;self.assertTrue(validate(p))
 def test_destructive_action(self):
  p=copy.deepcopy(self.p);p["destructive_change"]=True;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

```bash
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Seven authored tests; execution not yet verified.

## 24 hands-on exercises

1. Map API dependency graph; capture timestamps, metrics, expected outcome and reviewer evidence.
2. Define availability SLI; capture timestamps, metrics, expected outcome and reviewer evidence.
3. Define latency SLI; capture timestamps, metrics, expected outcome and reviewer evidence.
4. Capture RED metrics; capture timestamps, metrics, expected outcome and reviewer evidence.
5. Capture USE saturation; capture timestamps, metrics, expected outcome and reviewer evidence.
6. Inspect W3C propagation; capture timestamps, metrics, expected outcome and reviewer evidence.
7. Inspect DB spans; capture timestamps, metrics, expected outcome and reviewer evidence.
8. Inspect Redis spans; capture timestamps, metrics, expected outcome and reviewer evidence.
9. Inspect Kafka spans; capture timestamps, metrics, expected outcome and reviewer evidence.
10. Correlate structured logs; capture timestamps, metrics, expected outcome and reviewer evidence.
11. Inspect Collector drops; capture timestamps, metrics, expected outcome and reviewer evidence.
12. Review sampling; capture timestamps, metrics, expected outcome and reviewer evidence.
13. Profile CPU; capture timestamps, metrics, expected outcome and reviewer evidence.
14. Profile memory; capture timestamps, metrics, expected outcome and reviewer evidence.
15. Review GC; capture timestamps, metrics, expected outcome and reviewer evidence.
16. Review thread pools; capture timestamps, metrics, expected outcome and reviewer evidence.
17. Run bounded k6 smoke; capture timestamps, metrics, expected outcome and reviewer evidence.
18. Run arrival-rate test; capture timestamps, metrics, expected outcome and reviewer evidence.
19. Compare requested/achieved RPS; capture timestamps, metrics, expected outcome and reviewer evidence.
20. Inspect generator drops; capture timestamps, metrics, expected outcome and reviewer evidence.
21. Review SLO burn; capture timestamps, metrics, expected outcome and reviewer evidence.
22. Simulate dependency fault; capture timestamps, metrics, expected outcome and reviewer evidence.
23. Rehearse rollback; capture timestamps, metrics, expected outcome and reviewer evidence.
24. Score capstone; capture timestamps, metrics, expected outcome and reviewer evidence.

## 24 production failure scenarios

1. **API p99 regression:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
2. **HTTP 5xx surge:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
3. **Downstream timeout:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
4. **Retry storm:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
5. **DB pool wait:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
6. **PostgreSQL lock storm:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
7. **Redis hot key:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
8. **Kafka consumer lag:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
9. **Thread starvation:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
10. **CPU throttling:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
11. **Memory leak:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
12. **GC pauses:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
13. **Async blocking:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
14. **Broken trace context:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
15. **Collector queue overload:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
16. **Sampling blind spot:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
17. **Log/trace mismatch:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
18. **Sensitive span attributes:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
19. **Cardinality explosion:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
20. **Load generator saturation:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
21. **Coordinated omission:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
22. **Autoscaling oscillation:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
23. **SLO burn:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.
24. **Rollback failure:** correlate RED, traces and runtime evidence, choose reversible mitigation and validate rollback.

## Eight production runbooks

1. **Incident command:** identify owner, independent user impact, severity and communications.
2. **Latency and errors:** inspect p95/p99, errors, release markers, retry amplification and traces.
3. **Dependencies:** inspect PostgreSQL pool/locks, Redis hot keys and Kafka backlog.
4. **Runtime:** inspect CPU/wall time, GC, heap, threads, async waits and cgroup limits.
5. **Trace gaps:** inspect W3C context, SDK sampling, Collector drops and Tempo ingestion.
6. **Load testing:** validate generator health, arrival rates, saturation and safe abort limits.
7. **SLO and security:** test burn alerts, sanitized attributes, tenant access and retention.
8. **Recovery:** roll back safely, verify independent SLOs and publish postmortem.

## 100-point assessment

| Domain | Points |
|---|---:|
| APM architecture and RED/USE | 20 |
| Tracing, service maps and dependencies | 20 |
| Runtime profiling and diagnostics | 20 |
| Load testing, security and validation | 20 |
| Incident response, SLOs and rollback | 20 |
| **Total** | **100** |

Recommended passing score 85/100. Production sign-off requires witnessed staging game days, tested alert routing and rollback.

**Companion:** [Chapter 070 lab](labs/070-enterprise-application-performance-monitoring-incident-response-reliability-capstone-lab.md).

**Part 14 complete. Next:** Chapter 071 — Service Level Indicators, Objectives and Error Budget Engineering (Part 15).
