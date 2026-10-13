# Chapter 076 — Amazon EKS Architecture and Provisioning

**Track:** Kubernetes Administration · **Part 16 — Managed Kubernetes on AWS and Azure**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes platform engineers, AWS cloud engineers  
**Prerequisites:** Chapters 001–015, 026–030, 061–070; AWS account with approved permissions; Windows PowerShell; AWS CLI v2; kubectl; optional eksctl and Terraform

## 1. Production scenario and objectives

A platform team needs to deploy a new Amazon EKS cluster for a customer-facing application and stateful services. The cluster must use private networking, controlled API access, auditable IAM authentication, supported add-ons, and node capacity across availability zones. The design must support future autoscaling, disaster recovery, cost governance and controlled Kubernetes version upgrades.

**Mission:** understand EKS architecture, design a secure and operable cluster, produce a reviewed provisioning plan, and validate the resulting cluster without assuming cloud provisioning succeeded.

### Learning outcomes

1. Explain the EKS control plane and shared-responsibility model.
2. Design VPC/subnets, routing, IP capacity and API endpoint access.
3. Understand IAM cluster roles, node roles and Kubernetes authorization.
4. Choose managed node groups, Fargate and Karpenter appropriately.
5. Plan VPC CNI, CoreDNS, kube-proxy and CSI add-ons.
6. Compare eksctl, AWS CLI, Terraform and GitOps provisioning workflows.
7. Provision an isolated EKS staging cluster only after approval.
8. Validate node readiness, access, network, storage, observability and cost.
9. Establish operational runbooks, upgrade policy and disaster recovery prerequisites.

## 2. EKS architecture and responsibility boundaries

```text
AWS-managed EKS control plane
+---------------------------------------------+
| Kubernetes API servers / scheduler /         |
| controller manager / etcd                   |
| Managed by AWS; control-plane endpoints     |
+---------------------+-----------------------+
                      |
                 EKS API endpoint
                      |
Customer AWS VPC / subnets
+---------------------------------------------+
| Managed node groups / EC2 worker nodes      |
| or Fargate Pods / Karpenter-provisioned EC2 |
| VPC CNI / CoreDNS / kube-proxy               |
| EBS/EFS CSI / ingress / observability        |
| Application Pods / databases / workloads     |
+---------------------------------------------+
                      |
              IAM / KMS / CloudWatch / S3
```

AWS manages the EKS control-plane infrastructure and its etcd. Customers remain responsible for workload security, IAM configuration, network policies, node/Pod configuration, data backups, add-on lifecycle decisions and application availability. Managed control plane does **not** mean all Kubernetes components are patched or backed up automatically.

## 3. Lab 1 — Verify tools, AWS identity and region

```powershell
aws --version
kubectl version --client
eksctl version
terraform version
aws configure list-profiles
$profile = 'REPLACE_WITH_APPROVED_AWS_PROFILE'
$region = 'us-east-1'
aws sts get-caller-identity --profile $profile
aws ec2 describe-regions --profile $profile --region $region --query 'Regions[].RegionName' --output table
```

`eksctl` and `terraform` are optional; skip their version commands if not installed. Verify account ID and region before every provisioning action. Prefer AWS IAM Identity Center/SSO or approved short-lived credentials over static access keys.

**Expected:** the correct account, role, region and toolchain are documented. Do not proceed with an unexpected account or an expired SSO session.

## 4. Lab 2 — Inventory existing EKS and AWS prerequisites

```powershell
aws eks list-clusters --region $region --profile $profile
aws ec2 describe-vpcs --region $region --profile $profile --query 'Vpcs[].{VpcId:VpcId,Cidr:CidrBlock,State:State}' --output table
aws ec2 describe-subnets --region $region --profile $profile --query 'Subnets[].{SubnetId:SubnetId,VpcId:VpcId,AZ:AvailabilityZone,Cidr:CidrBlock,AvailableIPs:AvailableIpAddressCount}' --output table
aws ec2 describe-nat-gateways --region $region --profile $profile --query 'NatGateways[].{Id:NatGatewayId,State:State,VpcId:VpcId}' --output table
```

### Inventory worksheet

```text
AWS account / environment:
Region and availability zones:
VPC ID / CIDR:
Private subnet IDs / free IPs:
Public subnet IDs / ingress plan:
NAT gateway or private VPC endpoints:
DNS resolution / hostnames:
Security groups / NACLs:
KMS key and policy:
Cluster IAM role:
Node IAM role:
EKS access administrator:
Kubernetes version:
Node operating system/AMI:
Cost owner / tags:
```

**Expected:** existing infrastructure and CIDR/IP limits are understood before cluster design.

## 5. Lab 3 — Design VPC and subnet topology

A production EKS design commonly places worker nodes in private subnets across at least two or three availability zones, with carefully controlled ingress and egress.

