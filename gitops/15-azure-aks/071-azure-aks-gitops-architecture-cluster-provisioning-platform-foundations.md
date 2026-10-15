# Chapter 071 — Azure AKS GitOps Architecture, Cluster Provisioning and Platform Foundations

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 15:** Azure Kubernetes Service (AKS)  
**Chapter:** 071 / 100  
**Audience:** Platform Engineers, SREs, Cloud Engineers, DevSecOps, Kubernetes Administrators

> **Safety:** Run labs in a dedicated, budget-controlled Azure subscription and nonproduction resource group. AKS, NAT Gateway, Azure Firewall, Private DNS, Log Analytics and node VMs may incur charges. Do not run Terraform destroy against shared or production resources. Confirm the active Azure subscription and kubectl context before any write.

## 1. Learning objectives

By the end of this chapter, you will be able to:

1. Explain AKS control-plane, node-pool and networking responsibilities.
2. Design a resilient multi-AZ AKS landing zone with private API access.
3. Provision AKS using reviewed Terraform and managed identities.
4. Compare Azure CNI Overlay, Azure CNI Pod Subnet and kubenet migration considerations.
5. Configure Microsoft Entra integration, Azure RBAC and Kubernetes RBAC.
6. Configure AKS workload identity and Azure Container Registry access.
7. Bootstrap GitLab CI/CD and Argo CD without granting CI broad cluster credentials.
8. Establish system/user node-pool separation, add-ons and observability.
9. Troubleshoot cluster creation, authentication, networking and image pulls.
10. Validate enterprise operational readiness and a safe teardown plan.

## 2. AKS production reference architecture

~~~text
Microsoft Entra ID / Azure RBAC / PIM
                  |
         Azure subscription
                  |
        Terraform IaC pipeline
                  |
 Resource group / VNet / subnets / NSGs / UDRs
                  |
     Private AKS managed control plane
                  |
         System node pool (AZ spread)
             |           |
          CoreDNS    Argo CD controller
             |           |
       Azure CNI    GitOps reconciliation
             |
      User node pools / autoscaling
             |
   Workload identity / ACR pull
             |
   Application Deployments and Services
             |
 Azure Load Balancer / ingress / Private DNS
             |
 Azure Monitor / Managed Prometheus / Grafana
             |
  Azure Activity Log / Kubernetes audit logs

GitLab CI -> tests, scan, sign -> protected GitOps MR
                                      |
                                  Argo CD
                                      |
                              AKS desired state
~~~

**Ownership boundary:** Terraform owns Azure infrastructure and foundational AKS configuration. Argo CD owns explicitly delegated Kubernetes applications and controllers. AKS owns the managed control plane. Never assign Terraform and Argo CD conflicting ownership of the same Kubernetes resource.

## 3. AKS versus EKS operational differences

| Domain | AKS | EKS |
| --- | --- | --- |
| Cloud identity | Microsoft Entra / Azure managed identity | AWS IAM |
| Workload identity | Microsoft Entra Workload ID federation | IRSA / EKS Pod Identity |
| Networking | Azure CNI Overlay or Pod Subnet | Amazon VPC CNI |
| Image registry | Azure Container Registry | Amazon ECR |
| Node scaling | Cluster Autoscaler; node auto-provisioning where supported | Managed node groups / Karpenter |
| Logging | Azure Monitor / Log Analytics | CloudWatch / CloudTrail |
| Control-plane access | Private/public API endpoint modes | Private/public endpoint modes |
| Storage | Azure Disk CSI / Azure Files CSI | EBS CSI / EFS CSI |

Feature support, defaults and supported Kubernetes versions change. Check the selected AKS region, API version and cluster mode before deploying.

## 4. Enterprise design requirements

- Separate production and nonproduction subscriptions or resource groups as required by policy.
- Define Azure region, supported AZs and recovery region.
- Choose private API access and authorized operational connectivity.
- Use a dedicated system node pool with sufficient resilient capacity.
- Use user node pools for applications with scoped labels, taints and autoscaling.
- Size VNet and node subnets for nodes, Services and growth.
- Design private DNS, outbound egress and Azure service endpoints.
- Restrict control-plane and node access using Microsoft Entra and least privilege.
- Use OIDC issuer and workload identity federation for cloud access.
- Integrate ACR with narrowly scoped image-pull permissions.
- Enforce protected GitOps changes, admission policies and observability.
- Set SLO, RPO/RTO, cost allocation and incident ownership before go-live.

