# Chapter 066 — Amazon EKS GitOps Architecture, Cluster Bootstrap and Platform Foundations

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 14:** Amazon EKS  
**Chapter:** 066 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps, Cloud Architects and Kubernetes Administrators

> **Safety:** Use a dedicated nonproduction AWS account and disposable EKS cluster for hands-on labs. EKS, NAT gateways, load balancers, EC2 instances and log ingestion incur costs. Never run terraform destroy against shared or production infrastructure. Confirm AWS identity, region, cluster name, Terraform state and change approval before modifying resources.

## 1. Learning objectives

By completing this chapter you will:

1. Design a production-oriented EKS control-plane, networking and node architecture.
2. Provision a staging EKS cluster with Terraform and explicit lifecycle safeguards.
3. Understand EKS authentication, access entries, IAM and workload identity.
4. Configure managed node groups, add-ons, storage and ingress foundations.
5. Bootstrap Argo CD safely before transferring platform ownership to GitOps.
6. Integrate GitLab CI/CD with protected GitOps promotion.
7. Establish security, monitoring, backup and upgrade readiness.
8. Troubleshoot common EKS provisioning, identity, networking and scheduling failures.
9. Execute operational acceptance labs and produce auditable evidence.

## 2. Reference architecture

~~~text
AWS organization / dedicated staging account
                  |
        Terraform remote state
                  |
           VPC across 3 AZs
      /            |            \
 private subnet private subnet private subnet
      |            |            |
 managed nodes managed nodes managed nodes
      \            |            /
             Amazon EKS
        managed Kubernetes API
                  |
         EKS access entries / IAM
                  |
         platform bootstrap layer
      /          |            \
   VPC CNI    CoreDNS       kube-proxy
      |
 Argo CD + GitOps AppProject
      |
 platform add-ons and workloads
      |
 AWS Load Balancer Controller / EBS CSI / metrics
      |
 GitLab protected CI -> immutable image -> GitOps MR
      |
 observability, alerts, backup, upgrade governance
~~~

EKS control plane is managed by AWS; worker nodes, VPC, security groups, add-ons, IAM, workloads and many upgrade operations remain customer responsibilities.

## 3. EKS architecture decisions

| Domain | Staging choice | Production consideration |
| --- | --- | --- |
| Region | One approved AWS region | Data residency and DR |
| Availability Zones | 2–3 | Multi-AZ capacity and failure domains |
| API endpoint | Private preferred where reachable | Private endpoint, restricted public access if needed |
| Nodes | Managed node group | Multiple pools, Karpenter as separate design |
| Pod networking | Amazon VPC CNI | IP capacity and prefix delegation |
| Identity | EKS access entries | Least privilege and break-glass |
| Workload identity | EKS Pod Identity or IRSA | IAM role scope and trust |
| Storage | EBS CSI for zonal block | Multi-AZ replication at app layer |
| Ingress | AWS Load Balancer Controller | ALB/NLB design and TLS |
| GitOps | Argo CD | HA, project isolation, repo credentials |
| State | Remote encrypted S3 backend | Locking, retention and recovery |

## 4. Shared responsibility and blast radius

Keep separate AWS accounts or tightly isolated environments for staging and production. Use dedicated VPC CIDRs, cluster names, IAM roles, Terraform state and GitOps overlays. A Kubernetes namespace alone is not a strong isolation boundary for hostile tenants.

Do not give GitLab runners administrator access to production EKS merely to update GitOps files. Prefer GitLab CI building artifacts and opening protected GitOps merge requests; Argo CD reconciles workloads through scoped Kubernetes permissions.

## 5. Prerequisites

- AWS CLI v2 and approved SSO/assumed-role access.
- Terraform and AWS provider versions pinned to your tested release.
- kubectl compatible with the selected EKS Kubernetes minor version.
- Helm and Argo CD CLI versions compatible with the target controller.
- GitLab repository with protected branches and CI runner.
- AWS quotas for VPC, EKS, ENIs, IPs, EC2, EBS and load balancers.
- DNS, TLS, NAT or VPC endpoints and access to required registries.
- Security-approved IAM, KMS and logging baseline.

