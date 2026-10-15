# Chapter 067 — EKS Managed Node Groups, Karpenter and Production Capacity Automation

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 14:** Amazon EKS  
**Chapter:** 067 / 100  
**Audience:** Platform Engineers, SREs, Cloud Engineers, Kubernetes Administrators and FinOps

> **Safety:** Use a dedicated staging EKS cluster. Node termination, Spot interruption, consolidation and scaling tests can disrupt applications and incur costs. Never apply disruption exercises to production, critical system pools, stateful data stores or shared clusters without a reviewed change and tested recovery path.

## 1. Learning objectives

By completing this chapter you will:

1. Compare EKS managed node groups, Karpenter and Cluster Autoscaler.
2. Design safe bootstrap and application capacity separation.
3. Configure Karpenter NodePools, EC2NodeClasses and NodeClaims.
4. Manage Spot/On-Demand mix, topology, taints and resource reservations.
5. Understand Karpenter consolidation, drift, expiration and disruption budgets.
6. Prevent autoscaler conflicts and stranded workloads.
7. Diagnose pending Pods, insufficient IPs, EC2 capacity errors and node churn.
8. Integrate capacity automation with GitOps, GitLab and production observability.
9. Conduct scaling, failure, recovery and FinOps acceptance labs.

## 2. Reference architecture

~~~text
GitLab CI -> protected GitOps MR -> Argo CD
                                    |
                           Karpenter Helm/CRDs
                                    |
                     EC2NodeClass + NodePools
                                    |
Pending Pod -> scheduler -> Karpenter controller
                                    |
                       AWS EC2 / IAM / subnets
                                    |
                              NodeClaim
                                    |
                          EC2 worker node
                                    |
                        Pod scheduling and health

Parallel foundation:
EKS managed node group -> CoreDNS, VPC CNI, Karpenter controller,
                          Argo CD, observability and critical add-ons
~~~

**Critical bootstrap rule:** the Karpenter controller needs reliable compute before it can provision Karpenter-managed nodes. Keep a managed node group or other explicitly supported bootstrap capacity independent of Karpenter itself.

## 3. Capacity technology comparison

| Capability | EKS managed node group | Cluster Autoscaler | Karpenter |
| --- | --- | --- | --- |
| Primary object | AWS managed node group | Existing node groups | NodePool + EC2NodeClass |
| Provisioning | Desired size/ASG | Adjusts group size | Provisions suitable EC2 capacity |
| Instance selection | Configured group types | Group template | Flexible requirements |
| Consolidation | Not native workload-driven consolidation | Scale-down behavior | Policy-driven consolidation |
| Bootstrap role | Strong fit | Needs existing node groups | Needs independent controller capacity |
| GitOps surface | Terraform/IaC | Helm and ASG tags | Helm, NodePools, EC2NodeClasses |

Karpenter and Cluster Autoscaler should not independently control the **same** node capacity. A deliberate coexistence model may use Cluster Autoscaler for separate managed groups and Karpenter for its own NodePools, with clear ownership.

## 4. Capacity SLOs and requirements

Define:

- Pod scheduling latency target.
- Minimum On-Demand baseline for critical services.
- Spot interruption tolerance and fallback.
- Availability-zone diversity and capacity reservations.
- CPU/memory/ephemeral-storage headroom.
- DaemonSet overhead and kubelet/system reservations.
- Maximum node count and monthly spend.
- PodDisruptionBudget and workload graceful shutdown.
- Node provisioning time, drift remediation and rollout recovery.
- Instance family, generation and architecture compatibility.

Autoscaling cannot compensate for incorrect Pod resource requests, missing subnet IPs or incompatible affinity rules.

## 5. Prerequisites

- Existing healthy EKS staging cluster from Chapter 066.
- Approved EKS and Karpenter compatibility matrix.
- Terraform-managed VPC, IAM, security groups and bootstrap node group.
- Approved IAM roles for Karpenter controller and provisioned nodes.
- Karpenter Helm chart and CRDs pinned to tested versions.
- Argo CD with scoped platform AppProject.
- Prometheus/Grafana or approved CloudWatch observability.
- AWS quotas and EC2 Spot/On-Demand capacity limits reviewed.

~~~bash
aws sts get-caller-identity
aws eks describe-cluster --name demo-eks-staging --region us-east-1
kubectl get nodes -o wide
kubectl -n kube-system get pods
helm version
~~~

Stop if the AWS account, cluster context or ownership of node groups is unclear.

