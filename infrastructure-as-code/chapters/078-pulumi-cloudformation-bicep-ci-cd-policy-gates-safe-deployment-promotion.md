# Chapter 078 — Pulumi, CloudFormation and Bicep CI/CD Pipelines, Policy Gates and Safe Deployment Promotion

**Part 16 — IaC CI/CD · Chapter 078/120 · Enterprise SRE/DevOps/DBRE**

## Learning outcomes and prerequisites

Design an enterprise delivery system spanning **Pulumi Automation API**, **AWS CloudFormation change sets** and **Azure Bicep deployments**, with independently verified cloud identities, environment promotion, immutable artifacts, policy enforcement, observability and stateful DBRE protections. Prerequisites: Chapters 066–077, Python 3.10+, Git and Bash. Native cloud CLIs are optional; **the supplied executable lab is offline, requires no cloud credentials and cannot deploy resources**.

## 1. Reference architecture

~~~text
Signed PR / protected branch / change ticket
                 |
   lint, test, scan, pinned dependencies
                 |
       tool- and target-specific preview
     /             |                \
 Pulumi preview   CFN change set   Bicep what-if
     \             |                /
     normalize risk evidence (NOT cloud truth)
                 |
      fail-closed policy + approval gate
                 |
       signed immutable change artifact
                 |
      revalidate account/stack/subscription
                 |
        backup/PITR + DBRE sign-off
                 |
    canary deployment + telemetry/SLO gate
                 |
     promote / audit / GitOps reconciliation
~~~

Separate **CI validation** (unprivileged, pull-request safe) from **CD execution** (protected, short-lived identity, reviewed changes). A common governance contract does not make the tools equivalent: Pulumi operates stacks and provider plugins; CloudFormation uses AWS stack lifecycle and change sets; Bicep compiles to ARM and uses Azure deployments and what-if. Treat all previews as fallible, time-bound evidence.

## 2. Tool-specific semantics and production boundaries

| Tool | Preview/review | Apply/deployment | Recovery and risk |
|---|---|---|---|
| Pulumi | `pulumi preview --json` or Automation API `preview()` | `pulumi up` / Automation API `up()` | stack/backend identity, state locks, secret provider, partial updates |
| CloudFormation | create/describe change set; review replacements and IAM capabilities | execute reviewed change set | stack status, rollback failures, termination protection, StackSets target scope |
| Bicep | `az deployment group what-if` (or subscription/management-group scope) | corresponding Azure deployment | RBAC, tenant/subscription, deployment stacks deletion semantics, policy denies |

**Pulumi:** lock down stack and secrets provider; verify provider plugin versions, aliases, resource protection and unknown Outputs. Do not interpret a successful preview as a guaranteed safe update. Policy packs (CrossGuard) can provide resource-policy enforcement, but availability and organization enforcement differ by configuration and plan.

**CloudFormation:** validate templates and parameters; review `Replacement` and `RequiresRecreation` fields, resource import, drift and rollback triggers. A change set is not a transaction or a proof of availability. StackSets can impact many accounts and regions: require a separately approved target matrix and concurrency bounds.

**Bicep:** compile and validate Bicep, inspect what-if output for resource deletion, scope and property changes, and review Azure Policy/RBAC. What-if can report noise or omit runtime side effects. Deployment stacks and complete-mode deletion deserve explicit review; never assume incremental deployments remove obsolete resources.

## 3. Security, policy and change authorization

Require protected source, pinned dependencies, OIDC workload federation, least privilege, scoped backend access, encrypted secrets and logs, signed change artifacts, independent approvals and verified audit records. Bind approval to source revision, tool, target identity, preview digest, timestamp and ticket. Enforce fail-closed policy on missing preview, unexpected replacement, unknown production target, missing backup or failed SLO.

A self-reported evidence JSON file is **not a cryptographic attestation**. The offline lab tests policy logic, not actual signatures, AWS IAM, Azure RBAC, Pulumi engine output or CloudFormation/Bicep schemas. Production adapters must collect and validate those sources directly.

## 4. Stateful SRE/DBRE deployment safety

