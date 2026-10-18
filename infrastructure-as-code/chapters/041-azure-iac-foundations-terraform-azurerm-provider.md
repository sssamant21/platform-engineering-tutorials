# Chapter 041 — Azure Infrastructure as Code Foundations and Terraform AzureRM Provider

**Part 09 — Azure Infrastructure as Code · Chapter 041/120**  
**Audience:** SRE, DBRE, Platform Engineers, DevSecOps, Cloud Security  
**Prerequisites:** Chapters 001–040 · **Tools:** Terraform >=1.7, Python >=3.9, Bash; Azure CLI only for optional integration  
**Lab boundary:** The runnable lab uses Terraform's built-in \`terraform_data\` resource and does not contact Azure. AzureRM examples are **review-only** and must not be applied without account, cost, security and change approval.

## 1. Mission and outcomes

Establish a safe, reproducible Azure Terraform foundation for subscriptions, tenants, management groups, resource groups, provider configuration, identity, state, tags, policy, networking and operational evidence. By completion, distinguish Azure control-plane hierarchy and RBAC scopes, configure the AzureRM provider correctly, choose managed identity or workload identity federation, protect state, test environment boundaries and implement fail-closed preflight gates.

The critical rule: **a successful Terraform plan is not proof of authorized identity, correct subscription, compliance or production readiness**.

## 2. Azure hierarchy and architecture

~~~text
Microsoft Entra tenant
   |
Management group hierarchy / Azure Policy / RBAC guardrails
   |
Azure subscription (billing, quotas, provider registrations)
   |
Resource groups (lifecycle, RBAC, policy scope)
   |
Azure resources (VNet, AKS, VMSS, Storage, Azure SQL, PostgreSQL)
   |
Monitoring: Azure Monitor, Activity Log, Log Analytics, Defender
   |
SRE/DBRE acceptance: identity, backups, restore, SLO, cost, audit
~~~

An Entra tenant is the identity boundary, while a subscription is an Azure resource and billing boundary. Resource groups organize resources but are **not** isolation equivalent to separate subscriptions. Management groups allow hierarchical policy/RBAC governance. Azure Resource Manager (ARM) evaluates requests through identities, RBAC and policy; AzureRM is Terraform's provider for ARM resource management.

## 3. Provider configuration and versioning