## 6. Bootstrap managed node group

Use a small, highly available managed node group for platform-critical controllers. Spread nodes across approved AZs and use On-Demand capacity where appropriate.

Illustrative Terraform module fragment:

~~~hcl
eks_managed_node_groups = {
  system = {
    instance_types = ["m6i.large"]
    capacity_type  = "ON_DEMAND"
    min_size       = 2
    max_size       = 5
    desired_size   = 3

    labels = {
      "node-role" = "system"
    }
  }
}
~~~

This fragment assumes a compatible terraform-aws-eks module configuration. Pin and verify module versions and inputs. System nodes should have sufficient CPU/memory for CoreDNS, Karpenter, Argo CD, monitoring and rolling upgrades. If taints are used, add compatible tolerations for essential components.

## 7. Karpenter installation architecture

The Karpenter controller typically needs:

- IAM permissions for approved EC2 instance provisioning and lifecycle operations.
- A supported workload identity (IRSA or EKS Pod Identity).
- Node IAM role/instance profile configuration.
- Tagged subnets and security groups for discovery.
- Cluster endpoint and AWS API connectivity.
- Event interruption handling, commonly via SQS and EventBridge.
- Compatible VPC CNI and DNS.
- Node bootstrap user data compatible with the selected AMI family.
- Karpenter CRDs and controller chart deployed in the correct order.

Do not use broad wildcard EC2 permissions without the documented resource/tag conditions. Prefer an approved upstream reference IAM policy adapted and reviewed for your environment.

## 8. Karpenter controller Helm installation

Example Helm commands; replace versions and identity values with approved pinned values:

~~~bash
helm repo add karpenter https://charts.karpenter.sh
helm repo update
~~~

**Important:** the command above illustrates repository discovery only; current Karpenter releases may be distributed through OCI registries rather than that legacy chart repository. Use the official installation guide for the pinned release and pull from its supported OCI chart source. Install CRDs and controller in the prescribed sequence.

Illustrative modern OCI installation pattern:

~~~bash
helm upgrade --install karpenter   oci://public.ecr.aws/karpenter/karpenter   --version APPROVED_KARPENTER_VERSION   --namespace kube-system   --set settings.clusterName=demo-eks-staging   --set settings.interruptionQueue=demo-eks-staging-karpenter   --wait
~~~

The command is incomplete without the controller IAM identity, chart-version-specific settings and node role configuration. Validate the exact Helm values schema before use. The controller must run on reliable bootstrap capacity.

## 9. EC2NodeClass example

Karpenter's EC2NodeClass defines AWS-specific launch configuration. Example for an approved AL2023-based setup:

~~~yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: staging-general
spec:
  role: KarpenterNodeRole-demo-eks-staging
  amiSelectorTerms:
    - alias: al2023@REPLACE_WITH_APPROVED_AMI_VERSION
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: demo-eks-staging
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: demo-eks-staging
  tags:
    Environment: staging
    ManagedBy: karpenter
    Owner: platform
~~~

The AMI alias is intentionally a placeholder. Use a tested pinned AMI alias or explicit approved AMI selector for the installed Karpenter version; avoid unreviewed moving aliases in production. Subnet and security-group discovery tags must match actual AWS resources.

**Compatibility:** EC2NodeClass and NodePool API versions, fields and defaults depend on Karpenter release. Validate CRDs before applying.

## 10. NodePool example

~~~yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: staging-general
spec:
  template:
    metadata:
      labels:
        workload-tier: general
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: staging-general
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["4"]
      expireAfter: 720h
  limits:
    cpu: "100"
    memory: 400Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      - nodes: "10%"
~~~

**Warning:** a 10% disruption budget may be too permissive or too restrictive depending on node count, PodDisruptionBudgets and workload criticality. Start with conservative staging tests and validate actual controller behavior. Some NodePool fields are immutable or version-dependent; inspect current CRD documentation before rollout.

## 11. NodeClaims and ownership

Karpenter creates NodeClaims representing requested capacity. Operators generally manage NodePools and EC2NodeClasses declaratively and observe NodeClaims; avoid manually editing NodeClaims unless following an approved recovery procedure.

~~~bash
kubectl get nodepools
kubectl get ec2nodeclasses
kubectl get nodeclaims
kubectl describe nodepool staging-general
kubectl describe ec2nodeclass staging-general
~~~

## 12. Spot versus On-Demand strategy