~~~bash
aws sts get-caller-identity
aws configure list-profiles
aws eks list-clusters --region us-east-1
terraform version
kubectl version --client
helm version
~~~

Never assume the AWS profile or region. Explicitly set AWS_PROFILE and AWS_REGION in your approved shell session and verify account identity before applying infrastructure.

## 6. Network topology and IP planning

EKS nodes and Pods consume VPC networking resources. Plan:

- VPC CIDR without overlap with connected on-premises and cloud networks.
- Private subnets across multiple AZs for worker nodes.
- Public subnets only where internet-facing load balancers or NAT require them.
- Routing to ECR, STS, EC2, CloudWatch, S3 and other dependencies.
- NAT gateway versus VPC endpoint tradeoffs and failure modes.
- Security groups, network ACLs, Kubernetes NetworkPolicies and DNS.
- Pod IP demand under VPC CNI secondary-IP/prefix mode.
- Load balancer subnet tags and free IP capacity.

**Important:** EKS-managed control-plane ENIs use designated cluster subnets. Design API access and security groups accordingly. EBS volumes are AZ-scoped; a Pod using a zonal volume cannot freely fail over across AZs without a compatible storage or replication strategy.

## 7. Terraform repository layout

~~~text
infra/
  modules/
    network/
    eks/
    iam/
    observability/
  environments/
    staging/
      backend.tf
      providers.tf
      main.tf
      variables.tf
      terraform.tfvars.example
      outputs.tf
    production/
      backend.tf
      providers.tf
      main.tf
      variables.tf
      outputs.tf
gitops/
  bootstrap/
    argocd/
    platform-root/
  clusters/
    eks-staging/
      platform/
      apps/
    eks-production/
      platform/
      apps/
ci/
  validate-infrastructure.sh
  propose-gitops-mr.sh
runbooks/
  eks-bootstrap.md
  eks-api-unavailable.md
  node-notready.md
~~~

Separate cluster provisioning state from application GitOps desired state. Use protected approvals for Terraform plans and changes.

## 8. Terraform provider and remote state

Illustrative backend configuration:

~~~hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "REPLACE_WITH_APPROVED_TF_STATE_BUCKET"
    key          = "eks/staging/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "staging"
      ManagedBy   = "terraform"
      Owner       = "platform"
    }
  }
}
~~~

**Compatibility:** S3 backend native use_lockfile support and AWS provider version requirements must be checked against the installed Terraform release. Use a tested backend locking design; do not mix deprecated DynamoDB locking patterns blindly. Configure S3 versioning, access restrictions, encryption, retention and recovery separately.

## 9. Terraform VPC and EKS module example

The following uses the community terraform-aws-modules modules as a **version-pinned design example**. Select a currently supported module release matching your Terraform, AWS provider and EKS versions. Do not assume the placeholder versions are deployable.

~~~hcl
variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "cluster_name" {
  type    = string
  default = "demo-eks-staging"
}

variable "kubernetes_version" {
  type = string
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "PIN_APPROVED_VERSION"

  name = "demo-eks-staging-vpc"
  cidr = "10.64.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.64.0.0/20", "10.64.16.0/20", "10.64.32.0/20"]
  public_subnets  = ["10.64.64.0/24", "10.64.65.0/24", "10.64.66.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "PIN_APPROVED_VERSION"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = false
  cluster_endpoint_private_access = true

  authentication_mode = "API"

  eks_managed_node_groups = {
    general = {
      instance_types = ["m6i.large"]
      min_size       = 2
      max_size       = 6
      desired_size   = 3
    }
  }
}
~~~

