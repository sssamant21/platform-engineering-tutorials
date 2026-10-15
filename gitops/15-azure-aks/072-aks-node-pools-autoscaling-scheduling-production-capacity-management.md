# Chapter 072 — AKS Node Pools, Autoscaling, Scheduling and Production Capacity Management

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 15:** Azure Kubernetes Service (AKS)  
**Chapter:** 072 / 100  
**Audience:** Platform Engineers, SREs, Cloud Engineers, Kubernetes Administrators and FinOps

> **Lab safety:** All changes and disruption tests are for a dedicated staging AKS cluster with synthetic workloads. Node pool deletion, eviction, Spot interruption and autoscaler misconfiguration can cause outages. Never scale system capacity to zero or force-drain critical production workloads. Confirm Azure subscription and Kubernetes context before each write.

## 1. Learning objectives

After this chapter you will:

1. Design dedicated AKS system and user node pools.
2. Compare manual scaling, Cluster Autoscaler, Horizontal Pod Autoscaler and node auto-provisioning.
3. Configure autoscaling safely using Terraform and Azure CLI.
4. Control placement with selectors, affinity, taints, tolerations and topology spread.
5. Use Azure Spot node pools for interruption-tolerant workloads.
6. Diagnose Pending Pods, insufficient VM capacity, subnet limits and node readiness failures.
7. Apply PodDisruptionBudgets, graceful termination and safe upgrade policies.
8. Design capacity headroom, quotas, budgets and operational dashboards.
9. Validate failure recovery, GitOps ownership and FinOps acceptance.

## 2. Architecture

~~~text
GitLab protected infrastructure MR
               |
         Terraform plan/apply
               |
          AKS control plane
             /       \
System node pool    User node pools
  On-Demand          On-Demand / Spot
  CoreDNS            application Pods
  Argo CD            stateless/batch
  controllers          |
       |         Cluster Autoscaler
       |                |
       +--- scheduler --+
               |
         Azure VMSS capacity
               |
        Azure Monitor / alerts

GitLab app pipeline -> GitOps MR -> Argo CD -> workload replicas
                                              |
                                             HPA
                                              |
                                     unschedulable Pods
                                              |
                                    node scaling decision
~~~

**Control loops:** HPA changes workload replica counts based on metrics. Cluster Autoscaler changes node pool size based on schedulability and utilization constraints. AKS node auto-provisioning, where supported, can provision node configurations dynamically; it is not identical to Cluster Autoscaler and must not be assumed to coexist with every AKS configuration.

## 3. Capacity control comparison

| Control | Primary function | Common owner |
| --- | --- | --- |
| Manual node count | Fixed VM count | Terraform/AKS operator |
| Cluster Autoscaler | Scale existing eligible node pools | AKS managed autoscaler |
| Horizontal Pod Autoscaler | Scale Pod replicas | Kubernetes application |
| Vertical Pod Autoscaler | Recommend/adjust Pod requests | Platform/application team |
| AKS node auto-provisioning | Dynamically provision node capacity | AKS NAP controller |
| Scheduled scaling | Planned capacity changes | Approved automation |

**Important:** use the official AKS compatibility documentation before enabling node auto-provisioning. It has requirements and feature limitations, and its provisioning model must not conflict with Cluster Autoscaler ownership.

## 4. System versus user node pools

A system pool should provide stable capacity for critical Kubernetes components and approved platform controllers. User pools should host application workloads and may have different VM sizes, OS images, capacity types and scaling limits.

Recommended principles:

- Maintain sufficient system nodes for multi-AZ resilience and rolling upgrades.
- Use On-Demand for critical system workloads.
- Keep a minimum reliable application capacity for important services.
- Use taints and tolerations deliberately; do not strand essential add-ons.
- Avoid mixing privileged system workloads with untrusted application workloads.
- Plan resource reservations and DaemonSet overhead.
- Maintain separate ownership for infrastructure and Kubernetes workload placement.

## 5. Preflight and inventory