## 5. Prerequisites

- Azure subscription with permission to create AKS, VNets, managed identities and role assignments.
- Azure CLI, Terraform, kubectl, Helm and kubelogin installed.
- GitLab project with protected default branch and approved CI identity.
- Argo CD bootstrap plan and protected GitOps repository.
- Approved IP address ranges, Azure region, Kubernetes version and VM SKUs.
- Azure Policy, Log Analytics and cost budget design.

~~~bash
az login
az account show --output table
az account list --output table
az provider show --namespace Microsoft.ContainerService --query registrationState -o tsv
terraform version
kubectl version --client
helm version
kubelogin --version
~~~

**Stop:** if the subscription, tenant, environment or resource ownership differs from the approved change.

## 6. Azure landing-zone decisions

Create dedicated resource groups for environment-level infrastructure and avoid mixing test and production AKS clusters. Apply required tags such as Environment, Owner, CostCenter and DataClassification.

Use Azure Policy and resource locks deliberately; a lock can also block legitimate Terraform changes or cleanup. Use centrally approved key management, audit retention and budget alarms.

## 7. AKS networking selection

**Azure CNI Overlay:** Pods use an overlay address space distinct from VNet node IPs. It can reduce pressure on VNet subnet IP allocations, but requires correct service and egress planning.

**Azure CNI Pod Subnet:** Pod addresses come from delegated or configured Azure networking subnets under the supported model; plan capacity, routes and policies carefully.

Avoid assuming that changing networking modes is a simple in-place toggle. Migration may require cluster replacement or documented supported steps.

## 8. VNet, subnet and DNS layout

~~~text
vnet-aks-staging (10.40.0.0/16)
  aks-nodes       10.40.0.0/20
  ingress         10.40.16.0/24
  private-endpoints 10.40.17.0/24

Overlay Pod CIDR: 10.244.0.0/16
Service CIDR:     10.96.0.0/16
DNS service IP:   10.96.0.10
~~~

These ranges are illustrative. Validate they do not overlap on-premises networks, peered VNets, VPN/ExpressRoute routes or connected clusters. Actual AKS configuration must follow supported Azure CNI Overlay and private cluster requirements.

## 9. Private cluster connectivity

Private AKS requires a supported network path and DNS resolution for the private API endpoint. Choose an approved management network, VPN, ExpressRoute, private runner or jump-host architecture.

Never work around a private DNS issue by making the production API broadly public. Review private DNS zone ownership and VNet links.

## 10. Terraform project structure

~~~text
aks-foundations/
  terraform/
    versions.tf
    providers.tf
    variables.tf
    network.tf
    identity.tf
    aks.tf
    outputs.tf
    environments/
      staging.tfvars
  gitops/
    bootstrap/
    clusters/aks-staging/
      platform/
      applications/
  ci/
    validate-terraform.sh
    validate-gitops.sh
  runbooks/
    cluster-access.md
    node-pool-recovery.md
    network-dns.md
    gitops-bootstrap.md
~~~

Use remote Terraform state with encryption, access control and locking. Never commit state files, plan files containing secrets or client credentials.

## 11. Terraform provider and variables

~~~hcl
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

variable "subscription_id" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "cluster_name" { type = string }
variable "ssh_public_key" { type = string }
~~~

Pin exact provider constraints according to your approved compatibility matrix. Version examples are not a substitute for testing against the selected AKS region and Azure API.

## 12. Terraform resource group and network

~~~hcl
resource "azurerm_resource_group" "aks" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    Environment = "staging"
    ManagedBy   = "terraform"
  }
}

resource "azurerm_virtual_network" "aks" {
  name                = "vnet-aks-staging"
  address_space       = ["10.40.0.0/16"]
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
}

resource "azurerm_subnet" "nodes" {
  name                 = "snet-aks-nodes"
  resource_group_name  = azurerm_resource_group.aks.name
  virtual_network_name = azurerm_virtual_network.aks.name
  address_prefixes     = ["10.40.0.0/20"]
}
~~~