This is a **teaching skeleton**, not a copy-paste deployment: pin real compatible module versions, validate module input changes, configure cluster and node IAM, EKS add-ons, cluster access entries, endpoint connectivity and security policies. A private-only API endpoint requires a VPN, Direct Connect, peered/VPC-accessible runner or other approved network path.

**Cost:** single NAT gateway is a low-cost staging compromise and a single-AZ network egress failure domain; use multi-AZ NAT/endpoints where reliability requires it.

## 10. Terraform lifecycle and approval

~~~bash
terraform -chdir=infra/environments/staging init
terraform -chdir=infra/environments/staging fmt -check
terraform -chdir=infra/environments/staging validate
terraform -chdir=infra/environments/staging plan -out=staging.tfplan
terraform -chdir=infra/environments/staging show staging.tfplan
~~~

Apply only after independent review of the plan, account, region and expected resources. A Terraform plan file may contain sensitive data; store it in approved restricted CI artifacts, never in public repositories.

Do not put Kubernetes workloads and long-lived Argo CD Application manifests under the same Terraform ownership unless there is an explicit, documented reason. Avoid conflicting controllers.

## 11. EKS access entries and Kubernetes authorization

EKS access entries provide an AWS-supported way to associate IAM principals with cluster access. Access policy associations and Kubernetes RBAC are distinct mechanisms.

~~~bash
aws eks describe-cluster   --name demo-eks-staging   --region us-east-1   --query 'cluster.accessConfig'

aws eks list-access-entries   --cluster-name demo-eks-staging   --region us-east-1
~~~

Choose authentication mode (API, API_AND_CONFIG_MAP or CONFIG_MAP where supported) intentionally. Migrating away from legacy aws-auth must preserve required access and recovery paths. Access entries are not automatically created for every existing aws-auth mapping.

Restrict cluster-admin permissions. Use named operational roles, time-bound elevated access and audited break-glass.

## 12. kubeconfig and API connectivity

~~~bash
aws eks update-kubeconfig   --region us-east-1   --name demo-eks-staging   --alias demo-eks-staging

kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl auth can-i list pods --all-namespaces
~~~

An updated kubeconfig does not prove IAM or Kubernetes authorization. For private endpoint clusters, DNS resolution and network routing must work from the operator workstation or CI runner.

## 13. EKS add-on baseline

At minimum, validate:

- Amazon VPC CNI: Pod networking and IP allocation.
- CoreDNS: Kubernetes service discovery.
- kube-proxy: service routing where applicable.
- Amazon EBS CSI Driver: dynamic EBS volumes and IAM identity.
- Metrics Server: resource metrics for HPA and diagnostics.
- AWS Load Balancer Controller: ALB/NLB provisioning where required.
- EKS Pod Identity Agent: when using EKS Pod Identity.
- CloudWatch/Prometheus collectors and log routing.

Some are EKS-managed add-ons; others require separate Helm or GitOps installation. Check version compatibility with the EKS Kubernetes version and cluster operating mode.

~~~bash
aws eks list-addons --cluster-name demo-eks-staging --region us-east-1
aws eks describe-addon --cluster-name demo-eks-staging --addon-name vpc-cni --region us-east-1
kubectl -n kube-system get deploy,daemonsets,pods
kubectl get storageclasses
~~~

## 14. Workload identity: IRSA versus EKS Pod Identity

**IRSA:** IAM OIDC provider and a ServiceAccount annotation bind Pods to an IAM role through a trusted subject/audience.

**EKS Pod Identity:** an association between an EKS cluster, Kubernetes ServiceAccount and IAM role, using the Pod Identity agent and its supported trust model.

Do not assume an IRSA annotation configures EKS Pod Identity. Choose the supported model per controller and validate IAM policy, trust and network access to STS.

For ESO, EBS CSI and AWS Load Balancer Controller, give each component its own narrowly scoped IAM permissions. Avoid granting application Pods broad EC2, Secrets Manager or S3 access.