~~~bash
az account show --output table
kubectl config current-context
az aks show -g rg-aks-staging -n aks-staging \
  --query '{version:kubernetesVersion,location:location,identity:identity.type}' -o json
az aks nodepool list -g rg-aks-staging --cluster-name aks-staging -o table
kubectl get nodes -L agentpool,kubernetes.azure.com/mode,topology.kubernetes.io/zone
kubectl get pods -A -o wide
kubectl get pdb -A
~~~

Verify that resource groups, cluster names, Azure region and subscription match the approved staging environment.

## 6. Terraform system pool

~~~hcl
resource "azurerm_kubernetes_cluster" "aks" {
  # Required cluster, identity and network settings are defined
  # in Chapter 071 and the approved infrastructure module.

  default_node_pool {
    name           = "system"
    vm_size        = "Standard_D4s_v5"
    node_count     = 3
    zones          = ["1", "2", "3"]
    vnet_subnet_id = azurerm_subnet.nodes.id
    only_critical_addons_enabled = true
  }
}
~~~

This is a fragment, not a complete standalone Terraform resource. Availability zones and VM SKUs vary by region. The system pool must have adequate headroom for CoreDNS, monitoring, Argo CD, admission webhooks and maintenance.

## 7. Terraform user pool with Cluster Autoscaler

~~~hcl
resource "azurerm_kubernetes_cluster_node_pool" "apps" {
  name                  = "apps"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D4s_v5"
  mode                  = "User"
  auto_scaling_enabled  = true
  min_count             = 2
  max_count             = 8
  zones                 = ["1", "2", "3"]
  vnet_subnet_id        = azurerm_subnet.nodes.id

  node_labels = {
    "workload-tier" = "applications"
  }

  tags = {
    Environment = "staging"
    ManagedBy   = "terraform"
  }
}
~~~

Validate autoscaling argument names and provider compatibility against the pinned AzureRM provider version. Do not simultaneously manage a fixed desired node count and autoscaler-managed size in conflicting controllers.

## 8. Azure CLI node pool inspection and scaling

~~~bash
az aks nodepool show \
  -g rg-aks-staging \
  --cluster-name aks-staging \
  --name apps -o json

az aks nodepool update \
  -g rg-aks-staging \
  --cluster-name aks-staging \
  --name apps \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 8
~~~

CLI changes can introduce Terraform drift. Prefer an approved infrastructure change through Terraform; use direct CLI mutation only under documented emergency/change procedure and reconcile back to IaC.

## 9. Scheduling constraints

A Pod may be unschedulable because of:

- Insufficient requested CPU, memory, ephemeral storage or GPU.
- Node selector or required affinity that matches no pool.
- Missing toleration for a node taint.
- Strict zone/topology spread with insufficient AZ capacity.
- Volume node affinity (Azure Disk zonal storage).
- ResourceQuota, admission denial or unsupported architecture.
- Maximum Pods per node or networking/IP exhaustion.

Cluster Autoscaler can only help if an eligible node pool can supply a node satisfying the Pod constraints.

## 10. Workload placement example

~~~yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: demo-api
  template:
    metadata:
      labels:
        app: demo-api
    spec:
      nodeSelector:
        workload-tier: applications
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: demo-api
      containers:
        - name: api
          image: registry.example.internal/demo/api@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
~~~

Replace the digest with a real verified immutable image digest. ScheduleAnyway provides preferred spreading; it does not guarantee one replica per AZ. Use strict topology only when its Pending behavior is acceptable.

## 11. Node taints and tolerations

~~~yaml
apiVersion: v1
kind: Pod
metadata:
  name: synthetic-batch
  namespace: demo-staging
spec:
  tolerations:
    - key: "workload"
      operator: "Equal"
      value: "batch"
      effect: "NoSchedule"
  nodeSelector:
    workload-tier: batch
  containers:
    - name: worker
      image: registry.example.internal/demo/worker@sha256:REPLACE_WITH_REAL_DIGEST
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
  restartPolicy: Never