| Workload | Suggested default | Rationale |
| --- | --- | --- |
| Critical controllers | On-Demand | Avoid interruption feedback loops |
| Latency-sensitive API | On-Demand baseline + optional Spot | Preserve service floor |
| Stateless batch | Spot preferred with fallback | Cost reduction |
| Fault-tolerant workers | Mixed | Retry/checkpoint capability |
| Stateful databases | Dedicated carefully reviewed nodes | Storage, quorum and disruption risk |

Spot availability is not guaranteed. Use diverse instance types and AZs, interruption handling and application-level retries. Do not promise fixed savings percentages.

## 13. Scheduling and topology

Pod requests, affinity, topology spread, taints and tolerations determine whether Karpenter can create a feasible node.

~~~yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scale-demo
  namespace: demo-staging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scale-demo
  template:
    metadata:
      labels:
        app: scale-demo
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: scale-demo
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_DIGEST
          resources:
            requests:
              cpu: "500m"
              memory: 512Mi
            limits:
              memory: 1Gi
~~~

This image digest is a placeholder. Hard zone constraints can cause Pods to remain Pending when EC2 capacity is unavailable in one AZ; choose strict versus preferred spread intentionally.

## 14. Capacity limits and safety rails

Use NodePool CPU/memory limits, AWS quotas, budget alarms, controlled instance families and tagging. Karpenter limits are not a real-time financial hard cap; concurrent provisioning may temporarily exceed intended capacity limits.

Set appropriate per-workload ResourceQuotas and LimitRanges, and restrict who can edit NodePools or launch broad instance categories.

## 15. Consolidation, drift and disruption

Karpenter may voluntarily replace or remove nodes due to:

- Empty-node consolidation.
- Underutilized-node consolidation.
- Node expiration.
- NodePool/EC2NodeClass drift.
- Manual termination or infrastructure changes.

Voluntary disruption respects supported budgets and eviction semantics, but node failures and Spot interruptions may occur outside those controls. Test PodDisruptionBudgets, graceful termination and drain behavior. Never rely on a PDB as absolute protection from EC2 instance loss.

## 16. Drift and AMI lifecycle

Pin and review AMI changes. Updating the EC2NodeClass AMI selector may mark NodeClaims as drifted and trigger replacement under configured disruption behavior. Use staged rollout, capacity headroom, compatibility testing and node bootstrap observability.

Avoid auto-updating all production nodes merely because a new AMI alias appears.

## 17. GitOps ownership and ordering

Recommended GitOps sequence:

~~~text
Terraform -> managed bootstrap node group and AWS IAM
       |
Argo CD platform project -> Karpenter CRDs/controller
       |
Argo CD platform project -> EC2NodeClasses
       |
Argo CD platform project -> NodePools
       |
Application projects -> Deployments/StatefulSets
       |
Karpenter -> NodeClaims and EC2 nodes
~~~

Karpenter-managed NodeClaims and EC2 instances are controller-generated resources. Do not have Terraform and Karpenter both attempt to own the same application nodes.

## 18. GitLab policy gate

~~~yaml
stages: [validate, policy]

validate_karpenter:
  stage: validate
  image: registry.example.internal/ci/kubernetes-tools:PINNED_DIGEST
  script:
    - ./ci/validate-karpenter-crds.sh
    - ./ci/validate-nodepool-budgets.sh

policy_nodepools:
  stage: policy
  image: registry.example.internal/ci/policy-tools:PINNED_DIGEST
  script:
    - ./ci/check-approved-instance-families.sh
    - ./ci/check-spot-and-ondemand-baselines.sh
~~~

The internal scripts and images are illustrative interfaces. Implement them using approved schema validation and policy-as-code tooling, and enforce CODEOWNERS review for NodePool changes.

## 19. Observability and alerts

Monitor:

- Unschedulable Pods and scheduling latency.
- Karpenter controller availability and reconciliation errors.
- NodeClaims by phase and failure reason.
- Node provisioning duration and EC2 launch failures.
- Spot interruption notices and termination events.
- Consolidation and drift replacement frequency.
- Node Ready status and kubelet bootstrap failures.
- VPC CNI available IPs and ENI exhaustion.
- Node allocatable CPU/memory versus requested capacity.
- DaemonSet overhead and eviction rates.
- EC2 instance spend by capacity type, family and workload tags.

Metrics vary by Karpenter release; discover actual series from the installed controller rather than assuming legacy metric names.

## 20. Lab A — Bootstrap capacity verification

