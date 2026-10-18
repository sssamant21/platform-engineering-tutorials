# Chapter 058 — Kubernetes Workload, Pod, Application Logs and Distributed Tracing Observability

**Part 12 — Kubernetes, EKS, AKS and GKE Observability**  
**Audience:** Kubernetes SRE, DBRE, application and observability teams.  
**Prerequisites:** Chapters 056–057, Loki, OpenTelemetry, Jaeger/Tempo and Grafana.

## Objectives

Observe Kubernetes workload health and correlate pod events, structured logs, application RED metrics and distributed traces across EKS, AKS and GKE. Design safe logging/OTLP collection, sampling, privacy controls, incident runbooks and recovery.

## Architecture

```text
Kubernetes Deployment -> Pods -> stdout/stderr -> node log agent -> Loki
                      |                 |
                      +-> OTel SDK -> Collector -> Tempo/Jaeger
                      |
                      +-> /metrics -> Prometheus
                      |
                      +-> events / replica state -> kube-state-metrics
Grafana: RED dashboards -> exemplar/trace ID -> traces -> sanitized logs
```

Kubernetes pod logs are usually container stdout/stderr managed by the runtime and node log rotation. Sidecars are optional. A logging agent may be a DaemonSet or an approved managed provider integration; it should use minimal privileges.

## Workload health signals

| Signal | Source | Meaning | Limitation |
|---|---|---|---|
| Pod phase and conditions | Kubernetes API | scheduling/readiness state | not a user-facing SLI |
| Restart/OOM | kube-state-metrics, kubelet, events | workload instability | event retention may be short |
| Request count/errors/latency | application metrics | user-impact RED | requires instrumentation |
| Structured logs | stdout/agent/Loki | detailed diagnostics | not all logs arrive |
| Distributed traces | OTel SDK/Collector/Tempo | causal request path | sampling may hide failures |

## Read-only operational commands

```bash
kubectl config current-context
kubectl get pods -n observability-lab -o wide
kubectl get events -n observability-lab --sort-by=.lastTimestamp
kubectl describe pod -n observability-lab POD_NAME
kubectl logs -n observability-lab POD_NAME --tail=100 --timestamps
kubectl logs -n observability-lab POD_NAME --previous --tail=100
kubectl get deploy -n observability-lab
```

Use real pod names only after inspection. `--previous` works when a prior terminated container instance exists. Avoid collecting secrets, PHI or credentials.

## Correlation and queries

Example sanitized JSON log:

```json
{"timestamp":"2026-10-18T13:00:00Z","level":"ERROR","service":"orders-api","trace_id":"0123456789abcdef0123456789abcdef","span_id":"0123456789abcdef","message":"database connection pool wait"}
```

Example LogQL:

```logql
{namespace="observability-lab", app="orders-api"} | json | level="ERROR"
```

Example Tempo TraceQL:

```traceql
{ resource.service.name = "orders-api" }
```

Label names are deployment-specific. Use trace IDs in log fields rather than high-cardinality Loki stream labels. Ensure trace IDs and timestamps are correlated in Grafana without claiming sampled traces represent all requests.

## Production design

Set bounded log labels, explicit retention, encryption, authenticated OTLP, Collector memory/queue limits and sampling policies. For EKS, AKS and GKE verify IAM/workload identity, node agent permissions and provider-native logging integration. Never expose unrestricted Loki/Tempo query endpoints or sensitive span attributes.

## SRE/DBRE incident simulation

A PostgreSQL-backed API on AKS enters CrashLoopBackOff. Application p95 is elevated; a log agent is dropping entries and trace context is missing on Kafka consumers. Confirm user impact from independent metrics, inspect pod events/previous logs, trace exporter errors, database connection saturation and log pipeline backpressure. Restore agent and SDK config, verify log and trace retrieval, and document remaining visibility gaps.

## Executable offline acceptance gate

The synthetic manifest checks declarations and thresholds only; it **does not** access Kubernetes, Loki, Tempo or Jaeger.

### healthy.json

```json
{
  "owner": "workload-sre",
  "environment": "staging",
  "cloud": "eks",
  "namespace": "observability-lab",
  "application": "orders-api",
  "trace_id": "0123456789abcdef0123456789abcdef",
  "log_delivery_percent": 99,
  "minimum_log_delivery_percent": 98,
  "trace_query_p95_ms": 350,
  "max_trace_query_p95_ms": 1000,
  "production_delete": false,
  "pod_logs_reviewed": true,
  "namespace_labels_reviewed": true,
  "trace_context_reviewed": true,
  "otel_collector_reviewed": true,
  "loki_pipeline_reviewed": true,
  "tempo_jaeger_reviewed": true,
  "workload_red_metrics_reviewed": true,
  "pod_events_reviewed": true,
  "rbac_reviewed": true,
  "network_policy_reviewed": true,
  "pii_redaction_reviewed": true,
  "cardinality_reviewed": true,
  "retention_reviewed": true,
  "sampling_reviewed": true,
  "alert_routing_reviewed": true,
  "rollback_tested": true
}
```