~~~

A toleration permits placement but does not force it. Pair it with labels/affinity for isolation. Taints do not replace Kubernetes RBAC or network security.

## 12. HPA versus node autoscaling

~~~yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: demo-api
  minReplicas: 3
  maxReplicas: 12
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
~~~

HPA CPU utilization depends on CPU requests and available metrics. Ensure metrics-server or an approved metrics adapter is functional. HPA creates replicas; Cluster Autoscaler may then provision nodes for unschedulable Pods.

## 13. Cluster Autoscaler scale-down controls

Review:

- Scale-down delay after scale-up.
- Unneeded-node evaluation timing.
- PodDisruptionBudgets and eviction rules.
- System Pods and kube-system priority.
- Node group minimum and maximum sizes.
- Pod local storage and graceful termination.
- Autoscaler profile options supported by AKS.

Do not copy upstream Cluster Autoscaler flags into AKS blindly; AKS exposes a supported autoscaler profile subset through Azure configuration.

## 14. Spot node pools

Azure Spot VMs may be evicted when capacity is reclaimed or pricing conditions change. Use them only for tolerant batch, queue workers and appropriately replicated stateless workloads.

Example CLI (verify current CLI arguments and supported SKUs before use):

~~~bash
az aks nodepool add \
  -g rg-aks-staging \
  --cluster-name aks-staging \
  --name spotbatch \
  --priority Spot \
  --eviction-policy Delete \
  --spot-max-price -1 \
  --node-vm-size Standard_D4s_v5 \
  --node-count 1 \
  --labels workload-tier=batch \
  --node-taints workload=batch:NoSchedule
~~~

Spot availability is not guaranteed, and eviction may occur independently of PodDisruptionBudgets. Never rely on Spot as the sole capacity for critical system services. Include queue retries, idempotency and checkpoints.

## 15. Availability zones and disruption

Zone spreading protects against some infrastructure failures but does not automatically make an application highly available. Deploy multiple replicas, readiness probes, topology spread and safe PodDisruptionBudgets. Stateful Azure Disk volumes are typically zonal and require compatible placement or replication.

~~~yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: demo-api
~~~

A PDB constrains voluntary evictions; it cannot prevent an Azure VM failure or Spot eviction. A too-strict PDB can block upgrades and scale-down.

## 16. Resource requests and capacity planning

Estimate capacity from Pod **requests**, not just observed CPU. Include kubelet reservations, OS overhead, DaemonSets, CSI/CNI Pods, workload bursts and upgrade surge.

Example:

~~~text
Per-node allocatable CPU:        3.5 vCPU
Average Pod CPU request:         0.5 vCPU
Theoretical Pod count by CPU:    7
Less scheduling/headroom target: 20%
Planning estimate:               5-6 Pods per node

Also check memory, maxPods, disk, AZ and quota.
~~~

This is illustrative arithmetic, not a guarantee of actual node capacity. Derive values from kubectl describe node and actual workload requests.

## 17. Azure quotas and VM SKU availability

Node scale-up can fail because of regional or VM-family vCPU quota, zone scarcity, subscription policy, capacity reservations or networking limitations.

~~~bash
az vm list-usage --location eastus -o table
az aks nodepool list -g rg-aks-staging --cluster-name aks-staging -o table
kubectl get events -A --sort-by=.lastTimestamp
~~~

Use the target region rather than assuming eastus. Investigate the precise Azure operation error before changing instance sizes or quotas.

## 18. AKS node auto-provisioning (NAP)

Where supported, AKS node auto-provisioning uses a Karpenter-based model to dynamically select/provision capacity. Its feature compatibility, APIs and limitations are not the same as self-managed upstream Karpenter on EKS.

Before enabling:

1. Verify supported AKS region, version, network mode and cluster configuration.
2. Review whether Cluster Autoscaler must be disabled or migrated.
3. Check supported node pool and workload configurations.
4. Define approved VM families, Spot use and resource ceilings.
5. Test provisioning, disruption and drift behavior in staging.
6. Establish a migration and rollback plan.