Network security groups, route tables, NAT and private DNS resources must be added according to the organization's approved network design; this fragment alone is not a hardened landing zone.

## 13. AKS managed identity and role assignments

Use system-assigned or user-assigned managed identity as appropriate. AKS cluster identity and kubelet identity have different permissions and lifecycles.

For a bring-your-own subnet, grant the minimum required subnet permissions to the cluster identity. For ACR pulls, grant the kubelet identity appropriate registry pull permissions under the chosen ACR authorization mode.

Avoid granting Contributor across an entire subscription.

## 14. Terraform AKS cluster example

~~~hcl
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "aks-staging"

  private_cluster_enabled = true
  oidc_issuer_enabled     = true
  workload_identity_enabled = true

  default_node_pool {
    name           = "system"
    vm_size        = "Standard_D4s_v5"
    node_count     = 3
    vnet_subnet_id = azurerm_subnet.nodes.id
    zones          = ["1", "2", "3"]
    only_critical_addons_enabled = true
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    network_plugin_mode = "overlay"
    load_balancer_sku = "standard"
    pod_cidr        = "10.244.0.0/16"
    service_cidr    = "10.96.0.0/16"
    dns_service_ip  = "10.96.0.10"
  }

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
  }

  tags = {
    Environment = "staging"
    ManagedBy   = "terraform"
  }
}
~~~

**Important:** this is a teaching fragment, not a complete deployable enterprise module. Private DNS configuration, subnet role assignments, cluster Kubernetes version, managed add-ons, diagnostics, outbound connectivity, maintenance windows, node OS hardening and provider-specific schema must be reviewed before apply. AZ availability and VM SKU support vary by region. Ensure Terraform arguments are supported by the pinned provider release.

## 15. User node pool example

~~~hcl
resource "azurerm_kubernetes_cluster_node_pool" "apps" {
  name                  = "apps"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D4s_v5"
  mode                  = "User"
  auto_scaling_enabled  = true
  min_count             = 2
  max_count             = 6
  vnet_subnet_id        = azurerm_subnet.nodes.id
  zones                 = ["1", "2", "3"]

  node_labels = {
    "workload-tier" = "applications"
  }
}
~~~

Verify node-pool autoscaling attribute names against the pinned azurerm provider schema. Do not use Spot for all system components. Plan max surge, PodDisruptionBudgets and safe node image updates.

## 16. Terraform review and deployment

~~~bash
terraform -chdir=terraform fmt -check
terraform -chdir=terraform init
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=environments/staging.tfvars -out=staging.tfplan
terraform -chdir=terraform show staging.tfplan
~~~

Apply the approved plan through a protected pipeline. Ensure the executing principal has only the permissions necessary for the infrastructure being created.

## 17. AKS authentication with kubelogin

~~~bash
az account set --subscription SUBSCRIPTION_ID
az aks get-credentials \
  --resource-group rg-aks-staging \
  --name aks-staging \
  --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
kubectl config current-context
kubectl get nodes -o wide
~~~

For a private cluster, these commands must run from an authorized network. Microsoft Entra authentication and Kubernetes authorization are distinct; successfully obtaining a token does not guarantee cluster permissions.

## 18. AKS workload identity federation

Enable the AKS OIDC issuer and workload identity. Create a user-assigned managed identity and federated credential matching the exact Kubernetes ServiceAccount namespace and name.

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: demo-azure-reader
  namespace: demo-staging
  annotations:
    azure.workload.identity/client-id: REPLACE_WITH_MANAGED_IDENTITY_CLIENT_ID
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-azure-reader
  namespace: demo-staging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo-azure-reader
  template:
    metadata:
      labels:
        app: demo-azure-reader
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: demo-azure-reader
      containers:
        - name: app
          image: registry.example.internal/demo/azure-reader@sha256:REPLACE_WITH_REAL_DIGEST
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
~~~

Both client ID and image digest are placeholders. The Pod label is important for supported Azure Workload Identity webhook injection behavior. Configure exact federated credential subject and narrow Azure resource permissions before testing.

## 19. Azure Container Registry integration

Use a private ACR and approved pull authorization for the kubelet identity. With ABAC-enabled registries, role names and authorization semantics may differ from traditional AcrPull assignments. Verify the registry's permission mode.

