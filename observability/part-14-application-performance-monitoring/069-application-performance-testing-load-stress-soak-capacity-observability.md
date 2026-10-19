# Chapter 069 — Application Performance Testing, Load, Stress, Soak and Capacity Observability

**Part 14 — Application Performance Monitoring**  
**Audience:** SRE, performance engineers, DBRE and platform capacity owners.  
**Prerequisites:** Chapters 066–068, Prometheus/Grafana and application RED signals.

## Objectives

Design realistic, bounded performance tests, distinguish load/stress/spike/soak testing, avoid coordinated omission, measure throughput and latency under saturation, and convert observations into capacity forecasts and production guardrails.

## Architecture

```text
Synthetic traffic model -> isolated staging load generator
                               |
                           API / workers
                               |
                 PostgreSQL / Redis / Kafka
                               |
                  RED + USE + OTel traces
                               |
                   Prometheus / Grafana
                               |
            SLO evaluation + capacity / cost forecast
                               |
                      rollback / evidence
```

## Workload theory

| Test | Purpose | Evidence |
|---|---|---|
| Smoke | verify correctness and instrumentation | success rate |
| Load | validate expected concurrency/arrival rate | p95/p99, RPS, errors |
| Stress | find saturation and failure behavior | throughput knee, queues |
| Spike | test burst absorption and autoscaling | backlog, recovery time |
| Soak | identify gradual leaks and degradation | memory/GC/latency trend |
| Capacity | estimate sustainable headroom | safe throughput vs resources |

An **open-loop** model attempts a specified arrival rate independently of response times; a **closed-loop** virtual-user model naturally reduces arrivals when responses slow. Coordinated omission can hide severe latency. Always compare *requested* vs *achieved* arrival rates, dropped iterations and generator saturation. Include warmup, steady-state, cooldown and recovery windows.

## k6 staging example

Install k6 using your approved package process and target only an isolated staging service.

```javascript
// load.js
import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  scenarios: {
    bounded: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 20,
      maxVUs: 40
    }
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300'],
    dropped_iterations: ['count<10']
  }
};
export default function () {
  const res = http.get(__ENV.STAGING_URL + '/health');
  check(res, { 'health 200': r => r.status === 200 });
  sleep(0.05);
}
```

```bash
STAGING_URL=https://staging.example.invalid k6 run load.js
```

The placeholder URL is intentionally non-routable; substitute an approved staging endpoint. Use test credentials and synthetic data, never production patient data. Keep fixed maximum VUs, duration, request rate, and a stop plan.

## Prometheus/observability queries

```promql
sum(rate(http_server_request_duration_seconds_count[5m]))
```

```promql
histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket[5m])))
```

```promql
sum(rate(container_cpu_cfs_throttled_periods_total[5m]))
```

Exporter metric names and histogram types vary. Check achieved RPS, error rate, queue depth, CPU throttling, heap/GC, DB pool waits, Redis latency, Kafka consumer lag and autoscaler activity. Never use a single p95 threshold as proof of capacity without throughput and error evidence.

## Capacity and cost

For an observed stable throughput `T` at resource utilization `U`, a rough linear starting estimate is `T * target_U/U`, **only** when scaling is approximately linear and the downstream bottleneck is unchanged. Validate by multiple staged load levels. Model credits/instance-hours, observability ingestion cost, reserved headroom, failover capacity and burst requirements.

## Production incident simulation

A deployment causes p95 to exceed 300 ms at an expected 900 RPS. Autoscaling adds application pods but PostgreSQL pool waits and Kafka backlog increase; k6 dropped iterations reveal the generator also failed to sustain target traffic. Separate generator bottleneck from service saturation, compare RED and USE signals, stop the bounded test, roll back and re-run a controlled baseline.

## Offline acceptance gate

This gate validates a **synthetic review manifest**, not actual k6 output.

### healthy.json

```json
{
  "owner": "performance-sre",
  "environment": "staging",
  "change_id": "OBS-069",
  "achieved_rps": 950,
  "min_achieved_rps": 900,
  "p95_latency_ms": 190,
  "max_p95_latency_ms": 300,
  "error_rate_percent": 0.3,
  "max_error_rate_percent": 1,
  "load_generator_dropped_iterations": 0,
  "max_dropped_iterations": 10,
  "destructive_change": false,
  "checks": {
    "traffic_model": true,
    "staging_isolation": true,
    "load_generator": true,
    "baseline": true,
    "rps": true,
    "latency_histogram": true,
    "error_rate": true,
    "cpu": true,
    "memory": true,
    "db_pool": true,
    "redis": true,
    "kafka": true,
    "autoscaling": true,
    "soak": true,
    "cost": true,
    "rollback": true
  }
}
```

### load_gate.py