Do not install upstream AWS Karpenter controllers or AWS EC2NodeClass manifests into AKS.

## 19. GitOps ownership and policy checks

~~~text
Terraform:
  AKS cluster, system/user node pools, Azure quotas/identity
Argo CD:
  namespace quotas, workload requests, HPA, PDB, affinity
AKS controllers:
  Cluster Autoscaler or supported NAP-managed capacity
GitLab:
  protected MR review, validation, cost and policy gates
~~~

Do not let GitOps continuously revert autoscaler-managed node counts through Terraform. Keep autoscaler ownership explicit and review drift handling.

## 20. GitLab capacity governance example

~~~yaml
stages: [validate, policy]

validate:
  stage: validate
  image: registry.example.internal/ci/kubernetes-tools:PINNED_DIGEST
  script:
    - ./ci/validate-workload-resources.sh
    - ./ci/validate-pdb-topology.sh

capacity_policy:
  stage: policy
  image: registry.example.internal/ci/policy-tools:PINNED_DIGEST
  script:
    - ./ci/check-nodepool-min-max.sh
    - ./ci/check-spot-placement.sh
    - ./ci/check-approved-vm-skus.sh
~~~

The internal images and scripts are illustrative interfaces, not provided executable assets. Implement them with approved schema validation, policy-as-code and a maintained SKU/region matrix.

## 21. Monitoring and alerting

Monitor:

- Nodes Ready/NotReady by node pool and AZ.
- Pending Pods and scheduler failure reasons.
- Cluster Autoscaler activity, failures and scale latency.
- HPA desired/current replicas and metrics health.
- CPU/memory requests versus allocatable capacity.
- Node memory, disk and PID pressure.
- Azure VM quota and regional SKU capacity failures.
- Spot eviction signals and application recovery.
- PodDisruptionBudget violations and blocked drains.
- Azure CNI Pod IP/network capacity.
- Azure Disk CSI attachment failures.
- Node image version and upgrade progress.
- Node pool VM cost, idle headroom and log ingestion cost.

Metric series depend on installed monitoring components. Validate actual telemetry before creating alerts.

## 22. Production change workflow

1. Create an infrastructure or GitOps MR with capacity forecast.
2. Validate Terraform and Kubernetes manifests.
3. Review VM SKU, quota, AZ, Spot risk and monthly cost.
4. Confirm PDB, topology, storage and application SLO compatibility.
5. Apply to staging and observe for an agreed soak period.
6. Promote with independent approval.
7. Monitor scheduling latency and service health.
8. Reconcile any emergency CLI change back to IaC.

## 23. Upgrade and node image lifecycle

Coordinate node image updates with workload readiness, autoscaler limits and surge headroom. Validate PDBs and Azure Disk topology before draining. Keep system pool healthy during user-pool rotations.

AKS control-plane upgrades and node image upgrades are distinct operations. Neither should be assumed reversible by downgrading the control plane.

## 24. Lab A — Node pool inventory

1. Confirm subscription and cluster context.
2. Inventory system and user pools, sizes, AZs and autoscaling settings.
3. Record node labels and taints.
4. Calculate allocatable versus requested CPU/memory.
5. Identify system workload placement.
6. Save redacted baseline evidence.

**Pass:** every node has a documented capacity owner.

## 25. Lab B — Create a user pool with Terraform

1. Add a user pool with approved VM SKU.
2. Configure autoscaling min/max and AZs.
3. Run Terraform fmt, validate and plan.
4. Obtain reviewed staging approval.
5. Apply and verify node registration.
6. Document cost and rollback.

**Pass:** the user pool is healthy and Terraform-managed.

## 26. Lab C — Scheduling with node selectors

1. Deploy synthetic workload with nodeSelector matching user pool.
2. Confirm placement using kubectl get pods -o wide.
3. Change selector to nonexistent label in disposable namespace.
4. Observe Pending scheduler events.
5. Restore valid selector.
6. Record diagnosis.