## 15. Example application ServiceAccount

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-web
  namespace: demo-staging
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-web
  namespace: demo-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      serviceAccountName: demo-web
      automountServiceAccountToken: false
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_REAL_DIGEST
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
~~~

The digest is a placeholder. If the application requires AWS workload identity, review whether its provider needs a projected service-account token or agent-specific injection. Do not disable token mounting blindly for identity-enabled workloads.

## 16. Storage and availability foundations

EBS CSI provisions zonal block volumes; design StatefulSets and topology constraints with AZ boundaries in mind. Use application-level replication, backups and tested restores for data durability. EBS volume snapshots are not by themselves a complete application-consistent backup.

For shared POSIX access, evaluate EFS CSI and its availability, cost and performance characteristics. Do not assume every workload should use EBS.

## 17. Ingress and load balancing

Use AWS Load Balancer Controller with least-privilege IAM to provision ALB/NLB resources from approved Ingress/Service definitions. Confirm:

- Subnet discovery tags and available IP addresses.
- Public versus internal load balancer scheme.
- Security groups and target group health.
- ACM certificate and DNS ownership.
- Controller IAM permissions and cluster name.
- Target type instance versus ip and VPC CNI readiness.
- Cost allocation tags and lifecycle cleanup.

Do not expose Argo CD UI publicly without reviewed authentication, network restrictions and TLS.

## 18. Bootstrap Argo CD safely

Recommended bootstrap sequence:

~~~text
Terraform provisions VPC, EKS, node groups and IAM
             |
Install critical EKS add-ons and network access
             |
Bootstrap pinned Argo CD chart in controlled namespace
             |
Configure AppProject and repository credentials
             |
Create root Application pointing to protected GitOps revision
             |
Argo CD manages platform add-ons and applications
             |
Remove ad-hoc bootstrap ownership conflicts
~~~

The initial Argo CD installation is a chicken-and-egg problem: Terraform/Helm or a controlled bootstrap job can install Argo CD, then GitOps takes ownership. Define a single owner for each resource after handoff.

## 19. Argo CD AppProject example

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: eks-staging-platform
  namespace: argocd
spec:
  description: Approved EKS staging platform resources
  sourceRepos:
    - https://gitlab.example.internal/platform/gitops.git
  destinations:
    - namespace: demo-staging
      server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: ""
      kind: ServiceAccount
~~~

This example is intentionally narrow. Add only approved resource kinds. Actual platform add-ons that need cluster-scoped resources should use a **separate privileged platform AppProject**, not broaden the application project.

## 20. Argo CD Application example

~~~yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-web-staging
  namespace: argocd
spec:
  project: eks-staging-platform
  source:
    repoURL: https://gitlab.example.internal/platform/gitops.git
    targetRevision: main
    path: gitops/clusters/eks-staging/apps/demo-web
  destination:
    server: https://kubernetes.default.svc
    namespace: demo-staging
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
    syncOptions:
      - CreateNamespace=false
~~~

Pre-create the namespace and grant only necessary destination permissions. Automatic sync occurs after approved Git merge; a separate manual CI job cannot hold Argo CD auto-sync after merge unless the GitOps design explicitly gates reconciliation.

## 21. GitLab pipeline for infrastructure and GitOps

~~~yaml
stages: [validate, plan, propose]

terraform_validate:
  stage: validate
  image: registry.example.internal/ci/terraform:PINNED_DIGEST
  script:
    - terraform -chdir=infra/environments/staging fmt -check
    - terraform -chdir=infra/environments/staging init -backend=false
    - terraform -chdir=infra/environments/staging validate

terraform_plan:
  stage: plan
  image: registry.example.internal/ci/terraform:PINNED_DIGEST
  script:
    - ./ci/plan-staging.sh
  artifacts:
    paths: [staging.tfplan]
    expire_in: 1 day
    access: maintainer

propose_gitops:
  stage: propose
  image: registry.example.internal/ci/gitlab-client:PINNED_DIGEST
  script:
    - ./ci/propose-gitops-mr.sh
