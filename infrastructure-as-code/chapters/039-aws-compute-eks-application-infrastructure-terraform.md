# Chapter 039 — AWS Compute, EKS and Application Infrastructure with Terraform

**Part 08 — AWS Infrastructure as Code · Chapter 039/120**  
**Audience:** Platform Engineering, SRE, DBRE, DevSecOps · **Prerequisites:** Chapters 001–038  
**Tools:** Terraform >=1.7, Python >=3.9, Bash · **Default lab:** Offline, no AWS credentials required.

## 1. Mission and learning outcomes

Build a production-minded AWS compute and application infrastructure blueprint. Design EC2 launch templates and Auto Scaling Groups (ASGs), ALB target groups, EKS cluster and managed node group boundaries, pod/workload IAM, multi-AZ placement, encryption, deployment health, autoscaling and recovery. Validate architecture with executable Terraform contract resources and a fail-closed Python policy gate.

**Safety:** The runnable lab uses only Terraform's built-in \`terraform_data\` resource and creates **no AWS resources**. The AWS provider example is review-only; running it in a separate account may incur costs. No production deployment or operational acceptance is implied by publication.

## 2. Architecture and ownership boundaries

~~~text
Git + code review + CI OIDC + change approval
  |
  +-- network foundation: VPC, private/public subnets, routing, endpoints
  +-- identity foundation: IAM roles, KMS, secrets, state permissions
  |
  +-- application infrastructure Terraform root
        |
        +-- AWS provider (approved account, region, default tags)
        +-- EC2 Launch Template (IMDSv2, EBS encryption, hardened AMI)
        +-- Auto Scaling Group (multi-AZ private subnets)
        +-- Application Load Balancer (public or internal as approved)
        |     +-- HTTPS listener / target group / health checks
        +-- EKS cluster (private endpoint policy, logging, KMS)
              +-- managed node groups (private subnets, multi-AZ)
              +-- EKS Pod Identity or IRSA for workload permissions
              +-- metrics-server / HPA / Cluster Autoscaler or Karpenter
              +-- ingress / Gateway API / ALB Controller
        |
        +-- CloudWatch, CloudTrail, VPC Flow Logs, OpenTelemetry
        +-- SLOs, canaries, runbooks, incident evidence
~~~

**Boundary principle:** A network root owns subnets and security-group foundations; the EKS root owns cluster/node lifecycles; application delivery owns Deployments, Services and runtime configuration. Avoid overlapping ownership between Terraform, Helm and GitOps controllers.

## 3. EC2 and immutable instance lifecycle

