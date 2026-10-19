# Chapter 077 — Enterprise Incident Triage, Signal Correlation and Root Cause Investigation

**Part 16 — Incident Response and Troubleshooting (2/5)**  
**Audience:** Enterprise SRE, DBRE, on-call engineers, incident commanders.  
**Prerequisites:** Chapter 076, Prometheus, Grafana, Loki, Tempo, OpenTelemetry.

## Objectives

Investigate incidents systematically by correlating user-facing SLIs, RED/USE metrics, structured logs, distributed traces, deployments and database/platform telemetry. Separate causal evidence from coincidental correlation, validate hypotheses and preserve reproducible RCA evidence.

## Architecture

```text
User symptoms / SLO burn / synthetic probes
                     |
             Incident UTC timeline
                     |
         Prometheus + Grafana metrics
          /             |           \
       Loki logs     Tempo traces   change events
          \             |           /
               dependency map
            /      |       |      \
       Postgres  Redis   Kafka   Search / Snowflake
                     |
              hypotheses / tests
                     |
           reversible mitigation
                     |
             independent recovery
                     |
                  RCA
```

## Triage method

1. Establish the exact affected user journey, scope, start time and SLO burn. A host CPU spike alone is not customer impact.
2. Query RED (rate, errors, duration) and USE (utilization, saturation, errors) in the same UTC window.
3. Inspect deployments, feature flags, autoscaling, certificate rotation and network changes.
4. Pivot from a slow request trace to its dependency spans; distinguish critical path from asynchronous processing.
5. Correlate logs using trace IDs, bounded labels and redaction. Do not log credentials or patient data.
6. Form at least two competing hypotheses, predict evidence for each, and seek disconfirming signals.
7. Select a reversible mitigation, record owner and rollback criteria, then verify independent user-facing recovery.
8. Publish a causal timeline distinguishing triggering event, contributing factors, latent weaknesses and corrective actions.

## Investigation query examples

```promql
# Five-minute API error fraction: adapt names and labels
sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
```

```promql
# Pod CPU throttling ratio: compare throttled and total CFS periods
sum by (pod) (rate(container_cpu_cfs_throttled_periods_total[5m]))
/
clamp_min(sum by (pod) (rate(container_cpu_cfs_periods_total[5m])), 1e-9)
```

```logql
{service_name="api"} |= "timeout"
```

LogQL labels vary by ingestion pipeline; verify actual schema and privacy policy. For traces, inspect W3C trace context, span errors, sampling bias and dependency timing. A missing span is not proof that a dependency was healthy.

## Data-platform evidence matrix

| System | Primary signals | Causal validation |
|---|---|---|
| PostgreSQL | pg_stat_activity, wait events, locks, pool waits | blocked query tree and request trace |
| Redis | latency, CPU, hot keys, evictions | key-pattern concentration and client latency |
| Kafka/MSK | partition lag, rebalances, broker saturation | processing age and end-to-end freshness |
| Elasticsearch/OpenSearch | rejected searches, shard latency, disk queue | slowlog and storage saturation correlation |
| Snowflake | warehouse queue, task history, load latency | source-to-target freshness and failed tasks |
| Kubernetes | restarts, throttling, probes, node pressure | event timeline and application errors |

## Root cause vs correlation

A release immediately before an outage is a candidate trigger, not proof. Test whether rollback reverses the user-facing SLI, whether unaffected regions differ, and whether an independent dependency regression explains the timing. Document uncertainty rather than inventing a definitive root cause.

## Production simulation

A new release increases concurrency. PostgreSQL pool wait time rises, API p99 grows, retries amplify traffic and Redis latency also rises. Determine whether the release, database pool limit or retry policy is the primary trigger. Correlate request traces, pool metrics and UTC change history; perform a bounded staging rollback and verify API SLO recovery.

## Executable offline evidence gate

### healthy.json

```json
{
  "owner": "incident-triage-sre",
  "environment": "staging",
  "incident_id": "INC-077",
  "customer_impact_confirmed": true,
  "utc_timeline_complete": true,
  "hypotheses_reviewed": true,
  "destructive_action": false,
  "checks": {
    "incident_scope": true,
    "utc_timeline": true,
    "slo_burn": true,
    "red_metrics": true,
    "use_metrics": true,
    "logs": true,
    "traces": true,
    "deploy_changes": true,
    "dependency_map": true,
    "postgres": true,
    "redis": true,
    "kafka": true,
    "search": true,
    "snowflake": true,
    "hypothesis": true,
    "counterevidence": true,
    "rollback": true,
    "recovery": true
  }
}
```

