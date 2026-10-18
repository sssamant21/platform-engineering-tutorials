# Chapter 069 — Azure Bicep Advanced Modules, Deployment Stacks, Governance and Multi-Subscription Operations

**Part 14 — CloudFormation and Bicep · Chapter 069/120 · SRE/DevOps/DBRE**

## Objectives and prerequisites

Build reusable Bicep module contracts, model resource-group and subscription scopes, understand Azure deployment stacks and managed-resource deletion policies, govern multi-subscription rollouts, and prepare enterprise SRE/DBRE change plans. Use Python 3.9+ for the executable **offline** labs; optional Azure CLI with Bicep CLI for compilation. No Azure subscription, cloud credentials or paid resources are needed.

## 1. Enterprise architecture

~~~text
Protected Git PR / change ticket / owner + DBRE + security
                    |
         CI tests / lint / module pin / policy
                    |
           Entra workload federation
                    |
     scoped RBAC + management group policy
                    |
   subscription-scope orchestration template
           /                       \
  resource-group A             resource-group B
    module storage               module monitoring
           \                       /
        deployment stack (optional lifecycle boundary)
                    |
   what-if / stack what-if -> approval -> apply
                    |
 Activity Log / Azure Monitor / SLO / backup / drift
~~~

Bicep modules compile to nested ARM deployments; use explicit target scopes, named outputs, secure inputs and versioned registry references. A subscription-scope deployment can create resource groups, while resource-group modules configure resources within those groups. Managed identities and RBAC must be scoped to the minimum required resource group or subscription; avoid granting Owner to CI.

## 2. Advanced module architecture

