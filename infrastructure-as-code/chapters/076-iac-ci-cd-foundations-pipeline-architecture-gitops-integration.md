# Chapter 076 — Infrastructure as Code CI/CD Foundations, Pipeline Architecture and GitOps Integration

**Part 16 — IaC CI/CD · Chapter 076/120 · SRE/DevOps/DBRE**

## Learning outcomes

Design safe CI/CD pipelines for Terraform/OpenTofu, Pulumi, CloudFormation, Bicep and Ansible; distinguish CI validation from privileged CD, implement protected approval and workload identity, integrate GitOps reconciliation, and operate stateful deployments under SRE/DBRE change control. This chapter begins Part 16 (076–080). **The companion lab is executable offline and performs no cloud mutations.**

## 1. Enterprise delivery architecture

~~~text
Developer PR / signed commit / CODEOWNERS
               |
      lint / fmt / unit / SAST
               |
   provider + module dependency scans
               |
       environment target matrix
               |
  short-lived workload identity (OIDC)
               |
  remote state lock + plan/preview
               |
    signed immutable plan artifact
               |
   security / SRE / DBRE approvals
               |
    bounded canary apply / rollout
               |
  Prometheus / OTel / SLO health gate
               |
  GitOps reconciliation / audit trail
               |
      backup / restore / handover
~~~

**CI** validates source and expected behavior without broad deployment privileges. **CD** may execute infrastructure changes only with verified identities, immutable artifacts and change authorization. GitOps controllers reconcile desired Git state with the cluster; they do not replace cloud provisioning or backend locking. IaC pipelines must define ownership boundaries between Terraform/Pulumi-managed infrastructure and Argo CD/Flux-managed Kubernetes objects to prevent two controllers from fighting over the same resource.

## 2. Core design decisions

| Concern | Enterprise control | Failure prevented |
|---|---|---|
| Source | protected branches, reviews, signed commits | unauthorized changes |
| Supply chain | pinned runner images, actions, providers and checksums | tampered dependencies |
| Identity | scoped OIDC/workload federation | static key exposure |
| Target | verify account, subscription, project, region and stack | wrong-environment apply |
| State | encrypted versioned backend, locking and recovery | concurrent corruption |
| Plan | fresh, immutable, signed plan bound to commit and target | plan/apply mismatch |
| Policy | enforce destructive, encryption, tagging and identity constraints | unsafe resources |
| Approvals | separation of duties, DBRE sign-off for stateful changes | approval bypass |
| Rollout | bounded concurrency, canary, health gates | broad outage |
| Audit | CI logs, plan digest, state history, change ticket | untraceable operations |

Use provider-native preview mechanisms appropriately: Terraform/OpenTofu plan, Pulumi preview, CloudFormation change sets, ARM/Bicep what-if, Ansible check mode (not universally side-effect free). **A preview is not a guarantee** that apply will succeed or that provider state will remain unchanged. Recheck drift and target identity close to deployment.

## 3. IaC pipelines and GitOps

For Terraform/OpenTofu, do not commit state or secrets; use locked remote state and restrict apply to protected environments. For Pulumi, verify stack/backend, encrypted secrets and Automation API identity. For CloudFormation, review change sets, stack policies, StackSet targets and rollback status. For Bicep, validate scope, Azure RBAC/Policy, deployment stack deletion behavior and what-if. For Ansible, enforce inventory scope, privilege boundaries, idempotency and check-mode limitations.

Argo CD and Flux continuously reconcile Kubernetes desired state; pipeline promotion should update reviewed Git manifests rather than mutating the same Kubernetes objects directly. Use distinct owners for Helm releases, namespaces, CRDs and operators. Emergency hotfixes require incident records and subsequent Git reconciliation.

## 4. Production DBRE guardrails

**PostgreSQL/Aurora:** PITR retention, backup integrity, replica lag, parameter group reboot, connection budget and storage growth. **MongoDB:** election quorum, oplog window, backup and restore evidence. **Redis:** failover readiness, persistence tradeoffs, client retry and cache stampede protection. **Kafka/MSK:** ISR, replication factor, partition reassignment and broker drain. **Elasticsearch/OpenSearch:** shard size, disk IOPS, throughput, search rejections and reindex windows. **Kubernetes:** PDBs, disruption budgets, node draining, persistent volumes and identity.

A passing IaC unit test is not a database recovery test. Require actual restore rehearsal and SRE/DBRE acceptance for destructive or stateful changes.

## 5. Hands-on Lab A — Offline policy gate

