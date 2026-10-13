# Chapter 082 — AKS Node Pools and Autoscaling

**Track:** Kubernetes Administration · **Part 17 — Azure Kubernetes Service**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, Azure platform and FinOps engineers  
**Prerequisites:** Chapters 021–025 and 081; Azure CLI, kubectl, Windows PowerShell; approved AKS staging cluster; Metrics Server or equivalent for utilization inspection

## 1. Production scenario and mission

An AKS platform runs latency-sensitive APIs, stateful services and batch workloads. During peak processing, new Pods remain Pending while the cluster autoscaler cannot provision additional nodes. Meanwhile, an oversized system pool creates unnecessary spend, a Spot pool loses capacity during an eviction, and a node image upgrade stalls because a PodDisruptionBudget prevents safe eviction.

**Mission:** inventory AKS node pools, plan stable and elastic capacity, validate autoscaling behavior, investigate scheduling and Azure quota failures, and design safe node lifecycle procedures.

**Safety:** scaling, node pool upgrades, Spot tests, node drains and deletion can disrupt services and incur Azure charges. All mutating exercises require an approved staging subscription, budget and rollback plan. Do not force-delete database Pods or remove quorum members to complete a lab.

### Learning outcomes

1. Explain AKS system and user node pools and underlying VM Scale Sets.
2. Compare manual scaling, cluster autoscaler and workload-level HPA.
3. Design CPU/memory capacity, max Pods, IP headroom and upgrade surge.
4. Configure node pool labels, taints, zones and workload placement.
5. Understand Spot node pool eviction and retry semantics.
6. Troubleshoot Pending Pods and autoscaler scale-up failures.
7. Apply PodDisruptionBudgets and graceful termination.
8. Plan node image, OS and Kubernetes upgrades.
9. Monitor VMSS health, node pressure and cloud cost.
10. Produce an operational node pool readiness report.

## 2. AKS node pool architecture

```text
                         Kubernetes workloads
                                  |
                         Kubernetes scheduler
                                  |
                     Pending Pods / HPA replicas
                                  |
                         Cluster Autoscaler
                                  |
                      AKS node pool scaling
                                  |
                       Azure VM Scale Sets
                                  |
                 +----------------+----------------+
                 |                                 |
         System node pool                    User node pools
         Critical add-ons                   API / batch / stateful
                 |                                 |
           Azure VM nodes                   Azure VM nodes
                 +----------------+----------------+
                                  |
                         Azure VNet / CNI
```

The Kubernetes scheduler selects existing eligible nodes. The cluster autoscaler adjusts supported node pool capacity when unschedulable Pods indicate a need, subject to pool bounds, quotas, subnet capacity and constraints. The Horizontal Pod Autoscaler (HPA) changes workload replica counts; it does not create VM nodes directly.

### Pool choices

| Pool | Typical workloads | Operational consideration |
|---|---|---|
| System | CoreDNS and essential system Pods | Reliable capacity and upgrade headroom |
| User general | Stateless APIs | Autoscaling and zone distribution |
| User stateful | Database/application state | Disk topology, PDB, stable capacity |
| User Spot | Retryable batch jobs | Eviction, checkpointing and taints |
| User GPU | ML inference/training | GPU quota, drivers and device plugin |

AKS-managed system pool requirements, supported VM sizes and zone options vary with cluster configuration and Azure updates. Verify current AKS documentation and regional availability before making changes.

## 3. Lab 1 — Verify subscription, cluster and node pool inventory

```powershell
$ErrorActionPreference = 'Stop'
$subscription = 'REPLACE_WITH_APPROVED_SUBSCRIPTION_ID'
$resourceGroup = 'REPLACE_WITH_STAGING_RESOURCE_GROUP'
$cluster = 'REPLACE_WITH_STAGING_AKS_CLUSTER'
az account set --subscription $subscription
az account show --query '{Name:name,Id:id,Tenant:tenantId}' --output json
az aks show --resource-group $resourceGroup --name $cluster --query '{Name:name,Provisioning:provisioningState,Kubernetes:kubernetesVersion,NodeResourceGroup:nodeResourceGroup}' --output json
kubectl config current-context
kubectl get nodes -o wide
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --output table
```

**Stop** if Azure subscription and Kubernetes context do not match the approved staging environment.

**Expected:** a node pool inventory with pool mode, VM SKU, count, autoscaler state and upgrade version.

## 4. Lab 2 — Inspect node capacity, topology and pressure

