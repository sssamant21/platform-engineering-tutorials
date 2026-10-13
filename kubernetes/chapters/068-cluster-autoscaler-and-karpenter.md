# Chapter 068 — Cluster Autoscaler and Karpenter

**Track:** Kubernetes Administration · **Part 14 — Autoscaling and Capacity Management**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, cloud and platform engineers  
**Prerequisites:** Chapters 021–025 and 066–067; kubectl; Windows PowerShell; EKS/AKS access; approved staging cluster for optional exercises

## 1. Production scenario

A customer-facing API's HPA increases its desired replica count from 6 to 18 during a traffic spike. Eight replacement Pods remain Pending with `FailedScheduling: Insufficient cpu`. The cluster has a node autoscaler, but no eligible nodes are provisioned. Investigation reveals a combination of node-group maximum size, subnet IP exhaustion, and strict topology constraints.

**Goal:** distinguish Kubernetes scheduling from node provisioning, compare Cluster Autoscaler and Karpenter, troubleshoot provisioning failures, and design safe scale-up/scale-down policies that preserve application availability and stateful workload safety.

### Learning objectives

1. Explain node autoscaling architecture and scheduler integration.
2. Compare Cluster Autoscaler (CA) and Karpenter provisioning models.
3. Diagnose unschedulable Pods, node-group limits, cloud quotas and subnet/IP constraints.
4. Understand NodePools, EC2NodeClasses, NodeClaims and disruption controls in Karpenter.
5. Investigate CA expander decisions, scale-up failures and unneeded-node handling.
6. Design node consolidation, drift and disruption safeguards.
7. Connect HPA/VPA resource requests with node capacity and cloud cost.
8. Apply EKS/AKS-specific diagnostics and a production incident runbook.

## 2. Node autoscaling architecture

```text
Traffic / workload demand
          |
         HPA
          |
  Desired replicas increase
          |
  Scheduler tries to place Pods
          |
  Unschedulable Pending Pods
          |
  +----------------------------+
  |                            |
Cluster Autoscaler         Karpenter
  |                            |
Node group / ASG           NodePool / NodeClaim
scale decisions            instance provisioning
  |                            |
Cloud instances and Kubernetes nodes
          |
Scheduler places Pending Pods
          |
Pods start -> Ready -> serve traffic
```

**Key principle:** HPA adjusts Pod replica counts; node autoscaling adjusts eligible node capacity. Neither guarantees that applications become Ready or that downstream databases can handle the increased concurrency.

## 3. Cluster Autoscaler versus Karpenter

| Dimension | Cluster Autoscaler | Karpenter |
|---|---|---|
| Primary provisioning unit | Configured node groups / autoscaling groups | Dynamic NodeClaims from NodePools |
| Instance selection | Typically node-group-defined templates | Flexible instance type/zone/capacity selection |
| Scaling trigger | Unschedulable Pods and group simulation | Unschedulable Pods and scheduling/provisioning simulation |
| Scale-down | Removes unneeded nodes subject to safety rules | Consolidation, drift and disruption policies |
| Cloud support | Multiple providers including AWS/Azure | Karpenter provider ecosystem; AWS-focused examples here |
| Key constraints | Node-group bounds, templates, expander | NodePool requirements, limits, NodeClass, cloud capacity |
| Operational risks | Fragmented node groups, slow provisioning | Overbroad provisioning or disruptive consolidation |

**Avoid blanket claims:** performance and cost differences depend on workload, instance availability, version, topology and configuration. Karpenter is not a drop-in replacement for every managed node pool or every cloud environment.

## 4. Lab 1 — Establish cluster autoscaler inventory

```powershell
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl -n kube-system get deployments
kubectl get crd nodepools.karpenter.sh
kubectl get crd nodeclaims.karpenter.sh
Get-Date -Format o
```

**Expected:** identify whether CA, Karpenter, a cloud-managed autoscaler or multiple mechanisms are present. A missing CRD is not proof that the cluster lacks all node autoscaling.

### Ownership inventory

```text
Cluster:
Cloud / region:
Autoscaler(s):
CA node groups:
Karpenter NodePools:
Managed node pools:
Min/max limits:
Zones/subnets:
Node provisioning identity:
Responsible platform team:
```