For **PostgreSQL/RDS/Aurora**, require PITR and tested restore, replica lag checks, connection budgets and DBRE review before replacement. For **MongoDB**, verify quorum and oplog window. For **Redis**, validate failover and latency. For **Kafka/MSK**, check ISR and partition reassignments. For **OpenSearch/Elasticsearch**, review shard size, disk IOPS, throughput and indexing/search latency. For **EKS/AKS**, check PDBs, persistent volumes and node-drain disruption. Always distinguish infrastructure rollback from **data recovery**.

## 5. Hands-on labs

### Lab A — Offline multi-tool policy gate

~~~bash
cd infrastructure-as-code/labs/chapter-078
python3 governance_gate.py fixtures/safe.json policy.json
python3 governance_gate.py fixtures/unsafe.json policy.json  # expected nonzero
python3 -m unittest -v test_governance_gate.py test_pipeline.py
bash run-preflight.sh
~~~

The gate checks declared tool-specific preview evidence, exact target identity, artifact binding, approvals, DBRE restore evidence and SLO. The unsafe fixture includes a production target, missing DBRE backup and an unauthorized destructive change.

### Lab B — Controlled promotion simulator

The offline stage machine enforces `source -> validate -> preview -> policy -> approve -> backup -> revalidate -> canary -> health -> promote -> audit`. Inject missing approvals, backup failures, stale preview, canary failure and audit gaps; each must stop progression. A failed deployment does **not** automatically roll back.

### Lab C — CI examples and safe preview commands

Review `gitlab-ci.yml.example` and `github-actions.yml.example`. Both execute only the offline lab; production deploy jobs are **disabled placeholders**. `preview-commands.md` documents optional native read-only preview patterns for the three tools. Never run deployment commands without verified target, state, change window and authorization.

### Lab D — GitOps handoff and incident tabletop

Simulate a CloudFormation VPC update, Pulumi-managed Kubernetes cluster add-on and Bicep network change alongside Argo CD application reconciliation. Identify ownership boundaries, DNS/network dependencies, stateful blast radius, error budgets and change freezes. Build an incident timeline for a PostgreSQL PITR failure during canary; reject promotion and capture DBRE approval gaps.

## 6. Production incident simulations

| # | Scenario | Containment |
|---|---|---|
| 1 | Pulumi stack mismatch | Stop promotion; verify identity, approvals and service health |
| 2 | Pulumi secret provider key unavailable | Revoke or quarantine; preserve forensic evidence |
| 3 | Pulumi partial update | Stop promotion; verify identity, approvals and service health |
| 4 | Pulumi concurrent operation | Stop promotion; verify identity, approvals and service health |
| 5 | CloudFormation change set stale | Freeze deployment and preserve change/state evidence |
| 6 | CloudFormation rollback failed | Freeze deployment and preserve change/state evidence |
| 7 | CloudFormation stack UPDATE_ROLLBACK_FAILED | Freeze deployment and preserve change/state evidence |
| 8 | CloudFormation termination protection blocks action | Revoke or quarantine; preserve forensic evidence |
| 9 | CloudFormation StackSet targets wrong OU | Stop promotion; verify identity, approvals and service health |
| 10 | CloudFormation drift not reviewed | Stop promotion; verify identity, approvals and service health |
| 11 | Bicep wrong tenant | Stop promotion; verify identity, approvals and service health |
| 12 | Bicep wrong subscription | Stop promotion; verify identity, approvals and service health |
| 13 | Bicep wrong deployment scope | Stop promotion; verify identity, approvals and service health |
| 14 | Bicep what-if false assurance | Stop promotion; verify identity, approvals and service health |
| 15 | Azure deployment stack deletion risk | Stop promotion; verify identity, approvals and service health |
| 16 | Azure policy deny | Stop promotion; verify identity, approvals and service health |
| 17 | OIDC token audience mismatch | Revoke or quarantine; preserve forensic evidence |
| 18 | Long-lived secret in CI logs | Revoke or quarantine; preserve forensic evidence |
| 19 | Tampered Pulumi provider plugin | Revoke or quarantine; preserve forensic evidence |
| 20 | Unpinned GitHub Action | Revoke or quarantine; preserve forensic evidence |
| 21 | Runner compromise | Revoke or quarantine; preserve forensic evidence |
| 22 | Plan artifact wrong commit | Freeze deployment and preserve change/state evidence |
| 23 | Approval bypass | Stop promotion; verify identity, approvals and service health |
| 24 | Missing state checkpoint | Freeze deployment and preserve change/state evidence |
| 25 | Database replacement in change set | Freeze deployment and preserve change/state evidence |
| 26 | RDS PITR restore gap | Freeze deployment and preserve change/state evidence |
| 27 | PostgreSQL replication lag | Stop promotion; verify identity, approvals and service health |
| 28 | MongoDB election during promotion | Stop promotion; verify identity, approvals and service health |
| 29 | Redis failover p99 regression | Stop promotion; verify identity, approvals and service health |
| 30 | MSK under-replicated partitions | Stop promotion; verify identity, approvals and service health |
| 31 | OpenSearch disk saturation | Stop promotion; verify identity, approvals and service health |
| 32 | EKS PDB blocked rollout | Stop promotion; verify identity, approvals and service health |
| 33 | AKS node drain disruption | Stop promotion; verify identity, approvals and service health |
| 34 | GitOps dual ownership | Stop promotion; verify identity, approvals and service health |
| 35 | Canary error-budget burn | Stop promotion; verify identity, approvals and service health |
| 36 | Missing audit evidence | Stop promotion; verify identity, approvals and service health |