**Pass:** placement constraints are understood and recoverable.

## 27. Lab D — Taints and tolerations

1. Create isolated batch pool or disposable tainted node group.
2. Apply workload without toleration.
3. Observe unschedulability.
4. Add scoped toleration and node affinity.
5. Verify placement.
6. Remove test resources.

**Pass:** batch isolation works without affecting system workloads.

## 28. Lab E — Cluster Autoscaler scale-up

1. Deploy synthetic Pods with explicit CPU/memory requests.
2. Increase replicas beyond existing user-pool allocatable capacity.
3. Observe Pending Pods and autoscaler decisions.
4. Verify node pool scale-up.
5. Measure Pod scheduling latency.
6. Scale back and observe safe scale-down.

**Pass:** autoscaler reacts within approved objective.

## 29. Lab F — HPA plus node autoscaler

1. Deploy metrics-server-compatible synthetic CPU workload.
2. Configure HPA with min/max replicas.
3. Generate controlled CPU load.
4. Observe HPA increasing replicas.
5. Verify Cluster Autoscaler provisions nodes if needed.
6. Stop load and measure scale-down behavior.

**Pass:** both control loops operate without conflicting desired states.

## 30. Lab G — Resource request accuracy

1. Capture actual CPU/memory use and requests.
2. Identify under- and over-requested synthetic workloads.
3. Adjust requests through reviewed GitOps MR.
4. Observe scheduling and HPA changes.
5. Validate latency/error SLO.
6. Record capacity efficiency.

**Pass:** requests reflect workload demand and headroom.

## 31. Lab H — Availability-zone topology

1. Deploy three synthetic replicas.
2. Apply preferred topology spread across AZs.
3. Verify actual node/AZ placement.
4. Simulate a constrained AZ in staging using node affinity.
5. Observe scheduler and autoscaler behavior.
6. Restore safe placement.

**Pass:** zone constraints and capacity tradeoffs are documented.

## 32. Lab I — PDB and voluntary disruption

1. Deploy replicated synthetic API.
2. Configure PDB minAvailable 2.
3. Drain one disposable application node using approved procedure.
4. Observe evictions, readiness and rescheduling.
5. Test an overly strict PDB in isolated namespace.
6. Restore safe PDB.

**Pass:** voluntary disruption respects availability objective.

## 33. Lab J — Spot batch scheduling

1. Create isolated staging Spot pool.
2. Deploy retryable synthetic batch worker with toleration.
3. Verify Spot placement.
4. Simulate interruption through an approved test harness.
5. Confirm retries/checkpoints and completion.
6. Remove Spot test resources.

**Pass:** workload tolerates interruption without losing required work.

## 34. Lab K — VM quota or capacity failure

1. Record regional VM-family quota.
2. Restrict disposable staging pool max size below demand.
3. Trigger synthetic scale-up.
4. Observe autoscaler and Pending events.
5. Restore safe limits and capacity.
6. Document actual quota escalation process.

**Pass:** capacity failures are distinguished from scheduler errors.

## 35. Lab L — System pool resilience

1. Verify critical platform Pods on system nodes.
2. Check system pool capacity and AZ spread.
3. Simulate one disposable system-node maintenance drain with approval.
4. Verify CoreDNS, Argo CD and monitoring remain healthy.
5. Restore node readiness.
6. Record SLO impact.

**Pass:** platform controllers survive a controlled node rotation.

## 36. Lab M — Azure Disk topology

1. Create disposable Azure Disk PVC and workload.
2. Identify PV zone affinity.
3. Attempt incompatible scheduling in isolated test.
4. Inspect scheduler and CSI errors.
5. Restore compatible node placement.
6. Validate synthetic data integrity.

**Pass:** storage topology constraints are understood.

## 37. Lab N — GitOps capacity rollback