1. Confirm managed system node group spans approved AZs.
2. Check Karpenter controller placement on system nodes.
3. Validate controller replicas and PodDisruptionBudget.
4. Simulate application NodePool capacity reduction.
5. Verify controller remains available.
6. Record bootstrap recovery path.

**Pass:** Karpenter remains operational without Karpenter-managed application nodes.

## 21. Lab B — Install Karpenter with scoped IAM

1. Pin a compatible Karpenter release and CRD schema.
2. Configure IRSA or EKS Pod Identity.
3. Validate EC2 and interruption-queue IAM permissions.
4. Install controller through approved bootstrap.
5. Verify controller health and AWS API access.
6. Confirm unauthorized IAM actions are denied.

**Pass:** Karpenter can request only approved EC2 capacity.

## 22. Lab C — EC2NodeClass and NodePool

1. Label approved subnets/security groups for discovery.
2. Apply EC2NodeClass with approved AMI selector.
3. Apply staging NodePool with CPU/memory limits.
4. Verify NodePool and EC2NodeClass Ready conditions.
5. Inspect controller events for selector errors.
6. Record GitOps revision.

**Pass:** resources are valid and discover approved AWS infrastructure.

## 23. Lab D — Scale from Pending Pods

1. Deploy synthetic workload requesting more CPU than existing application nodes offer.
2. Observe Pods Pending.
3. Watch NodeClaims and new EC2 nodes.
4. Confirm Pods schedule and become Ready.
5. Measure provisioning latency.
6. Scale back to a safe baseline.

~~~bash
kubectl -n demo-staging get pods -w
kubectl get nodeclaims -w
kubectl get nodes -o wide
~~~

**Pass:** capacity is provisioned and Pods reach Ready within the staging objective.

## 24. Lab E — Spot and On-Demand fallback

1. Configure mixed capacity type requirements.
2. Deploy interruption-tolerant synthetic workers.
3. Record actual capacity types and instance diversity.
4. Simulate Spot unavailability through a controlled policy/selector change rather than terminating shared nodes.
5. Verify permitted On-Demand fallback.
6. Compare cost and recovery behavior.

**Pass:** the workload remains schedulable without relying on a single Spot pool.

## 25. Lab F — Topology spread and AZ shortage

1. Deploy replicas with preferred AZ spread.
2. Observe actual placement.
3. Add a stricter staging-only spread rule.
4. Simulate insufficient capacity in one AZ.
5. Observe Pending behavior and Karpenter decisions.
6. Restore safe placement policy.

**Pass:** topology constraints and their capacity tradeoffs are understood.

## 26. Lab G — Consolidation safety

1. Deploy multiple synthetic workloads.
2. Enable conservative consolidation in staging.
3. Reduce workload replicas.
4. Observe eligible node consolidation.
5. Confirm PodDisruptionBudgets and readiness remain satisfied.
6. Record node churn and savings estimate.

**Pass:** voluntary consolidation does not violate the test application's availability objective.

## 27. Lab H — Node expiration and drift

1. Pin approved AMI version.
2. Review a staged AMI selector change.
3. Observe drift conditions.
4. Verify controlled node replacement under disruption budget.
5. Check application SLO and bootstrap success.
6. Revert configuration if compatibility fails.

**Pass:** node rotation completes without uncontrolled fleet churn.

## 28. Lab I — Spot interruption tabletop

1. Select an isolated synthetic Spot workload.
2. Review interruption queue, EventBridge and controller configuration.
3. Simulate interruption notification in an approved staging test harness.
4. Observe drain/replacement behavior.
5. Confirm worker retries or checkpoints.
6. Record interruption recovery time.

**Pass:** interruption handling is observable and workload recovery succeeds.

## 29. Lab J — PodDisruptionBudget protection

1. Deploy a replicated synthetic API.
2. Create an appropriate PDB.
3. Trigger safe voluntary node consolidation/drain.
4. Observe eviction behavior and PDB constraints.
5. Test a too-restrictive PDB in staging.
6. Restore balanced disruption settings.

**Pass:** voluntary disruption is controlled and recovery is documented.

## 30. Lab K — VPC CNI IP exhaustion

1. Inspect subnet free IPs and CNI allocation settings.
2. Estimate IP consumption at target node scale.
3. Simulate an insufficient-IP condition using a disposable restricted subnet design.
4. Observe Karpenter and CNI errors.
5. Restore approved subnet capacity.
6. Document alert thresholds.

**Pass:** operators distinguish EC2 capacity from Pod IP capacity.

## 31. Lab L — IAM AccessDenied failure