## 7. Production runbooks

**R1 — Target preflight:** Verify project, stack, backend, AWS account, Azure tenant/subscription and deployment scope before any privileged operation.

**R2 — Identity and provenance:** Validate OIDC audience/subject, scoped roles, protected runner, source signature and pinned artifacts.

**R3 — Pulumi preview:** Review resource replacements, secrets handling, policy findings and state locks; preserve operation logs.

**R4 — CloudFormation change set:** Confirm exact stack, change set, region, parameters, capabilities, deletes and rollback policy.

**R5 — Bicep what-if:** Validate subscription, resource group, deployment scope, policy findings and destructive changes.

**R6 — Approval:** Require independent SRE/security/DBRE approval bound to digest, target, source commit and ticket.

**R7 — Stateful DBRE:** Check PITR, backups, replica lag, quorum, RPO/RTO and actual restore drill before change.

**R8 — Partial deployment:** Stop subsequent promotions, capture checkpoints, inspect real resource state; never assume automatic rollback.

**R9 — Canary SLO:** Pause on p99, availability, lag or error-budget breach; coordinate forward fix or rollback.

**R10 — Audit and handover:** Archive immutable evidence, service health, ownership, state backup and post-change review.

## 8. Troubleshooting matrix

| Symptom | Diagnose | Safe response |
|---|---|---|
| Pulumi update locked | active operation and backend | identify owner; do not blindly unlock |
| CloudFormation rollback failed | stack events, dependencies | freeze, follow documented continue-rollback plan |
| Bicep what-if noisy | API default properties and scope | inspect actual change and policy |
| Wrong provider identity | cloud account/subscription and OIDC claims | abort and revoke session |
| Partial cross-cloud promotion | tool status, dependency and health | freeze other environments, reconcile actual state |
| Database latency spikes | p99, replication, storage metrics | stop promotion, assess data consistency |
| GitOps drift loop | resource owner and reconciliation | eliminate dual writers |

## 9. 100-point final assessment

| Domain | Points |
|---|---:|
| Multi-tool architecture and preview semantics | 20 |
| CI/CD identity, provenance and policy enforcement | 20 |
| State, change-set and Azure deployment safety | 20 |
| Executable negative-path tests and evidence | 15 |
| SRE/DBRE incidents, recovery and runbooks | 15 |
| SLO, GitOps handoff and audit | 10 |
| **Total** | **100** |

Pass >=85 and zero critical findings. Critical: wrong target, unauthorized destructive replacement, leaked secret, bypassed approval, untested DB restore or failed SLO. **Publication and authored tests do not constitute operational acceptance**; native cloud integration, backup restore, CI evidence and change approvals remain pending.

**Next:** Chapter 079 — Ansible, Kubernetes and GitOps CI/CD Automation, Environment Promotion and Production Change Controls.