```powershell
kubectl get nodes -L agentpool,topology.kubernetes.io/zone,kubernetes.azure.com/mode -o wide
kubectl top nodes
kubectl get pods -A -o wide
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl get pdb -A
```

Metrics Server must be available for `kubectl top`. If unavailable, inspect requests/allocatable and the configured monitoring stack.

### Capacity worksheet

```text
Node pool and VM SKU:
System/user mode:
Node count, min and max:
Availability zones:
CPU/memory allocatable:
CPU/memory requested:
DaemonSet/system overhead:
Pod density and max Pods:
VNet/subnet free IP headroom:
Upgrade surge capacity:
Azure VM quota:
Spot versus regular:
Cost owner and budget:
```

**Expected:** distinguish allocatable capacity, scheduled requests and actual utilization.

## 5. Lab 3 — Inspect node pool configuration and VMSS backing

```powershell
$pool = 'REPLACE_WITH_NODEPOOL_NAME'
az aks nodepool show --resource-group $resourceGroup --cluster-name $cluster --name $pool --query '{Name:name,Mode:mode,Count:count,VmSize:vmSize,Zones:availabilityZones,Autoscaling:enableAutoScaling,Min:minCount,Max:maxCount,MaxPods:maxPods,OsSku:osSKU,Version:orchestratorVersion,Provisioning:provisioningState}' --output json
$nodeResourceGroup = az aks show --resource-group $resourceGroup --name $cluster --query nodeResourceGroup --output tsv
az vmss list --resource-group $nodeResourceGroup --output table
```

Do not edit AKS-managed VM Scale Sets directly as a shortcut to node pool management. Use supported AKS APIs and approved IaC workflows.

**Expected:** identify VMSS infrastructure and its AKS node pool ownership.

## 6. Lab 4 — Design system and user pool separation

### Placement strategy

- Reserve reliable system capacity for cluster-critical add-ons.
- Keep application workloads in user pools where practical.
- Use node labels/affinity and taints/tolerations for intentional placement.
- Avoid hard constraints that prevent critical workload recovery.
- Spread critical replicas across available failure domains.
- Use PDBs, graceful termination and spare capacity for upgrades.
- Align stateful workload zones with Azure Disk volume topology.

### Illustrative Pod placement

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: ch082
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      nodeSelector:
        agentpool: REPLACE_WITH_USER_POOL
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: api
      containers:
        - name: api
          image: nginx:stable
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

**Expected:** a reviewed placement policy that does not accidentally pin all replicas to a single AZ.

## 7. Lab 5 — Understand AKS cluster autoscaler

The cluster autoscaler evaluates unschedulable Pods and node pool scaling options. It respects supported node pool bounds and Kubernetes scheduling constraints.

```powershell
az aks nodepool show --resource-group $resourceGroup --cluster-name $cluster --name $pool --query '{Autoscaling:enableAutoScaling,Min:minCount,Max:maxCount,Count:count}' --output json
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

### Scale-up prerequisites

1. Pool autoscaling enabled.
2. `maxCount` greater than current count.
3. Pod requests fit at least one eligible node SKU.
4. Node selectors, taints and topology permit scheduling.
5. Azure VM family quota and regional capacity available.
6. Node subnet and CNI IP headroom sufficient.
7. Cluster identity and networking permissions correct.

**Expected:** documented autoscaler configuration and likely scale-up blockers.

## 8. Lab 6 — Plan a bounded autoscaler change

**Mutating command — staging approval required.**

```powershell
$minNodes = 2
$maxNodes = 4
az aks nodepool update `
  --resource-group $resourceGroup `
  --cluster-name $cluster `
  --name $pool `
  --enable-cluster-autoscaler `
  --min-count $minNodes `
  --max-count $maxNodes
```

Before execution, verify the pool supports autoscaling, the values are approved, and the additional VM, disk and networking costs fit the budget. Do not enable autoscaling on an inappropriate or shared pool merely to test the command.

**Expected:** when executed under approval, node pool reports autoscaling enabled and approved min/max bounds.

## 9. Lab 7 — Generate safe staging scheduling demand

Save `ch082-burst.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch082
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst
  namespace: ch082
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
```

```powershell
kubectl apply -f .\ch082-burst.yaml
kubectl -n ch082 rollout status deployment/burst --timeout=300s
kubectl -n ch082 get pods -o wide
kubectl get nodes -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

