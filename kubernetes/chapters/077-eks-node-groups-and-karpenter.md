# Chapter 077 — EKS Node Groups and Karpenter

**Track:** Kubernetes Administration · **Part 16 — Managed Kubernetes on AWS and Azure**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, AWS platform and FinOps engineers  
**Prerequisites:** Chapter 076; scheduling and resource management (Chapters 021–025); AWS CLI v2, kubectl, Windows PowerShell; approved EKS staging cluster; optional Karpenter installation and Helm

## 1. Production scenario

An EKS cluster runs latency-sensitive APIs, PostgreSQL workloads and batch jobs. A nightly ingestion job causes Pods to remain Pending, while existing EC2 nodes are underutilized during daytime. The platform team wants to use EKS managed node groups for stable baseline capacity and Karpenter for workload-driven scaling without triggering unsafe disruptions to databases.

**Mission:** compare provisioning models, design baseline and elastic capacity, configure safe NodePools and EC2NodeClasses, validate scheduling and consolidation, and create incident runbooks for node pressure, Spot interruptions and failed node replacement.

**Safety:** Node provisioning, scale-down, consolidation, eviction, node deletion and cluster IAM changes are mutating operations. Execute only in an approved staging cluster with change authorization, workload ownership and a cost budget.

### Learning outcomes

1. Explain EKS managed node groups, Auto Scaling Groups and Karpenter responsibilities.
2. Distinguish Cluster Autoscaler-style group scaling from Karpenter's direct node provisioning.
3. Inventory node capacity, taints, labels, topology and workload requests.
4. Configure Karpenter NodePools, EC2NodeClasses and NodeClaims.
5. Use On-Demand and Spot safely for different workload classes.
6. Apply disruption budgets, consolidation and graceful termination safeguards.
7. Understand PDBs, `do-not-disrupt`, stateful Pods and topology constraints.
8. Troubleshoot unschedulable Pods, capacity shortages and bootstrap failures.
9. Model node utilization, IP exhaustion, quotas and cloud cost.
10. Validate a controlled staging rollout and rollback strategy.

## 2. Architecture and provisioning models

```text
                         Kubernetes Scheduler
                                 |
                        Unschedulable Pods
                                 |
                    +------------+-------------+
                    |                          |
           EKS managed node group          Karpenter
                    |                          |
          EC2 Auto Scaling Group       NodePool + EC2NodeClass
                    |                          |
             EC2 worker nodes               NodeClaims
                    |                          |
                    +---------- EC2 ----------+
                                 |
                      VPC CNI / EBS / IAM
```

A managed node group creates and manages a set of EC2 worker nodes using an underlying Auto Scaling Group. It supports scaling bounds, managed updates and integration with Kubernetes. **A managed node group does not independently react to every unschedulable Pod** without a separate autoscaling mechanism.

Karpenter watches scheduling demand and creates capacity according to NodePool requirements, limits, disruption policy and EC2NodeClass infrastructure settings. It is not a replacement for the Kubernetes scheduler, and it does not automatically correct invalid resource requests or broken storage topology.

### Comparison

| Concern | Managed node groups | Karpenter |
|---|---|---|
| Provisioning unit | Node group/ASG | NodeClaim backed by EC2 instance |
| Instance flexibility | Defined group types/config | Flexible instance constraints |
| Scale-out trigger | ASG desired capacity or autoscaler | Unschedulable Pod demand |
| Lifecycle | EKS managed updates | Karpenter disruption/expiration and node lifecycle |
| Stable baseline | Excellent fit | Possible with careful policies |
| Spot diversification | Multiple groups or mixed instances | Flexible eligible instance selection |
| Operational risk | Group scaling/update limits | Provisioning and consolidation policy complexity |

Do not run multiple autoscalers against the same ownership domain without an explicit design. Karpenter-provisioned nodes should not be treated as managed-node-group members.

## 3. Lab 1 — Confirm AWS identity and EKS cluster ownership