1. Propose workload resource and HPA changes through protected MR.
2. Run capacity and policy checks.
3. Merge to staging.
4. Simulate unsafe replica/request combination.
5. Revert reviewed GitOps change.
6. Verify application health and node scale stabilization.

**Pass:** workload capacity policy is safely reversible.

## 38. Lab O — FinOps and operational acceptance

1. Inventory node pool VM SKUs and hourly cost.
2. Measure requested/allocatable CPU and memory.
3. Compare On-Demand and Spot workload placement.
4. Review unused node headroom and autoscaler bounds.
5. Calculate projected monthly cost and disruption risk.
6. Approve production capacity guardrails.

**Pass:** capacity changes improve efficiency without violating SLOs.

## 39. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | Pods Pending despite spare nodes | Affinity/taints/requests | Inspect scheduler events |
| 2 | Node pool does not scale | Autoscaler disabled/max reached | Review autoscaler configuration |
| 3 | Scale-up fails | Azure vCPU quota | Review quota and Azure operations |
| 4 | Scale-up unavailable in AZ | VM SKU scarcity | Use approved zone/SKU alternative |
| 5 | Nodes NotReady | CNI/kubelet/OS/network | Inspect node conditions |
| 6 | System Pods Pending | Insufficient system capacity | Restore system pool headroom |
| 7 | HPA shows unknown metrics | Metrics pipeline unavailable | Repair metrics-server/adapter |
| 8 | HPA scales but Pods stay Pending | Node capacity or constraints | Diagnose Cluster Autoscaler |
| 9 | Spot Pods evicted | Azure Spot interruption | Retry/fallback to On-Demand |
| 10 | Scale-down blocked | PDB/local storage/system Pods | Review eviction constraints |
| 11 | Excessive node churn | Aggressive scale-down | Tune supported autoscaler profile |
| 12 | Application concentrated in one AZ | Weak topology spread | Adjust scheduling rules |
| 13 | Disk PVC prevents rescheduling | PV zone affinity | Restore zonal node capacity |
| 14 | Wrong VM architecture | Missing architecture constraint | Restrict supported architecture |
| 15 | Pod density exhausted | maxPods/CNI capacity | Review networking configuration |
| 16 | Terraform continually changes count | Autoscaler/IaC ownership conflict | Resolve desired-size ownership |
| 17 | Upgrade stalls | PDB/insufficient surge | Restore headroom and eviction path |
| 18 | Azure spend spikes | Overprovisioned nodes | Review requests, pools and budgets |

## 40. Runbook — Pending Pods and failed scale-up

1. Confirm subscription, AKS context, namespace and affected Pods.
2. Inspect Pod requests, selectors, taints, affinity and topology.
3. Check autoscaler status, node pool bounds and node conditions.
4. Review Azure quota, VM SKU capacity and subnet networking.
5. Restore approved capacity or correct constraints.
6. Verify Pod readiness, Service endpoints and application SLO.
7. Record incident timeline and forecast changes.

## 41. Runbook — Spot interruption

1. Identify evicted Spot nodes and affected batch workloads.
2. Confirm retries, checkpoint status and queue backlog.
3. Check remaining Spot availability and On-Demand fallback.
4. Restore capacity within approved cost guardrails.
5. Validate data/work completion and application health.
6. Review diversification and interruption handling.
7. Document recovery and follow-up.

## 42. Runbook — system node pool outage

1. Identify unavailable system nodes and critical add-ons.
2. Check AKS control-plane status and node pool health.
3. Restore On-Demand system capacity and zone coverage.
4. Validate CoreDNS, CNI, CSI, Argo CD and monitoring.
5. Avoid deleting the last healthy system node.
6. Confirm platform and application SLO.
7. Record preventive headroom and maintenance improvements.

## 43. Runbook — autoscaler oscillation

1. Inspect recent workload and Terraform/GitOps changes.
2. Review autoscaler events, HPA metrics and node churn.
3. Identify over-aggressive requests, limits or scale-down.
4. Stabilize workload replica policy and capacity headroom.
5. Correct supported autoscaler profile under change control.
6. Verify stable scale behavior and costs.
7. Add regression tests.