### Design considerations

- VPC CIDR and subnet sizes must accommodate node and Pod IP growth.
- EKS requires suitable subnets in multiple availability zones.
- Control-plane network interfaces and cluster operations need free subnet IPs.
- NAT gateways can create substantial hourly and per-GB charges.
- Private VPC endpoints can reduce NAT dependency for supported AWS services.
- EBS volumes are availability-zone scoped; schedule stateful Pods accordingly.
- Internal/external load balancers require correct subnet discovery and routing.
- Use dedicated security groups and least-privilege traffic rules.
- Avoid CIDR overlap with on-premises, peered VPCs or recovery regions.

### IP planning worksheet

```text
Peak EC2 nodes:
Max Pods per node:
Estimated Pod IPs:
Warm IP/prefix allocation:
Control-plane ENI headroom:
Load balancer ENIs:
Zone-failure spare IPs:
Growth reserve:
Available subnet IPs:
```

**Expected:** an explicit Pod IP and subnet headroom model, not merely a node count estimate.

## 6. Lab 4 — Understand EKS API endpoint access

EKS supports public and private Kubernetes API endpoint access. Public endpoint CIDR restrictions and private network connectivity must be designed together.

```powershell
$cluster = 'REPLACE_WITH_EXISTING_CLUSTER'
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Status:status,Version:version,Endpoint:endpoint,ResourcesVpcConfig:resourcesVpcConfig,AccessConfig:accessConfig}' --output json
```

For a new production-oriented design, prefer private endpoint access where operational connectivity permits, with a documented VPN, Direct Connect, bastion or approved access path. If public access is required, restrict CIDRs and audit exceptions.

**Expected:** API endpoint reachability is intentional; a private-only endpoint will not be accessible from an arbitrary public workstation.

## 7. Lab 5 — IAM roles, EKS access entries and authorization

### Three separate permission layers

1. **AWS IAM permissions:** who may create/describe/update EKS and AWS resources.
2. **EKS authentication and access entries:** how IAM principals authenticate to the Kubernetes API.
3. **Kubernetes RBAC/EKS access policies:** what authenticated principals can do.

Do not assume an IAM AdministratorAccess policy automatically implies Kubernetes cluster-admin in every cluster configuration.

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.accessConfig'
aws eks list-access-entries --cluster-name $cluster --region $region --profile $profile
aws eks list-associated-access-policies --cluster-name $cluster --principal-arn REPLACE_WITH_PRINCIPAL_ARN --region $region --profile $profile
```

Access-entry commands require a compatible cluster authentication mode and an existing principal entry. Older clusters may still use the legacy `aws-auth` ConfigMap; assess migration rather than changing authentication modes casually.

### Security principles

- Prefer IAM Identity Center and short-lived credentials.
- Use least-privilege cluster access and namespace RBAC.
- Separate break-glass cluster admin from routine operators.
- Use EKS Pod Identity or IRSA for application AWS permissions.
- Never grant node IAM roles broad application permissions.
- Audit access entries, CloudTrail and Kubernetes audit logs.

## 8. Lab 6 — Select compute: managed nodes, Fargate or Karpenter

| Option | Strength | Operational consideration |
|---|---|---|
| EKS managed node groups | AWS-managed node group lifecycle | Node sizing, updates and capacity still require planning |
| Self-managed EC2 nodes | Customization and control | Greater bootstrap and patching responsibility |
| EKS Fargate | No customer-managed worker EC2 nodes for supported Pods | Workload/daemon/storage limitations and pricing |
| Karpenter | Flexible, workload-aware EC2 provisioning | NodePool/NodeClass policies, limits and disruption safeguards |

For DBRE workloads, assess storage attachment, local storage, networking, kernel requirements, Pod placement and graceful shutdown. Stateful services may need more controlled placement than stateless APIs.

```powershell
aws eks list-nodegroups --cluster-name $cluster --region $region --profile $profile
aws eks list-fargate-profiles --cluster-name $cluster --region $region --profile $profile
kubectl get nodepools
kubectl get nodeclaims
```

The last two commands apply only where Karpenter CRDs are installed.

## 9. Lab 7 — Plan and verify EKS add-ons

Common cluster components include Amazon VPC CNI, CoreDNS, kube-proxy, EBS CSI, EFS CSI, load balancer controller, metrics and observability agents.

```powershell
aws eks list-addons --cluster-name $cluster --region $region --profile $profile
aws eks describe-addon-versions --addon-name vpc-cni --region $region --profile $profile --query 'addons[].addonVersions[].addonVersion' --output table
kubectl -n kube-system get daemonsets,deployments
kubectl get csidrivers
kubectl get storageclasses
```

**Compatibility:** add-on versions must match the supported Kubernetes version and platform configuration. Use AWS compatibility information and release notes; do not automatically install the newest version without review.

### Operational checks

- VPC CNI Pod IP allocation and ENI limits.
- CoreDNS availability and autoscaling.
- kube-proxy version compatibility.
- EBS CSI permissions, snapshots and topology.
- EFS CSI availability for shared file use cases.
- AWS Load Balancer Controller identity and subnet discovery.
- Metrics Server and observability pipeline.

## 10. Lab 8 — Provisioning with eksctl (design and optional staging execution)

**Cost and change warning:** creating an EKS cluster provisions billable AWS resources, potentially including EKS control plane, EC2, EBS, NAT and load balancers. Run only in an approved isolated AWS account with an owner, budget and teardown plan.

Save `ch076-eksctl.yaml`:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ch076-eks-lab
  region: us-east-1
  version: "REPLACE_WITH_SUPPORTED_EKS_VERSION"
iam:
  withOIDC: true
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - "REPLACE_WITH_APPROVED_PUBLIC_IP/32"
managedNodeGroups:
  - name: general
    instanceType: t3.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 3
    privateNetworking: true
    labels:
      workload: general
    tags:
      environment: staging
      owner: platform-team
```