```powershell
aws --version
kubectl version --client
$profile = 'REPLACE_WITH_APPROVED_AWS_PROFILE'
$region = 'us-east-1'
$cluster = 'REPLACE_WITH_STAGING_EKS_CLUSTER'
aws sts get-caller-identity --profile $profile
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Name:name,Status:status,Version:version,Endpoint:endpoint}' --output table
kubectl config current-context
kubectl get nodes -o wide
```

**Stop if** AWS account, cluster name or kubeconfig context is not the expected staging environment. An AWS CLI profile does not automatically select the same identity as an existing kubeconfig exec credential configuration.

**Expected:** cloud identity, region and Kubernetes context are documented.

## 4. Lab 2 — Inventory managed node groups and node health

```powershell
aws eks list-nodegroups --cluster-name $cluster --region $region --profile $profile
aws eks describe-nodegroup --cluster-name $cluster --nodegroup-name REPLACE_WITH_NODEGROUP --region $region --profile $profile --query 'nodegroup.{Status:status,Scaling:scalingConfig,Capacity:capacityType,InstanceTypes:instanceTypes,Subnets:subnets,Health:health}' --output json
kubectl get nodes -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone,karpenter.sh/nodepool -o wide
kubectl top nodes
kubectl get pods -A -o wide
```

Metrics Server must be available for `kubectl top`.

### Inventory worksheet

```text
Node group:
Min / desired / max:
Instance family and generation:
On-Demand / Spot:
AMI / Kubernetes version:
Subnets and AZs:
Labels / taints:
CPU and memory allocatable:
Requested vs actual CPU/memory:
Pod IP headroom:
EBS attachment limits:
PDB-sensitive workloads:
Current cost owner:
```

**Expected:** distinguish baseline nodes, Karpenter-owned nodes and any legacy self-managed nodes.

## 5. Lab 3 — Diagnose scheduling demand before scaling

```powershell
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe node REPLACE_WITH_NODE
kubectl get resourcequotas -A
kubectl get limitranges -A
kubectl get pdb -A
```

### Pending Pod decision tree

1. Read the actual `FailedScheduling` Event.
2. Check CPU/memory requests against allocatable capacity.
3. Check taints, tolerations, node selectors and affinity.
4. Check topology spread and PVC zone binding.
5. Check namespace quotas and Pod count limits.
6. Check available VPC subnet IPs and CNI configuration.
7. Check Karpenter NodePool requirements and limits.
8. Check EC2 quota, instance availability and IAM.
9. Scale only after identifying the binding constraint.

**Expected:** a documented root cause rather than an indiscriminate increase in node count.

## 6. Lab 4 — Design baseline versus elastic node capacity

### Workload placement

| Workload | Preferred capacity strategy | Why |
|---|---|---|
| CoreDNS, CNI-critical add-ons, Karpenter controller | Reliable baseline nodes | Avoid bootstrap/dependency loops |
| Latency-sensitive API | On-Demand baseline plus elastic headroom | Availability and predictable scheduling |
| Batch processing | Diversified Spot where interruption-tolerant | Lower cost |
| PostgreSQL/MongoDB | Controlled On-Demand placement | Storage and eviction sensitivity |
| GPU inference | Dedicated constraints, quotas and node classes | Hardware-specific scheduling |
| Temporary jobs | Elastic NodePool with limits | Avoid idle baseline spend |

A Karpenter controller needs stable compute. If its only hosting nodes are provisioned by itself and are disrupted, recovery can become difficult. Use managed nodes or another documented reliable hosting strategy.

### Capacity worksheet

```text
Baseline peak requested CPU:
Baseline peak requested memory:
System DaemonSet overhead:
Kube/system reserved resources:
Peak burst requests:
Zone-failure spare capacity:
Spot interruption tolerance:
Max Pod density and IP limits:
NodePool aggregate CPU/memory limits:
Monthly compute budget:
```

**Expected:** capacity design incorporates requests, DaemonSet overhead and failure-domain headroom.

## 7. Lab 5 — Inspect Karpenter installation and API versions

```powershell
kubectl get crds | Select-String 'karpenter'
kubectl get nodepools
kubectl get nodeclaims
kubectl get ec2nodeclasses
kubectl -n kube-system get deployment karpenter
kubectl -n kube-system get pods -l app.kubernetes.io/name=karpenter
```