This workload may fit existing nodes and therefore **may not trigger scale-up**. That is correct behavior. Increase replica counts only after checking approved headroom and budget; never create artificial production load.

**Expected:** record scheduler decisions, any node additions and time to Pod readiness.

## 10. Lab 8 — Distinguish HPA from node autoscaling

HPA changes Pod replica count based on supported metrics; cluster autoscaler adds nodes when needed for scheduling.

```powershell
kubectl get hpa -A
kubectl -n ch082 get deployment burst
kubectl -n ch082 top pods
```

### Illustrative HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: burst
  namespace: ch082
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

The HPA requires functioning resource metrics and suitable CPU requests. Do not interpret an HPA with unknown metrics as a node autoscaler failure.

## 11. Lab 9 — Spot node pool design and interruption handling

Spot capacity is appropriate only for workloads that tolerate eviction and retries.

### Spot checklist

- Explicit Spot pool taints and workload tolerations.
- Retryable, idempotent jobs or checkpointed consumers.
- Appropriate termination handling and queue visibility.
- On-Demand fallback for critical workloads.
- Diverse VM SKU and AZ strategy where supported.
- Monitoring of eviction and pending time.
- No reliance on Spot for critical system Pods or database primaries.

```powershell
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --query '[].{Name:name,Priority:scaleSetPriority,Eviction:scaleSetEvictionPolicy,Count:count,Mode:mode}' --output table
kubectl get nodes -L kubernetes.azure.com/scalesetpriority,agentpool
```

**Expected:** a Spot interruption tabletop and documented fallback, not an intentional eviction of production nodes.

## 12. Lab 10 — PodDisruptionBudgets and graceful node drains