This is a **design template**, not ready-to-run configuration. Confirm version support, VPC/subnets, egress/NAT, identity, cluster endpoint policy, node AMI, add-ons, quotas and cost. A new eksctl-created VPC may incur NAT costs; existing-VPC provisioning requires explicit subnet configuration.

```powershell
eksctl create cluster -f .\ch076-eksctl.yaml
```

**Do not run** until the reviewed file is populated, the AWS account is confirmed, a change is approved and budget guardrails are active.

**Expected:** an approved, reproducible cluster provisioning design; runtime execution is optional and must be marked Not run when not performed.

## 11. Lab 9 — Provisioning with Terraform and IaC governance

Terraform can manage EKS clusters, IAM, VPC, managed node groups and add-ons through AWS resources or approved modules.

### IaC design checklist

```text
Provider/account/region pinned:
Terraform/module versions pinned:
Remote state encrypted and locked:
VPC and subnet inputs validated:
Cluster Kubernetes version pinned:
Control-plane logging configured:
API endpoint restrictions:
Cluster and node IAM roles:
EKS access entries:
Node group scaling bounds:
Add-on versions:
KMS and secret management:
Tags and budget:
Plan review and approval:
Drift detection:
Destroy protection and teardown:
```

```powershell
terraform fmt -check
terraform validate
terraform plan -out=ch076.plan
terraform show ch076.plan
```

Run these commands only in a reviewed Terraform project with initialized providers and state. A plan is not evidence of successful provisioning. Never commit state files, secrets or sensitive plan output.

## 12. Lab 10 — Validate cluster creation and kubeconfig