Karpenter namespace and Helm labels vary by installation. Query the actual namespace if not `kube-system`.

### Installation prerequisites

- Supported EKS/Karpenter/Kubernetes version combination.
- IAM controller role or EKS Pod Identity and node instance profile/role.
- EC2, pricing and interruption event permissions as required.
- Subnet/security group discovery tags and selection.
- SQS interruption queue/event integration where configured.
- Node bootstrap and AMI family compatibility.
- CoreDNS/CNI and network access to AWS APIs.
- Capacity and spending limits.

**Expected:** Karpenter CRDs and controller are healthy before any NodePool is applied.

## 8. Lab 6 — Define an EC2NodeClass

**Staging-only template.** Save `ch077-ec2nodeclass.yaml`:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: ch077-general
spec:
  amiSelectorTerms:
    - alias: al2023@REPLACE_WITH_APPROVED_VERSION
  role: REPLACE_WITH_KARPENTER_NODE_IAM_ROLE_NAME
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: REPLACE_WITH_CLUSTER_DISCOVERY_TAG
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: REPLACE_WITH_CLUSTER_DISCOVERY_TAG
  tags:
    environment: staging
    owner: platform-team
```

This is a **version-specific design template**. Verify the installed Karpenter API schema, supported AMI alias, role/instance-profile model and discovery tags. A pinned AMI alias is preferable for reviewed rollout reproducibility; a floating `@latest` can change unexpectedly.

```powershell
kubectl explain ec2nodeclass.spec --api-version=karpenter.k8s.aws/v1
kubectl apply --dry-run=server -f .\ch077-ec2nodeclass.yaml
```

The dry run requires the CRD to be installed and placeholders replaced. It does not validate all AWS resource permissions or prove nodes can launch.

## 9. Lab 7 — Define a bounded NodePool

Save `ch077-nodepool.yaml`:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ch077-general
spec:
  template:
    metadata:
      labels:
        workload-tier: elastic
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: ch077-general
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["4"]
  limits:
    cpu: "32"
    memory: 128Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
```

The `limits` constrain aggregate NodePool provisioning, not individual Pod resource usage. NodePool limit enforcement can be eventually consistent during rapid scale-out; use AWS quotas and budget alarms as additional safeguards.

```powershell
kubectl apply --dry-run=server -f .\ch077-nodepool.yaml
kubectl get nodepools -o yaml
```

**Expected:** after approved configuration, the NodePool is valid and has bounded capacity and conservative disruption controls. Do not apply for real until cost and eviction behavior are reviewed.

## 10. Lab 8 — Generate controlled scheduling demand

**Approved staging only.** Save `ch077-workload.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch077
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elastic-demo
  namespace: ch077
spec:
  replicas: 3
  selector:
    matchLabels:
      app: elastic-demo
  template:
    metadata:
      labels:
        app: elastic-demo
    spec:
      nodeSelector:
        workload-tier: elastic
      terminationGracePeriodSeconds: 30
      containers:
        - name: web
          image: nginx:stable
          resources:
            requests:
              cpu: 250m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          ports:
            - containerPort: 80
```

```powershell
kubectl apply -f .\ch077-workload.yaml
kubectl -n ch077 get pods -o wide
kubectl get nodeclaims
kubectl get nodes -L karpenter.sh/nodepool,karpenter.sh/capacity-type
kubectl -n ch077 rollout status deployment/elastic-demo --timeout=300s
```

If the Pod selector matches an existing node, Karpenter may not create a new NodeClaim. This is expected: Karpenter provisions for unschedulable demand, not for every Deployment.

**Expected:** Pods schedule on compatible capacity; any new NodeClaims, launch delays and costs are recorded.

## 11. Lab 9 — Disruption budgets, consolidation and graceful termination

Karpenter may consolidate or replace nodes when doing so is permitted by its policies. Kubernetes PodDisruptionBudgets and workload termination behavior affect voluntary evictions.

