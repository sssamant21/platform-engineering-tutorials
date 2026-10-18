# Chapter 057 — Kubernetes Cluster and Node Metrics, kube-state-metrics, cAdvisor and Exporters

**Part 12 — Kubernetes, EKS, AKS and GKE Observability**  
**Audience:** Kubernetes administrators, SRE, DBRE and platform teams.  
**Prerequisites:** Chapter 056, Prometheus, kubectl and Grafana.

## Learning objectives

Collect and interpret node, container and Kubernetes object-state metrics. Design reliable Prometheus discovery, dashboards, alerts and recording rules for EKS, AKS and GKE. Troubleshoot kubelet access, scrape gaps, cardinality and noisy signals.

## Architecture and component ownership

```text
Kubernetes API -> kube-state-metrics -> Prometheus
Worker nodes -> node-exporter ---------^
kubelet/cAdvisor -> container metrics --^
Prometheus -> recording/alert rules -> Alertmanager
           -> Grafana dashboards
metrics-server -> kubectl top / HPA (not a long-term metrics store)
```

**kube-state-metrics** reports Kubernetes object state (replicas, conditions, requests and limits). **node-exporter** reports host OS CPU, memory, disk and network. **kubelet/cAdvisor** reports container resource usage. **metrics-server** serves the Kubernetes resource metrics API for autoscaling and `kubectl top`; it is not a Prometheus replacement.

Managed clusters may restrict control-plane/kubelet endpoints and expose alternative cloud metrics. Do not assume all cAdvisor metrics are present in every Kubernetes release.

