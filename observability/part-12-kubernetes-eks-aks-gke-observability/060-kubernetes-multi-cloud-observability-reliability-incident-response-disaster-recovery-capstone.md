# Chapter 060 — Kubernetes Multi-Cloud Observability, Reliability, Incident Response and Disaster Recovery Capstone

**Part 12 — Kubernetes, EKS, AKS and GKE Observability: FINAL CAPSTONE**  
**Audience:** SRE, DBRE, Kubernetes administrators, incident commanders and platform teams.  
**Prerequisites:** Chapters 056–059, Prometheus, Grafana, Loki, OpenTelemetry and cloud monitoring.

## Mission

Demonstrate observability and operational recovery across EKS, AKS and GKE. Validate node/workload/control-plane telemetry, logs, traces, storage, networking and autoscaling; rehearse realistic outages, preserve evidence, restore safely and measure recovery objectives.

## Reference architecture

```text
EKS / AKS / GKE -> cloud control-plane monitoring
       |           |
       +-> node-exporter / kube-state-metrics / kubelet
       +-> CoreDNS / CNI / ingress / CSI / HPA / autoscaler
       +-> application RED metrics -> Prometheus -> Grafana/Alertmanager
       +-> pod logs -> OTel/log agent -> Loki
       +-> OTLP traces -> Collector -> Tempo/Jaeger
       +-> GitOps / backups / approved recovery workflows
```

Managed control-plane access varies by cloud and cluster mode. Do not equate telemetry availability with independent workload reliability; sampling, collection delays and exporter outages can create false confidence.

## Acceptance matrix

| Domain | Staging evidence |
|---|---|
| EKS, AKS, GKE | supported cloud metrics and identity paths documented |
| Node/workload | scrape health, restarts, CPU throttling, RED |
| Control plane | API latency, errors and provider coverage |
| Networking | DNS, CNI, ingress and load balancer health |
| Storage | CSI/PVC, disk latency and throughput |
| Autoscaling | HPA signals, pending pods and scale latency |
| Logs/traces | synthetic known IDs retrievable |
| Security | RBAC, tenant boundaries, redaction |
| Recovery | backups, restore, RPO/RTO and rollback |
| Reliability | independent user-facing SLI and error budget |

## Production incident simulation

A multi-region platform serves an API backed by PostgreSQL and Redis. During a deployment, CoreDNS experiences SERVFAIL, CSI attachment latency increases and node autoscaling is blocked by subnet capacity. Prometheus loses targets and the OTel Collector drops traces. Establish impact from independent API SLIs, inspect managed control-plane telemetry, recover DNS and storage, restore telemetry, validate backup integrity and conduct an approved failover rehearsal. Record decision authority, blast radius, RPO/RTO, rollback criteria and communications.

## Read-only discovery

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl get hpa -A
kubectl get pvc -A
kubectl get daemonsets -A
kubectl get networkpolicies -A
```

Run only in approved contexts. Do not trigger production failover, deletion or chaos without explicit change authorization.

## Executable offline capstone gate

This synthetic attestation checks declared reviews and numeric RPO/RTO/coverage thresholds. It does **not** verify a cloud deployment, execute disaster recovery or query live telemetry.

### healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "change_id": "OBS-060",
  "rpo_minutes": 10,
  "max_rpo_minutes": 15,
  "rto_minutes": 25,
  "max_rto_minutes": 30,
  "observability_coverage_percent": 99,
  "minimum_observability_coverage_percent": 95,
  "production_delete": false,
  "eks_visibility_reviewed": true,
  "aks_visibility_reviewed": true,
  "gke_visibility_reviewed": true,
  "node_metrics_reviewed": true,
  "workload_metrics_reviewed": true,
  "control_plane_reviewed": true,
  "network_dns_reviewed": true,
  "storage_csi_reviewed": true,
  "autoscaling_reviewed": true,
  "logs_reviewed": true,
  "traces_reviewed": true,
  "independent_slo_reviewed": true,
  "tenant_isolation_reviewed": true,
  "pii_redaction_reviewed": true,
  "backup_restore_tested": true,
  "failover_tested": true,
  "rollback_tested": true,
  "incident_drill_completed": true
}
```

### multicloud_capstone_gate.py

