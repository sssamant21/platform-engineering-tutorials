# Chapter 087 — GKE Standard vs Autopilot, Node Pools and Autoscaling

**Track:** Kubernetes Administration · **Part 18 — Google Kubernetes Engine**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes platform and Google Cloud FinOps engineers  
**Prerequisites:** Chapters 021–025 and 086; Windows PowerShell, Google Cloud CLI, gke-gcloud-auth-plugin, kubectl; approved staging project and GKE cluster

## 1. Production scenario

A GKE platform hosts stateless APIs, batch consumers and a stateful database. A traffic spike increases desired replicas, but Pods remain Pending despite apparent idle CPU. The Standard cluster autoscaler has reached its node pool maximum, one node pool has a restrictive taint, and a PodDisruptionBudget blocks an upgrade. Meanwhile, the team is considering Autopilot to reduce node-management overhead, without yet verifying privileged-agent and GPU requirements.

**Mission:** compare Standard and Autopilot operating models, inventory capacity, validate scheduling, understand workload and node autoscaling, and deliver safe upgrade, Spot and cost-management procedures.

**Safety:** node pool changes, workload stress, drains and upgrades may incur costs or disrupt services. Perform mutations only in approved staging clusters with a defined budget, quota and rollback procedure. Do not force-delete stateful Pods.

### Learning outcomes

1. Choose Standard or Autopilot based on operational requirements.
2. Inventory Standard node pools, machine types, zones and autoscaler bounds.
3. Understand Autopilot resource admission, workload constraints and provisioning.
4. Distinguish HPA, VPA and cluster autoscaler responsibilities.
5. Diagnose Pending Pods caused by requests, taints, topology, quota or IP exhaustion.
6. Plan Spot VM capacity and interruption-tolerant workloads.
7. Design safe PodDisruptionBudgets and maintenance procedures.
8. Review node auto-upgrades, release channels and surge capacity.
9. Forecast compute cost and capacity growth.
10. Produce operational acceptance evidence.

## 2. Architecture and scaling layers

```text
          Incoming workload demand
                    |
           HPA / application scaler
                    |
             Desired Pod replicas
                    |
           Kubernetes scheduler
                    |
       +------------+------------+
       |                         |
    Existing nodes          Pending Pods
       |                         |
       |               GKE capacity provisioning
       |                         |
       +------------+------------+
                    |
       Standard node pool autoscaler
           or Autopilot platform
                    |
            Google Compute VMs
                    |
        Ready nodes and scheduled Pods
```

**HPA** adjusts replicas based on metrics. **VPA** recommends or changes Pod requests depending on its configured mode. **Cluster autoscaler** adds/removes Standard nodes within supported bounds. **Autopilot** manages node infrastructure to satisfy eligible workloads under its constraints. These are related but separate mechanisms.

## 3. Lab 1 — Verify project, cluster and operating mode

```powershell
$ErrorActionPreference = 'Stop'
$project = 'REPLACE_WITH_APPROVED_STAGING_PROJECT'
$location = 'us-central1'
$cluster = 'REPLACE_WITH_APPROVED_GKE_CLUSTER'
gcloud config set project $project
gcloud auth list
gcloud config get-value project
gcloud container clusters list --project $project
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(name,location,autopilot,currentMasterVersion,releaseChannel,autoscaling)'
kubectl config current-context
kubectl get nodes -o wide
```

**Stop:** if Google Cloud project, authenticated identity or kubeconfig context differs from the approved staging target. Use the cluster's actual region or zone as `$location`.

**Expected:** mode, version, release channel and cluster location recorded.

## 4. Lab 2 — Compare Standard and Autopilot

| Dimension | Standard | Autopilot |
|---|---|---|
| Node pool configuration | Customer-managed pools | Platform-managed node infrastructure |
| VM family control | Broad supported machine-type choices | Workload and compute-class driven |
| Autoscaling | Configurable cluster autoscaler | Managed provisioning behavior |
| Pod resource requests | Customer-defined | Admission/defaulting/minimums may apply |
| Privileged/host access | Possible with security review | More restrictive |
| Spot | Supported node pool options | Supported eligible Spot workload patterns |
| Upgrade responsibility | Control-plane and node pool planning | More node lifecycle automation |
| Billing | Nodes and cluster-related resources | Autopilot-specific workload/cluster pricing |