## 5. Lab 2 — Diagnose unschedulable Pending Pods

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$pod = 'REPLACE_WITH_PENDING_POD'
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns get events --sort-by=.lastTimestamp
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl -n $ns get resourcequota,limitrange,pvc
```

### Scheduler reason matrix

| Event clue | Investigation |
|---|---|
| Insufficient cpu | Requests versus node allocatable; node capacity |
| Insufficient memory | Requests, allocatable and resource pressure |
| Untolerated taint | Node taints and Pod tolerations |
| Node affinity mismatch | Labels, selectors, eligible pools |
| Topology spread constraints | Zone/skew and `whenUnsatisfiable` |
| PVC node affinity conflict | PV zone/topology |
| Max Pods/IP exhaustion | CNI/IPAM, subnet capacity, ENI limits |
| No matching instance type | NodePool/NodeClass constraints, resource sizes |

**Expected:** distinguish a genuinely capacity-constrained Pod from a Pod that no node type can satisfy due to incompatible constraints.

## 6. Lab 3 — Cluster Autoscaler architecture and diagnostics

Cluster Autoscaler commonly runs as a Deployment and integrates with cloud node groups.

```powershell
kubectl -n kube-system get deployments | Select-String -Pattern 'cluster-autoscaler'
kubectl -n kube-system get pods | Select-String -Pattern 'cluster-autoscaler'
kubectl -n kube-system get configmap cluster-autoscaler-status -o yaml
kubectl get events -A --sort-by=.lastTimestamp
```

If the CA Deployment exists, inspect its actual name and logs:

```powershell
kubectl -n kube-system logs deployment/cluster-autoscaler --since=30m --tail=300
```

Deployment/configmap names vary by installation. Adjust to discovered names and RBAC.

### CA investigation checklist

1. Are Pending Pods truly unschedulable and eligible for scale-up?
2. Is the node group already at its maximum?
3. Does the node-group template satisfy Pod selector/taints/topology?
4. Are cloud quotas, launch permissions and instance capacity available?
5. Does the expander select a compatible group?
6. Are provisioning and node registration succeeding?
7. Are new nodes Ready with working CNI, DNS and image pulls?

**Expected:** isolate CA decision failure from cloud launch failure and node bootstrap failure.

## 7. Lab 4 — Karpenter resources and provisioning flow

Karpenter's AWS provider commonly uses:

- `NodePool`: scheduling requirements, limits, disruption policy.
- `EC2NodeClass`: AWS-specific subnets, security groups, AMI and instance profile/role settings.
- `NodeClaim`: concrete node provisioning request and lifecycle.

```powershell
kubectl get nodepools
kubectl get ec2nodeclasses
kubectl get nodeclaims -o wide
kubectl get nodes -L karpenter.sh/nodepool,topology.kubernetes.io/zone -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** correlate unschedulable Pods with NodePool selection, NodeClaim creation and node registration. CRD names and supported fields depend on Karpenter release; verify installed schemas before applying manifests.

## 8. Lab 5 — Review an illustrative Karpenter NodePool

**Design-only example. Do not apply to production without validating installed Karpenter version, NodeClass and cloud constraints.**

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: general-purpose
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m6i.large", "m6i.xlarge", "m7i.large"]
  limits:
    cpu: "100"
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

### Design considerations

- NodeClass must match subnet, security group, AMI and IAM configuration.
- Instance availability varies by region and zone.
- Restrictive instance lists reduce provisioning flexibility.
- NodePool limits bound total provisioned resources, not application SLOs.
- Consolidation policies and API fields are version-sensitive.
- NodePool requirements must align with Pod affinity, tolerations and topology.

## 9. Lab 6 — Diagnose Karpenter provisioning failures

```powershell
kubectl get nodepools -o yaml
kubectl get nodeclaims -o wide
kubectl describe nodepool REPLACE_WITH_NODEPOOL
kubectl get events -A --sort-by=.lastTimestamp
kubectl -n kube-system get deployments | Select-String -Pattern 'karpenter'
```

Karpenter may be installed in a dedicated namespace; discover its actual Deployment before collecting logs.

### Failure matrix