Save `ch082-pdb.yaml`:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: burst
  namespace: ch082
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: burst
```

```powershell
kubectl apply -f .\ch082-pdb.yaml
kubectl -n ch082 get pdb
kubectl -n ch082 describe pdb burst
kubectl get nodes -o wide
```

### Safe drain considerations

- Ensure sufficient ready replicas and replacement capacity.
- Confirm PDB `disruptionsAllowed` before voluntary eviction.
- Check stateful storage attachment and zone placement.
- Respect `terminationGracePeriodSeconds`.
- Never use `kubectl drain --force` as a default incident fix.
- Remember PDBs do not prevent every involuntary disruption.

**Expected:** a reviewed drain plan. No node is drained by this lab.

## 13. Lab 11 — Node image and Kubernetes upgrade planning

```powershell
az aks nodepool show --resource-group $resourceGroup --cluster-name $cluster --name $pool --query '{Version:orchestratorVersion,NodeImage:nodeImageVersion,Upgrade:upgradeSettings,Provisioning:provisioningState}' --output json
az aks get-upgrades --resource-group $resourceGroup --name $cluster --output table
kubectl get pdb -A
kubectl get pods -A -o wide
```

### Upgrade runbook

1. Verify supported AKS Kubernetes version and node OS image.
2. Review add-on/CSI/CNI compatibility.
3. Check PDBs and maintenance windows.
4. Validate max surge and subnet/VM quota headroom.
5. Upgrade staging first, one pool at a time where appropriate.
6. Monitor node readiness, Pod rescheduling and application SLIs.
7. Verify storage and network connectivity after replacement.
8. Record rollback constraints; control-plane downgrades are not a routine recovery option.

**Expected:** an approved node image and version upgrade plan, not an executed production upgrade.

## 14. Lab 12 — Autoscaler failure incident tabletop

**Scenario:** Pods are Pending during a peak ingestion job; the user pool has reached its configured maximum, subnet IPs are low, and the requested VM SKU is unavailable in one zone.

### Investigation

1. Read `FailedScheduling` Events.
2. Confirm autoscaler enabled and maxCount.
3. Check Pod CPU/memory requests against node SKU.
4. Check node selectors, taints and topology spread.
5. Inspect Azure quota and regional VM capacity.
6. Review subnet IP availability and CNI mode.
7. Verify cluster identity permissions.
8. Evaluate an approved alternate pool/SKU or quota change.
9. Confirm recovery without violating database topology.
10. Record time-to-recovery, cost and prevention.

**Expected:** evidence that differentiates autoscaler bounds, Azure capacity, subnet constraints and invalid scheduling policy.

## 15. Lab 13 — Cost and capacity acceptance project

### Cost model

```text
System pool VM-hours:
User pool VM-hours:
Spot node VM-hours:
Azure Disk volumes and snapshots:
Public IP / Load Balancer / NAT Gateway:
Azure Monitor and Log Analytics:
Upgrade surge capacity:
Reserved Instances / Savings Plan applicability:
Idle nodes and overprovisioning:
Monthly budget and owner:
```

### Capacity acceptance

- System pool has resilient baseline capacity.
- User pool has bounded autoscaler settings.
- Pods can schedule under expected peak requests.
- Quotas and subnet headroom support node growth.
- Stateful workloads preserve volume topology.
- Spot workloads can recover from interruption.
- PDBs permit safe maintenance.
- Alerts exist for Pending Pods, NotReady nodes and cost spikes.

## 16. Production node pool operations runbook

### Detect

1. Identify impacted application and Pending Pods.
2. Check node pool count, autoscaler bounds and node health.
3. Inspect scheduler Events, quotas and resource requests.
4. Check Azure VMSS health, SKU availability and subnet IPs.
5. Review storage and topology constraints.

### Remediate

1. Correct invalid scheduling constraints first.
2. Increase capacity only within approved limits and budget.
3. Use supported AKS node pool APIs, not direct VMSS edits.
4. Protect stateful Pods and verify PDBs.
5. Confirm new nodes Ready and application SLO recovery.

### Prevent

1. Alert on Pending Pods and node provisioning latency.
2. Forecast CPU/memory and subnet IP growth.
3. Review system pool and user pool cost monthly.
4. Test Spot interruption recovery.
5. Plan node image and Kubernetes upgrades.
6. Audit PDBs and graceful termination behavior.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Autoscaler not scaling | Disabled or max reached | Node pool config |
| Pods Pending | Requests, affinity, taints | Scheduler Events |
| New nodes NotReady | Bootstrap, CNI, identity | Node conditions, VMSS |
| Scale-up fails | VM quota/SKU unavailable | Azure quotas, Activity Log |
| IP exhaustion | Subnet/CNI limits | VNet IP capacity |
| PDB blocks upgrade | Insufficient available replicas | PDB status |
| Spot workload interrupted | Capacity eviction | Job retries, events |
| Node pool update stuck | Surge, quota, drain | AKS operations, PDB |
| Database PVC attach fails | Disk AZ mismatch | PV topology and node zone |
| Cost spike | Excess node count or SKU | Cost Management |

## 18. Cleanup and safety

```powershell
kubectl config current-context
kubectl -n ch082 get deployments,pods,hpa,pdb
kubectl delete namespace ch082
```

Deleting this lab namespace does not revert a node pool autoscaler change. If Lab 6 was executed, restore the **recorded original** autoscaler settings through a separately approved change. Do not delete shared node pools, VMSS resources, Azure identities or production nodes.

## 19. Acceptance checklist

- [ ] Subscription, AKS cluster and kubeconfig context verified.
- [ ] System and user node pool inventory captured.
- [ ] Node capacity, requests and topology analyzed.
- [ ] VMSS ownership and AKS lifecycle boundaries understood.
- [ ] Cluster autoscaler settings and bounds reviewed.
- [ ] Autoscaler change executed under approval or marked Not run.
- [ ] Staging scheduling test executed or marked Not run.
- [ ] HPA and node autoscaling responsibilities differentiated.
- [ ] Spot interruption recovery designed.
- [ ] PDB and drain safety reviewed.
- [ ] Node image and Kubernetes upgrade plan documented.
- [ ] Autoscaler failure tabletop completed.
- [ ] Capacity and cost acceptance report completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [AKS Node Pools](https://learn.microsoft.com/en-us/azure/aks/use-multiple-node-pools)
- [AKS Cluster Autoscaler](https://learn.microsoft.com/en-us/azure/aks/cluster-autoscaler)
- [AKS Spot Node Pools](https://learn.microsoft.com/en-us/azure/aks/spot-node-pool)
- [AKS Node Image Upgrades](https://learn.microsoft.com/en-us/azure/aks/node-image-upgrade)
- [AKS Upgrade Cluster](https://learn.microsoft.com/en-us/azure/aks/upgrade-aks-cluster)
- [AKS Networking Concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-network)
- [Kubernetes Cluster Autoscaling](https://kubernetes.io/docs/concepts/cluster-administration/cluster-autoscaling/)
- [Kubernetes Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Azure CLI AKS Nodepool](https://learn.microsoft.com/en-us/cli/azure/aks/nodepool)

**Next:** Chapter 083 — AKS Networking, Load Balancing and Storage.
