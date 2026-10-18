# Chapter 068 — Azure Bicep Foundations, ARM Templates, Modules and Deployment Operations

**Part 14 — CloudFormation and Bicep · Chapter 068/120 · Enterprise SRE/DBRE**

## Outcomes and prerequisites

Understand Azure Resource Manager (ARM) control-plane deployment, Bicep language, resources, parameters, outputs, modules, scopes, symbolic names, dependencies, deployment modes, what-if, RBAC, managed identity and operational recovery. Build a **local-only** Azure Bicep contract and policy lab with negative fixtures and automated tests. Prerequisites: Chapters 001–067, Python 3.9+, optional Azure CLI + Bicep CLI for compilation. No Azure subscription or credentials are needed for the offline lab.

## 1. Architecture and deployment trust boundaries

~~~text
Git PR / owner review / change ticket
          |
CI syntax + Bicep build + policy + tests
          |
Entra workload identity / federated CI
          |
Azure RBAC deployment principal
          |
ARM deployment scope: tenant / management group / subscription / resource group
          |
Bicep main.bicep -> module storage.bicep
          |
What-if -> approval -> deployment
          |
Azure Activity Log / deployment operations / Azure Monitor / SLO
          |
Drift review / backup / restore / incident handover
~~~

Bicep is a declarative language that compiles to ARM JSON templates. Azure Resource Manager evaluates the dependency graph and applies resource-provider operations. Bicep does not hold a Terraform-style state file. Deployments and resources are scope-bound. A module is a separately compiled template linked through Bicep; module deployments have their own deployment records. Resource IDs and scopes must be explicitly reviewed to avoid cross-subscription and cross-resource-group targeting.

## 2. Bicep language essentials