| Symptom | Potential cause | Evidence |
|---|---|---|
| No NodeClaim created | NodePool mismatch/limits | NodePool conditions, controller logs |
| NodeClaim created but not launched | IAM, EC2 quota, instance capacity | NodeClaim status, cloud events |
| Instance launched but node absent | Bootstrap, networking, kubelet | Cloud logs, NodeClaim conditions |
| Node joins but NotReady | CNI, runtime, certificates | Node conditions, kube-system Pods |
| Pods remain Pending | Affinity, PVC topology, requests | Scheduler Events |
| Excessive nodes | Overbroad pools, workload churn | NodeClaims, consolidation metrics |

**Expected:** identify the failing stage rather than restarting Karpenter indiscriminately.

## 10. Lab 7 — Optional staging Pending Pod exercise

**Staging only.** This lab intentionally creates an unschedulable Pod using a non-existent selector; it tests diagnosis, **not successful autoscaler provisioning**.

Save `ch068-pending.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch068
---
apiVersion: v1
kind: Pod
metadata:
  name: unschedulable-demo
  namespace: ch068
spec:
  restartPolicy: Never
  nodeSelector:
    ch068.example.com/nonexistent: "required"
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "sleep 300"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
```

```powershell
kubectl apply -f .\ch068-pending.yaml
kubectl -n ch068 get pod unschedulable-demo -o wide
kubectl -n ch068 describe pod unschedulable-demo
kubectl -n ch068 get events --sort-by=.lastTimestamp
```

**Expected:** Pending/FailedScheduling due to selector mismatch. A correctly configured autoscaler should not be expected to provision a node with an arbitrary unsupported label. For a true scale-up acceptance test, use a pre-approved NodePool/node-group label and a bounded workload request in a dedicated test cluster.

## 11. Lab 8 — Scale-down, consolidation and disruption safety

### Cluster Autoscaler scale-down

CA identifies underutilized/unneeded nodes and evaluates whether their Pods can be safely moved. Scale-down can be blocked by Pod placement constraints, disruption rules, system workloads or configured CA policies.

### Karpenter consolidation and drift

Karpenter may replace or remove nodes for consolidation or configuration drift, subject to NodePool disruption budgets, Pod disruption rules and installed-version behavior.

### Stateful safety checklist

1. Check PDBs and actual application quorum.
2. Check StatefulSet storage class, volume zone and attach/detach behavior.
3. Confirm leader/follower roles, replication lag and failover.
4. Validate terminationGracePeriodSeconds and shutdown hooks.
5. Review `karpenter.sh/do-not-disrupt` use where supported and approved.
6. Ensure capacity exists for replacement Pods before disruption.
7. Avoid simultaneous disruption across availability zones.

**Important:** a PDB alone does not guarantee database consistency or quorum safety. Apply database-specific safeguards.

## 12. Lab 9 — EKS versus AKS autoscaling operations

| Dimension | EKS | AKS |
|---|---|---|
| Common node autoscaling | Cluster Autoscaler / managed node groups; Karpenter on AWS | AKS cluster autoscaler / node pools |
| Cloud provisioning | EC2 / Auto Scaling | VM Scale Sets |
| IP constraints | VPC CNI, ENIs, subnet IPs | Azure CNI/overlay and subnet capacity |
| IAM/identity | IAM roles and policies | Managed identities/RBAC |
| Instance capacity | EC2 types, AZs, quotas | VM SKUs, zones, quotas |
| Karpenter examples | AWS EC2NodeClass | Not an AKS default replacement |

Do not apply AWS Karpenter manifests to AKS. For AKS, focus on managed node pool autoscaling and Azure-specific provisioning diagnostics.

## 13. Lab 10 — Capacity and cost modeling

Assume 12 Pending Pods each request 500m CPU and 1 GiB memory. Existing nodes have no schedulable headroom.

```text
Additional Pod requests:
CPU = 12 × 0.5 = 6 vCPU
Memory = 12 × 1 GiB = 12 GiB
```

A candidate node type has 4 vCPU and 16 GiB RAM, but allocatable is lower after system reservations.

### Capacity planning steps

1. Use **allocatable**, not advertised instance capacity.
2. Include DaemonSet overhead and per-node Pod count limits.
3. Consider CPU/memory fragmentation and topology.
4. Include network/IP and volume attachment limits.
5. Plan for rollout surge and failure-zone headroom.
6. Compare On-Demand/Spot interruption risk and workload tolerance.
7. Measure actual instance cost and provisioning time.

**Expected:** a node plan that fits all requests and constraints, not merely aggregate CPU totals.

## 14. Lab 11 — Production incident tabletop