Terraform provider constraints and lockfiles govern reproducibility. Pin a reviewed AzureRM major/minor line, commit \`.terraform.lock.hcl\`, and upgrade only after compatibility tests. AzureRM provider 4.x requires an explicit subscription ID for many workflows; configure \`subscription_id\` deliberately and verify your installed version's requirements. Use provider aliases for approved cross-subscription operations; every alias must be explicitly mapped into child modules when needed.

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
  tenant_id       = var.tenant_id
}
~~~

This provider example requires approved credentials and an actual subscription. The offline lab below intentionally has **no AzureRM provider dependency**.

## 4. Authentication: humans, CI and workloads

Prefer Microsoft Entra Workload ID federation/OIDC for CI and managed identities for Azure-hosted workloads. Use Azure CLI or a tightly scoped service principal for interactive/sandbox work. Avoid long-lived client secrets and certificates in Git, Terraform state or CI logs. A service principal must be assigned only necessary Azure RBAC roles at the narrowest feasible scope. For CI, constrain federated credential issuer, audience and subject to a specific repository, branch/environment and workflow context as appropriate.

~~~bash
az login
az account show --query '{subscription:id,tenant:tenantId,name:name}' -o json
az account list --query '[].{name:name,id:id,isDefault:isDefault}' -o table
az account set --subscription "APPROVED-SUBSCRIPTION-ID"
az account show --query id -o tsv
~~~

Never rely on the default subscription in automation. Verify tenant and subscription before every plan/apply. In production, use protected environments, separate plan/apply permissions and short-lived tokens.

## 5. Azure RBAC, Policy and resource providers

Azure RBAC role assignments have a principal, role definition and scope. Built-in Contributor is often too broad for individual module responsibilities. Design custom roles carefully, especially \`Microsoft.Authorization/roleAssignments/write\`, Key Vault permissions and managed identity assignment. Azure Policy can audit, deny, modify or deployIfNotExists according to definition and assignment; evaluate exemptions and remediation effects separately.

Resource provider registration is a subscription-level prerequisite for many services. Registration can require privileges not held by workload deployment roles. Coordinate pre-registration with platform governance instead of granting broad permissions to every CI identity. AzureRM's provider registration behavior varies by version and configuration; review the installed version's \`resource_provider_registrations\` options.

## 6. Terraform state on Azure

Use an Azure Storage account/container backend with secure transport, encryption, restricted network access, blob versioning/soft delete as appropriate, and RBAC-based data-plane authentication. The \`azurerm\` backend and \`azurerm\` provider have separate authentication/configuration surfaces; validate both. Prefer OIDC/Entra auth over account keys or SAS in CI. Azure Blob leases support Terraform state locking. Avoid manually breaking a lease or force-unlocking without incident investigation.

~~~hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "REPLACE_WITH_APPROVED_STORAGE_ACCOUNT"
    container_name       = "tfstate"
    key                  = "prod/platform.tfstate"
    use_azuread_auth     = true
    use_oidc             = true
  }
}
~~~

Backend block values are examples, not provisioned resources. Initialize remote state only after the storage, permissions, network access and recovery procedure are independently prepared. Treat state and plan artifacts as sensitive.

## 7. Naming, tags and environment isolation

Use a consistent resource naming strategy that respects per-service length and character constraints. Tags such as \`Environment\`, \`Owner\`, \`ManagedBy\`, \`CostCenter\`, \`DataClassification\` and \`ChangeTicket\` help operations but do not enforce security by themselves. Apply policy to required tags and allowed regions.

Isolate prod from non-prod by subscription and state when possible; separate managed identities, RBAC, Key Vault access and CI environments. Do not switch \`terraform.tfvars\` from dev to prod against the same state.

## 8. Executable lab layout

~~~text
labs/chapter-041/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/azurerm-resource-group.tf.example
  examples/azurerm-backend.tf.example
  examples/azure-identity-preflight.sh.example
  azure-policy.json
  fixtures/azure-safe.json, azure-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  azure_gate.py, test_azure_gate.py, run-preflight.sh
  runbook.md, acceptance.md, .gitignore
~~~

## 9. Lab A — Offline Azure foundation contract

~~~bash
cd infrastructure-as-code/labs/chapter-041
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter041.tfplan
terraform apply chapter041.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: four \`terraform_data\` resources for subscription identity, governance, state and audit. The second unchanged plan should exit 0. No Azure credentials or provider download is needed.

## 10. Lab B — Policy gate and automated negative tests

~~~bash
python3 azure_gate.py fixtures/azure-safe.json fixtures/plan-safe.json azure-policy.json
python3 azure_gate.py fixtures/azure-unsafe.json fixtures/plan-destructive.json azure-policy.json
python3 -m unittest -v test_azure_gate.py
bash run-preflight.sh
~~~

The safe fixture must pass; the unsafe fixture must fail. Tests exercise tenant/subscription isolation, allowed regions, workload federation, no static secrets, restricted RBAC, Azure Policy, provider registration, secure state, backup, Key Vault, logging, tags and destructive plan actions. The gate validates **declared JSON evidence**, not real Azure policy definitions or live resource inventory.

## 11. Lab C — Optional Azure plan-only exercise

1. Obtain an approved sandbox subscription and cost budget.
2. Verify \`az account show\`, tenant, subscription and deployment principal.
3. Inspect \`examples/azurerm-resource-group.tf.example\` and provider constraints.
4. In a **separate** root, configure reviewed OIDC/managed identity and state backend.
5. Run \`terraform init\`, \`terraform validate\`, \`terraform plan\`; do not apply automatically.
6. Review policy compliance, RBAC, storage backend permissions, resource provider registration and region quotas.
7. Record plan digest, approval, audit and expected cost before any deployment.

## 12. SRE/DBRE production scenarios

| Platform | Azure dependency | Failure scenario | Validation |
|---|---|---|---|
| Azure Database for PostgreSQL | private DNS, delegated subnet, identity | endpoint/DNS failure | connect, query, restore |
| Azure SQL | firewall/private endpoint, Entra auth | RBAC or network deny | auth, failover, PITR |
| AKS | cluster identity, CNI, RBAC | pod identity exchange fails | token, pod health |
| VMSS | image, subnet, managed identity | wrong image or quota | instance health, scale |
| Storage / Blob | network rules, RBAC, leases | state inaccessible or locked | lease and version recovery |
| Key Vault | RBAC, private endpoint, soft delete | secret/key access outage | approved decrypt/retrieve |
| Event Hubs | namespace identity, network | producer 401/timeout | throughput, lag, retry |
| Azure Monitor | diagnostics settings | missing logs | alerts and audit evidence |

## 13. Troubleshooting

| Symptom | Root cause | Safe diagnostic |
|---|---|---|
| \`AuthorizationFailed\` | missing RBAC at scope | inspect principal, role and scope |
| \`SubscriptionNotFound\` | wrong tenant/subscription | check Azure CLI and provider IDs |
| \`MissingSubscriptionRegistration\` | provider not registered | governance-approved registration |
| AzureRM backend 403 | data-plane role, firewall, OIDC | verify blob permissions and network |
| State lease conflict | concurrent Terraform run | identify holder; do not blindly unlock |
| Policy \`RequestDisallowedByPolicy\` | deny assignment | review compliance and exemption |
| Key Vault 403 | RBAC/access model or network | inspect vault role and private endpoint |
| PostgreSQL cannot connect | private DNS/subnet/NSG | resolve FQDN and test approved path |

## 14. Production runbooks

**Preflight:** verify tenant/subscription/identity → check remote backend and lease → validate Azure Policy/RBAC → run Terraform tests and plan gate → approve change → apply under lock → validate logs, health and budget.

**Wrong subscription:** immediately stop pipeline, preserve plan/identity evidence, assess any created resources, revoke unintended access, obtain incident approval before remediation.

**State lock/backend outage:** stop concurrent writers, inspect Azure Storage logs, RBAC and network, recover from versioned state only under change control.

**Identity federation failure:** inspect issuer/audience/subject and federated credential, ensure correct role assignment, avoid granting Contributor broadly as a shortcut.

**DBRE recovery:** independently restore PostgreSQL/SQL data and validate KMS/Key Vault access; Terraform state recovery alone cannot restore databases.

## 15. 100-point acceptance rubric

| Domain | Points |
|---|---:|
| Tenant/subscription/resource group architecture | 20 |
| AzureRM provider, versioning and identity | 20 |
| RBAC, Azure Policy and security | 20 |
| Remote state, locking and recovery | 15 |
| Automated policy and negative tests | 15 |
| SRE/DBRE monitoring and incident evidence | 10 |

Pass >=85 with no critical failures: wrong subscription, static CI credentials, public state, unrestricted role assignment, destructive plan without approval, missing audit or untested recovery. Evidence must be independently observed.

## 16. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the local offline lab resources.

Review: Why is tenant different from subscription? How does Azure RBAC scope differ from Terraform state scope? Why does AzureRM 4.x require careful subscription configuration? How do provider and backend authentication differ? What protects blob state locking? Why are Azure Policy exemptions an audit concern?

**Next: Chapter 042 — Azure Virtual Networks, Subnets, NSGs, Routing and Private Connectivity with Terraform.**