Files: \`labs/chapter-076/gate.py\`, \`policy.json\`, \`fixtures/safe.json\`, \`fixtures/unsafe.json\`, \`test_gate.py\`.

~~~bash
cd infrastructure-as-code/labs/chapter-076
python3 gate.py fixtures/safe.json policy.json
python3 gate.py fixtures/unsafe.json policy.json  # expected nonzero
python3 -m unittest -v test_gate.py
~~~

The fail-closed gate validates a declared evidence manifest for source provenance, OIDC, target, plan, state, backups, DBRE approvals and SLO. It **does not** inspect actual cloud identities, parse native plan files or validate signed approvals. Production implementations must independently collect and cryptographically verify evidence.

## 6. Hands-on Lab B — Offline pipeline simulator

~~~bash
python3 -m unittest -v test_pipeline.py
bash run-preflight.sh
~~~

The state machine enforces \`lint -> unit -> security -> plan -> approval -> backup -> canary -> slo -> audit\`. Inject skipped approvals, missing backups, failed SLO and duplicate stages. Every failure halts progress. A pipeline failure is not proof of rollback.

## 7. Hands-on Lab C — CI templates

Study \`gitlab-ci.yml.example\` and \`github-actions.yml.example\`. They intentionally run **validation only**; any plan, approval or apply jobs are placeholders, not deployable production workflows. Before enabling CD, implement workload identity federation, signed immutable plans, state locking, policy verification, protected environment approvals, real canary telemetry and change auditing. Do not enable cloud mutations during this chapter.

## 8. Hands-on Lab D — GitOps conflict tabletop

A GitLab job directly patches a Kubernetes Deployment while Argo CD owns the same resource. Diagnose continuous drift and repeated rollbacks. Resolve ownership: IaC provisions cluster/network/identity; GitOps manages declared application manifests. Document sync windows, health checks, CRD upgrade ownership and emergency exceptions.

## 9. Production SRE/DBRE incident simulations

| Incident | Signal | First containment |
|---|---|---|
| Wrong AWS account | caller mismatch | stop pipeline |
| Wrong Azure subscription | scope mismatch | revoke session |
| Wrong GCP project | project mismatch | block |
| Wrong Pulumi stack | stack mismatch | abort |
| Wrong Terraform workspace | workspace mismatch | halt |
| OIDC trust misconfiguration | claims denied | fix trust safely |
| CI static token leaked | secret scan | rotate |
| Compromised runner | suspicious jobs | quarantine |
| Tampered provider plugin | digest mismatch | block |
| Unpinned action changed | provenance drift | pin |
| Remote state lock contention | lock error | identify owner |
| Lost state checkpoint | backend error | restore backup |
| Stale plan artifact | digest/commit mismatch | regenerate |
| Approval bypass | unsigned change | reject |
| Policy engine unavailable | enforcement gap | fail closed |
| Terraform replacement of RDS | destructive plan | DBRE gate |
| PostgreSQL PITR gap | restore test | stop |
| Aurora replica lag | replication alert | pause |
| MongoDB primary stepdown | election alarm | preserve quorum |
| Redis failover regression | p99 spike | halt |
| MSK ISR shrink | under-replicated partitions | freeze |
| OpenSearch IOPS saturation | latency/disk queue | capacity review |
| EKS PDB blocks rollout | eviction failures | stop |
| AKS node drain disruption | unavailable pods | pause |
| GitOps reconciliation loop | drift alert | resolve ownership |
| CRD operator version skew | controller errors | halt |
| Cloud API rate limiting | 429 responses | bounded retry |
| Partial infrastructure apply | resource mismatch | preserve state |
| Backup checksum failure | integrity alarm | block |
| Canary SLO breach | error-budget burn | stop promotion |
| Cost spike | budget alarm | owner review |
| Audit artifact missing | compliance gap | reject acceptance |

## 10. Production runbooks

**R1 PR preflight:** verify source provenance, dependency pins, static/unit/security checks.

**R2 Identity:** verify OIDC audience, subject, scoped role and expiry; revoke leaked credentials.

**R3 Backend locking:** identify active operation and checkpoint; never force unlock blindly.

**R4 Plan approval:** verify target, signed digest, deletes/replacements, drift and change ticket.

**R5 Stateful recovery:** verify backups, PITR, quorum, replica lag, RPO/RTO and restore drill.

**R6 GitOps drift:** compare desired Git, actual state and controller health; resolve ownership.

**R7 Partial apply:** freeze, preserve state/logs, assess resources and coordinate recovery.

**R8 Canary SLO:** stop promotion on error-budget burn, investigate telemetry and choose safe rollback.

**R9 Supply chain:** quarantine runner/artifacts, rotate identities and rebuild pinned inputs.

**R10 Handover:** archive plan, approvals, state evidence, health checks and incident timeline.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Architecture and stage separation | 20 |
| Identity, secrets and supply chain | 20 |
| Plan, approval and state governance | 20 |
| Offline executable tests | 15 |
| SRE/DBRE incidents and recovery | 15 |
| Audit, SLO, GitOps and handover | 10 |
| **Total** | **100** |

Pass >=85/100 with **zero critical findings**. Critical: wrong cloud target, unauthorized destructive apply, credential leak, missing backup/restore evidence, bypassed approval or failed SLO. Offline test results alone do not constitute operational acceptance.

**Validation evidence:** 43 Python unit tests passed locally on 2026-10-19; safe fixture passed, unsafe fixture rejected. No cloud infrastructure changes or live integration tests performed.

**Next:** Chapter 077 — Terraform and OpenTofu CI/CD Pipelines, Plan/Apply Controls and State-Safe Delivery.