After an approved cluster exists:

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Status:status,Version:version,Endpoint:endpoint}' --output table
aws eks update-kubeconfig --name $cluster --region $region --profile $profile --alias ch076-eks-lab
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl -n kube-system get pods
kubectl get storageclasses
kubectl auth can-i get pods --all-namespaces
```

The alias does not grant access. IAM authentication, access entries/RBAC, network reachability and valid AWS credentials must all work. `update-kubeconfig` modifies local kubeconfig; review the context before applying resources.

### Acceptance checks

- EKS status ACTIVE.
- Expected Kubernetes version and cluster endpoint policy.
- Node group capacity and nodes Ready.
- CoreDNS, CNI and kube-proxy healthy.
- CSI driver and StorageClass available where required.
- Access entries/RBAC match approved role design.
- Control-plane logs, audit and alerts configured.
- Cluster tagging, budgets and inventory recorded.

## 13. Lab 11 — EKS networking, scheduling and storage smoke test

**Approved staging cluster only.** Save `ch076-smoke.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch076
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch076
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:stable
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 250m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch076
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch076-smoke.yaml
kubectl -n ch076 rollout status deployment/web --timeout=180s
kubectl -n ch076 get pods -o wide
kubectl -n ch076 get service web
kubectl -n ch076 get events --sort-by=.lastTimestamp
```

**Expected:** two Ready Pods, correct node placement and ClusterIP service. This smoke test does not validate external ingress or persistent storage; test those separately with approved workloads.

## 14. Lab 12 — Production readiness and failure tabletop

**Scenario:** a newly provisioned EKS cluster has healthy nodes but Pods remain Pending, DNS lookups time out, and the private API endpoint is unreachable from the SRE workstation.

### Investigation steps

1. Verify AWS account, cluster status and endpoint configuration.
2. Confirm VPC routes, DNS and security groups.
3. Inspect node Ready conditions and VPC CNI health.
4. Check Pod IP/subnet capacity and max Pods per node.
5. Review scheduler Events, taints, affinity and requests.
6. Inspect CoreDNS and kube-proxy.
7. Validate EKS access entries and Kubernetes RBAC.
8. Check private endpoint connectivity through approved network path.
9. Review IAM permissions for add-ons and Pod identities.
10. Record corrective actions, rollback and change approval.

**Expected:** distinguish cloud networking, IAM, Kubernetes scheduling and add-on faults without defaulting to node replacement.

## 15. Operational observability and cost controls

### Metrics and alerts

- API server availability and control-plane logging.
- Node Ready state and allocatable/requested resources.
- VPC CNI IP allocation failures and subnet capacity.
- CoreDNS latency/errors and DNS availability.
- Pending Pods and FailedScheduling Events.
- Managed node group health and update failures.
- EBS/EFS latency, throughput and attachment errors.
- Load balancer health and ingress error rates.
- CloudTrail access changes and unexpected IAM grants.
- AWS Cost Explorer/Budgets anomalies.

### Cost inventory

```text
EKS cluster hourly charge:
EC2 node instance-hours:
EBS/EFS storage and snapshots:
NAT gateways and data processing:
Load balancers and traffic:
CloudWatch logs and metrics:
Cross-AZ and cross-region data transfer:
Backup/object storage:
Expected monthly budget:
Cost owner:
```

No cost figures are hard-coded because rates vary by region, pricing model and usage.

## 16. EKS production provisioning runbook

### Before change

1. Approve architecture, Kubernetes version, VPC/subnets and endpoint access.
2. Validate IAM cluster/node roles and access-entry strategy.
3. Review node capacity, Pod IP budget and failure-zone headroom.
4. Pin add-on versions and IaC dependencies.
5. Establish budgets, tags, monitoring and recovery ownership.
6. Capture Terraform/eksctl plan and rollback procedure.

### Provision

1. Confirm AWS account, region and credentials.
2. Apply approved IaC/eksctl changes.
3. Verify cluster status and control-plane endpoint.
4. Provision managed nodes or approved Karpenter baseline.
5. Configure access entries and add-ons.
6. Enable audit/logging and cluster monitoring.
7. Execute staging smoke and dependency tests.

### Handover

1. Record cluster configuration and runbooks.
2. Assign on-call ownership and escalation.
3. Schedule version/add-on lifecycle review.
4. Verify backups, GitOps, disaster recovery and cost reporting.
5. Obtain application/platform/security acceptance.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Cluster creation fails | IAM, quota, VPC/subnet config | EKS/CloudFormation events |
| kubectl timeout | API endpoint network path | Public/private endpoint, DNS, SG |
| kubectl Unauthorized | AWS auth/token/role | STS, kubeconfig, access entries |
| kubectl Forbidden | Kubernetes authorization | RBAC/access policy |
| Nodes NotReady | Bootstrap, CNI, IAM, network | Node conditions, kubelet/CNI |
| Pods Pending | Resources, taints, IPs | Scheduler Events |
| Pods cannot resolve DNS | CoreDNS/CNI/network | CoreDNS logs and Service |
| PVC Pending | CSI role, StorageClass, topology | PVC Events, EBS CSI logs |
| LoadBalancer Pending | Controller/IAM/subnet tags | Controller logs and Events |
| Cost exceeds budget | NAT, EC2, EBS, LB, logs | Cost Explorer, tags and usage |

## 18. Cleanup and safeguards

For an approved staging smoke test:

```powershell
kubectl config current-context
kubectl -n ch076 get deployments,pods,services
kubectl delete namespace ch076
```

**Do not delete an EKS cluster, VPC, node group, KMS key or shared IAM role as routine tutorial cleanup.** A lab-owned cluster can be decommissioned only under a separate reviewed plan that checks PVC reclaim policies, snapshots, load balancers, Terraform state, CloudFormation stacks and residual AWS charges.

## 19. Chapter acceptance checklist

- [ ] AWS account/region and short-lived identity verified.
- [ ] EKS architecture and responsibility boundaries documented.
- [ ] VPC, subnets, routing and Pod IP capacity modeled.
- [ ] API endpoint exposure and access paths reviewed.
- [ ] IAM roles, access entries and RBAC designed.
- [ ] Managed node groups/Fargate/Karpenter selection justified.
- [ ] VPC CNI, CoreDNS, kube-proxy and CSI add-ons planned.
- [ ] eksctl configuration reviewed or marked not run.
- [ ] Terraform/IaC governance and drift strategy documented.
- [ ] Cluster/kubeconfig validation performed or marked not run.
- [ ] Staging smoke test performed or marked not run.
- [ ] Operational alerts, budgets and ownership assigned.
- [ ] Failure tabletop and troubleshooting completed.
- [ ] Independent technical review and runtime validation completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [EKS Cluster Endpoint Access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [EKS VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS Add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [eksctl Documentation](https://eksctl.io/)
- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

**Next:** Chapter 077 — EKS Node Groups and Karpenter.
