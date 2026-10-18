# Chapter 043 — Azure Identity, Key Vault, Managed Identities and Secure Infrastructure with Terraform

**Part 09 — Azure Infrastructure as Code · Chapter 043/120**  
**Audience:** SRE, DBRE, Cloud Security, Platform Engineering, DevSecOps  
**Prerequisites:** Chapters 041–042; Terraform >=1.7; Python >=3.9; optional Azure CLI and approved sandbox  
**Execution boundary:** The core lab is provider-free Terraform and Python. The AzureRM examples are review-only and require explicit authorization, budget, identity review, and approved state storage before any live deployment.

## 1. Outcomes and threat model

Build an enterprise Azure security foundation around Microsoft Entra ID, workload identity federation, managed identities, Azure RBAC, Key Vault, encryption, secret rotation, policy, audit and recovery. Demonstrate least-privilege enforcement, environment isolation, fail-closed checks, and SRE/DBRE incident response.

**Primary threats:** leaked service-principal credentials, OIDC subject confusion, wildcard role assignment, excessive Owner/User Access Administrator privileges, managed identity lateral movement, Key Vault public exposure, secret values leaked into Terraform state or logs, premature key purge, cross-tenant deployment, and outage caused by revoking database encryption keys.

## 2. Identity and authorization architecture

~~~text
Source control / CI job
     | OIDC token (issuer + audience + subject)
     v
Microsoft Entra application + federated credential
     | short-lived access token
     v
Azure Resource Manager -> Azure RBAC scope -> Azure Policy
     |
     +-- Resource Group / Storage / Key Vault / AKS / Database
     |
Azure-hosted workload -> managed identity -> Key Vault data-plane RBAC
                                           -> Storage / database auth
Audit: Entra sign-in logs + Azure Activity Log + Key Vault diagnostics
~~~

A Microsoft Entra tenant is an identity boundary. A service principal represents an application in a tenant. A **system-assigned managed identity** is tied to one Azure resource lifecycle; a **user-assigned managed identity** is independently managed and can be attached to supported resources. Managed identities avoid customer-managed application credentials but still need narrowly scoped permissions.

Azure RBAC controls management-plane operations at management-group, subscription, resource-group or resource scopes. Key Vault can use Azure RBAC for data-plane authorization; the legacy access-policy model has different behavior. Avoid mixing assumptions between these modes. The principal's Azure RBAC scope and the Key Vault data-plane permission are both important.

## 3. Federated CI authentication