```powershell
kubectl get pdb -A
kubectl get nodepools -o yaml
kubectl get nodeclaims -o wide
kubectl get nodes -L karpenter.sh/nodepool
kubectl -n ch077 describe deployment elastic-demo
```

### Safe disruption policy

- Use PDBs to protect minimum availability.
- Configure `terminationGracePeriodSeconds` for graceful shutdown.
- Review Karpenter NodePool disruption budgets.
- Use `karpenter.sh/do-not-disrupt` only with clear ownership and lifecycle plan.
- Avoid consolidation experiments on database primaries or quorum-sensitive workloads.
- Understand that some forceful interruption/expiration or node-failure paths may not honor normal voluntary-disruption protections.
- Observe replacement readiness before approving node removal.

**Expected:** disruption policy protects availability while permitting maintenance; do not assume a PDB guarantees safety against every failure mode.

## 12. Lab 10 — Spot interruption and capacity shortage tabletop

**Scenario:** a batch NodePool uses Spot instances and a capacity interruption occurs during a large ingestion job.

### Response sequence

1. Confirm interruption signal and affected NodeClaims.
2. Check queue/job retry and idempotency behavior.
3. Validate graceful termination and checkpointing.
4. Check Karpenter interruption-handling configuration.
5. Ensure multiple eligible instance families/sizes and AZs.
6. Evaluate On-Demand fallback policy for critical work.
7. Monitor provisioning latency and Pending Pods.
8. Record interrupted jobs, replay and cost impact.

### Design comparison

| Workload | Spot recommendation |
|---|---|
| Stateless idempotent batch | Often appropriate |
| Queue consumers with checkpointing | Appropriate with careful termination |
| Latency-sensitive serving | Limited/controlled use |
| Database primary or quorum member | Usually prefer stable On-Demand |
| GPU batch inference | Depends on checkpoint and capacity availability |

**Expected:** an interruption response that prioritizes data correctness and recovery over immediate cost savings.

## 13. Lab 11 — Managed node group upgrade and safe replacement

EKS managed node group updates can replace worker nodes. Plan PodDisruptionBudgets, capacity headroom, zone constraints and workload termination before an update.

```powershell
aws eks describe-nodegroup --cluster-name $cluster --nodegroup-name REPLACE_WITH_NODEGROUP --region $region --profile $profile --query 'nodegroup.{Status:status,Version:version,ReleaseVersion:releaseVersion,UpdateConfig:updateConfig,Health:health}' --output json
aws eks list-updates --name $cluster --nodegroup-name REPLACE_WITH_NODEGROUP --region $region --profile $profile
kubectl get pdb -A
kubectl get pods -A -o wide
```

### Maintenance gate

1. Validate control-plane and node Kubernetes version skew.
2. Confirm add-on/AMI compatibility.
3. Verify PDBs and graceful shutdown behavior.
4. Check spare capacity and EC2 quotas.
5. Schedule a maintenance window for stateful workloads.
6. Update one capacity domain at a time where feasible.
7. Validate application SLIs and storage attachment after replacement.
8. Preserve rollback strategy; node AMI downgrades may require replacement with a prior approved configuration.

**Expected:** reviewed update plan; no production node group update is performed by this tutorial.

## 14. Lab 12 — Capacity and cost acceptance project

### Capacity metrics