**Scenario:** HPA scales an API from 8 to 24 replicas. Ten Pods remain Pending. CA is at node-group maximum, Karpenter NodeClaims are blocked by EC2 quota, and PostgreSQL connection utilization is already 85%.

### Investigation tasks

1. Confirm desired, current and Ready replicas.
2. Inspect FailedScheduling reasons and eligible node pools.
3. Review CA maximum size and Karpenter NodeClaim failures.
4. Check subnet IPs, cloud quotas and zone capacity.
5. Calculate DB connection budget at 24 replicas.
6. Decide whether adding nodes will improve or worsen customer SLIs.
7. Choose a bounded mitigation with approver and rollback.
8. Verify node provisioning, Pod readiness and database health.
9. Document capacity, autoscaler and dependency preventive controls.

**Expected:** recognize that node provisioning alone may not resolve a downstream bottleneck.

## 15. Production troubleshooting runbook

### Detect

- Pending Pods with FailedScheduling.
- Desired replicas above Ready replicas.
- Node autoscaler scale-up failure or NodeClaim provisioning errors.
- Node capacity, subnet/IP, cloud quota or instance availability alerts.

### Diagnose

1. Capture cluster context, namespace, node groups/NodePools and timestamps.
2. Inspect scheduler Events and Pod placement constraints.
3. Confirm autoscaler ownership and configuration.
4. Review CA logs or Karpenter NodeClaims/controller logs.
5. Validate cloud launch, bootstrap and CNI readiness.
6. Evaluate stateful disruption and downstream capacity.

### Mitigate

1. Correct confirmed configuration/capacity constraints through approved changes.
2. Avoid unreviewed max-limit increases and expensive instance provisioning.
3. Preserve PDBs, quorum and volume topology.
4. Apply rate limiting/load shedding if application or DB cannot scale safely.
5. Document rollback and cost impact.

### Verify

- New nodes become Ready and register correctly.
- Pending Pods schedule and become Ready.
- Customer latency/error rate returns to SLO.
- Database and queue dependencies remain healthy.
- Autoscaler stops unexpected provisioning and consolidation churn.

## 16. Operational observability

### Kubernetes metrics examples

```promql
sum by (namespace) (kube_pod_status_phase{phase="Pending"} == 1)
```

```promql
sum by (node) (kube_node_status_condition{condition="Ready",status="true"} == 1)
```

```promql
sum(kube_node_status_allocatable{resource="cpu",unit="core"})
```

Metric names/labels and availability depend on kube-state-metrics version. Combine with cloud autoscaler/Karpenter metrics, instance launch errors and billing dashboards.

### Alert priorities

- Sustained Pending Pods due to insufficient capacity.
- Node-group/NodePool maximum reached.
- Cloud quota or subnet IP exhaustion.
- NodeClaims stuck in provisioning.
- Unhealthy node registration.
- Excessive consolidation or disruption.
- Rapid cloud spend increase.

## 17. Acceptance checklist

- [ ] CA and Karpenter architecture compared accurately.
- [ ] Autoscaler ownership inventoried for the cluster.
- [ ] Pending Pod scheduler Events classified.
- [ ] CA node-group bounds and logs reviewed.
- [ ] Karpenter NodePools, NodeClasses and NodeClaims inspected.
- [ ] Cloud quota, subnet IP and instance availability failure paths reviewed.
- [ ] Isolated staging Pending exercise completed or marked not run.
- [ ] Consolidation, PDB and stateful quorum safety assessed.
- [ ] EKS and AKS differences documented.
- [ ] Capacity/cost model calculated using allocatable resources.
- [ ] Incident tabletop and runbook acceptance completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 18. Cleanup

Delete only the isolated training namespace:

```powershell
kubectl -n ch068 get pods
kubectl delete namespace ch068
```

Do not delete CA, Karpenter, NodePools, NodeClaims or production nodes as part of training cleanup.

**Status:** Draft — runtime validation and technical review pending.

## 19. References

- [Cluster Autoscaler (Kubernetes Autoscaler repository)](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter NodeClaims](https://karpenter.sh/docs/concepts/nodeclaims/)
- [Karpenter Disruption](https://karpenter.sh/docs/concepts/disruption/)
- [Kubernetes Scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Kubernetes Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

**Next:** Chapter 069 — CPU, Memory, Network and Storage Capacity Planning.