Prefer OIDC workload identity federation over client secrets. Federated identity credentials must bind the **exact** token issuer, audience and subject expected from the CI provider. For GitHub Actions, a protected environment may produce a subject such as \`repo:ORG/REPO:environment:prod\`; for branch-scoped credentials the subject is different. GitLab issuer and subject syntax differs: do not copy a GitHub pattern to GitLab. Protect environments, deployment approvals and runner provenance independently.

Never store \`ARM_CLIENT_SECRET\` in the repository. Verify \`ARM_TENANT_ID\`, \`ARM_SUBSCRIPTION_ID\`, \`ARM_CLIENT_ID\`, \`ARM_USE_OIDC\` and provider/backend authentication independently. Explicitly check tenant/subscription before \`terraform plan\` or \`apply\`.

## 4. Least-privilege Azure RBAC

A role assignment combines a principal ID, role definition and scope. Avoid subscription-level Contributor for narrow resource deployment; avoid Owner and User Access Administrator except approved privileged workflows. Watch \`Microsoft.Authorization/roleAssignments/write\`, identity assignment, policy exemptions, Key Vault administration, Storage account keys, and data-plane role grants. Use separate CI identities for planning and applying where feasible, with protected production approvals.

Custom role actions and dataActions must be reviewed together. Deny assignments and Azure Policy may restrict operations despite an apparent allow. Propagation of RBAC changes can be delayed; do not repeatedly escalate privileges while waiting.

## 5. Key Vault design

Use Azure Key Vault for keys, secrets and certificates, with the appropriate tier and availability design. Enable soft delete (modern vaults have it enabled) and purge protection for production; understand retention and irreversibility implications. Prefer Azure RBAC permission model, restrict public network access, use private endpoints and private DNS, and enable diagnostic logging to an independently controlled destination. Use key rotation policies and monitor expiry, disabled key versions and service access.

**Important:** Azure Key Vault secret *metadata* can be managed in Terraform, but writing secret values through \`azurerm_key_vault_secret\` can place values in Terraform state. Terraform's \`sensitive\` flag hides routine CLI display; it is not encryption or removal from state. For production, prefer a controlled external secret-injection/rotation workflow or carefully assessed ephemeral/write-only features supported by your exact provider and Terraform versions. Do not put production credentials in \`.tfvars\`, GitHub Actions output or plan JSON.

## 6. Key rotation and database encryption

Distinguish key rotation from rotating the underlying encrypted data or application credentials. Check whether the Azure service tracks a versionless Key Vault key URI or pins a specific key version. For customer-managed keys on Storage, Azure SQL or PostgreSQL where supported, the managed identity needs continuous decrypt/wrap/unwrap access as required by the service. Key deletion, disablement, vault firewall changes or lost role assignments can cause production data unavailability. Plan emergency access and tested recovery before enabling CMK.

Use managed database identities and approved Microsoft Entra authentication when supported; use short-lived application credentials or controlled Key Vault retrieval otherwise. Rotation requires compatibility with application connection pools and rollback windows.

## 7. Terraform architecture and secure state

Separate \`identity\`, \`rbac\`, \`key_vault\`, \`secret_metadata\`, \`diagnostics\`, and \`policy\` modules. Limit module outputs: do not export secret values. Pin AzureRM versions and the dependency lockfile; test provider changes in a sandbox. Use Azure Blob remote state with Entra/OIDC authentication, encryption, network restrictions, versioning, and locking; protect saved plans and CI logs as sensitive artifacts.

Avoid circular dependencies between Terraform's state backend and the vault/identity it needs to initialize. Bootstrap the state and foundational identity in a separate, controlled stack.

## 8. Executable lab layout

~~~text
labs/chapter-043/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/azurerm-identity-keyvault.tf.example
  examples/azure-security-preflight.sh.example
  security-policy.json
  fixtures/security-safe.json, security-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  security_gate.py, test_security_gate.py, run-preflight.sh
  runbook.md, acceptance.md, .gitignore
~~~

## 9. Lab A — Offline Terraform security contracts

~~~bash
cd infrastructure-as-code/labs/chapter-043
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter043.tfplan
terraform apply chapter043.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Four \`terraform_data\` resources represent identity, RBAC, Key Vault and audit controls. No Azure credentials are used. For the second unchanged plan, exit code 0 means no changes; exit 2 means drift or pending changes. The offline lab is not proof of live Azure RBAC, Key Vault or secret rotation.

## 10. Lab B — Python fail-closed policy gate

~~~bash
python3 security_gate.py fixtures/security-safe.json fixtures/plan-safe.json security-policy.json
python3 security_gate.py fixtures/security-unsafe.json fixtures/plan-destructive.json security-policy.json
python3 -m unittest -v test_security_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes, unsafe fixture is denied, unit tests pass. The gate checks declared tenant/subscription isolation, exact OIDC trust, absence of static credentials, RBAC restrictions, Key Vault network/purge protection, rotation, CMK recovery, state, tags, approvals and destructive plan actions. It validates a simplified contract, **not** the actual AzureRM plan schema or deployed cloud posture. Production acceptance requires cloud-side evidence.

## 11. Lab C — Azure plan-only integration

1. Obtain an approved sandbox tenant/subscription and budget.
2. Verify \`az account show\` identity, tenant and subscription; record the exact service principal or managed identity.
3. Inspect \`examples/azurerm-identity-keyvault.tf.example\` and its required permissions. Review Key Vault RBAC, purge protection, public access and diagnostics.
4. Copy the example into a separate approved root and configure a secure backend. Use workload identity federation or a managed identity; never paste credentials into the example.
5. Run \`terraform init\`, \`terraform validate\` and \`terraform plan\` only. Have Security review role assignment scope, principal trust and potential state contents before approval.
6. Validate Key Vault private DNS and network path, secret retrieval with a non-privileged test identity, audit logs, and approved key/secret rotation.
7. Do not \`apply\` without change authorization, operational owner, rollback and data-recovery evidence.

## 12. SRE/DBRE production scenarios

| System | Failure mode | Signal | Recovery strategy |
|---|---|---|---|
| Azure Database for PostgreSQL | identity loses CMK access | encryption/key errors, database unavailable | restore approved key access, verify queries |
| Azure SQL | key version disabled or vault inaccessible | service errors and failed failover | restore key and network access |
| AKS | workload identity subject mismatch | token exchange 401/403 | correct issuer/audience/subject and service account |
| Storage | identity loses data-plane role | 403, Terraform backend unavailable | restore scoped RBAC and blob connectivity |
| Key Vault | private DNS link missing | resolution failure, 403/timeouts | repair DNS and network policy |
| CI deployment | federated credential trust drift | \`AADSTS\` token errors | validate exact trust and environment |
| Application | secret rotation breaks connection pool | authentication failures | controlled rollback to approved version |
| DR | secondary region cannot unwrap CMK | restore/failover blocked | validate key access and replication design |

## 13. Troubleshooting

| Symptom | Diagnostic | Unsafe shortcut |
|---|---|---|
| \`AuthorizationFailed\` | RBAC role, principal and scope | subscription-wide Contributor |
| \`AADSTS70021\` or token exchange failure | federated credential issuer/subject/audience | static CI client secret |
| Key Vault 403 | data-plane RBAC and vault network settings | opening public access |
| Secret version not visible | permissions, enabled/expiry/version stages | exporting secret to logs |
| CMK service outage | key state, key URI, grants/RBAC, vault connectivity | disabling encryption |
| Terraform backend 403 | blob data role, Entra auth and private DNS | storage account keys |
| Role change seems ignored | token caching and propagation | escalating to Owner |
| Terraform replacement | plan actions and immutable attributes | blind apply |

## 14. Production runbooks

**Pre-change:** verify tenant/subscription, exact CI subject, role scope, Key Vault network and purge protection, key rotation policy, state backend and audit → run tests and plan → obtain security/DBRE approvals → deploy with controlled lock → validate application key retrieval.

**Credential exposure:** revoke/rotate affected credential, invalidate sessions where possible, inspect sign-in and Activity Logs, assess blast radius, rotate dependent secrets, document incident. Never publish compromised values in tickets.

**Key disabled / deleted:** declare high-severity incident, freeze key operations, inspect key versions, soft-delete state, purge protection and service dependencies; restore authorized access or recover soft-deleted key under dual control, then validate database read/write and backups.

**OIDC federation outage:** compare token claims to Entra federated credential, verify branch/environment protection, update narrowly scoped trust, retry; do not create long-lived credentials as a workaround.

**Rotation failure:** stop rollout, identify current/previous approved secret version, coordinate application credential refresh and DB connection pool restart, verify authentication, schedule root-cause fix.

**Terraform state leak:** isolate state storage and CI artifacts, audit access, rotate exposed secrets, restore least-privilege backend controls; state encryption alone does not negate an exposure.

## 15. 100-point acceptance

| Domain | Points |
|---|---:|
| Entra identity and OIDC trust architecture | 20 |
| RBAC least privilege and Azure Policy | 20 |
| Key Vault keys, secrets and network security | 20 |
| Terraform and Python positive/negative tests | 15 |
| Rotation, CMK recovery and DBRE incident drills | 15 |
| Monitoring, audit and operational approval | 10 |

Pass >=85/100 with **zero critical failures**. Critical failures include wildcard production federation, static CI credentials, unreviewed privileged role assignment, public vault, purge-protection gap, secret leakage, destructive plan or untested database key recovery. Attach sanitized CI run, Azure role assignment export, vault diagnostics, approved change, rotation evidence and recovery measurements.

## 16. Cleanup and review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

This destroys only offline \`terraform_data\` resources. Review: Why does \`sensitive = true\` not remove secrets from state? How do managed identities differ from service principals? How does Key Vault data-plane RBAC differ from ARM permissions? Why is purge protection operationally significant? What can break when a database CMK is disabled?

**Next: Chapter 044 — Azure Compute, AKS and Application Infrastructure with Terraform.**
