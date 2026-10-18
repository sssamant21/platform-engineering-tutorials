# Chapter 059 — Kubernetes Control Plane, Networking, Storage and Autoscaling Observability

**Part 12 — Kubernetes, EKS, AKS and GKE Observability**  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers.  
**Prerequisites:** Chapters 056–058, Prometheus, Grafana, Kubernetes networking and storage.

## Objectives

Monitor Kubernetes control-plane health, DNS/CNI/ingress, CSI and persistent storage, HPA/VPA and node autoscaling across EKS, AKS and GKE. Identify managed-service visibility boundaries and correlate platform failures with application and database SLOs.

## Architecture

```text
 EKS / AKS / GKE control plane
    API server -> scheduler -> controllers
        |               |
     cloud-native telemetry + permitted metrics
        |
 nodes -> CoreDNS / CNI -> Service / Ingress / Load Balancer
        |
 CSI controller -> PV/PVC -> cloud block/file storage
        |
 HPA / VPA / cluster autoscaler / node provisioning
        |
 Prometheus / cloud metrics -> Grafana -> Alertmanager
        |
 application RED SLIs + PostgreSQL / Redis / Kafka health
```

Managed control planes may not expose direct scheduler, controller-manager or etcd scrape endpoints. Cloud-native monitoring is the supported fallback where necessary; never bypass provider controls.

## Control-plane monitoring

Track API server request rates, error classes, latency percentiles, inflight requests and throttling. For scheduler/controller-manager, use exposed metrics and events where available. Watch Pending pods, failed scheduling reasons, reconciliation errors, admission failures and node conditions.

Example PromQL (verify actual metric availability and labels):

```promql
sum(rate(apiserver_request_total{code=~"5.."}[5m]))
```

```promql
histogram_quantile(0.95, sum by (le) (rate(apiserver_request_duration_seconds_bucket[5m])))
```

The API server histogram metric and labels depend on Kubernetes release; managed offerings may provide aggregated equivalents.

## Networking: DNS, CNI, ingress

Inspect CoreDNS request volume, SERVFAIL and latency; CNI IP allocation, routing and packet drops; Service endpoint readiness; ingress controller errors and load balancer health. A DNS failure can resemble database connection timeouts; correlate app logs and DNS metrics before blaming PostgreSQL.

```bash
kubectl get pods -n kube-system
kubectl get svc,endpointslices -A
kubectl get networkpolicies -A
kubectl get ingress -A
kubectl get events -A --sort-by=.lastTimestamp
```

Use least-privilege, read-only staging contexts. EndpointSlice API availability and permissions vary.

## Storage: CSI and DBRE diagnosis

Review PVC/PV status, volume attach/mount events, filesystem usage and cloud disk latency/IOPS/throughput. For EKS inspect EBS/EFS and CSI metrics, for AKS Azure Disk/Files, and for GKE Persistent Disk/Filestore. Storage pressure may increase PostgreSQL checkpoint latency, Elasticsearch merge latency and Kafka log flush time. Do not equate high application query time with a database CPU bottleneck without storage evidence.

```bash
kubectl get storageclasses
kubectl get pvc,pv -A
kubectl get csidrivers
kubectl describe pvc -n staging PVC_NAME
```

PVC names and namespaces must be resolved before execution.

## Autoscaling: HPA, VPA and node capacity

HPA relies on resource/custom/external metrics and can fail when metrics are unavailable. VPA recommendation and eviction behavior depends on configuration; node autoscaling depends on cloud quotas, subnet IPs, instance capacity and scheduling constraints. Watch pending pod age, scale-up latency, unschedulable reasons and replica oscillation.

```bash
kubectl get hpa -A
kubectl describe hpa -n staging HPA_NAME
kubectl get nodes
kubectl get pods -A --field-selector=status.phase=Pending
```

Karpenter applies where deployed (commonly EKS); do not assume the same autoscaler across AKS/GKE.

## SRE/DBRE incident simulation

A stateful MongoDB workload has high write latency and Pending pods. DNS errors rise, CSI attachment is slow and autoscaler cannot provision nodes due to subnet exhaustion. Separate user impact, DNS failures, volume latency and scheduling bottlenecks; compare cloud-specific diagnostics across EKS, AKS and GKE. Recover only through approved changes with rollback evidence.

## Executable offline architecture gate

The synthetic manifest validates declared reviews and thresholds; it does **not** query a real Kubernetes cluster or cloud provider.

### healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "cloud": "eks",
  "cluster": "staging-cluster",
  "api_server_p95_ms": 220,
  "max_api_server_p95_ms": 500,
  "dns_success_percent": 99,
  "minimum_dns_success_percent": 98,
  "pv_capacity_used_percent": 70,
  "max_pv_capacity_used_percent": 85,
  "production_delete": false,
  "api_server_reviewed": true,
  "scheduler_reviewed": true,
  "controller_manager_reviewed": true,
  "cloud_control_plane_reviewed": true,
  "cni_reviewed": true,
  "dns_reviewed": true,
  "ingress_reviewed": true,
  "service_mesh_reviewed": true,
  "csi_reviewed": true,
  "persistent_volume_reviewed": true,
  "hpa_reviewed": true,
  "vpa_reviewed": true,
  "cluster_autoscaler_reviewed": true,
  "rbac_reviewed": true,
  "cloud_identity_reviewed": true,
  "alert_routing_reviewed": true,
  "rollback_tested": true
}
```

### platform_signals_gate.py

```python
"""Synthetic Kubernetes control-plane/network/storage/autoscaling review."""
import json,sys
from pathlib import Path
FLAGS=["api_server_reviewed","scheduler_reviewed","controller_manager_reviewed","cloud_control_plane_reviewed","cni_reviewed","dns_reviewed","ingress_reviewed","service_mesh_reviewed","csi_reviewed","persistent_volume_reviewed","hpa_reviewed","vpa_reviewed","cluster_autoscaler_reviewed","rbac_reviewed","cloud_identity_reviewed","alert_routing_reviewed","rollback_tested"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","cluster"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("cloud") not in ("eks","aks","gke"):e.append("invalid cloud")
 for k in FLAGS:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("api_server_p95_ms","max_api_server_p95_ms"):
  if type(p.get(k)) is not int or p[k]<=0:e.append("invalid "+k)
 for k in ("dns_success_percent","minimum_dns_success_percent","pv_capacity_used_percent","max_pv_capacity_used_percent"):
  if type(p.get(k)) is not int or not 0<=p[k]<=100:e.append("invalid "+k)
 for a,b,rule in (("api_server_p95_ms","max_api_server_p95_ms","max"),("dns_success_percent","minimum_dns_success_percent","min"),("pv_capacity_used_percent","max_pv_capacity_used_percent","max")):
  x,y=p.get(a),p.get(b)
  if type(x) is int and type(y) is int and ((rule=="max" and x>y) or (rule=="min" and x<y)):e.append("threshold missed "+a)
 if p.get("production_delete") is not False:e.append("unsafe production action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_platform_signals_gate.py

```python
import copy,json,unittest
from pathlib import Path
from platform_signals_gate import validate
class PlatformSignalsTests(unittest.TestCase):
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
 def test_05_api_server_reviewed(self):
  p=copy.deepcopy(self.p);p["api_server_reviewed"]=False;self.assertTrue(validate(p))
 def test_06_scheduler_reviewed(self):
  p=copy.deepcopy(self.p);p["scheduler_reviewed"]=False;self.assertTrue(validate(p))
 def test_07_controller_manager_reviewed(self):
  p=copy.deepcopy(self.p);p["controller_manager_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_cloud_control_plane_reviewed(self):
  p=copy.deepcopy(self.p);p["cloud_control_plane_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_cni_reviewed(self):
  p=copy.deepcopy(self.p);p["cni_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_dns_reviewed(self):
  p=copy.deepcopy(self.p);p["dns_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_ingress_reviewed(self):
  p=copy.deepcopy(self.p);p["ingress_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_service_mesh_reviewed(self):
  p=copy.deepcopy(self.p);p["service_mesh_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_csi_reviewed(self):
  p=copy.deepcopy(self.p);p["csi_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_persistent_volume_reviewed(self):
  p=copy.deepcopy(self.p);p["persistent_volume_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_hpa_reviewed(self):
  p=copy.deepcopy(self.p);p["hpa_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_vpa_reviewed(self):
  p=copy.deepcopy(self.p);p["vpa_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_cluster_autoscaler_reviewed(self):
  p=copy.deepcopy(self.p);p["cluster_autoscaler_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_rbac_reviewed(self):
  p=copy.deepcopy(self.p);p["rbac_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_cloud_identity_reviewed(self):
  p=copy.deepcopy(self.p);p["cloud_identity_reviewed"]=False;self.assertTrue(validate(p))
 def test_20_alert_routing_reviewed(self):
  p=copy.deepcopy(self.p);p["alert_routing_reviewed"]=False;self.assertTrue(validate(p))
 def test_21_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_22_api_server_p95_ms(self):
  p=copy.deepcopy(self.p);p["api_server_p95_ms"]=900;self.assertTrue(validate(p))
 def test_23_max_api_server_p95_ms(self):
  p=copy.deepcopy(self.p);p["max_api_server_p95_ms"]=0;self.assertTrue(validate(p))
 def test_24_dns_success_percent(self):
  p=copy.deepcopy(self.p);p["dns_success_percent"]=50;self.assertTrue(validate(p))
 def test_25_minimum_dns_success_percent(self):
  p=copy.deepcopy(self.p);p["minimum_dns_success_percent"]=101;self.assertTrue(validate(p))
 def test_26_pv_capacity_used_percent(self):
  p=copy.deepcopy(self.p);p["pv_capacity_used_percent"]=99;self.assertTrue(validate(p))
 def test_27_max_pv_capacity_used_percent(self):
  p=copy.deepcopy(self.p);p["max_pv_capacity_used_percent"]=0;self.assertTrue(validate(p))
 def test_28_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter059 && cd chapter059
# Save blocks as healthy.json, platform_signals_gate.py, test_platform_signals_gate.py
python3 platform_signals_gate.py healthy.json
python3 -m unittest -v test_platform_signals_gate.py
```

Expected PASS and **30 authored Python tests**.

## 24 hands-on exercises

1. Inventory control-plane signals.
2. Inspect API request latency.
3. Inspect API error rate.
4. Review scheduler queue.
5. Review controller reconcile failures.
6. Review managed provider visibility.
7. Inspect CoreDNS health.
8. Test DNS resolution.
9. Review CNI errors.
10. Review service routing.
11. Inspect ingress controller.
12. Inspect load balancer metrics.
13. Review service mesh telemetry.
14. Inspect CSI controller.
15. Inspect PV and PVC conditions.
16. Review cloud disk IOPS/latency.
17. Review storage capacity.
18. Inspect HPA conditions.
19. Inspect VPA recommendations.
20. Inspect cluster autoscaler.
21. Inspect Karpenter or node autoscaling.
22. Correlate node provisioning delays.
23. Simulate DNS failure.
24. Validate rollback.

## 24 production failure scenarios

1. **API server latency spike:** inspect platform signals, cloud provider telemetry and independent SLIs.
2. **API server 429 throttling:** inspect platform signals, cloud provider telemetry and independent SLIs.
3. **Scheduler pending pods:** inspect platform signals, cloud provider telemetry and independent SLIs.
4. **Controller reconcile errors:** inspect platform signals, cloud provider telemetry and independent SLIs.
5. **Managed-plane metrics unavailable:** inspect platform signals, cloud provider telemetry and independent SLIs.
6. **CoreDNS CrashLoopBackOff:** inspect platform signals, cloud provider telemetry and independent SLIs.
7. **DNS NXDOMAIN increase:** inspect platform signals, cloud provider telemetry and independent SLIs.
8. **CNI IP exhaustion:** inspect platform signals, cloud provider telemetry and independent SLIs.
9. **NetworkPolicy drops traffic:** inspect platform signals, cloud provider telemetry and independent SLIs.
10. **Service endpoints missing:** inspect platform signals, cloud provider telemetry and independent SLIs.
11. **Ingress 5xx:** inspect platform signals, cloud provider telemetry and independent SLIs.
12. **Load balancer unhealthy targets:** inspect platform signals, cloud provider telemetry and independent SLIs.
13. **Service mesh sidecar missing:** inspect platform signals, cloud provider telemetry and independent SLIs.
14. **CSI attach timeout:** inspect platform signals, cloud provider telemetry and independent SLIs.
15. **PV Pending:** inspect platform signals, cloud provider telemetry and independent SLIs.
16. **Disk IOPS throttling:** inspect platform signals, cloud provider telemetry and independent SLIs.
17. **Filesystem space exhaustion:** inspect platform signals, cloud provider telemetry and independent SLIs.
18. **HPA unable to get metrics:** inspect platform signals, cloud provider telemetry and independent SLIs.
19. **HPA oscillation:** inspect platform signals, cloud provider telemetry and independent SLIs.
20. **VPA eviction pressure:** inspect platform signals, cloud provider telemetry and independent SLIs.
21. **Cluster autoscaler scale-up blocked:** inspect platform signals, cloud provider telemetry and independent SLIs.
22. **Karpenter provisioning stalled:** inspect platform signals, cloud provider telemetry and independent SLIs.
23. **RBAC denies metrics:** inspect platform signals, cloud provider telemetry and independent SLIs.
24. **Rollback fails:** inspect platform signals, cloud provider telemetry and independent SLIs.

## Eight production runbooks

1. **API degradation:** inspect API p95/errors, request throttling, audit logs and cloud provider signals.
2. **DNS outage:** inspect CoreDNS pods, upstream resolution, NetworkPolicy and query success.
3. **CNI/IP pressure:** inspect node pod IP allocation, CNI logs and cloud subnet capacity.
4. **Ingress outage:** inspect endpoints, controller logs, load balancer target health and TLS.
5. **PV latency:** inspect CSI events, filesystem saturation, cloud disk IOPS/throughput and application latency.
6. **HPA issue:** inspect resource/custom metrics, desired replicas, stabilization and requests.
7. **Node scaling delay:** inspect autoscaler/Karpenter decisions, quotas, capacity and taints.
8. **Recovery:** restore reviewed config, verify traffic/SLIs, audit changes and document rollback.

## 100-point assessment

| Domain | Points |
|---|---:|
| Control-plane metrics and access | 20 |
| Networking and DNS | 20 |
| CSI/storage and DBRE analysis | 20 |
| Autoscaling, offline tests and evidence | 20 |
| Incident recovery and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires witnessed platform telemetry, incident drills, cloud provider permissions and recovery.

**Companion:** [Chapter 059 hands-on lab](labs/059-kubernetes-control-plane-networking-storage-autoscaling-observability-lab.md).

**Next:** Chapter 060 — Kubernetes Multi-Cloud Observability, Reliability, Incident Response and Disaster Recovery Capstone.