Use modules to isolate resource types, establish typed parameter/output contracts and reuse reviewed components. Modules can be local files, template specs or Bicep registry artifacts; pin versions and check provenance. Avoid module-level secret outputs, circular dependencies and uncontrolled dynamic names. \`existing\` references are read/modify boundaries, not guarantees of read-only authorization. Understand dependency inference and when explicit \`dependsOn\` is appropriate.

The lab's \`main.bicep\` uses **subscription scope** to reference an existing resource group and invokes a resource-group-scoped module. The module describes a private storage account. It is **not deployed**. Resource names and the subscription target are placeholders; a production workflow must resolve and approve exact tenant/subscription IDs and region.

## 3. Azure deployment stacks

Deployment stacks track resources managed through a stack and support explicit actions when managed resources are removed from the template or the stack is deleted. Policies such as \`detachAll\`, \`deleteResources\` and \`deleteAll\` (depending on the CLI/API operation) can have materially different deletion consequences. Never assume deployment-stack resource deletion behaves like ordinary incremental ARM deployment. Resource locks and deny settings affect permissions and change management. Review stack-specific what-if and lifecycle semantics for the deployed Azure CLI/API version.

**Stateful guardrail:** production databases, storage, Key Vault and disks require backup/restore evidence, ownership and DBRE approval before any stack-managed deletion or replacement. The lab's policy gate forbids destructive lifecycle actions.

## 4. Multi-subscription governance

Use management groups, Azure Policy, resource locks, tags, cost budgets, RBAC/PIM, workload identity federation and approved target matrices. Distinguish tenant, subscription, management group and resource-group scopes. Deployment pipelines should validate target subscriptions and resource groups, review \`what-if\`, use canary subscriptions, bound concurrency and stop on errors. Maintain per-target deployment operation evidence; a successful control-plane deployment does not prove application SLO health.

## 5. Executable labs

~~~text
labs/chapter-069/
  main.bicep
  modules/private-storage.bicep
  parameters/lab.bicepparam
  fixtures/safe.json
  fixtures/unsafe.json
  policy.json
  deployment_gate.py
  test_deployment_gate.py
  run-preflight.sh
  runbook.md
  acceptance.md
  examples/readonly-azure-diagnostics.sh.example
~~~

### Lab A — Offline Bicep contract

~~~bash
cd infrastructure-as-code/labs/chapter-069
python3 deployment_gate.py fixtures/safe.json policy.json
python3 deployment_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_deployment_gate.py
bash run-preflight.sh
~~~

Safe evidence passes; unsafe evidence fails. The gate validates a narrow set of **declared governance evidence and static source markers**, not Bicep AST, Azure Policy, Azure RBAC, deployment-stack API payloads or live Azure behavior.

### Lab B — Native compilation (optional, offline)

~~~bash
az bicep version
az bicep build --file main.bicep --outfile /tmp/ch069-main.json
az bicep build-params --file parameters/lab.bicepparam --outfile /tmp/ch069-params.json
~~~

These commands compile locally when Azure CLI/Bicep is installed; they do not deploy resources. Inspect compiled ARM templates and parameter outputs before any use.

### Lab C — Multi-subscription failure injection

Edit the safe manifest to use \`subscription=production\`, \`scope=managementGroup\`, \`delete_all=true\`, \`canary_approved=false\`, \`what_if_reviewed=false\` or \`dbre.backup_verified=false\`. The gate must reject each mutation. Model a partial rollout: stop later targets, collect deployment operations and rollback only after DBRE assessment.

### Lab D — Production design tabletop

Design a rollout through sandbox, canary and production subscriptions. Document Entra workload federation, module digest, resource group ownership, stack deletion behavior, policy exemptions, approval, SLO, backup, RPO/RTO, and cross-subscription recovery. No production mutation is included.

## 6. SRE/DBRE incident simulations

| Incident | Signal | Containment and recovery |
|---|---|---|
| Wrong tenant | identity mismatch | abort and revoke session |
| Wrong subscription | target matrix mismatch | stop and audit |
| Wrong management group | inherited policy surprise | block rollout |
| Cross-subscription scope | unapproved deployment | fail closed |
| Module artifact tampering | digest mismatch | quarantine |
| Module version drift | inconsistent environments | pin and rebuild |
| Secret output | sensitive CI log | revoke and rotate |
| Overprivileged identity | broad RBAC | revoke and scope |
| PIM elevation expired | authorization failure | review activation |
| Azure Policy deny | policy violation | remediate |
| Resource lock conflict | ScopeLocked | owner approval |
| Deployment-stack deletion | removal preview | stop, DBRE review |
| Detach vs delete confusion | orphan or loss risk | verify lifecycle |
| Resource group replacement | cascading resource risk | block |
| PostgreSQL Flexible Server change | replica lag | freeze rollout |
| Azure SQL data risk | PITR missing | stop, restore test |
| Cosmos DB throughput change | 429 increase | capacity review |
| AKS upgrade | PDB blocked | stage capacity |
| Redis cache change | connection spikes | replica/failover review |
| Storage account exposure | public access | policy deny |
| Key Vault deletion | soft-delete/purge risk | backup and recovery |
| Regional quota | provisioning failure | capacity plan |
| Partial deployment | failed target | stop later subscriptions |
| What-if unresolved | unknown changes | sandbox test |
| Drift after manual hotfix | unexpected diff | owner reconciliation |
| Missing Activity Log | audit gap | block acceptance |
| FinOps spike | retained/orphaned resource | ownership cleanup |

## 7. Enterprise runbooks

**R1 Target identity:** verify tenant, subscription, resource group, workload identity and RBAC.

**R2 Module supply chain:** verify registry source, version, digest, approvals and CI provenance.

**R3 Deployment-stack review:** inspect managed resource list, deny settings, deletion/detach policy and stateful ownership.

**R4 What-if:** inspect resource additions, changes, removals, unresolved expressions and cross-scope effects.

**R5 Partial multi-subscription rollout:** freeze new targets, record successes/failures, reconcile deployments and approve recovery.

**R6 DBRE stateful recovery:** verify PITR/backup, replication, SLO, RPO/RTO and restore before replacement.

**R7 Security incident:** revoke identity, rotate secrets, audit Activity Log and quarantine artifacts.

**R8 Drift:** compare source of truth with deployed state, review manual changes, reconcile safely.

**R9 FinOps:** inspect retained resources, tags, budgets, quotas and ownership.

**R10 Post-change:** verify Azure Monitor, deployments, backup, policy compliance and handover.

## 8. 100-point acceptance

| Domain | Points |
|---|---:|
| Advanced Bicep modules, scope and architecture | 20 |
| Deployment stacks and deletion safety | 20 |
| Multi-subscription governance and RBAC | 15 |
| What-if, drift, recovery and operations | 15 |
| Automated tests and negative cases | 15 |
| SRE/DBRE incidents, runbooks and handover | 15 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong tenant/subscription, unauthorized stack deletion, secret disclosure, overprivileged CI, unapproved stateful change, or missing restore evidence.

**Status:** authored and published; local tests, native Bicep compilation, Azure what-if, deployment-stack integration and production operational acceptance remain pending.

**Next:** Chapter 070 — CloudFormation and Bicep Enterprise Multi-Cloud Automation and Reliability Capstone.