```python
"""Offline load-test acceptance manifest validator; synthetic only."""
import json,sys
from pathlib import Path
CHECKS=["traffic_model","staging_isolation","load_generator","baseline","rps","latency_histogram","error_rate","cpu","memory","db_pool","redis","kafka","autoscaling","soak","cost","rollback"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["expected object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 for k in ("achieved_rps","min_achieved_rps","p95_latency_ms","max_p95_latency_ms","error_rate_percent","max_error_rate_percent","load_generator_dropped_iterations","max_dropped_iterations"):
  x=p.get(k)
  if type(x) not in (int,float) or x<0:e.append("invalid "+k)
 for k in ("error_rate_percent","max_error_rate_percent"):
  x=p.get(k)
  if type(x) in (int,float) and x>100:e.append("invalid percent "+k)
 for a,b,kind in (("achieved_rps","min_achieved_rps","min"),("p95_latency_ms","max_p95_latency_ms","max"),("error_rate_percent","max_error_rate_percent","max"),("load_generator_dropped_iterations","max_dropped_iterations","max")):
  x,y=p.get(a),p.get(b)
  if type(x) in (int,float) and type(y) in (int,float) and ((kind=="min" and x<y) or (kind=="max" and x>y)):e.append("threshold breach "+a)
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_load_gate.py

```python
import copy,json,unittest
from pathlib import Path
from load_gate import validate
class LoadTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["traffic_model"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["staging_isolation"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["load_generator"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["baseline"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rps"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["latency_histogram"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["error_rate"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["cpu"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["memory"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["db_pool"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["redis"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kafka"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["autoscaling"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["soak"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["cost"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["achieved_rps"]=100
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["p95_latency_ms"]=900
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["error_rate_percent"]=20
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["load_generator_dropped_iterations"]=100
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["max_error_rate_percent"]=200
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=True
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 load_gate.py healthy.json
python3 -m unittest -v test_load_gate.py
```

Expected PASS and **28 authored tests**. Runtime validation remains pending.

## 24 hands-on exercises

1. Define workload and SLO baseline.
2. Identify representative traffic mix.
3. Select closed-loop and open-loop model.
4. Define arrival-rate targets.
5. Set staging load isolation.
6. Configure k6 smoke scenario.
7. Capture request latency histogram.
8. Capture HTTP error rate.
9. Inspect RPS throughput.
10. Inspect CPU throttling.
11. Inspect heap/GC.
12. Inspect DB pool saturation.
13. Inspect PostgreSQL waits.
14. Inspect Redis hot keys.
15. Inspect Kafka backlog.
16. Measure queue depth.
17. Run bounded ramp test.
18. Run controlled stress test.
19. Run staged soak test.
20. Inspect retry amplification.
21. Estimate capacity headroom.
22. Review cost per request.
23. Verify recovery and rollback.
24. Produce capacity recommendation.

## 24 production failure scenarios

1. **Latency cliff:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
2. **Error-rate surge:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
3. **CPU saturation:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
4. **Memory leak during soak:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
5. **GC pause spike:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
6. **DB pool exhaustion:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
7. **PostgreSQL lock contention:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
8. **Redis hot key:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
9. **Kafka lag growth:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
10. **Queue overflow:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
11. **Connection reset:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
12. **Load generator bottleneck:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
13. **Coordinated omission:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
14. **Unrepresentative traffic mix:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
15. **Cache warmup bias:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
16. **Autoscaler oscillation:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
17. **Rate-limit breach:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
18. **Downstream shared-resource impact:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
19. **Cost runaway:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
20. **Retry storm:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
21. **Saturation masked by average:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
22. **Insufficient histogram buckets:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
23. **Soak test data contamination:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.
24. **Rollback fails:** record requested/achieved load, RED/USE, dependency signals, root-cause hypothesis and rollback evidence.

## Eight production runbooks

1. **Load regression: compare baseline throughput, error rate, latency percentiles and release changes.**
2. **Saturation: inspect CPU throttling, GC, pools, queues, DB/Redis/Kafka dependencies.**
3. **Generator bottleneck: verify achieved arrival rate, client CPU, dropped iterations and network.**
4. **Coordinated omission: use arrival-rate model and count unmet iterations as failures.**
5. **Soak degradation: trend RSS, heap, GC, connection leaks and latency over time.**
6. **Autoscaling: inspect HPA targets, scale lag, warmup and downstream saturation.**
7. **Safety and cost: isolate staging, cap RPS, duration, users and credit budget.**
8. **Recovery: stop load, restore test state, verify SLOs and record rollback.**

## 100-point assessment

| Area | Points |
|---|---:|
| Workload design and test safety | 20 |
| Load/stress/soak instrumentation | 20 |
| Capacity, dependencies and autoscaling | 20 |
| Offline tests, cost and evidence | 20 |
| Incident recovery and rollback | 20 |
| **Total** | **100** |

Suggested pass 85/100. Production acceptance requires witnessed staging load tests, generator validation, privacy review and rollback.

**Companion:** [Chapter 069 lab](labs/069-application-performance-testing-load-stress-soak-capacity-observability-lab.md).

**Next:** Chapter 070 — Enterprise Application Performance Monitoring, Incident Response and Reliability Capstone.