### workload_gate.py

```python
"""Offline Kubernetes workload observability gate; no cluster/backend access."""
import json,re,sys
from pathlib import Path
FLAGS=["pod_logs_reviewed","namespace_labels_reviewed","trace_context_reviewed","otel_collector_reviewed","loki_pipeline_reviewed","tempo_jaeger_reviewed","workload_red_metrics_reviewed","pod_events_reviewed","rbac_reviewed","network_policy_reviewed","pii_redaction_reviewed","cardinality_reviewed","retention_reviewed","sampling_reviewed","alert_routing_reviewed","rollback_tested"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","namespace","application"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("cloud") not in ("eks","aks","gke"):e.append("unsupported cloud")
 t=p.get("trace_id")
 if not isinstance(t,str) or not re.fullmatch("[0-9a-f]{32}",t) or int(t,16)==0:e.append("invalid trace id")
 for k in FLAGS:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("log_delivery_percent","minimum_log_delivery_percent"):
  if type(p.get(k)) is not int or not 0<=p[k]<=100:e.append("invalid "+k)
 for k in ("trace_query_p95_ms","max_trace_query_p95_ms"):
  if type(p.get(k)) is not int or p[k]<=0:e.append("invalid "+k)
 for a,b,rule in (("log_delivery_percent","minimum_log_delivery_percent","min"),("trace_query_p95_ms","max_trace_query_p95_ms","max")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((rule=="min" and x<y) or (rule=="max" and x>y)):e.append("threshold missed "+a)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_workload_gate.py

```python
import copy,json,unittest
from pathlib import Path
from workload_gate import validate
class WorkloadGateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_cloud(self):
  p=copy.deepcopy(self.p);p["cloud"]="invalid";self.assertTrue(validate(p))
 def test_04_namespace(self):
  p=copy.deepcopy(self.p);p["namespace"]="";self.assertTrue(validate(p))
 def test_05_application(self):
  p=copy.deepcopy(self.p);p["application"]="";self.assertTrue(validate(p))
 def test_06_trace_id(self):
  p=copy.deepcopy(self.p);p["trace_id"]="bad";self.assertTrue(validate(p))
 def test_07_pod_logs_reviewed(self):
  p=copy.deepcopy(self.p);p["pod_logs_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_namespace_labels_reviewed(self):
  p=copy.deepcopy(self.p);p["namespace_labels_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_trace_context_reviewed(self):
  p=copy.deepcopy(self.p);p["trace_context_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_otel_collector_reviewed(self):
  p=copy.deepcopy(self.p);p["otel_collector_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_loki_pipeline_reviewed(self):
  p=copy.deepcopy(self.p);p["loki_pipeline_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_tempo_jaeger_reviewed(self):
  p=copy.deepcopy(self.p);p["tempo_jaeger_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_workload_red_metrics_reviewed(self):
  p=copy.deepcopy(self.p);p["workload_red_metrics_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_pod_events_reviewed(self):
  p=copy.deepcopy(self.p);p["pod_events_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_rbac_reviewed(self):
  p=copy.deepcopy(self.p);p["rbac_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_network_policy_reviewed(self):
  p=copy.deepcopy(self.p);p["network_policy_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_pii_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_retention_reviewed(self):
  p=copy.deepcopy(self.p);p["retention_reviewed"]=False;self.assertTrue(validate(p))
 def test_20_sampling_reviewed(self):
  p=copy.deepcopy(self.p);p["sampling_reviewed"]=False;self.assertTrue(validate(p))
 def test_21_alert_routing_reviewed(self):
  p=copy.deepcopy(self.p);p["alert_routing_reviewed"]=False;self.assertTrue(validate(p))
 def test_22_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_23_log_delivery_percent(self):
  p=copy.deepcopy(self.p);p["log_delivery_percent"]=50;self.assertTrue(validate(p))
 def test_24_minimum_log_delivery_percent(self):
  p=copy.deepcopy(self.p);p["minimum_log_delivery_percent"]=101;self.assertTrue(validate(p))
 def test_25_trace_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["trace_query_p95_ms"]=2000;self.assertTrue(validate(p))
 def test_26_max_trace_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["max_trace_query_p95_ms"]=0;self.assertTrue(validate(p))
 def test_27_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter058 && cd chapter058
# Save blocks as healthy.json, workload_gate.py, test_workload_gate.py
python3 workload_gate.py healthy.json
python3 -m unittest -v test_workload_gate.py
```

Expected PASS and **29 authored Python tests**.

## 24 hands-on exercises

1. Inventory namespace workloads.
2. Inspect pod lifecycle.
3. Review pod restart events.
4. Collect pod stdout logs.
5. Review sidecar logging.
6. Inspect container termination.
7. Configure structured JSON logs.
8. Review log label mapping.
9. Verify Loki query.
10. Verify log delivery lag.
11. Inject trace_id into logs.
12. Propagate traceparent.
13. Instrument HTTP spans.
14. Instrument PostgreSQL spans.
15. Instrument Redis spans.
16. Instrument Kafka consumer.
17. Review Collector OTLP receivers.
18. Review sampling policy.
19. Query Tempo trace.
20. Query Jaeger trace.
21. Correlate Grafana dashboard.
22. Verify workload RED metrics.
23. Simulate log pipeline outage.
24. Test rollback.

## 24 production failure scenarios

1. **Pod logs missing:** inspect workload, logs, traces, security and independent SLIs.
2. **Container runtime log rotation:** inspect workload, logs, traces, security and independent SLIs.
3. **Log agent unscheduled:** inspect workload, logs, traces, security and independent SLIs.
4. **Loki ingestion rejected:** inspect workload, logs, traces, security and independent SLIs.
5. **Loki label cardinality high:** inspect workload, logs, traces, security and independent SLIs.
6. **JSON parse failure:** inspect workload, logs, traces, security and independent SLIs.
7. **Timestamp skew:** inspect workload, logs, traces, security and independent SLIs.
8. **Trace ID missing in logs:** inspect workload, logs, traces, security and independent SLIs.
9. **Trace context broken:** inspect workload, logs, traces, security and independent SLIs.
10. **OTLP endpoint unreachable:** inspect workload, logs, traces, security and independent SLIs.
11. **Collector queue full:** inspect workload, logs, traces, security and independent SLIs.
12. **Collector OOM:** inspect workload, logs, traces, security and independent SLIs.
13. **Tempo query timeout:** inspect workload, logs, traces, security and independent SLIs.
14. **Jaeger storage unavailable:** inspect workload, logs, traces, security and independent SLIs.
15. **Sampled traces missing:** inspect workload, logs, traces, security and independent SLIs.
16. **Pod CrashLoopBackOff:** inspect workload, logs, traces, security and independent SLIs.
17. **Container OOMKilled:** inspect workload, logs, traces, security and independent SLIs.
18. **Deployment unavailable:** inspect workload, logs, traces, security and independent SLIs.
19. **Replica mismatch:** inspect workload, logs, traces, security and independent SLIs.
20. **NetworkPolicy blocks OTLP:** inspect workload, logs, traces, security and independent SLIs.
21. **RBAC blocks log access:** inspect workload, logs, traces, security and independent SLIs.
22. **Sensitive data leaked:** inspect workload, logs, traces, security and independent SLIs.
23. **Alert routing missing:** inspect workload, logs, traces, security and independent SLIs.
24. **Rollback fails:** inspect workload, logs, traces, security and independent SLIs.

## Eight production runbooks

1. **Pod logs absent:** inspect pod/container, log agent, node files and Loki ingestion.
2. **Trace gaps:** inspect W3C context, SDK instrumentation, Collector export and sampling.
3. **Collector overload:** inspect memory, queues, exporter errors, retries and drops.
4. **CrashLoopBackOff:** inspect events, previous container logs, probes and dependencies.
5. **Loki query failure:** inspect tenant, labels, time range, retention and backend health.
6. **PII exposure:** stop unsafe emission, isolate access, redact and escalate appropriately.
7. **SLO regression:** compare independent RED metrics with logs and representative traces.
8. **Recovery:** restore pinned agents/configs, validate log and trace retrieval and rollback.

## 100-point assessment

| Domain | Points |
|---|---:|
| Workload/pod signals and lifecycle | 20 |
| Structured logs and Loki operations | 20 |
| Distributed tracing and correlation | 20 |
| Offline tests, security and evidence | 20 |
| Incident investigation and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production readiness requires witnessed end-to-end log and trace retrieval, access reviews and recovery tests.

**Companion:** [Chapter 058 hands-on lab](labs/058-kubernetes-workload-pod-application-logs-distributed-tracing-observability-lab.md).

**Next:** Chapter 059 — Kubernetes Control Plane, Networking, Storage and Autoscaling Observability.
