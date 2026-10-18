# Chapter 056 — Kubernetes Observability Architecture for EKS, AKS and GKE

**Part 12 — Kubernetes, EKS, AKS and GKE Observability**  
**Audience:** Kubernetes administrators, SRE, DBRE and platform engineers.  
**Prerequisites:** Kubernetes, Prometheus, Grafana, Loki, OpenTelemetry and Chapters 001–055.

## 1. Learning objectives

Design a multi-cloud Kubernetes observability architecture for Amazon EKS, Azure AKS and Google GKE. Distinguish managed control-plane visibility from worker-node and application telemetry. Build metrics, logs, traces, dashboards and alert pipelines with RBAC, tenancy and cost controls.

## 2. Reference architecture

```text
 EKS / AKS / GKE managed control planes -> cloud-native monitoring
                     |
            Kubernetes API
                     |
 node-exporter + kubelet/cAdvisor + kube-state-metrics
                     |
     Prometheus / managed metrics remote write
                     |
                  Grafana
                     |
 Pods -> logs -> OTel Collector / log agents -> Loki
 Pods -> traces -> OTel Collector -> Jaeger / Tempo
                     |
            alerts -> Alertmanager
```

Control-plane metrics availability and access differ by cloud, cluster mode and version. Managed provider monitoring is not automatically equivalent to self-managed Prometheus scraping.

## 3. Signal ownership matrix

| Signal | Source | Typical use | Caveat |
|---|---|---|---|
| Node CPU/memory/disk | node-exporter, kubelet/cAdvisor | saturation, capacity | metric names vary by release |
| Pod/container resource use | kubelet/cAdvisor | throttling, OOM | account for limits and cgroups |
| Desired vs ready replicas | kube-state-metrics | deployment availability | reflects API state, not user success |
| HPA input | metrics-server / custom metrics adapter | autoscaling | metrics-server is not historical monitoring |
| Control plane | cloud-native provider, supported endpoints | API errors, etcd/control plane | managed-plane access varies |
| App RED | application/OTel metrics | SLOs | avoid unbounded labels |
| Logs | node/pod log pipeline | diagnostics | enforce PII redaction |
| Traces | OTel SDK/Collector | causal analysis | sampling bias |

## 4. Multi-cloud operational differences

**EKS:** Validate IAM roles for service accounts or EKS Pod Identity as applicable, CloudWatch control-plane logging, endpoint access and managed Prometheus/Grafana integration if used.

**AKS:** Validate Microsoft Entra authentication, managed identity, Azure Monitor/Container Insights and Azure Managed Prometheus. Distinguish Azure control-plane logs from application logs.

**GKE:** Validate Workload Identity Federation for GKE, Cloud Monitoring/Logging, managed collection options and cluster-mode differences. Confirm exposed metrics and quotas.

Never assume all three clouds expose identical etcd, scheduler or API server telemetry.