~~~

This is a pipeline skeleton: approved images, plan script, GitLab feature compatibility and OIDC-based AWS credentials must be supplied. Terraform plans can contain sensitive data; restrict artifact access and retention. Keep production apply behind a separately approved deployment process.

## 22. Observability and SRE baseline

Capture:

- EKS API server availability, error rate and audit/control-plane logs.
- Managed node group health and node Ready status.
- VPC CNI IP allocation errors and subnet free IPs.
- CoreDNS error rate, latency and saturation.
- kube-proxy/Service connectivity and load balancer target health.
- EBS CSI provisioning and attach/detach failures.
- Argo CD Application health, sync failures and drift.
- Cluster autoscaling, pending Pods, CPU/memory and disk pressure.
- IAM AccessDenied and unusual API access.
- AWS spend by cluster, node group, NAT, load balancer and storage.

Enable EKS control-plane logs according to organizational retention and security policy. Use Prometheus/Grafana, CloudWatch or approved telemetry platform. Do not enable high-cardinality logging or metrics without capacity and cost planning.

## 23. Security baseline

- Private endpoint or restricted public API access.
- EKS access entries and least-privilege Kubernetes RBAC.
- Cloud IAM workload identity; no long-lived static AWS keys in Pods.
- Encryption at rest for EBS and Kubernetes Secrets where configured.
- Pod Security Admission and approved admission policies.
- Signed, digest-pinned container images and trusted provenance.
- NetworkPolicy enforcement with a compatible CNI implementation.
- Restricted Argo CD AppProjects and protected GitOps repositories.
- IMDS exposure controls on nodes and Pods.
- Regular EKS, add-on and node AMI patching.
- Centralized audit logging and incident runbooks.

NetworkPolicy behavior depends on the installed CNI and configuration. Do not assume creating a NetworkPolicy automatically enforces isolation on every EKS networking setup.

## 24. Lab A — AWS account and preflight

1. Select the approved staging AWS SSO profile and region.
2. Confirm account ID and assumed role.
3. Check EKS, VPC and EC2 quotas.
4. Confirm CIDR allocation and DNS/network requirements.
5. Review cost estimate and teardown owner.

**Pass:** the correct AWS account/region and resource boundaries are documented.

## 25. Lab B — Terraform VPC plan

1. Pin Terraform and provider versions.
2. Configure encrypted remote state and locking.
3. Create multi-AZ VPC and subnet design.
4. Validate subnet tags, routes and NAT/endpoints.
5. Review terraform plan for unexpected changes.
6. Obtain independent approval before apply.

**Pass:** no overlapping CIDRs or unintended public resources.

## 26. Lab C — EKS cluster provisioning

1. Select a supported Kubernetes version and module release.
2. Configure private API endpoint and approved access path.
3. Provision EKS control plane and managed node group.
4. Validate cluster ACTIVE and node group ACTIVE.
5. Record endpoint, subnets, security groups and version.
6. Verify cluster can be accessed from approved network.

~~~bash
aws eks describe-cluster --name demo-eks-staging --region us-east-1   --query 'cluster.{Status:status,Version:version,Endpoint:endpoint}'
aws eks list-nodegroups --cluster-name demo-eks-staging --region us-east-1
~~~

**Pass:** healthy control plane and Ready nodes in intended AZs.

## 27. Lab D — Access entries and least privilege

1. Create a staging operator access entry through approved IaC.
2. Associate only required access permissions.
3. Test read-only kubectl operations.
4. Verify unauthorized namespace or cluster operations are denied.
5. Document break-glass recovery.
6. Review CloudTrail evidence.

**Pass:** expected access succeeds and excessive access is denied.

## 28. Lab E — Core EKS add-ons

1. Validate VPC CNI, CoreDNS and kube-proxy.
2. Install/verify approved EBS CSI Driver.
3. Check add-on version compatibility.
4. Deploy synthetic DNS and network tests.
5. Inspect Pod IP assignment and node pressure.
6. Record failure indicators and alerts.