```powershell
kubectl top nodes
kubectl top pods -A
kubectl get nodes -o wide
kubectl get nodeclaims -o wide
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

### Cost model

```text
Baseline On-Demand node hours:
Elastic On-Demand node hours:
Spot node hours and interruptions:
EC2 family/generation:
Savings Plans / Reserved Instance applicability:
EBS volume and snapshot costs:
NAT/data transfer costs:
Karpenter consolidation savings estimate:
Peak burst capacity:
Monthly budget and owner:
```

Savings Plans and Reserved Instance applicability depends on the organization's billing arrangements. Do not present Spot savings as guaranteed; prices and availability change.

### Acceptance gates

- Pending Pods resolve for expected workloads.
- NodePool limits and instance constraints are respected.
- Core add-ons remain on reliable capacity.
- PDBs and disruption controls are reviewed.
- Spot interruption recovery is documented.
- Node group upgrade plan is approved.
- Cost budget and cloud quotas are enforced.
- No data integrity regression or dual-writer incident is introduced.

## 15. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Karpenter controller unavailable | Baseline nodes, IAM, image or network | Controller Pod/Events |
| No NodeClaim for Pending Pod | Constraints, requests, quotas | Pod Events, NodePool status |
| NodeClaim launched but node absent | Bootstrap, IAM, networking | NodeClaim conditions, EC2 logs |
| Node NotReady | CNI, kubelet, DNS, security groups | Node conditions and CNI |
| NodePool not Ready | EC2NodeClass unresolved | NodePool/NodeClass conditions |
| Pods Pending despite nodes | Taints, affinity, topology, PVC | Scheduler Events |
| EC2 capacity unavailable | Spot/instance type/AZ scarcity | Broaden safe constraints |
| High churn | Aggressive consolidation/expiration | Disruption policies and events |
| Database eviction blocked | PDB or do-not-disrupt | PDB status and workload policy |
| Cost spike | Excess scale-out, oversized requests | NodeClaims, Cost Explorer |
| Managed node update stalls | PDB, capacity, node health | EKS update details and Events |

## 16. Production operations runbook

### Diagnose

1. Confirm workload impact and Pending Pods.
2. Inspect scheduler Events and requests.
3. Identify node ownership: managed node group or Karpenter.
4. Inspect NodePool/NodeClaim or ASG/node group health.
5. Verify IAM, subnet IPs, EC2 quotas and instance availability.
6. Check PDBs, topology and stateful storage constraints.

### Remediate

1. Prefer correcting invalid requests/constraints before scaling.
2. Expand capacity only within approved budget and limits.
3. Adjust NodePool requirements with reviewed impact.
4. Avoid disruptive consolidation of critical stateful Pods.
5. Validate replacement nodes and application SLIs.
6. Record cost and capacity effects.

### Prevent

1. Set alerts on Pending Pods and provisioning latency.
2. Monitor subnet IPs, EC2 quotas and node health.
3. Review PDBs and termination behavior.
4. Keep core components on stable baseline capacity.
5. Run scheduled cost and consolidation reviews.
6. Test Spot interruption and AZ failure tabletop scenarios.

## 17. Cleanup and safeguards

**Staging only.** Review all lab-owned NodeClaims and cloud instances before removing test workloads.

```powershell
kubectl -n ch077 get deployments,pods
kubectl get nodeclaims
kubectl delete namespace ch077
```

Do not delete shared NodePools, EC2NodeClasses, managed node groups, IAM roles or production EC2 instances as tutorial cleanup. A lab-only NodePool/NodeClass can be decommissioned only after confirming no other workloads depend on it and reviewing disruption/cost consequences.

## 18. Acceptance checklist

- [ ] AWS account, region and staging context verified.
- [ ] Managed node group inventory and scaling bounds captured.
- [ ] Scheduling constraints and Pod resource requests analyzed.
- [ ] Stable baseline and elastic capacity design documented.
- [ ] Karpenter installation/version and controller health checked.
- [ ] EC2NodeClass schema, IAM and subnet discovery reviewed.
- [ ] NodePool instance constraints, limits and budgets reviewed.
- [ ] Staging scheduling test executed or marked Not run.
- [ ] PDB, consolidation and graceful termination controls reviewed.
- [ ] Spot interruption tabletop completed.
- [ ] Managed node group upgrade safety plan documented.
- [ ] Capacity/cost acceptance report completed.
- [ ] Troubleshooting and rollback runbooks reviewed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 19. References

- [EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter NodeClaims](https://karpenter.sh/docs/concepts/nodeclaims/)
- [Karpenter EC2NodeClasses](https://karpenter.sh/docs/concepts/nodeclasses/)
- [Karpenter Disruption](https://karpenter.sh/docs/concepts/disruption/)
- [EKS Best Practices — Autoscaling](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)

**Next:** Chapter 078 — EKS Networking, Load Balancers and Storage.