## Read-only staging discovery

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get daemonsets -A
kubectl get deployments -A
kubectl get pods -A --field-selector=status.phase!=Running
kubectl top nodes
kubectl top pods -A
kubectl get servicemonitors,podmonitors -A  # Prometheus Operator CRDs only
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes  # if metrics-server installed
```

Use an approved staging context; no production mutations. For `kubectl top`, distinguish instantaneous resource API observations from historical Prometheus time series.

## PromQL troubleshooting examples

```promql
up{job=~".*node-exporter.*"}
```

```promql
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))
```

```promql
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
```

```promql
sum by (namespace,pod) (increase(kube_pod_container_status_restarts_total[15m]))
```

```promql
sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m]))
/
clamp_min(sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{container!=""}[5m])), 1e-9)
```

```promql
kube_deployment_status_replicas_available
/
clamp_min(kube_deployment_spec_replicas, 1)
```

Metric names and label sets must be checked against the deployed exporter version. The replica ratio should not be interpreted as an SLO when desired replicas are zero.

## Operational dashboards and alerting

Create node utilization/saturation, filesystem space/inodes, pod restarts, replica availability, CPU throttling, HPA status, scrape health and exporter errors dashboards. Use stable cluster, namespace and workload labels. Never label metrics by pod UID, trace ID, SQL query, patient identifier or request ID unless there is a justified bounded use. Group alerts by cluster and owner; pair alerts with runbooks and independent user-impact SLIs.

## Production SRE/DBRE simulation

PostgreSQL pods on EKS are restarting, application p95 latency rises and HPA signals are stale. Node-exporter is healthy, but kube-state-metrics has lost RBAC and kubelet scrapes time out. Determine what is known from independent app RED metrics, node CPU/memory, pod events, EBS disk latency and cloud provider telemetry. Restore scrape visibility before drawing conclusions about DB bottlenecks.

## Executable offline validation

The following synthetic design attestation checks thresholds and declared reviews. It does **not** query a Kubernetes cluster.

### healthy.json

```json
{
  "owner": "k8s-observability",
  "environment": "staging",
  "cloud": "eks",
  "cluster": "staging-cluster",
  "scrape_targets": 50,
  "healthy_targets": 49,
  "scrape_success_percent": 98,
  "minimum_scrape_success_percent": 95,
  "cpu_throttling_percent": 8,
  "max_cpu_throttling_percent": 20,
  "production_delete": false,
  "node_exporter_reviewed": true,
  "kube_state_metrics_reviewed": true,
  "kubelet_cadvisor_reviewed": true,
  "metrics_server_scope_reviewed": true,
  "prometheus_targets_verified": true,
  "service_monitor_reviewed": true,
  "rbac_reviewed": true,
  "tls_reviewed": true,
  "network_policy_reviewed": true,
  "cardinality_reviewed": true,
  "recording_rules_reviewed": true,
  "alerts_reviewed": true,
  "dashboards_reviewed": true,
  "capacity_reviewed": true,
  "rollback_tested": true
}
```

### metrics_gate.py

```python
"""Synthetic Kubernetes metrics acceptance gate. Does not access clusters."""
import json,sys
from pathlib import Path
FLAGS=["node_exporter_reviewed","kube_state_metrics_reviewed","kubelet_cadvisor_reviewed","metrics_server_scope_reviewed","prometheus_targets_verified","service_monitor_reviewed","rbac_reviewed","tls_reviewed","network_policy_reviewed","cardinality_reviewed","recording_rules_reviewed","alerts_reviewed","dashboards_reviewed","capacity_reviewed","rollback_tested"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be an object"]
 for k in ("owner","environment","cluster"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("cloud") not in ("eks","aks","gke"):e.append("invalid cloud")
 for k in FLAGS:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("scrape_targets","healthy_targets"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 if type(p.get("scrape_targets")) is int and p["scrape_targets"]<=0:e.append("no scrape targets")
 if all(type(p.get(k)) is int for k in ("scrape_targets","healthy_targets")) and p["healthy_targets"]>p["scrape_targets"]:e.append("healthy targets exceed total")
 for k in ("scrape_success_percent","minimum_scrape_success_percent","cpu_throttling_percent","max_cpu_throttling_percent"):
  if type(p.get(k)) is not int or not 0<=p[k]<=100:e.append("invalid "+k)
 for a,b,kind in (("scrape_success_percent","minimum_scrape_success_percent","min"),("cpu_throttling_percent","max_cpu_throttling_percent","max")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((kind=="min" and x<y) or (kind=="max" and x>y)):e.append("threshold breached "+a)
 if p.get("production_delete") is not False:e.append("unsafe deletion")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_metrics_gate.py

```python
import unittest,json,copy
from pathlib import Path
from metrics_gate import validate
class MetricsGateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_valid(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_cloud(self):
  p=copy.deepcopy(self.p);p["cloud"]="other";self.assertTrue(validate(p))
 def test_04_cluster(self):
  p=copy.deepcopy(self.p);p["cluster"]="";self.assertTrue(validate(p))
 def test_05_node_exporter_reviewed(self):
  p=copy.deepcopy(self.p);p["node_exporter_reviewed"]=False;self.assertTrue(validate(p))
 def test_06_kube_state_metrics_reviewed(self):
  p=copy.deepcopy(self.p);p["kube_state_metrics_reviewed"]=False;self.assertTrue(validate(p))
 def test_07_kubelet_cadvisor_reviewed(self):
  p=copy.deepcopy(self.p);p["kubelet_cadvisor_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_metrics_server_scope_reviewed(self):
  p=copy.deepcopy(self.p);p["metrics_server_scope_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_prometheus_targets_verified(self):
  p=copy.deepcopy(self.p);p["prometheus_targets_verified"]=False;self.assertTrue(validate(p))
 def test_10_service_monitor_reviewed(self):
  p=copy.deepcopy(self.p);p["service_monitor_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_rbac_reviewed(self):
  p=copy.deepcopy(self.p);p["rbac_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_tls_reviewed(self):
  p=copy.deepcopy(self.p);p["tls_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_network_policy_reviewed(self):
  p=copy.deepcopy(self.p);p["network_policy_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_cardinality_reviewed(self):
  p=copy.deepcopy(self.p);p["cardinality_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_recording_rules_reviewed(self):
  p=copy.deepcopy(self.p);p["recording_rules_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_alerts_reviewed(self):
  p=copy.deepcopy(self.p);p["alerts_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_dashboards_reviewed(self):
  p=copy.deepcopy(self.p);p["dashboards_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_capacity_reviewed(self):
  p=copy.deepcopy(self.p);p["capacity_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_20_scrape_targets(self):
  p=copy.deepcopy(self.p);p["scrape_targets"]=0;self.assertTrue(validate(p))
 def test_21_healthy_targets(self):
  p=copy.deepcopy(self.p);p["healthy_targets"]=100;self.assertTrue(validate(p))
 def test_22_scrape_success_percent(self):
  p=copy.deepcopy(self.p);p["scrape_success_percent"]=50;self.assertTrue(validate(p))
 def test_23_minimum_scrape_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_scrape_success_percent"]=101;self.assertTrue(validate(p))
 def test_24_cpu_throttling_percent(self):
  p=copy.deepcopy(self.p);p["cpu_throttling_percent"]=30;self.assertTrue(validate(p))
 def test_25_max_cpu_throttling_percent(self):
  p=copy.deepcopy(self.p);p["max_cpu_throttling_percent"]=0;self.assertTrue(validate(p))
 def test_26_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter057 && cd chapter057
# Save the three blocks as healthy.json, metrics_gate.py and test_metrics_gate.py
python3 metrics_gate.py healthy.json
python3 -m unittest -v test_metrics_gate.py
```

Expected PASS and **28 authored tests**.

## 24 hands-on exercises

1. Inventory cluster/node metric endpoints.
2. Identify kube-state-metrics resource objects.
3. Compare node-exporter vs kubelet/cAdvisor.
4. Inspect metrics-server role.
5. Inspect DaemonSet placement.
6. Inspect kube-state-metrics Deployment.
7. Review scrape service discovery.
8. Review ServiceMonitor selectors.
9. Review PodMonitor selectors.
10. Check RBAC.
11. Check TLS trust.
12. Check network policies.
13. Query up and scrape_duration_seconds.
14. Query node CPU utilization.
15. Query node memory pressure.
16. Query node filesystem availability.
17. Query container CPU throttling.
18. Query pod restarts.
19. Query desired vs available replicas.
20. Review HPA desired/current replicas.
21. Design recording rules.
22. Design multiwindow alerts.
23. Simulate exporter outage.
24. Validate recovery and rollback.

## 24 production failure scenarios

1. **node-exporter missing:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
2. **DaemonSet unschedulable:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
3. **kube-state-metrics unavailable:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
4. **kubelet authorization denied:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
5. **cAdvisor metrics renamed:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
6. **ServiceMonitor CRD absent:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
7. **ServiceMonitor selector mismatch:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
8. **PodMonitor namespace mismatch:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
9. **Scrape timeout:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
10. **TLS trust failure:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
11. **RBAC forbidden:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
12. **NetworkPolicy blocks scrape:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
13. **Scrape target duplicate:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
14. **Node labels high cardinality:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
15. **Container metrics absent:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
16. **CPU throttling elevated:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
17. **OOM kills rising:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
18. **Disk pressure hidden:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
19. **Ephemeral container missing:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
20. **Metrics-server down:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
21. **HPA metrics stale:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
22. **Recording rule error:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
23. **Alert storm:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.
24. **Rollback incomplete:** verify exporter, scrape, RBAC, metric semantics and independent SLIs.

## Eight runbooks

1. **Exporter down: inspect DaemonSet, pod logs, Service and target health.**
2. **KSM missing: inspect deployment, RBAC, API discovery and metrics endpoints.**
3. **Kubelet denied: validate authorized credentials, TLS and managed-cluster restrictions.**
4. **CPU pressure: compare node utilization, throttling, quotas and application latency.**
5. **Memory pressure: inspect working set, OOM events, limits and node conditions.**
6. **Storage pressure: inspect filesystem availability, inodes and cloud volume metrics.**
7. **Cardinality incident: identify explosive labels and apply reviewed relabeling.**
8. **Recovery: restore pinned scrape rules and verify up, dashboards and alert routing.**

## 100-point assessment

| Area | Points |
|---|---:|
| Component architecture and metric semantics | 20 |
| PromQL and dashboards | 20 |
| Discovery, security and cardinality | 20 |
| Offline tests and operational evidence | 20 |
| Incident investigation and rollback | 20 |
| **Total** | **100** |

Recommended passing score: 85/100. Production readiness requires real scrape, RBAC, alert and recovery validation.

**Companion:** [Chapter 057 hands-on lab](labs/057-kubernetes-cluster-node-metrics-kube-state-metrics-cadvisor-exporters-lab.md).

**Next:** Chapter 058 — Kubernetes Workload, Pod, Application Logs and Distributed Tracing Observability.