~~~bash
az acr show --name ACR_NAME --query '{id:id,loginServer:loginServer}' -o json
az aks show -g rg-aks-staging -n aks-staging \
  --query '{identity:identity,kubeletIdentity:identityProfile.kubeletidentity}' -o json
kubectl -n demo-staging get pods
~~~

Never put registry admin credentials in application manifests or Git.

## 20. Argo CD bootstrap and GitOps ownership

Install Argo CD using a pinned, tested Helm chart or approved manifest release. Place Argo CD on stable system capacity with appropriate tolerations and resource requests. Configure SSO, scoped AppProjects, repository credentials and audit logging.

~~~text
Terraform -> AKS cluster, identities, networking, system node pool
       |
Approved bootstrap -> Argo CD CRDs and controller
       |
Argo CD platform AppProject -> networking/security/monitoring add-ons
       |
Argo CD app AppProjects -> namespaces and application workloads
       |
GitLab CI -> signed image digest -> reviewed GitOps MR
       |
Argo CD -> AKS desired state
~~~

Do not configure overlapping Terraform and Argo CD control of the same Helm release or Kubernetes resource.

## 21. GitLab CI validation example

~~~yaml
stages: [validate, policy, plan]

terraform_validate:
  stage: validate
  image: registry.example.internal/ci/terraform:PINNED_DIGEST
  script:
    - terraform -chdir=terraform fmt -check
    - terraform -chdir=terraform init -backend=false
    - terraform -chdir=terraform validate

policy_check:
  stage: policy
  image: registry.example.internal/ci/policy-tools:PINNED_DIGEST
  script:
    - ./ci/validate-aks-security.sh
    - ./ci/validate-network-ranges.sh

terraform_plan:
  stage: plan
  image: registry.example.internal/ci/terraform-azure:PINNED_DIGEST
  script:
    - ./ci/create-approved-plan.sh
~~~

Scripts and internal images are illustrative. Use short-lived GitLab-to-Azure workload identity federation where supported and restrict plan artifacts because they may contain sensitive values. Require manual approval for infrastructure apply.

## 22. Platform observability

Configure Azure Monitor Container Insights or approved managed Prometheus/Grafana stack, AKS diagnostic settings, Azure Activity Logs and workload tracing.

Minimum alerts:

- AKS API reachability and authentication errors.
- System node pool insufficient Ready nodes.
- Pod Pending duration and autoscaler failures.
- CoreDNS errors and Azure CNI networking failures.
- Ingress target health and TLS errors.
- Disk/Files CSI provisioning and attachment errors.
- Argo CD Degraded/OutOfSync beyond grace period.
- Workload identity token exchange failures.
- Unexpected Azure role assignment changes.
- Cost budget threshold and log ingestion failures.

Metric names and capabilities vary by Azure Monitor configuration. Validate deployed data before creating alerts.

## 23. AKS security baseline

Use private API access, Microsoft Entra integration, least-privilege Azure/Kubernetes RBAC, workload identity, Azure Policy and Pod Security Admission where compatible. Enforce signed image policy through an approved admission controller, encrypt disks and secrets, restrict egress and protect cluster admin credentials.

Do not assume Azure RBAC alone enforces all Kubernetes admission and Pod security requirements.

## 24. AKS upgrades and maintenance

Before upgrades, check target Kubernetes version availability, deprecated APIs, admission webhooks, CNI/CSI compatibility, node pool surge capacity, PodDisruptionBudgets and backups.

~~~bash
az aks get-upgrades -g rg-aks-staging -n aks-staging -o table
az aks show -g rg-aks-staging -n aks-staging --query kubernetesVersion -o tsv
kubectl get nodes -o wide
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
~~~

AKS control-plane downgrade is not a routine rollback strategy. Rehearse staged upgrades and forward recovery in a separate environment.

## 25. Lab A — Azure subscription and security preflight

1. Authenticate to the approved tenant.
2. Confirm subscription, region, resource group and permissions.
3. Inspect quota and regional AZ support.
4. Verify cost budget and tags.
5. Review private API connectivity.
6. Archive redacted evidence.

**Pass:** all resources target the approved nonproduction subscription.

## 26. Lab B — Terraform landing zone