## 5. Read-only operational commands

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get deploy -A
kubectl get daemonsets -A
kubectl top nodes  # requires metrics-server or equivalent
kubectl top pods -A
kubectl get servicemonitors,podmonitors -A  # requires installed CRDs
```

Some commands require optional components and permissions; absence of ServiceMonitor CRDs is not a Kubernetes failure. Avoid changing production resources during discovery.

## 6. Prometheus and OpenTelemetry design

Use explicit scrape discovery, relabeling, namespace boundaries and bounded label cardinality. Instrument workload RED metrics independently from sampled traces. Deploy OTel Collectors as gateway and/or agent patterns where appropriate; size queues, retries and memory limiter. Secure remote write/OTLP endpoints and avoid embedding secrets in ConfigMaps.

## 7. Dashboard and alert baseline

Dashboards: cluster capacity, node CPU/memory, pod readiness, deployment rollout, OOM/restarts, container throttling, network errors, scrape health and Collector exporter failures. Alerts: user-facing SLO burn, pod unavailability, node pressure, storage pressure and telemetry blind spots. Use routing, grouping, ownership and runbooks.

## 8. Executable offline architecture gate

The synthetic manifest checks declared design review and arithmetic thresholds. It does **not** connect to Kubernetes or validate cloud permissions.

### healthy.json

```json
{
  "owner": "platform-observability",
  "environment": "staging",
  "cloud": "eks",
  "cluster": "staging-cluster",
  "scrape_success_percent": 99,
  "minimum_scrape_success_percent": 98,
  "telemetry_delay_seconds": 20,
  "max_telemetry_delay_seconds": 60,
  "production_delete": false,
  "cluster_identity_reviewed": true,
  "kube_state_metrics_reviewed": true,
  "node_exporter_reviewed": true,
  "kubelet_cadvisor_reviewed": true,
  "metrics_server_role_reviewed": true,
  "otel_collector_reviewed": true,
  "prometheus_scrape_reviewed": true,
  "grafana_dashboard_reviewed": true,
  "loki_logging_reviewed": true,
  "tracing_reviewed": true,
  "rbac_reviewed": true,
  "network_policy_reviewed": true,
  "cardinality_reviewed": true,
  "pii_redaction_reviewed": true,
  "retention_reviewed": true,
  "alert_routing_reviewed": true,
  "rollback_tested": true
}
```

### kubernetes_observability_gate.py

```python
"""Offline Kubernetes observability review; no cluster/API access."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","cluster"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("cloud") not in ("eks","aks","gke"):e.append("unsupported cloud")
 for k in ["cluster_identity_reviewed","kube_state_metrics_reviewed","node_exporter_reviewed","kubelet_cadvisor_reviewed","metrics_server_role_reviewed","otel_collector_reviewed","prometheus_scrape_reviewed","grafana_dashboard_reviewed","loki_logging_reviewed","tracing_reviewed","rbac_reviewed","network_policy_reviewed","cardinality_reviewed","pii_redaction_reviewed","retention_reviewed","alert_routing_reviewed","rollback_tested"]:
  if p.get(k) is not True:e.append("unverified "+k)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 for k in ("scrape_success_percent","minimum_scrape_success_percent"):
  v=p.get(k)
  if type(v) is not int or not 0<=v<=100:e.append("invalid "+k)
 for k in ("telemetry_delay_seconds","max_telemetry_delay_seconds"):
  v=p.get(k)
  if type(v) is not int or v<=0:e.append("invalid "+k)
 for a,b,rule in (("scrape_success_percent","minimum_scrape_success_percent","min"),("telemetry_delay_seconds","max_telemetry_delay_seconds","max")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((rule=="min" and x<y) or (rule=="max" and x>y)):e.append("threshold missed "+a)
 return e
if __name__=="__main__":
 try: errors=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_kubernetes_observability_gate.py

```python
import copy,json,unittest
from pathlib import Path
from kubernetes_observability_gate import validate
class KubernetesObservabilityTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_cloud(self):
  p=copy.deepcopy(self.p);p["cloud"]="unknown";self.assertTrue(validate(p))
 def test_04_cluster(self):
  p=copy.deepcopy(self.p);p["cluster"]="";self.assertTrue(validate(p))
 def test_05_cluster_identity_reviewed(self):
  p=copy.deepcopy(self.p);p["cluster_identity_reviewed"]=False;self.assertTrue(validate(p))
 def test_06_kube_state_metrics_reviewed(self):
  p=copy.deepcopy(self.p);p["kube_state_metrics_reviewed"]=False;self.assertTrue(validate(p))
 def test_07_node_exporter_reviewed(self):
  p=copy.deepcopy(self.p);p["node_exporter_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_kubelet_cadvisor_reviewed(self):
  p=copy.deepcopy(self.p);p["kubelet_cadvisor_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_metrics_server_role_reviewed(self):
  p=copy.deepcopy(self.p);p["metrics_server_role_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_otel_collector_reviewed(self):
  p=copy.deepcopy(self.p);p["otel_collector_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_prometheus_scrape_reviewed(self):
  p=copy.deepcopy(self.p);p["prometheus_scrape_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_grafana_dashboard_reviewed(self):
  p=copy.deepcopy(self.p);p["grafana_dashboard_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_loki_logging_reviewed(self):
  p=copy.deepcopy(self.p);p["loki_logging_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_tracing_reviewed(self):
  p=copy.deepcopy(self.p);p["tracing_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_rbac_reviewed(self):
  p=copy.deepcopy(self.p);p["rbac_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_network_policy_reviewed(self):
  p=copy.deepcopy(self.p);p["network_policy_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_pii_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_retention_reviewed(self):
  p=copy.deepcopy(self.p);p["retention_reviewed"]=False;self.assertTrue(validate(p))
 def test_20_alert_routing_reviewed(self):
  p=copy.deepcopy(self.p);p["alert_routing_reviewed"]=False;self.assertTrue(validate(p))
 def test_21_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_22_scrape_success_percent(self):
  p=copy.deepcopy(self.p);p["scrape_success_percent"]=50;self.assertTrue(validate(p))
 def test_23_minimum_scrape_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_scrape_success_percent"]=101;self.assertTrue(validate(p))
 def test_24_telemetry_delay_seconds(self):
  p=copy.deepcopy(self.p);p["telemetry_delay_seconds"]=100;self.assertTrue(validate(p))
 def test_25_max_telemetry_delay_seconds(self):
  p=copy.deepcopy(self.p);p["max_telemetry_delay_seconds"]=0;self.assertTrue(validate(p))
 def test_26_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter056 && cd chapter056
# Save blocks as healthy.json, kubernetes_observability_gate.py and test_kubernetes_observability_gate.py
python3 kubernetes_observability_gate.py healthy.json
python3 -m unittest -v test_kubernetes_observability_gate.py
```

Expected PASS and **28 authored Python tests**.

## 9. Twenty-four exercises

1. Identify EKS control plane signals.
2. Identify AKS control plane signals.
3. Identify GKE control plane signals.
4. Inventory kube-state-metrics.
5. Review kubelet/cAdvisor.
6. Review node-exporter.
7. Explain metrics-server limits.
8. Design OTel Collector.
9. Inspect ServiceMonitor.
10. Inspect PodMonitor.
11. Check scrape targets.
12. Review API server metrics access.
13. Review scheduler metrics access.
14. Review controller-manager metrics access.
15. Collect pod logs.
16. Correlate pod traces.
17. Create Grafana cluster overview.
18. Create workload RED dashboard.
19. Review namespace labels.
20. Review cardinality limits.
21. Test RBAC.
22. Test network policy.
23. Simulate scrape outage.
24. Document rollback.

## 10. Twenty-four production failure scenarios

1. **kube-state-metrics missing:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
2. **node-exporter DaemonSet crash:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
3. **kubelet scrape denied:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
4. **cAdvisor metric changed:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
5. **metrics-server confused with Prometheus:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
6. **Prometheus targets down:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
7. **ServiceMonitor selector mismatch:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
8. **PodMonitor wrong namespace:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
9. **EKS endpoint unreachable:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
10. **AKS AAD auth expired:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
11. **GKE permissions missing:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
12. **Control plane metrics unavailable:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
13. **Collector OOM:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
14. **Collector exporter retries:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
15. **High label cardinality:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
16. **Namespace label mismatch:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
17. **Container restart not alerted:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
18. **CrashLoopBackOff unnoticed:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
19. **Pod log pipeline stalled:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
20. **Trace context missing:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
21. **NetworkPolicy blocks scrape:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
22. **RBAC overprivileged:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
23. **Alert storm after rollout:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.
24. **Rollback fails:** inspect Kubernetes objects, scrape/collection paths, cloud provider metrics and independent SLIs.

## 11. Eight production runbooks

1. Targets down: inspect ServiceMonitor selectors, endpoints, RBAC, TLS and network policies.
2. Node blind spot: inspect node-exporter, kubelet/cAdvisor access, DaemonSet scheduling and CNI.
3. Control plane gap: distinguish EKS/AKS/GKE managed-plane exposure and provider metrics.
4. Collector pressure: inspect memory, batching, queues, retries and exporter drops.
5. Logging gap: inspect node log agents, Loki labels, retention and redaction.
6. Missing traces: inspect SDK propagation, OTLP collector, sampling and query backend.
7. Alert storm: check rollout labels, cardinality, grouping, silences and independent SLIs.
8. Recovery: restore pinned dashboards/scrapes/collectors and validate baseline evidence.

## 12. SRE/DBRE incident simulation

A stateful PostgreSQL workload on EKS shows slow API queries and pod restarts. Node metrics show CPU pressure, but kube-state-metrics is missing and application traces are incomplete. Reconstruct impact from independent RED metrics, verify node saturation, pod OOM/restart events, EBS I/O, Collector queues and trace propagation. Compare how the same signals would be collected on AKS and GKE.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| Multi-cloud architecture | 20 |
| Metrics, logs and traces | 20 |
| Security, cost and cardinality | 20 |
| Offline gate and evidence | 20 |
| Incident investigation and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Production acceptance requires observed cluster telemetry, access checks, incident drills and rollback.

**Companion:** [Chapter 056 hands-on lab](labs/056-kubernetes-observability-architecture-eks-aks-gke-lab.md).

**Next:** Chapter 057 — Kubernetes Cluster and Node Metrics, kube-state-metrics, cAdvisor and Exporters.