**Pass:** Pods receive networking, DNS works and storage components are healthy.

## 29. Lab F — EKS workload identity

1. Choose IRSA or EKS Pod Identity.
2. Create a scoped synthetic S3/Secrets Manager permission.
3. Bind the approved ServiceAccount identity.
4. Test an authorized read.
5. Test an unauthorized AWS action.
6. Verify no static credentials were injected.

**Pass:** cloud IAM boundaries work for the intended Pod identity.

## 30. Lab G — Storage and AZ behavior

1. Create a synthetic PVC using approved EBS StorageClass.
2. Deploy a test StatefulSet.
3. Observe PV topology and Pod scheduling.
4. Attempt rescheduling to an incompatible AZ in staging.
5. Confirm topology constraints and failure behavior.
6. Delete test data using approved cleanup procedure.

**Pass:** operators understand zonal EBS constraints and safe recovery options.

## 31. Lab H — Ingress and target health

1. Deploy a synthetic HTTP Service.
2. Configure internal ALB ingress with approved annotations.
3. Verify controller IAM and subnet discovery.
4. Test health checks and target registration.
5. Review TLS/DNS requirements and security groups.
6. Remove test ingress and confirm load balancer cleanup.

**Pass:** traffic reaches healthy targets without accidental public exposure.

## 32. Lab I — Argo CD bootstrap

1. Install pinned Argo CD into its dedicated namespace.
2. Configure repository credentials securely.
3. Create narrow AppProject.
4. Create staging root Application.
5. Verify initial sync and resource ownership.
6. Record bootstrap-to-GitOps handoff.

**Pass:** Argo CD reconciles only approved source and destination resources.

## 33. Lab J — GitLab secure deployment

1. Build and verify an immutable synthetic image.
2. Open a protected GitOps MR changing digest.
3. Obtain required approvals.
4. Merge and observe Argo CD sync.
5. Confirm Pod imageID and readiness.
6. Revert the digest through an approved MR and verify recovery.

**Pass:** CI does not require broad production kubeconfig or admin access.

## 34. Lab K — Node failure and rescheduling

1. Deploy multiple replicas with topology spread constraints.
2. Cordon/drain one disposable staging node under approved conditions.
3. Observe Pod rescheduling and service health.
4. Verify PodDisruptionBudget behavior.
5. Restore node or managed group capacity.
6. Record recovery time and capacity headroom.

**Pass:** workload remains available within the defined staging SLO.

## 35. Lab L — Cluster observability

1. Enable approved control-plane log categories.
2. Deploy metrics collection.
3. Validate node, Pod, DNS and CNI dashboards.
4. Generate a synthetic scheduling failure.
5. Verify alert routing and incident evidence.
6. Review telemetry retention and estimated cost.

**Pass:** an operator can detect and diagnose the failure without relying on ad-hoc cluster access.

## 36. Lab M — Add-on compatibility and upgrade rehearsal

1. Inventory EKS, add-on and node versions.
2. Check supported Kubernetes version skew.
3. Review deprecations and API compatibility.
4. Rehearse add-on upgrade in staging.
5. Validate DNS, CNI, storage and application health.
6. Record rollback constraints and follow-up.

**Pass:** compatibility checks and post-upgrade smoke tests succeed.

## 37. Lab N — EKS access outage tabletop

1. Simulate private endpoint inaccessibility from a test runner.
2. Separate DNS/routing failures from IAM authorization.
3. Verify approved break-glass access path.
4. Restore network reachability without opening broad public CIDRs.
5. Validate kubectl and Argo CD connectivity.
6. Record time to diagnose and recover.

**Pass:** access recovery does not compromise endpoint security.

## 38. Lab O — Cost and teardown acceptance