- **Parameters:** typed inputs, decorators such as \`@allowed\`, \`@minLength\` and \`@secure\`; secure parameters must not be written to logs or outputs.
- **Variables and expressions:** string interpolation, arrays, objects, conditionals, loops and functions; avoid nondeterministic naming and secret disclosure.
- **Resources:** declare provider type and API version, \`name\`, \`location\`, \`properties\`; prefer reviewed API versions.
- **Existing resources:** \`existing\` references do not create resources, but still need correct scope and permissions.
- **Modules:** isolate components, parameter/output contracts, target scopes and deployment ordering; use trusted, versioned registry modules.
- **Outputs:** export non-secret values and IDs; never output credentials.
- **Dependencies:** Bicep infers dependencies from symbolic references; use \`dependsOn\` only when required.
- **Deployment scopes:** resource group, subscription, management group and tenant have different RBAC and blast radius.
- **Azure Policy and locks:** deny noncompliant resources and protect critical infrastructure, but locks can complicate planned updates.

## 3. What-if, validation and deployment safety

Use \`az bicep build\` offline to compile Bicep and inspect the generated ARM template. \`az deployment group what-if\` calls Azure and requires appropriate permissions; it is **not** part of the offline preflight. What-if predicts changes, but has limitations with unresolved expressions, nested deployments and resource-provider behavior; do not treat it as a guarantee. Prefer incremental deployments and explicit scope. Azure's complete deployment mode can remove resources not declared in the template; it is deprecated in favor of deployment stacks for resource deletion workflows. Do not use destructive modes in this chapter.

Production gate: identity and subscription verification; what-if output; RBAC/Policy; lock review; approval; backup/PITR and DBRE acceptance; health checks and rollback plan. Revalidate what-if after code or parameter changes.

## 4. Executable Lab A — Bicep contract

Files under \`labs/chapter-068/\` contain \`main.bicep\`, \`modules/storage.bicep\`, and \`parameters/lab.bicepparam\`. The template creates a **storage account definition** in a lab resource group, with secure transport, TLS minimum, public blob access disabled and a private container. **Do not deploy it**: the offline exercise compiles and checks contracts only, avoiding cloud cost and public endpoints.

~~~bash
cd infrastructure-as-code/labs/chapter-068
python3 bicep_gate.py fixtures/safe.json policy.json
python3 bicep_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_bicep_gate.py
bash run-preflight.sh
~~~

The Python gate checks a deliberately scoped **declared-evidence** JSON manifest and basic static Bicep contract strings. It is **not** a Bicep AST parser, Azure Policy engine, ARM what-if parser or Azure RBAC verifier.

### Optional offline Bicep compilation

~~~bash
az bicep version
az bicep build --file main.bicep --outfile /tmp/ch068-main.json
az bicep build-params --file parameters/lab.bicepparam --outfile /tmp/ch068-params.json
~~~

Bicep CLI is optional; a compatible local installation is required. Generated ARM JSON and parameter files must be inspected for secrets and kept outside version control.

## 5. Lab B — Negative governance testing

Change the safe manifest to an unapproved subscription, production environment, broader deployment scope, missing what-if, missing backup, unapproved resource deletion, disabled TLS or public network exposure. Run the gate; it must reject the evidence. The unsafe fixture intentionally violates several controls.

## 6. Lab C — Operational design exercise

Draft an approved resource-group deployment workflow using Entra workload identity, least-privilege RBAC, Azure Policy, protected environments, immutable module versions and Azure Monitor. Show how a reviewed what-if output becomes a change ticket and how the deployment operations are audited. This is a tabletop exercise; no live mutation is authorized.

## 7. Production SRE/DBRE incident scenarios

| Incident | Signal | Containment / recovery |
|---|---|---|
| Wrong subscription | account mismatch | stop, verify \`az account show\` |
| Wrong resource group | scope mismatch | block, reconcile target |
| Unapproved complete mode | delete preview | abort and re-plan |
| Storage public access | policy violation | deny and correct |
| TLS weakened | security finding | block deployment |
| Key Vault secret exposed | pipeline log | revoke and rotate |
| Entra identity expired | token failure | review federated credential |
| RBAC denied | AuthorizationFailed | least-privilege role review |
| Policy deny | RequestDisallowedByPolicy | remediate resource configuration |
| Resource lock conflict | ScopeLocked | review owner and approval |
| What-if unresolved | uncertain preview | isolate and test in sandbox |
| Module version drift | checksum mismatch | pin trusted artifact |
| Cross-scope module | unexpected subscription | reject and audit |
| Storage account name collision | conflict | use deterministic approved naming |
| Azure SQL replacement | database outage risk | DBRE backup/PITR gate |
| PostgreSQL Flexible Server change | failover risk | replica and connection checks |
| AKS upgrade conflict | node drain failure | PDB and capacity review |
| Cosmos DB throughput change | throttling | capacity/SLO gate |
| Azure Monitor missing | blind deployment | block acceptance |
| Resource provider throttling | 429 responses | bounded retry/backoff |
| Regional quota exhausted | allocation failure | request quota or resize |
| Deployment failed midway | partial resources | inspect operations and reconcile |
| Backup restore failed | RPO/RTO violation | block stateful changes |
| Orphaned resources | cost drift | tag, owner and cleanup review |

## 8. Runbooks

**R1 Preflight:** verify tenant, subscription, resource group, caller, module pins, policy, locks, quota and approval.

**R2 What-if review:** inspect resource additions, updates and deletes, unresolved expressions and secure parameter handling.

**R3 RBAC failure:** inspect role assignment, scope, identity and token; do not grant broad Owner by default.

**R4 Policy/lock:** identify policy assignment or lock owner and obtain reviewed exception if justified.

**R5 Partial deployment:** inspect deployment operations, resource status and dependency graph; preserve evidence before retry.

**R6 DBRE stateful change:** validate backup/PITR, replica health, connection budgets, SLO and restore drill.

**R7 Secret incident:** revoke/rotate credentials, restrict artifacts, inspect managed identity and Key Vault access.

**R8 Drift:** compare deployed configuration with Git/Bicep and reconcile via reviewed what-if.

**R9 FinOps:** inspect unused disks, storage lifecycle, tags and SKU capacity before cleanup.

**R10 Post-change:** verify Activity Log, Azure Monitor, backup, security posture and handover.

## 9. 100-point acceptance

| Domain | Max |
|---|---:|
| ARM/Bicep architecture and language contracts | 20 |
| Modules, scopes and dependencies | 20 |
| What-if, deployment lifecycle and rollback | 15 |
| RBAC, secrets, Azure Policy and security | 15 |
| Automated tests and negative fixtures | 15 |
| SRE/DBRE incidents, runbooks and handover | 15 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong subscription/tenant, unauthorized deletion, exposed secret, public data access, unapproved DB change, or missing verified backup. Evidence must include real Bicep compilation, Azure what-if, scoped RBAC, backup restore and reviewer sign-off.

**Publication status:** authored. Local tests and Azure-native integration must be executed before operational acceptance.

**Next proposed:** Chapter 069 — Azure Bicep Advanced Modules, Deployment Stacks, Governance and Multi-Subscription Operations.