GKE features and pricing evolve. Validate the current support matrix for GPU, privileged DaemonSets, host networking, local SSD, CSI and specialized workloads.

### Decision worksheet

```text
Application type:
Privileged/host access:
Node-local observability agent:
GPU / custom machine family:
Spot tolerance:
Stateful volume topology:
Autoscaling requirements:
SLO and failure-domain design:
Cost model and budget:
Chosen mode and justification:
```

## 5. Lab 3 — Inventory Standard node pools and machine capacity

**Standard clusters only:**

```powershell
gcloud container node-pools list --cluster $cluster --location $location --project $project
gcloud container node-pools describe REPLACE_WITH_NODE_POOL --cluster $cluster --location $location --project $project --format='yaml(name,config.machineType,config.spot,autoscaling,management,locations,upgradeSettings)'
kubectl get nodes -L cloud.google.com/gke-nodepool,topology.kubernetes.io/zone -o wide
kubectl describe nodes
```

On Autopilot, use supported cluster/Pod inventory instead of trying to administer Google-managed node pools.

### Capacity evidence

- Machine type and allocatable CPU/memory.
- DaemonSet overhead and reserved resources.
- Pod requests versus actual utilization.
- Nodes per zone and failure-domain distribution.
- Max Pods and VPC secondary range capacity.
- Node pool min/max and location policy.
- VM quota and regional capacity.

## 6. Lab 4 — Identify scheduler constraints

```powershell
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl get nodes --show-labels
kubectl describe nodes
kubectl get pdb -A
kubectl top nodes
```

`kubectl top` requires resource metrics. If unavailable, use the configured Cloud Monitoring source.

### Investigation order

1. Read `FailedScheduling` Events.
2. Compare Pod requests with node allocatable capacity.
3. Inspect node selectors, required affinity and taints.
4. Check topology spread and zonal disk placement.
5. Confirm autoscaler provisioning and limits.
6. Review project quota, VM availability and subnet IP ranges.
7. Check namespace ResourceQuota and LimitRange.
8. Verify image pull and admission policy only after scheduling.

**Expected:** evidence-backed classification, not the assumption that low observed CPU means a Pod must fit.

## 7. Lab 5 — Design bounded Standard cluster autoscaling

**Read-only:**

```powershell
gcloud container node-pools describe REPLACE_WITH_NODE_POOL --cluster $cluster --location $location --project $project --format='yaml(autoscaling,initialNodeCount,locations)'
```

**Staging change template — do not run without approval:**

```powershell
$pool = 'REPLACE_WITH_APPROVED_STANDARD_NODE_POOL'
gcloud container node-pools update $pool `
  --cluster $cluster `
  --location $location `
  --project $project `
  --enable-autoscaling `
  --min-nodes 1 `
  --max-nodes 3
```

Verify current gcloud syntax and whether bounds are per-zone or total for the chosen configuration. Use the supported node pool update syntax for the installed SDK and cluster version. Preserve original settings before any change.

### Scaling acceptance

- Autoscaler enabled for the intended Standard pool.
- Min/max match budget and SLO.
- Quota and secondary CIDR support growth.
- New nodes can join and reach Ready.
- System Pods retain stable capacity.
- Scale-down respects disruption and utilization constraints.

## 8. Lab 6 — Isolated workload scheduling test

Save `ch087-burst.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch087
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst
  namespace: ch087
spec:
  replicas: 3
  selector:
    matchLabels:
      app: burst
  template:
    metadata:
      labels:
        app: burst
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: burst
      containers:
        - name: web
          image: nginx:stable
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
```

```powershell
kubectl apply -f .\ch087-burst.yaml
kubectl -n ch087 rollout status deployment/burst --timeout=300s
kubectl -n ch087 get pods -o wide
kubectl get nodes -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** Pods schedule and become Ready. This small test might not trigger new nodes; that is normal. Never increase load solely to force scale-up without quota and cost approval.

## 9. Lab 7 — Horizontal Pod Autoscaler

Save `ch087-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: burst
  namespace: ch087
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: burst
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

```powershell
kubectl apply -f .\ch087-hpa.yaml
kubectl -n ch087 get hpa
kubectl -n ch087 describe hpa burst
kubectl -n ch087 top pods
```