1. Inventory cluster, node groups, load balancers, NAT, EBS and logs.
2. Estimate hourly and monthly run rate.
3. Identify idle resources and unused storage.
4. Review termination protection and cleanup dependencies.
5. Tear down only the disposable environment with explicit approval.
6. Verify cloud resources and Terraform state are reconciled.

**Pass:** no orphaned chargeable test resources remain.

## 39. Troubleshooting — sixteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | EKS cluster creation fails | IAM/quota/subnet errors | Review EKS events and Terraform plan |
| 2 | kubectl timeout | Private endpoint DNS/routing | Verify approved network path |
| 3 | kubectl Unauthorized | Wrong AWS identity/access entry | Check authentication and IAM role |
| 4 | kubectl Forbidden | Kubernetes RBAC | Correct scoped authorization |
| 5 | Nodes NotReady | Bootstrap/CNI/network | Inspect node and kube-system events |
| 6 | Pods Pending | CPU, taints, topology or IPs | Inspect scheduler and capacity |
| 7 | VPC CNI cannot allocate IP | Subnet exhaustion/ENI limits | Expand approved IP capacity |
| 8 | CoreDNS unavailable | Scheduling/network/upstream DNS | Restore DNS and capacity |
| 9 | EBS PVC Pending | CSI IAM/topology | Validate driver, StorageClass and AZ |
| 10 | ALB not created | IAM/subnet tags/controller | Inspect controller logs and events |
| 11 | ALB unhealthy targets | Health check/SG/readiness | Repair network and probes |
| 12 | IRSA AccessDenied | OIDC trust/annotation/IAM | Fix scoped trust |
| 13 | Pod Identity fails | Association/agent/trust | Validate chosen identity model |
| 14 | Argo CD OutOfSync | Git revision/permissions | Correct GitOps desired state |
| 15 | Terraform state locked | Concurrent apply/stale lock | Confirm owner before safe unlock |
| 16 | Cost spike | NAT, LB, nodes, logs or EBS | Attribute and rightsize safely |

## 40. Production runbook — EKS bootstrap

1. Confirm approved account, region, cluster name, CIDR and Terraform backend.
2. Review and approve infrastructure plan.
3. Provision VPC, IAM, EKS and managed node groups.
4. Validate API access, node readiness, CNI, CoreDNS and kube-proxy.
5. Install storage/ingress/identity/observability add-ons.
6. Bootstrap pinned Argo CD and scoped AppProjects.
7. Reconcile GitOps platform and application layers.
8. Record security, availability, cost and recovery evidence.

## 41. Production runbook — API endpoint unavailable

1. Determine whether outage affects all clients or only one network.
2. Check AWS EKS cluster status and control-plane health.
3. Validate private endpoint DNS and route connectivity.
4. Confirm AWS IAM identity and access entries.
5. Check VPN, Direct Connect, VPC endpoints and security groups.
6. Restore approved connectivity; do not open public access indiscriminately.
7. Verify Argo CD and operational access.
8. Document impact and recovery time.

## 42. Production runbook — node or Pod networking incident

1. Inspect affected nodes, Pods, scheduler events and CNI health.
2. Check subnet free IPs, ENI allocation, security groups and routes.
3. Check node resource pressure, taints and managed node group status.
4. Restore capacity or networking through approved changes.
5. Verify DNS, Service connectivity and application SLOs.
6. Preserve logs and event timeline for RCA.

## 43. Production runbook — failed GitOps platform rollout

1. Freeze further promotions and identify GitOps commit.
2. Inspect Argo CD Application status, events and policy denials.
3. Confirm whether failure is image, add-on, IAM, network or admission.
4. Revert approved GitOps revision or roll forward safely.
5. Restore platform add-on readiness before application retries.
6. Validate actual running digest and health.
7. Record recovery and preventive tests.

## 44. Production runbook — safe EKS upgrade