1. Create staging VNet and node subnet using Terraform.
2. Verify CIDRs do not overlap peered/on-prem networks.
3. Review NSG, routing and outbound connectivity design.
4. Validate tags and remote state controls.
5. Review plan through protected MR.
6. Confirm expected Azure resources.

**Pass:** network is reviewable, repeatable and isolated.

## 27. Lab C — AKS cluster provisioning

1. Pin approved Terraform provider and AKS version.
2. Provision private AKS with managed identity.
3. Enable OIDC issuer and workload identity.
4. Verify control-plane provisioning status.
5. Check system node readiness.
6. Record cluster version and configuration.

**Pass:** private AKS is reachable from authorized network.

## 28. Lab D — Microsoft Entra access and kubelogin

1. Obtain kubeconfig from approved operator workstation.
2. Convert kubeconfig to Azure CLI login mode.
3. Verify read-only namespace access.
4. Attempt unauthorized Secret read.
5. Capture authorization denial.
6. Confirm break-glass procedure without using it routinely.

**Pass:** authentication and authorization boundaries are proven.

## 29. Lab E — System and user node pools

1. Verify system node pool and AZ placement.
2. Create user node pool with autoscaling.
3. Deploy synthetic workload with user-pool affinity.
4. Observe scheduling and scale-up.
5. Verify critical system Pods remain on stable capacity.
6. Record scale-down and cost impact.

**Pass:** workloads and system controllers have clear capacity ownership.

## 30. Lab F — Azure CNI and DNS

1. Inspect Azure CNI networking mode.
2. Record VNet subnet, Pod CIDR and Service CIDR.
3. Deploy disposable DNS test Pod.
4. Resolve internal Service and approved external name.
5. Test network policy where enforced.
6. Document IP and DNS failure signatures.

**Pass:** Pod networking and DNS function as designed.

## 31. Lab G — Managed identity workload federation

1. Create user-assigned managed identity.
2. Configure federated credential for exact ServiceAccount subject.
3. Apply labeled Pod and ServiceAccount.
4. Test authorized Azure API operation.
5. Test denied operation and unrelated ServiceAccount.
6. Revoke test association.

**Pass:** no static Azure client secret is required.

## 32. Lab H — ACR pull integration

1. Create or identify approved private ACR.
2. Grant kubelet identity narrowly scoped pull access.
3. Push synthetic digest-pinned image.
4. Deploy it to AKS.
5. Remove pull access in staging and observe ImagePullBackOff.
6. Restore permission and verify recovery.

**Pass:** image pulls depend on controlled identity, not registry admin credentials.

## 33. Lab I — Argo CD bootstrap

1. Install pinned Argo CD release.
2. Configure SSO and restricted AppProjects.
3. Register approved GitOps repository.
4. Deploy synthetic application through Argo CD.
5. Observe sync, health and Git revision.
6. Verify unauthorized project destination is rejected.

**Pass:** GitOps reconciliation is operational and scoped.

## 34. Lab J — GitLab protected promotion

1. Build and test synthetic application.
2. Scan and sign immutable image digest.
3. Propose GitOps manifest update through MR.
4. Obtain CODEOWNERS approval.
5. Merge and verify Argo CD sync.
6. Revert via reviewed MR.

**Pass:** no direct unreviewed CI cluster-admin deployment occurs.

## 35. Lab K — Private API connectivity failure

1. Verify private AKS endpoint DNS and authorized access path.
2. Simulate a DNS misconfiguration in an isolated test resolver.
3. Observe kubectl connectivity failure.
4. Confirm AKS control plane remains healthy.
5. Restore private DNS path.
6. Record incident evidence.

**Pass:** connectivity is restored without exposing the API publicly.

## 36. Lab L — Workload identity failure injection

1. Remove a narrow test Azure role assignment.
2. Trigger authorized synthetic API request.
3. Observe authorization failure.
4. Inspect workload identity federation and Azure Activity Logs.
5. Restore minimum required permission.
6. Verify successful request.

**Pass:** failure is diagnosed without broad Contributor grants.

## 37. Lab M — Node pool pressure and recovery