### triage_gate.py

```python
"""Offline incident-triage evidence gate; synthetic manifest only."""
import json,sys
from pathlib import Path
CHECKS=["incident_scope","utc_timeline","slo_burn","red_metrics","use_metrics","logs","traces","deploy_changes","dependency_map","postgres","redis","kafka","search","snowflake","hypothesis","counterevidence","rollback","recovery"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["expected object"]
 for k in ("owner","incident_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("customer_impact_confirmed","utc_timeline_complete","hypotheses_reviewed"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());findings=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_triage_gate.py

```python
import copy,json,unittest
from pathlib import Path
from triage_gate import validate
class TriageTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["incident_scope"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["utc_timeline"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["slo_burn"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["red_metrics"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["use_metrics"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["logs"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["traces"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["deploy_changes"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dependency_map"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["postgres"]=False
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
  p["checks"]["search"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["snowflake"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["hypothesis"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["counterevidence"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["recovery"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["incident_id"]=""
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["customer_impact_confirmed"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["utc_timeline_complete"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["hypotheses_reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["checks"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 triage_gate.py healthy.json
python3 -m unittest -v test_triage_gate.py
```

Expected PASS and **28 authored tests**. Execution and live RCA verification remain pending.

## 24 hands-on exercises

1. Define customer symptom.
2. Set UTC time window.
3. Confirm service owner.
4. Identify affected journey.
5. Quantify SLO burn.
6. Inspect request errors.
7. Inspect latency histogram.
8. Inspect saturation.
9. Check deployment timeline.
10. Query structured logs.
11. Follow trace critical path.
12. Inspect service dependency graph.
13. Review PostgreSQL waits.
14. Review Redis latency.
15. Review Kafka lag.
16. Review Elasticsearch rejections.
17. Review Snowflake freshness.
18. Review Kubernetes restarts.
19. Identify competing hypotheses.
20. Collect disconfirming evidence.
21. Prioritize reversible mitigation.
22. Test recovery signal.
23. Draft causal timeline.
24. Conduct RCA review.

## 24 production failure scenarios

1. **5xx surge:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
2. **p99 spike:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
3. **CPU throttling:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
4. **OOMKilled pods:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
5. **PostgreSQL lock chain:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
6. **Connection pool starvation:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
7. **Redis hot-key overload:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
8. **Redis eviction:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
9. **Kafka consumer lag:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
10. **Kafka rebalance storm:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
11. **Elasticsearch rejected searches:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
12. **Elasticsearch storage saturation:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
13. **Snowflake queueing:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
14. **Snowflake stale CDC:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
15. **DNS timeout:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
16. **Network packet loss:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
17. **TLS certificate expiration:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
18. **OpenTelemetry trace gap:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
19. **Log sampling bias:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
20. **Prometheus scrape gap:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
21. **Deploy-induced regression:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
22. **Misleading correlation:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
23. **Cascading retries:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.
24. **Recovery not sustained:** establish impact, compare competing hypotheses, collect evidence, mitigate and verify recovery.

## Eight production runbooks

1. **Frame impact: document affected user journey, blast radius, severity and SLO burn.**
2. **Build timeline: correlate UTC deployments, alert transitions, metrics and logs.**
3. **Trace critical path: identify spans, dependencies and missing sampling evidence.**
4. **Database triage: inspect PostgreSQL locks/pools, Redis, Kafka, search and Snowflake.**
5. **Hypothesis discipline: list causes, predicted evidence, disconfirming tests and confidence.**
6. **Telemetry integrity: detect absent series, counter resets, log drops and trace sampling.**
7. **Mitigate safely: choose approved reversible action with clear rollback trigger.**
8. **RCA: distinguish trigger, contributing conditions, root cause and preventive actions.**

## 100-point assessment

| Area | Points |
|---|---:|
| Impact framing and timeline | 20 |
| Metrics, logs and traces correlation | 20 |
| Dependency investigation | 20 |
| Hypothesis testing and offline gate | 20 |
| Mitigation, recovery and RCA | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production sign-off requires witnessed staging drills and reviewed RCA evidence.

**Companion:** [Chapter 077 lab](labs/077-enterprise-incident-triage-signal-correlation-root-cause-investigation-lab.md).

**Next:** Chapter 078 — Enterprise Incident Mitigation, Safe Rollback and Recovery Verification.