1. Inventory current control-plane, node, add-on and workload versions.
2. Review AWS support window and deprecated Kubernetes APIs.
3. Confirm backups, capacity, PDBs and application compatibility.
4. Upgrade staging control plane and add-ons using supported sequence.
5. Roll managed nodes in controlled batches.
6. Verify DNS, CNI, storage, ingress, GitOps and application SLOs.
7. Repeat in production through approved change window.
8. Document recovery options: EKS control-plane minor-version downgrade is not generally supported, so design forward recovery and rollback at compatible component layers.

## 45. Evidence template

~~~text
Change / cluster ID:
AWS account, region and VPC:
Terraform revision, plan and approvers:
EKS version, endpoint mode and access entries:
Managed node groups, AZs and instance types:
VPC CNI, CoreDNS, kube-proxy and CSI versions:
Workload identity model and IAM review:
Argo CD revision and AppProject:
GitLab pipeline and immutable image digest:
Ingress/storage/network validation:
Observability and audit logging:
Failure injection and recovery time:
Cost estimate and chargeback tags:
DR and upgrade readiness:
Evidence archive and owner:
~~~

## 46. Scored operational acceptance

| Domain | Points | Evidence |
| --- | ---: | --- |
| Architecture and Terraform governance | 20 | Reviewed multi-AZ design and plan |
| IAM, access and workload identity | 20 | Scoped grants and denied tests |
| Networking, nodes and storage | 20 | CNI/DNS/PVC/ingress validation |
| Argo CD and GitLab delivery | 15 | Protected GitOps release |
| Observability and security | 15 | Logs, alerts and admission checks |
| Reliability, upgrade and FinOps | 10 | Recovery drill and cost review |
| **Total** | **100** | |

**Pass:** at least **85/100** and no critical failure: wrong AWS account, uncontrolled public endpoint, overbroad cluster-admin, plaintext credentials, unreviewed infrastructure apply, or unrecoverable control-plane access.

## 47. Final acceptance checklist

- [ ] AWS account, region and cluster identity verified.
- [ ] Terraform backend encryption, locking and recovery reviewed.
- [ ] VPC CIDR, AZs, subnets and IP capacity documented.
- [ ] EKS endpoint access and access entries restricted.
- [ ] Managed nodes healthy and capacity headroom validated.
- [ ] VPC CNI, CoreDNS, kube-proxy and CSI functional.
- [ ] IRSA or EKS Pod Identity permissions scoped and tested.
- [ ] Storage topology and load balancer health verified.
- [ ] Argo CD bootstrapped with restricted AppProjects.
- [ ] GitLab promotions use protected GitOps revisions.
- [ ] Workloads deploy verified immutable digests.
- [ ] Observability and control-plane audit logging operational.
- [ ] Failure recovery and upgrade rehearsal documented.
- [ ] Fifteen labs have pass/fail evidence.
- [ ] Cost, cleanup and ownership approved.

## 48. Knowledge check

1. Which EKS components are AWS-managed and which remain customer-managed?
2. Why does a private-only EKS API endpoint require a network access design?
3. How do EKS access entries differ from Kubernetes RBAC?
4. What is the difference between IRSA and EKS Pod Identity?
5. Why can VPC CNI IP exhaustion leave Pods Pending?
6. Why is EBS AZ affinity important for stateful workloads?
7. How should Terraform bootstrap transition to Argo CD ownership?
8. Why should GitLab not need cluster-admin to promote application images?
9. What are the limitations of control-plane rollback during EKS upgrades?
10. What evidence proves an EKS cluster is operationally ready?

## 49. References

- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [EKS Cluster Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Networking](https://docs.aws.amazon.com/eks/latest/userguide/eks-networking.html)
- [Amazon VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [EBS CSI Driver](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/)
- [Terraform AWS EKS Module](https://github.com/terraform-aws-modules/terraform-aws-eks)
- [Argo CD Documentation](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 066 complete.** Next: **Chapter 067 — EKS Managed Node Groups, Karpenter and Production Capacity Automation**.