1. Create synthetic CPU pressure using resource requests.
2. Observe Pending Pods and autoscaler behavior.
3. Review VM SKU availability and Azure quota.
4. Simulate a constrained max-count setting.
5. Restore approved scaling limit.
6. Measure scheduling recovery.

**Pass:** capacity recovery meets staging objective.

## 38. Lab N — Audit and monitoring

1. Enable approved AKS diagnostic settings.
2. Generate authorized and denied API requests.
3. Verify Azure Activity Log and Kubernetes audit evidence.
4. Validate node and Pod metrics.
5. Trigger a synthetic alert.
6. Verify alert routing and retention.

**Pass:** security and reliability events are observable.

## 39. Lab O — AKS bootstrap recovery

1. Capture Terraform state backup and approved GitOps revision.
2. Simulate disposable Argo CD configuration loss.
3. Reinstall pinned Argo CD release.
4. Restore repository and AppProject configuration.
5. Reconcile synthetic application.
6. Verify no data or secret leakage.

**Pass:** GitOps bootstrap can be recovered from documented sources.

## 40. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe remediation |
| --- | --- | --- | --- |
| 1 | AKS creation fails | Region, quota, permission | Inspect Azure operation |
| 2 | Subnet join fails | Missing network role | Grant scoped subnet permission |
| 3 | Private API unreachable | DNS/routing/VPN | Restore private access path |
| 4 | kubectl authentication fails | kubelogin/tenant mismatch | Verify Azure CLI identity |
| 5 | kubectl Forbidden | Azure/Kubernetes RBAC | Correct scoped assignment |
| 6 | System Pods Pending | System pool pressure | Restore system capacity |
| 7 | User nodes do not scale | Autoscaler limit/quota | Review max count and quota |
| 8 | Pod networking fails | Azure CNI/subnet/routing | Inspect CNI and IP plan |
| 9 | DNS resolution fails | CoreDNS/private DNS | Repair DNS dependency |
| 10 | ACR ImagePullBackOff | Kubelet identity/pull role | Restore registry access |
| 11 | Workload identity fails | Federation subject/client ID | Fix exact identity binding |
| 12 | Azure API AccessDenied | Missing resource role | Grant minimum required role |
| 13 | Argo CD sync denied | AppProject/admission | Correct GitOps policy |
| 14 | Ingress not reachable | LB/NSG/DNS/TLS | Trace target health |
| 15 | PVC Pending | CSI/storage class/zone | Repair provisioning |
| 16 | Audit logs missing | Diagnostic settings | Restore log export |
| 17 | Node upgrade blocked | PDB/capacity | Restore surge headroom |
| 18 | Terraform drift | Manual Azure changes | Reconcile through reviewed IaC |

## 41. Runbook — AKS cluster provisioning failure

1. Verify subscription, region, resource provider registration and quota.
2. Inspect Azure deployment operation and Terraform plan.
3. Check VNet/subnet role assignments and DNS prerequisites.
4. Validate selected VM SKU and AZ support.
5. Repair only failed dependencies.
6. Reapply reviewed Terraform plan.
7. Record root cause and cost impact.

## 42. Runbook — AKS private API access outage

1. Confirm AKS control-plane provisioning state.
2. Check operator identity, kubelogin and current context.
3. Resolve private endpoint DNS from approved management network.
4. Validate VNet links, routing and VPN/ExpressRoute.
5. Restore private connectivity without public CIDR bypass.
6. Verify kubectl and Argo CD access.
7. Record recovery evidence.

## 43. Runbook — workload identity incident

1. Identify ServiceAccount, federated credential and managed identity.
2. Check issuer, subject, audience and client ID.
3. Inspect Azure role assignments and token exchange errors.
4. Restore narrowly scoped identity configuration.
5. Validate permitted and denied operations.
6. Rotate any exposed credentials and preserve audit trail.
7. Record preventive checks.

## 44. Runbook — node pool and autoscaling failure

1. Identify Pending Pods, requests, taints and topology.
2. Inspect system/user node pool health and autoscaler events.
3. Validate Azure quota, VM SKU availability and subnet capacity.
4. Restore approved scaling range or compatible SKU.
5. Check PodDisruptionBudgets and application readiness.
6. Verify cost and availability objectives.
7. Update capacity forecast.

## 45. Runbook — GitOps bootstrap recovery