1. Remove a narrowly scoped staging EC2 permission from Karpenter's role.
2. Trigger a safe synthetic scale-up.
3. Observe NodeClaim/controller errors.
4. Confirm CloudTrail records the denial.
5. Restore the minimum required permission.
6. Verify provisioning recovery.

**Pass:** permission failures are diagnosed without granting wildcard administrator access.

## 32. Lab M — Cluster Autoscaler coexistence

1. Inventory any Cluster Autoscaler deployment.
2. Identify ASGs managed by Cluster Autoscaler.
3. Confirm Karpenter NodePools do not overlap ownership.
4. Trigger independent scaling tests.
5. Check for duplicate provisioning or oscillation.
6. Document separation and retirement plan if migrating.

**Pass:** each capacity pool has exactly one scaling controller.

## 33. Lab N — GitOps rollback of NodePool policy

1. Propose a staging NodePool change through protected MR.
2. Run schema, capacity and disruption policy checks.
3. Merge and observe Argo CD reconciliation.
4. Simulate an unsafe instance restriction.
5. Revert GitOps revision through approved process.
6. Verify Pending Pods recover and controller health remains stable.

**Pass:** NodePool misconfiguration is recoverable through reviewed GitOps changes.

## 34. Lab O — FinOps and reliability acceptance

1. Record baseline node count, instance types and hourly cost.
2. Run representative scaling workload.
3. Compare Spot/On-Demand utilization and interruptions.
4. Review consolidation opportunities and headroom.
5. Validate application SLO and scheduling latency.
6. Calculate expected monthly run rate and approve safe limits.

**Pass:** savings do not come at the expense of unacceptable availability or operational risk.

## 35. Troubleshooting — sixteen scenarios

| # | Symptom | Likely cause | Response |
| --- | --- | --- | --- |
| 1 | Karpenter controller Pending | No bootstrap capacity | Restore managed system group |
| 2 | EC2NodeClass NotReady | Subnet/SG/AMI selector mismatch | Inspect status and AWS tags |
| 3 | NodePool NotReady | Missing NodeClass or invalid fields | Check CRD/version and references |
| 4 | NodeClaim never launches | IAM or EC2 quota | Inspect controller and CloudTrail |
| 5 | EC2 insufficient capacity | Spot/instance/AZ shortage | Broaden approved diversity |
| 6 | Pods remain Pending | Requests/affinity/taints | Inspect scheduler events |
| 7 | Pods cannot get IP | VPC CNI/subnet exhaustion | Restore IP capacity |
| 8 | Nodes NotReady after launch | Bootstrap/user data/network | Inspect kubelet and CNI |
| 9 | Karpenter churns nodes | Aggressive consolidation | Tighten disruption controls |
| 10 | PDB blocks consolidation | Too few healthy replicas | Adjust workload/PDB safely |
| 11 | Spot interruption causes outage | No fallback/retries | Add On-Demand floor and resilience |
| 12 | Wrong architecture scheduled | Missing arch constraints | Pin supported architecture |
| 13 | EBS Pod cannot reschedule | Volume AZ topology | Restore compatible zonal capacity |
| 14 | NodePool limit reached | CPU/memory cap | Review quota and approved limits |
| 15 | Autoscaler conflict | Two controllers manage pool | Separate ownership |
| 16 | Cost spike | Overprovisioning or poor consolidation | Inspect NodeClaims and spend |

## 36. Production runbook — Pending Pods and failed scale-up

1. Identify affected namespace, Pod requests, affinity, taints and topology.
2. Check scheduler events and NodePool matching.
3. Inspect NodePool/EC2NodeClass Ready conditions.
4. Inspect NodeClaims, controller logs and EC2 capacity errors.
5. Validate IAM, subnets, security groups, AMI and quotas.
6. Restore approved capacity or adjust safe scheduling constraints.
7. Verify Pod readiness, service health and provisioning latency.
8. Record root cause and capacity forecast.

## 37. Production runbook — Spot interruption

1. Identify affected NodeClaims and application workloads.
2. Confirm interruption notification processing and controller health.
3. Check PodDisruptionBudgets, drain progress and replacement nodes.
4. Verify On-Demand fallback and capacity diversity.
5. Confirm application retries, checkpoints and health.
6. Review interruption rate and workload placement policy.
7. Record customer impact and preventive actions.

## 38. Production runbook — runaway consolidation