HPA requires working CPU metrics and appropriate requests. Low test traffic may not increase replicas. In Autopilot, resource defaulting or admission changes may affect requests and therefore utilization calculations.

## 10. Lab 8 — VPA and resource request governance

```powershell
kubectl get verticalpodautoscalers -A
kubectl get limitranges -A
kubectl get resourcequotas -A
kubectl -n ch087 describe deployment burst
```

VPA CRDs/components may not be installed. Record Not installed rather than treating it as a failure. Evaluate VPA recommendations before enabling automated request changes for critical services.

### Request sizing principles

- CPU requests affect scheduling and autoscaler calculations.
- Memory requests must cover normal working set with headroom.
- Memory limits can cause OOMKilled during spikes.
- Over-requesting drives excess node capacity and cost.
- Under-requesting increases contention and latency.
- Autopilot has mode-specific request rules and billing implications.

**Expected:** resource request and limit policy linked to SLO and cost evidence.

## 11. Lab 9 — Spot VM and interruption-tolerant capacity

```powershell
gcloud container node-pools list --cluster $cluster --location $location --project $project
kubectl get nodes -L cloud.google.com/gke-spot,cloud.google.com/gke-nodepool
kubectl get pods -A -o wide
```

### Spot workload acceptance

1. Job is retryable and idempotent.
2. Checkpoints or durable queue protect progress.
3. No database primary depends solely on Spot capacity.
4. Node selectors/tolerations match actual Spot pool policy.
5. Graceful termination and eviction handling are tested.
6. On-demand fallback and capacity quotas are planned.
7. SLO and cost tradeoff documented.

Spot availability is not guaranteed. Do not use intentional production eviction as a tutorial exercise.

## 12. Lab 10 — PodDisruptionBudgets and maintenance safety

Save `ch087-pdb.yaml`:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: burst
  namespace: ch087
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: burst
```

```powershell
kubectl apply -f .\ch087-pdb.yaml
kubectl -n ch087 get pdb
kubectl -n ch087 describe pdb burst
kubectl get nodes -o wide
```

### Drain safety

- Check Ready replicas and `disruptionsAllowed`.
- Ensure replacement capacity and correct zone placement.
- Protect stateful volume ownership and quorum.
- Respect graceful termination.
- Check autoscaler and upgrade maintenance policies.
- Avoid `kubectl drain --force` as a default workaround.

**Expected:** maintenance plan and PDB evidence. No node drain is executed.

## 13. Lab 11 — Node upgrades and release channel readiness

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(currentMasterVersion,releaseChannel,maintenancePolicy)'
gcloud container node-pools list --cluster $cluster --location $location --project $project
kubectl get pdb -A
kubectl get apiservices
kubectl get crds
```

### Upgrade gates

1. Review supported Kubernetes target and release channel.
2. Audit deprecated APIs, admission webhooks and CRDs.
3. Validate CSI, CNI, ingress and metrics compatibility.
4. Ensure surge/blue-green capacity where applicable.
5. Review PDBs, quotas, IP ranges and node image policy.
6. Test staging application and database recovery.
7. Monitor during rollout and document rollback constraints.

Autopilot automates more node lifecycle work, but application owners still own compatibility and SLO acceptance. A Kubernetes control-plane downgrade is not a routine recovery strategy.

## 14. Lab 12 — Autoscaling failure tabletop

**Scenario:** API replicas double, but Pods remain Pending. A Standard pool is at maximum size, a zonal VM SKU is temporarily unavailable, and a database Pod is pinned to a zonal disk.

### Investigation

1. Identify Pending Pods and scheduler reasons.
2. Compare HPA desired/current replicas.
3. Inspect node pool autoscaling limits.
4. Check VM quotas, regional capacity and selected zones.
5. Review taints, affinity and topology spread.
6. Check VPC Pod secondary range capacity.
7. Inspect PVC topology and storage constraints.
8. Evaluate approved alternate pool/SKU and placement.
9. Record recovery time, cost and application SLIs.
10. Document preventive monitoring and forecast.

**Expected:** distinguish autoscaler failure from intentional scheduling constraints.

## 15. Lab 13 — Capacity and FinOps acceptance

### Forecast worksheet