## 44. Runbook — node upgrade blocked by PDB

1. Identify affected node pool and Pods blocking eviction.
2. Inspect PDB allowed disruptions and workload health.
3. Restore missing replicas or capacity before changing PDB.
4. Review topology and Azure Disk placement.
5. Resume approved node rotation with surge headroom.
6. Verify workload readiness and data consistency.
7. Record change evidence.

## 45. Evidence template

~~~text
Change / incident ID:
Azure subscription, region, AKS cluster:
System/user node pools:
VM SKUs, AZs and autoscaler bounds:
Node labels, taints and topology:
Workload requests/limits and HPA:
Cluster Autoscaler / NAP configuration:
Pending Pods and scheduler events:
Spot eviction and fallback evidence:
PDB and node rotation results:
Azure quota and networking:
GitOps and Terraform revisions:
SLO and scheduling latency:
Monthly cost baseline and forecast:
Recovery time, owner and approver:
~~~

## 46. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| System/user pool architecture | 20 | Capacity ownership and availability |
| Cluster Autoscaler/HPA behavior | 20 | Scale-up/down tests |
| Scheduling and topology | 15 | Affinity, taints, AZ spread |
| Spot and disruption resilience | 15 | Retry/PDB/drain tests |
| GitOps and Terraform governance | 10 | Reviewed changes and rollback |
| Monitoring and incident recovery | 10 | Alerts and runbooks |
| FinOps and capacity planning | 10 | Budget and utilization analysis |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: critical system services depend solely on Spot capacity, unauthorized node pool changes, uncontrolled autoscaler ownership conflict, untested data loss risk, or missing recovery procedure.

## 47. Final acceptance checklist

- [ ] System/user node pool separation validated.
- [ ] Autoscaler ownership and Terraform drift handling documented.
- [ ] Node pool min/max bounds and Azure quotas reviewed.
- [ ] Workload requests, HPA and scheduler constraints tested.
- [ ] Taints, tolerations and topology spread validated.
- [ ] Spot limited to interruption-tolerant workloads.
- [ ] PDBs and controlled node drains tested.
- [ ] Azure Disk topology considered for stateful Pods.
- [ ] System pool survives controlled maintenance.
- [ ] GitOps capacity changes and rollback reviewed.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks tested.
- [ ] SLO, cost and capacity objectives accepted.

## 48. Knowledge check

1. Why are AKS system and user pools separated?
2. How do HPA and Cluster Autoscaler interact?
3. Why can a Pending Pod fail to trigger a successful node scale-up?
4. What is the difference between a toleration and a node selector?
5. Why does a PDB not protect against all Spot evictions?
6. How does Azure Disk zone affinity constrain rescheduling?
7. Why must Terraform not fight autoscaler-managed node count?
8. When should AKS node auto-provisioning be considered?
9. Which metrics indicate under-requested versus over-requested workloads?
10. What evidence proves a node pool is production-ready?

## 49. References

- [AKS Node Pools](https://learn.microsoft.com/azure/aks/create-node-pools)
- [AKS Cluster Autoscaler](https://learn.microsoft.com/azure/aks/cluster-autoscaler)
- [AKS Node Auto-Provisioning](https://learn.microsoft.com/azure/aks/node-auto-provisioning)
- [AKS Spot Node Pools](https://learn.microsoft.com/azure/aks/spot-node-pool)
- [AKS Availability Zones](https://learn.microsoft.com/azure/aks/availability-zones)
- [AKS Monitoring](https://learn.microsoft.com/azure/aks/monitor-aks)
- [Kubernetes Assign Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Kubernetes Topology Spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Terraform AzureRM Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

---

**Chapter 072 complete.** Next: **Chapter 073 — AKS Networking, Ingress, Azure Disk and Azure Files CSI Integration for GitOps**.