```python
"""Offline multi-cloud Kubernetes observability capstone attestation."""
import json,sys
from pathlib import Path
FLAGS=["eks_visibility_reviewed","aks_visibility_reviewed","gke_visibility_reviewed","node_metrics_reviewed","workload_metrics_reviewed","control_plane_reviewed","network_dns_reviewed","storage_csi_reviewed","autoscaling_reviewed","logs_reviewed","traces_reviewed","independent_slo_reviewed","tenant_isolation_reviewed","pii_redaction_reviewed","backup_restore_tested","failover_tested","rollback_tested","incident_drill_completed"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 for k in FLAGS:
  if p.get(k) is not True:e.append("unverified "+k)
 for k in ("rpo_minutes","max_rpo_minutes","rto_minutes","max_rto_minutes"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 for k in ("observability_coverage_percent","minimum_observability_coverage_percent"):
  if type(p.get(k)) is not int or not 0<=p[k]<=100:e.append("invalid "+k)
 for a,b,rule in (("rpo_minutes","max_rpo_minutes","max"),("rto_minutes","max_rto_minutes","max"),("observability_coverage_percent","minimum_observability_coverage_percent","min")):
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

### test_multicloud_capstone_gate.py

```python
import copy,json,unittest
from pathlib import Path
from multicloud_capstone_gate import validate
class MultiCloudCapstoneTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_change_id(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_04_eks_visibility_reviewed(self):
  p=copy.deepcopy(self.p);p["eks_visibility_reviewed"]=False;self.assertTrue(validate(p))
 def test_05_aks_visibility_reviewed(self):
  p=copy.deepcopy(self.p);p["aks_visibility_reviewed"]=False;self.assertTrue(validate(p))
 def test_06_gke_visibility_reviewed(self):
  p=copy.deepcopy(self.p);p["gke_visibility_reviewed"]=False;self.assertTrue(validate(p))
 def test_07_node_metrics_reviewed(self):
  p=copy.deepcopy(self.p);p["node_metrics_reviewed"]=False;self.assertTrue(validate(p))
 def test_08_workload_metrics_reviewed(self):
  p=copy.deepcopy(self.p);p["workload_metrics_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_control_plane_reviewed(self):
  p=copy.deepcopy(self.p);p["control_plane_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_network_dns_reviewed(self):
  p=copy.deepcopy(self.p);p["network_dns_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_storage_csi_reviewed(self):
  p=copy.deepcopy(self.p);p["storage_csi_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_autoscaling_reviewed(self):
  p=copy.deepcopy(self.p);p["autoscaling_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_logs_reviewed(self):
  p=copy.deepcopy(self.p);p["logs_reviewed"]=False;self.assertTrue(validate(p))
 def test_14_traces_reviewed(self):
  p=copy.deepcopy(self.p);p["traces_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_independent_slo_reviewed(self):
  p=copy.deepcopy(self.p);p["independent_slo_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_tenant_isolation_reviewed(self):
  p=copy.deepcopy(self.p);p["tenant_isolation_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_pii_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_backup_restore_tested(self):
  p=copy.deepcopy(self.p);p["backup_restore_tested"]=False;self.assertTrue(validate(p))
 def test_19_failover_tested(self):
  p=copy.deepcopy(self.p);p["failover_tested"]=False;self.assertTrue(validate(p))
 def test_20_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_21_incident_drill_completed(self):
  p=copy.deepcopy(self.p);p["incident_drill_completed"]=False;self.assertTrue(validate(p))
 def test_22_rpo_minutes(self):
  p=copy.deepcopy(self.p);p["rpo_minutes"]=30;self.assertTrue(validate(p))
 def test_23_max_rpo_minutes(self):
  p=copy.deepcopy(self.p);p["max_rpo_minutes"]=0;self.assertTrue(validate(p))
 def test_24_rto_minutes(self):
  p=copy.deepcopy(self.p);p["rto_minutes"]=60;self.assertTrue(validate(p))
 def test_25_max_rto_minutes(self):
  p=copy.deepcopy(self.p);p["max_rto_minutes"]=0;self.assertTrue(validate(p))
 def test_26_observability_coverage_percent(self):
  p=copy.deepcopy(self.p);p["observability_coverage_percent"]=50;self.assertTrue(validate(p))
 def test_27_minimum_observability_coverage_percent(self):
  p=copy.deepcopy(self.p);p["minimum_observability_coverage_percent"]=101;self.assertTrue(validate(p))
 def test_28_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter060 && cd chapter060
# Save blocks as healthy.json, multicloud_capstone_gate.py and test_multicloud_capstone_gate.py
python3 multicloud_capstone_gate.py healthy.json
python3 -m unittest -v test_multicloud_capstone_gate.py
```

Expected PASS and **30 authored Python tests**.

## 24 hands-on exercises

1. Inventory EKS observability.
2. Inventory AKS observability.
3. Inventory GKE observability.
4. Verify node metrics.
5. Verify workload RED metrics.
6. Verify control-plane metrics.
7. Verify CoreDNS.
8. Verify CNI telemetry.
9. Verify ingress signals.
10. Verify CSI storage metrics.
11. Verify autoscaler events.
12. Verify Loki logs.
13. Verify Tempo traces.
14. Verify independent SLO.
15. Review RBAC and identity.
16. Review tenant isolation.
17. Review PII redaction.
18. Simulate exporter outage.
19. Simulate DNS outage.
20. Simulate CSI latency.
21. Simulate autoscaler stall.
22. Execute restore drill.
23. Measure RPO/RTO.
24. Execute rollback.

## 24 production failure scenarios

1. **EKS API latency:** identify independent user impact, platform evidence, owner, mitigation and rollback.
2. **AKS control-plane blind spot:** identify independent user impact, platform evidence, owner, mitigation and rollback.
3. **GKE permissions denied:** identify independent user impact, platform evidence, owner, mitigation and rollback.
4. **Node-exporter unavailable:** identify independent user impact, platform evidence, owner, mitigation and rollback.
5. **kube-state-metrics absent:** identify independent user impact, platform evidence, owner, mitigation and rollback.
6. **Collector queue full:** identify independent user impact, platform evidence, owner, mitigation and rollback.
7. **Prometheus scrape outage:** identify independent user impact, platform evidence, owner, mitigation and rollback.
8. **Loki ingest stalled:** identify independent user impact, platform evidence, owner, mitigation and rollback.
9. **Tempo query unavailable:** identify independent user impact, platform evidence, owner, mitigation and rollback.
10. **DNS SERVFAIL storm:** identify independent user impact, platform evidence, owner, mitigation and rollback.
11. **CNI IP exhaustion:** identify independent user impact, platform evidence, owner, mitigation and rollback.
12. **Ingress 5xx:** identify independent user impact, platform evidence, owner, mitigation and rollback.
13. **NetworkPolicy blocks telemetry:** identify independent user impact, platform evidence, owner, mitigation and rollback.
14. **CSI attach failure:** identify independent user impact, platform evidence, owner, mitigation and rollback.
15. **Cloud disk IOPS saturation:** identify independent user impact, platform evidence, owner, mitigation and rollback.
16. **HPA metric unavailable:** identify independent user impact, platform evidence, owner, mitigation and rollback.
17. **Node autoscaler blocked:** identify independent user impact, platform evidence, owner, mitigation and rollback.
18. **DB workload OOM:** identify independent user impact, platform evidence, owner, mitigation and rollback.
19. **Tenant data exposure:** identify independent user impact, platform evidence, owner, mitigation and rollback.
20. **Sensitive span attribute:** identify independent user impact, platform evidence, owner, mitigation and rollback.
21. **Alert storm:** identify independent user impact, platform evidence, owner, mitigation and rollback.
22. **Restore fails:** identify independent user impact, platform evidence, owner, mitigation and rollback.
23. **RPO breach:** identify independent user impact, platform evidence, owner, mitigation and rollback.
24. **Rollback fails:** identify independent user impact, platform evidence, owner, mitigation and rollback.

## Eight production runbooks

1. **Control-plane incident:** compare managed provider metrics, API latency, auth and audit logs.
2. **Telemetry outage:** inspect scrapes, Collector queues, Loki/Tempo and independent SLOs.
3. **DNS/CNI incident:** inspect CoreDNS, IP allocation, NetworkPolicy and application errors.
4. **Storage incident:** inspect CSI, PVC events, disk IOPS and DBRE latency.
5. **Autoscaling incident:** inspect HPA metrics, Pending pods, quotas and provisioning.
6. **Security incident:** isolate tenants, restrict credentials, redact data and preserve evidence.
7. **DR restore:** recover pinned manifests/storage, verify known telemetry and measure RPO/RTO.
8. **Rollback:** revert approved changes, confirm SLIs, close incident and record postmortem.

## 100-point acceptance

| Domain | Points |
|---|---:|
| Multi-cloud architecture and signal coverage | 20 |
| Networking, storage and autoscaling | 20 |
| Logs, traces, SLOs and security | 20 |
| Offline gate, tests and evidence | 20 |
| Incident command, DR and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Production acceptance additionally requires witnessed cloud telemetry, DR drills, security checks and recovery verification.

## Evidence template

```text
UTC / incident commander / change ID:
EKS, AKS and GKE monitoring paths:
Known trace IDs / Loki query evidence:
Independent RED SLI and error budget:
Control-plane / DNS / CNI / CSI / HPA signals:
Backup / restore / failover:
Measured RPO / RTO:
Tenant security and redaction:
Rollback / incident timeline:
Offline gate / 30 tests / final score:
```

**Companion:** [Chapter 060 capstone lab](labs/060-kubernetes-multi-cloud-observability-reliability-incident-response-disaster-recovery-capstone-lab.md).

**Part 12 complete. Next:** Chapter 061 — Database and Data Platform Observability Architecture, Metrics and Reliability Signals (Part 13).