1. Freeze unauthorized direct cluster modifications.
2. Confirm AKS access and healthy system capacity.
3. Restore pinned Argo CD controller and CRDs.
4. Reapply approved AppProjects, repository trust and Applications.
5. Reconcile platform components before applications.
6. Validate admission, secrets and workload identities.
7. Confirm application SLO and record Git revision.

## 46. Evidence template

~~~text
Change / lab ID:
Azure tenant and subscription:
Resource group, region and AKS cluster:
Terraform state and plan:
AKS version and private endpoint mode:
System/user node pools and VM SKUs:
VNet, subnets, Pod CIDR and Service CIDR:
Microsoft Entra and Kubernetes RBAC:
Managed identity and federated credential:
ACR pull permission and image digest:
Argo CD project and Git revision:
GitLab pipeline, signing and approval:
Azure Monitor / audit evidence:
Incident simulation and recovery time:
Cost estimate and cleanup status:
Owner and reviewer:
~~~

## 47. Scored operational readiness

| Domain | Points | Required evidence |
| --- | ---: | --- |
| Azure landing zone and Terraform | 20 | Approved IaC, network, remote state |
| AKS cluster and node-pool design | 20 | Healthy control plane, capacity |
| Identity, RBAC and ACR security | 20 | Authorized/denied access tests |
| GitLab/Argo CD governance | 15 | Protected promotion and rollback |
| Networking and private API access | 10 | DNS and connectivity tests |
| Observability and recovery | 10 | Alerts and bootstrap recovery |
| FinOps and documentation | 5 | Budget and cleanup |
| **Total** | **100** | |

**Pass:** at least 85/100 with no critical failures: wrong subscription, unreviewed public API exposure, unscoped administrator access, leaked credentials, or inability to recover GitOps bootstrap.

## 48. Final acceptance checklist

- [ ] Approved subscription, region and budget confirmed.
- [ ] Terraform state secured and reviewed.
- [ ] VNet/subnet and nonoverlapping CIDRs validated.
- [ ] AKS private API connectivity tested.
- [ ] System/user node pool separation established.
- [ ] Azure CNI and CoreDNS health verified.
- [ ] Microsoft Entra authentication and RBAC tested.
- [ ] Workload identity federation scoped and verified.
- [ ] ACR pull permission restricted to required identities.
- [ ] Argo CD bootstrap and AppProjects protected.
- [ ] GitLab CI promotes reviewed signed image digests.
- [ ] Azure Monitor and audit logging enabled.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks validated.
- [ ] Cost and teardown plan approved.

## 49. Knowledge check

1. How do AKS and EKS workload identities differ?
2. Why separate system and user node pools?
3. When would Azure CNI Overlay be preferable to Pod Subnet?
4. Why is private DNS essential for a private AKS cluster?
5. How do Microsoft Entra authentication and Kubernetes RBAC interact?
6. Why must the workload identity federated credential match the ServiceAccount?
7. What role does the kubelet identity play in ACR pulls?
8. Why should GitLab CI not have persistent cluster-admin credentials?
9. What is the safe recovery approach for a failed AKS upgrade?
10. Which evidence demonstrates that the AKS foundation is production-ready?

## 50. References

- [Azure Kubernetes Service documentation](https://learn.microsoft.com/azure/aks/)
- [AKS baseline architecture](https://learn.microsoft.com/azure/architecture/reference-architectures/containers/aks/baseline-aks)
- [AKS private clusters](https://learn.microsoft.com/azure/aks/private-clusters)
- [Azure CNI Overlay](https://learn.microsoft.com/azure/aks/azure-cni-overlay)
- [AKS workload identity](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [AKS Microsoft Entra integration](https://learn.microsoft.com/azure/aks/enable-authentication-microsoft-entra-id)
- [AKS Azure RBAC](https://learn.microsoft.com/azure/aks/manage-azure-rbac)
- [AKS node pools](https://learn.microsoft.com/azure/aks/create-node-pools)
- [AKS monitoring](https://learn.microsoft.com/azure/aks/monitor-aks)
- [Terraform AzureRM provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 071 complete — Part 15: Azure AKS started.**

**Next:** Chapter 072 — AKS Node Pools, Autoscaling, Scheduling and Production Capacity Management.