1. Identify NodePool disruption settings and recent GitOps changes.
2. Inspect consolidation events, Pod evictions and SLO degradation.
3. Freeze further unsafe NodePool changes through approved process.
4. Revert to conservative consolidation/disruption settings.
5. Restore application capacity and verify readiness.
6. Check PDBs, topology and graceful termination.
7. Record rollback and policy regression tests.

## 39. Production runbook — IAM or AWS capacity outage

1. Determine whether failure is IAM, AWS API availability, quota or instance scarcity.
2. Inspect Karpenter controller logs and CloudTrail.
3. Validate identity association and role trust.
4. Restore scoped permissions or switch to approved instance/AZ alternatives.
5. Avoid wildcard IAM grants and unbounded NodePool limits.
6. Verify NodeClaim launch, registration and Pod readiness.
7. Document operational impact and escalation.

## 40. Production runbook — node AMI upgrade

1. Inventory current AMI, kubelet, CNI and workload compatibility.
2. Approve new AMI selector and disruption budget.
3. Test a small staging NodePool first.
4. Monitor drift, replacement, PDBs and Pod readiness.
5. Roll out progressively to production pools.
6. Verify security patch and workload health.
7. Preserve rollback-compatible AMI policy and evidence.

## 41. Evidence template

~~~text
Change / incident ID:
AWS account, EKS cluster and region:
Karpenter version and CRD schema:
Managed bootstrap node group:
NodePool and EC2NodeClass revisions:
AMI version and allowed instance families:
Spot / On-Demand ratio:
NodeClaims and provision time:
Pod scheduling latency:
PDB and disruption settings:
Subnet IP capacity and EC2 quotas:
IAM role and CloudTrail evidence:
Argo CD and GitLab revision:
Observed application SLO:
Cost baseline and after-change estimate:
Rollback and recovery duration:
Evidence archive and owner:
~~~

## 42. Scored acceptance

| Domain | Points | Evidence |
| --- | ---: | --- |
| Bootstrap and controller availability | 20 | Independent system capacity |
| NodePool/NodeClass/IAM security | 20 | Scoped resources and denial tests |
| Scheduling and scale-up | 20 | Provisioning and placement |
| Disruption and Spot resilience | 20 | PDB, drift and interruption tests |
| GitOps governance and rollback | 10 | Reviewed changes and recovery |
| Observability and FinOps | 10 | Alerts and cost analysis |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failures: Karpenter controller depends solely on its own nodes, uncontrolled IAM privileges, overlapping autoscaler ownership, unsafe disruption of critical services, or unbounded provisioning.

## 43. Final acceptance checklist

- [ ] Managed system capacity is independent of Karpenter.
- [ ] Karpenter version and CRDs are pinned and compatible.
- [ ] Controller IAM uses scoped workload identity.
- [ ] EC2NodeClass discovers approved AMIs, subnets and security groups.
- [ ] NodePools restrict instance types, capacity and cost exposure.
- [ ] Spot fallback and workload interruption tolerance are tested.
- [ ] Pod requests, affinity, topology and taints are reviewed.
- [ ] Consolidation, drift and disruption budgets are validated.
- [ ] VPC CNI IP capacity is forecasted.
- [ ] Karpenter and Cluster Autoscaler ownership does not overlap.
- [ ] GitOps policy checks and rollback are functional.
- [ ] Provisioning, churn and cost alerts are configured.
- [ ] Fifteen labs have evidence and owners.
- [ ] Production runbooks are tested.

## 44. Knowledge check

1. Why does Karpenter need bootstrap capacity independent of itself?
2. How do NodePools, EC2NodeClasses and NodeClaims differ?
3. Why can Pods remain Pending even when EC2 capacity is available?
4. What is the difference between Spot interruption and voluntary consolidation?
5. Why do PDBs not guarantee protection from all node failures?
6. How can AMI drift trigger node replacement?
7. Why must Karpenter and Cluster Autoscaler have separate capacity ownership?
8. Why is VPC subnet IP capacity a scaling constraint?
9. How should a production NodePool policy be rolled back?
10. Which metrics prove scaling is both reliable and cost-effective?

## 45. References

- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter NodeClasses](https://karpenter.sh/docs/concepts/nodeclasses/)
- [Karpenter Disruption](https://karpenter.sh/docs/concepts/disruption/)
- [Amazon EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [Amazon EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Amazon VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [Kubernetes PodDisruptionBudgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Kubernetes Scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 067 complete.** Next: **Chapter 068 — EKS Networking, AWS Load Balancer Controller and Storage Integration for GitOps**.