A launch template captures the AMI, instance type, block devices, security groups, instance profile, metadata options and user data. Pin a reviewed AMI identifier or controlled image-pipeline output, verify architecture compatibility and enforce encrypted EBS. Require IMDSv2 (\`http_tokens = "required"\`), least-privilege instance profile and no public IP for private workloads.

ASGs reconcile desired capacity. Spread instances across at least two AZs, respect capacity constraints and configure health checks, instance refresh, termination policies and warmup. An ASG can replace instances automatically; **Terraform apply success is not a healthy deployment**. Coordinate ASG rolling refresh with target deregistration, application readiness and DB connection budgets.

## 4. ALB, listeners and target health

ALB distributes Layer 7 traffic; target groups use application-specific health endpoints, thresholds and deregistration delay. Terminate TLS with an approved ACM certificate and enforce current security policy. Redirect HTTP to HTTPS when applicable; limit listener exposure and ALB security groups. Evaluate internal ALBs for private applications.

Health check design must separate liveness from readiness: an endpoint that always returns 200 can hide broken database dependencies. Avoid expensive DB queries on every ALB health check. Monitor HTTP 5xx, target health, request latency and connection errors during deploys.

## 5. EKS control plane and managed nodes

EKS manages Kubernetes control plane infrastructure, but the operator remains responsible for worker capacity, add-ons, networking, IAM, security and workloads. Choose supported Kubernetes/EKS platform versions and plan upgrades of control plane, VPC CNI, CoreDNS, kube-proxy, node AMIs and controllers. Configure control-plane logging, endpoint exposure, secrets encryption as applicable, network policies and private access patterns.

Managed node groups support node updates and scaling, but do not replace application PodDisruptionBudgets, topology spread constraints, probes or backup/recovery. Use managed node groups or Karpenter with clear ownership to avoid competing scaling loops. For IAM, prefer EKS Pod Identity where supported or IRSA with scoped service-account trust; never mount broad node credentials into pods.

## 6. Capacity, autoscaling and reliability

- **ASG:** min/desired/max capacities and instance refresh settings.
- **HPA:** application scaling from resource or custom metrics; requests and metrics availability matter.
- **Cluster Autoscaler/Karpenter:** node provisioning based on pending pods, instance offerings, topology and disruption.
- **AZ resilience:** distribute nodes and targets, configure topology spread, PDBs and sufficient spare capacity.
- **Cost:** idle nodes, NAT cross-AZ egress, ALB LCUs, EBS volumes and data transfer can dominate budgets.
- **DBRE coupling:** database max connections, query latency, pool sizing and rate limiting must be checked before scaling stateless replicas.

For an SLO, calculate availability and latency using real traffic measurements, not only Terraform resource counts. Define rollback triggers before rollout.

## 7. State, modules and security

Pin provider and module versions, protect \`.terraform.lock.hcl\`, separate remote state by environment/account, and use CI OIDC. Use \`allowed_account_ids\` in the AWS provider and check \`aws sts get-caller-identity\` before planning. Treat cluster endpoint outputs, IAM policies, userdata, kubeconfig and state as potentially sensitive. Avoid plaintext secrets in Terraform or cloud-init.

Use dedicated module contracts for \`compute\`, \`load_balancer\`, \`eks_cluster\`, \`node_group\`, \`workload_identity\` and \`observability\`. Pass narrow identifiers and outputs; prohibit circular dependency chains.

## 8. Executable lab inventory

~~~text
labs/chapter-039/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/aws-compute-eks.tf.example
  examples/aws-identity-check.sh.example
  compute-policy.json
  fixtures/compute-safe.json, compute-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  compute_gate.py, test_compute_gate.py, run-preflight.sh
  runbook.md, acceptance.md, .gitignore
~~~

The lab models an EC2/ASG contract, ALB contract, EKS contract and audit contract using \`terraform_data\`. It intentionally does not install AWS providers or create AWS infrastructure.

## 9. Lab A — Offline Terraform plan/apply

~~~bash
cd infrastructure-as-code/labs/chapter-039
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter039.tfplan
terraform apply chapter039.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: four \`terraform_data\` resources. Repeating an unchanged plan should return exit 0. Do **not** reuse dev state for prod variables; use distinct state/backend per environment.

## 10. Lab B — Fail-closed policy and negative tests

~~~bash
python3 compute_gate.py fixtures/compute-safe.json fixtures/plan-safe.json compute-policy.json
python3 compute_gate.py fixtures/compute-unsafe.json fixtures/plan-destructive.json compute-policy.json
python3 -m unittest -v test_compute_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes, unsafe fixture fails. Unit tests cover account/region isolation, multi-AZ placement, private compute, IMDSv2, EBS encryption, ASG capacity, ALB TLS and health checks, EKS endpoint/logging/KMS, node group health, workload IAM, approval/audit, and destructive plans.

The JSON manifest is **declared evidence**, not a live AWS inventory or a full Terraform HCL parser. Production validation additionally requires actual plan JSON, IAM analysis, runtime probes and SLO evidence.

## 11. Lab C — Review-only AWS integration

1. Obtain a dedicated sandbox AWS account and budget approval.
2. Verify STS identity, expected account and region.
3. Review \`examples/aws-compute-eks.tf.example\`; replace placeholders and inspect current provider/EKS compatibility.
4. In a separate root, initialize approved provider and secure backend.
5. Run \`terraform validate\` and \`terraform plan\`; **do not apply automatically**.
6. Review IAM trust, subnet associations, endpoint access, EBS encryption, cluster logging, node refresh and cost.
7. For real acceptance, deploy only under an approved change and observe target health, EKS node readiness and application SLOs.

## 12. SRE/DBRE production scenarios

| System | Failure mode | Required verification |
|---|---|---|
| EC2/ASG | bad AMI or refresh replaces healthy fleet | launch failures, target health, error rate |
| ALB | health checks fail after rollout | 5xx, target deregistration, listener rules |
| EKS | node group upgrade drains stateful pods | PDBs, volumes, readiness, topology |
| EKS CNI | pod IP exhaustion | subnet free IPs, pending pods, CNI metrics |
| PostgreSQL/RDS | scaling app replicas saturates DB connections | connection pool, wait events, p99 latency |
| Redis | node disruption or DNS change | client reconnect, cache miss, failover |
| OpenSearch | request fan-out overload | heap, search latency, shard health |
| Kafka/MSK | consumer scaling changes broker pressure | lag, ISR, rebalances |
| Multi-AZ | one AZ or NAT path unavailable | endpoint reachability, failover and capacity |

## 13. Troubleshooting

| Symptom | Diagnostic focus | Safe response |
|---|---|---|
| ASG instances fail to launch | AMI, quotas, instance profile, subnet IPs | inspect activity and launch failures |
| ALB 503 | no healthy targets | verify SG, port, readiness, target health |
| EKS nodes NotReady | CNI, IAM, DNS, bootstrap, kubelet | inspect nodes and cloud logs |
| Pods Pending | insufficient resources/IPs, taints, affinity | inspect events and scheduler |
| 403 from AWS API in pod | Pod Identity/IRSA trust and policy | verify scoped role, no wildcard escalation |
| EKS upgrade stuck | PDB, unhealthy node, incompatible add-on | stop and remediate safely |
| High DB latency after scaling | connection storm | throttle rollout and tune pools |
| Unexpected resource replacement | immutable Terraform argument | freeze, inspect plan and data impact |

## 14. Operational runbooks

**Deployment:** verify identity/state lock → policy and plan gates → ASG/EKS rollout budget → canary → monitor ALB target health and workload SLO → approve promotion.

**Failed ASG refresh:** pause rollout, inspect launch/health failures, return to reviewed AMI/launch template, verify restored healthy capacity and application latency.

**EKS node disruption:** cordon/drain only with PDB review, check CSI volumes and zone constraints, preserve service capacity, verify node/pod health and workload error budget.

**DB overload:** freeze replica growth, limit concurrency, inspect DB wait events and pool metrics, recover using rate limits or a reviewed scaling change; do not indiscriminately raise DB max connections.

**DR:** separately test EKS manifests, EBS snapshots, application data, database backups and KMS decryptability. A Terraform state restore is not a data restore.

## 15. 100-point acceptance

| Area | Points |
|---|---:|
| EC2/ASG lifecycle and security | 20 |
| ALB/TLS and health checks | 15 |
| EKS cluster/node architecture | 20 |
| Workload IAM, encryption and state isolation | 15 |
| Automated positive/negative tests | 15 |
| SRE/DBRE runbooks, SLO and DR evidence | 15 |

Pass >=85/100 and no critical failures: public worker exposure, missing IMDSv2, unencrypted EBS, open EKS public endpoint without approved restrictions, wildcard workload IAM, destructive plan without approval, or untested recovery.

## 16. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the disposable offline lab.

Review: What does an ASG health check prove? Why can ALB report healthy while DB is failing? How do PodDisruptionBudgets affect EKS upgrades? Why must EKS node IAM differ from pod IAM? How do ASG/HPA/Karpenter scaling loops interact? What is the effect of an AZ outage on target capacity? Why is an approved plan not production acceptance?

**Next: Chapter 040 — AWS Stateful Data, Storage, Resilience and Production Operations Capstone.**
