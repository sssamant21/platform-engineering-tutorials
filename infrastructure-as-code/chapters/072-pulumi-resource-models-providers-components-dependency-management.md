# Chapter 072 — Pulumi Resource Models, Providers, Components and Dependency Management

**Part 15 — Pulumi · Chapter 072/120 · SRE/DevOps/DBRE**

## Goals and prerequisites

Build an enterprise Pulumi Python component architecture, distinguish custom, component and provider resources, manage \`Input\`/\`Output\` dependencies, understand aliases, parents, protection, explicit providers and lifecycle options, and operate safely during incidents. Prerequisites: Chapter 071, Python 3.10+, Pulumi CLI, optional Pulumi Python SDK. The executable Python unit/policy lab needs only the standard library; the native Pulumi lab uses a **mock provider** and does not contact AWS, Azure or GCP.

## 1. Resource model and architecture

~~~text
Git / PR / policy / change ticket
                 |
Python program + component classes
                 |
  ComponentResource("acme:platform:Service")
      /                \
  Child A            Child B
  CustomResource     CustomResource
      \                /
       Pulumi engine graph
                 |
     provider configuration
                 |
  provider plugin / cloud API
                 |
  encrypted state / URNs / outputs
~~~

A **CustomResource** represents a provider-managed object and has a provider registration. A **ComponentResource** groups resources under a logical parent; it does not itself call a cloud API. A **ProviderResource** represents an explicit provider instance, useful for targeting specific regions, subscriptions and accounts. A resource's URN combines its stack, project, type, parent path and logical name; changes in type, parent or name can cause identity changes without an alias.

\`ResourceOptions(parent=...)\` establishes parentage; \`provider\` supplies a specific provider for compatible custom resources; \`providers\` can propagate provider maps to components. \`depends_on\` creates explicit ordering when references do not infer the required dependency. \`protect=True\` blocks normal deletion until protection is deliberately removed. \`retain_on_delete\` and \`delete_before_replace\` have materially different effects and need owner review.

## 2. Inputs, Outputs and dependency graph

Pulumi inputs accept concrete values or deferred outputs. An \`Output\` carries dependencies and possibly secret metadata. Use \`Output.apply\` for derived values; do not stringify or log secret outputs, and do not assume output values are available during the Python program's initial evaluation. The engine infers edges from resource outputs passed to other resource inputs. Explicit dependencies are reserved for relationships that cannot be inferred from inputs.

**SRE/DBRE example:** database security group -> database cluster -> replica -> application secret reference -> health monitor. Database backups and restore readiness are independent approval gates, not inferred merely from resource dependencies.

## 3. Providers and multi-account boundaries

Explicit provider instances prevent accidental reliance on ambient credentials. Verify AWS account/region, Azure tenant/subscription and GCP project before any \`pulumi up\`. Provider plugins and language SDK versions must be pinned, reviewed and compatible. Provider configuration may include sensitive values; use encrypted configuration, workload identities and least privilege. Do not assume parentage alone guarantees a child's provider configuration across all provider types; explicitly test propagation and pass the correct provider as needed.

## 4. Components and reusable contracts

Components should validate inputs, register children, expose only necessary outputs and call \`register_outputs\`. Design modules around stable interfaces, ownership, tagging, encryption, backup and observability. Avoid hidden implicit providers, mutable global configuration and embedded credentials. Define a compatibility policy for renamed components and use aliases to preserve resource identities during refactoring. A component is an abstraction boundary, **not** a security boundary.

## 5. Hands-on lab A — Mocked Pulumi resource graph

The lab contains a \`ComponentResource\` named \`LabService\` with two child \`CustomResource\` objects, an explicit dependency edge and protected stateful child. It uses \`pulumi.runtime.set_mocks\` for unit tests, so it **never provisions cloud resources**.

~~~bash
cd infrastructure-as-code/labs/chapter-072
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v test_components.py
~~~

The mock resource IDs are synthetic. Successful tests validate the local component contract and options only; they do not verify a real provider's cloud behavior.

## 6. Hands-on lab B — Fail-closed deployment governance

~~~bash
python3 resource_gate.py fixtures/safe.json policy.json
python3 resource_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_resource_gate.py
bash run-preflight.sh
~~~

The gate checks a **declared evidence manifest** and basic source markers, not native Pulumi previews, state snapshots, IAM/RBAC or cloud provider responses. It rejects wrong account/region, unreviewed replacement, missing backup, secret exposure, unprotected stateful resources and unapproved provider upgrades.

## 7. Hands-on lab C — Refactor and state recovery tabletop

Simulate renaming a component, changing its parent, changing provider region, moving a database between components and adding \`depends_on\`. Explain the expected URN changes, aliases and preview outcomes. Never manually edit state to force a resource rename in production. Capture the old and new URNs, stack export, provider versions, backups and signed migration plan.

## 8. Operational delivery

1. Validate backend, stack, project and cloud target identities.
2. Pin SDK and provider versions; scan dependencies and provenance.
3. Run component tests, static policy gate and \`pulumi preview --diff\` with an authorized account.
4. Review resource URNs, parent/provider changes, replacements, deletions and secret outputs.
5. Confirm DBRE backup/PITR, restore drill, replica quorum, connection budgets and RPO/RTO.
6. Approve canary and bounded rollout; monitor SLO and error budget.
7. Preserve audit, state checkpoints, provider versions, stack outputs and post-change health evidence.

## 9. Production incident simulations

| Incident | Signal | Containment |
|---|---|---|
| Wrong Pulumi stack | stack mismatch | abort |
| Wrong AWS account | caller mismatch | revoke session |
| Wrong Azure subscription | subscription mismatch | freeze |
| Wrong GCP project | project mismatch | block |
| Wrong provider region | preview target mismatch | halt |
| Ambient credential override | unexpected identity | enforce explicit provider |
| Provider plugin drift | version mismatch | pin and rebuild |
| SDK API mismatch | type/runtime error | align versions |
| Component parent rename | URN replacement | add reviewed aliases |
| Missing alias | unexpected replace | stop |
| Implicit dependency missing | ordering race | add reviewed edge |
| Dependency cycle | engine error | redesign graph |
| Secret Output logged | CI exposure | rotate/revoke |
| Protected resource delete | protection error | assess, never bypass casually |
| Retained resource orphan | FinOps alert | reconcile ownership |
| Database replacement | preview replace | DBRE PITR gate |
| Aurora failover | connection errors | quorum/replica review |
| PostgreSQL replication lag | replica alarm | freeze |
| MongoDB stepdown | election event | protect quorum |
| Redis failover | p99 increase | connection recovery |
| MSK ISR shrink | under-replicated partitions | stop |
| OpenSearch disk pressure | latency/disk | capacity review |
| EKS PDB conflict | blocked rollout | revise strategy |
| AKS node drain | eviction failure | pause |
| State lock conflict | concurrent update | identify owner |
| Provider rate limit | API 429 | backoff |
| Stale preview | diff changed | re-preview |
| Missing backups | restore evidence absent | block |
| Canary SLO regression | error budget burn | stop |
| State checkpoint loss | URN mismatch | restore backup |

## 10. Runbooks

**R1 Provider identity:** verify stack, account, region, subscription, project, provider version and workload identity.

**R2 Component refactor:** compare old/new URNs, aliases, parentage, providers and resource options before preview.

**R3 Dependency failure:** inspect inferred/explicit edges, cyclic relationships and eventual-consistency assumptions.

**R4 Preview replacement:** stop stateful replacement, inspect protection/retain/aliases and DBRE sign-off.

**R5 Secret incident:** revoke and rotate, audit logs, review secret outputs and provider configuration.

**R6 DBRE stateful recovery:** validate backup, PITR, replicas, RPO/RTO and restore drills.

**R7 State recovery:** preserve stack checkpoint, investigate active operations, use approved backup/restore.

**R8 Provider upgrade:** pin versions, test compatibility and canary before rollout.

**R9 FinOps:** inventory retained resources, orphaned identities, tags and owner.

**R10 Post-change:** verify SLO, backups, state encryption, outputs, drift and handover.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Custom, component and provider resource architecture | 20 |
| Inputs, Outputs, dependency graph and options | 20 |
| Mocked executable component tests | 15 |
| Provider isolation, secrets and governance | 15 |
| Automated policy tests and negative fixtures | 15 |
| SRE/DBRE incidents, runbooks and recovery | 15 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong provider target, unauthorized database replacement, leaked secret, unprotected stateful resource, invalid recovery evidence or missing approval. Attach actual unit test logs, real preview, DBRE restore evidence and signed acceptance for production.

**Status:** authored and published; mock test execution, Pulumi native integration and operational acceptance pending.

**Next proposed:** Chapter 073 — Pulumi Stack Configuration, Secrets, State Backends and Enterprise Governance.