```text
Cluster mode:
Region/zones:
Peak concurrent Pods:
CPU/memory requests:
Standard node pool min/max:
Autopilot resource classes:
VM quota and IP headroom:
Spot percentage and fallback:
Upgrade surge allowance:
Persistent storage:
Logging/monitoring:
Expected monthly spend:
Budget owner and alert:
```

### Operational signals

| Domain | Signal | Response |
|---|---|---|
| Scheduling | Pending Pods and FailedScheduling | Check requests, constraints, quota |
| Autoscaling | Desired versus actual nodes | Check pool bounds and cloud capacity |
| Nodes | Ready, pressure and eviction | Review node health |
| Workloads | HPA desired/current replicas | Check metrics and load |
| Storage | PVC Pending and disk topology | Check CSI and zones |
| Cost | Node-hours or Autopilot usage | Rightsize and forecast |
| Maintenance | PDB and upgrade blockers | Plan safe replacement capacity |

**Expected:** documented scaling limits, alert thresholds, ownership and cost budget.

## 16. Production operations runbook

### Detect

1. Identify customer symptoms and SLO impact.
2. Capture Pod, node and HPA state.
3. Inspect scheduling Events and cloud node provisioning.
4. Review quota, Pod IPs, node capacity and topology.
5. Distinguish application load from infrastructure failure.

### Remediate

1. Correct invalid requests or placement policies.
2. Adjust approved Standard node pool bounds only if required.
3. Avoid breaking PDBs or stateful quorum.
4. Prefer reversible changes and monitor node readiness.
5. Confirm application recovery and cost impact.

### Prevent

1. Maintain capacity forecasts and alert thresholds.
2. Test Spot interruption and retry behavior.
3. Review VPA/HPA request governance.
4. Validate upgrade and node lifecycle plans.
5. Review Standard versus Autopilot economics periodically.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Pods Pending | Requests, affinity, taints | Scheduler Events |
| Autoscaler at max | Pool bounds | Node pool configuration |
| Nodes not provisioned | Quota/SKU capacity | GKE operations, quotas |
| New nodes NotReady | Network/bootstrap | Node conditions |
| Pod IP exhaustion | Secondary range capacity | VPC-native network plan |
| HPA metrics unknown | Metrics pipeline | HPA describe, monitoring |
| Upgrade stalled | PDB, compatibility, quota | Upgrade state, Events |
| Spot job interrupted | Capacity reclaim | Retry/checkpoint logs |
| Unexpected spend | Oversizing or scaling | Billing and requests |
| Disk Pod Pending | Zonal PV topology | PV/node labels |

## 18. Cleanup

```powershell
kubectl config current-context
kubectl -n ch087 get deployments,pods,hpa,pdb
kubectl delete namespace ch087
```

Deleting the namespace does not restore node pool settings. If autoscaler bounds were changed, restore the **recorded original configuration** under a separate approved change. Do not delete shared GKE node pools or clusters.

## 19. Acceptance checklist

- [ ] Project, cluster and context verified.
- [ ] Standard versus Autopilot decision documented.
- [ ] Standard node pool inventory captured or marked Not applicable.
- [ ] Requests, allocatable resources and topology analyzed.
- [ ] Autoscaler bounds and quota/IP capacity reviewed.
- [ ] Scaling change approved and executed or marked Not run.
- [ ] Staging workload scheduling validated or marked Not run.
- [ ] HPA and VPA responsibilities understood.
- [ ] Spot recovery and fallback strategy documented.
- [ ] PDB and safe maintenance plan reviewed.
- [ ] Upgrade and release channel readiness documented.
- [ ] Autoscaling failure tabletop completed.
- [ ] Cost/capacity forecast and owners recorded.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Choose a GKE Cluster Mode](https://cloud.google.com/kubernetes-engine/docs/concepts/choose-cluster-mode)
- [GKE Standard Node Pools](https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools)
- [GKE Cluster Autoscaler](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler)
- [GKE Autopilot Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [GKE Spot VMs](https://cloud.google.com/kubernetes-engine/docs/how-to/spot-vms)
- [GKE Release Channels](https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels)
- [GKE Node Auto-upgrades](https://cloud.google.com/kubernetes-engine/docs/concepts/node-auto-upgrades)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [gcloud container node-pools](https://cloud.google.com/sdk/gcloud/reference/container/node-pools)

**Next:** Chapter 088 — GKE Networking, VPC-Native Clusters, Load Balancing and Storage.
