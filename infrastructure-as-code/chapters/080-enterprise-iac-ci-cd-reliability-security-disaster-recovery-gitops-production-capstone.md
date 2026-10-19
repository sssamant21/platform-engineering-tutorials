# Chapter 080 — Enterprise IaC CI/CD Reliability, Security, Disaster Recovery and GitOps Production Capstone

**Part 16 — IaC CI/CD · Chapter 080/120 · Final enterprise reliability capstone**

## Learning outcomes

Integrate Chapters 076–079 into a governed enterprise IaC delivery platform spanning Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes, Helm, Argo CD and Flux. Build a fail-closed promotion model, secure identity and artifact provenance, state/lock recovery, DBRE safeguards, SLO-driven canaries and tested disaster recovery. The companion labs run **offline** and **never mutate cloud resources**. A passing offline lab is not production acceptance.

## 1. Reference architecture and trust boundaries

~~~text
Signed source / CODEOWNERS / change ticket
                 |
  unprivileged CI: fmt, validate, unit, SAST, SBOM
                 |
  pinned toolchain / modules / providers / runner
                 |
       isolated plan/preview workers
    Terraform/OpenTofu | Pulumi | CFN | Bicep
                 |
    Ansible dry-run | K8s diff | GitOps diff
                 |
     policy-as-code / risk classification
                 |
    immutable plan, digest, provenance, target
                 |
   protected approval + DBRE recovery evidence
                 |
  short-lived OIDC / least privilege / state lock
                 |
  canary/serial rollout / bounded concurrency
                 |
     telemetry + SLO / error-budget gate
                 |
  production promotion / GitOps reconciliation
                 |
  audit / FinOps / backup / DR / handover
~~~

**CI trust boundary:** PR validation cannot access privileged production credentials or untrusted secrets. **CD trust boundary:** approved release artifact is bound to immutable commit, tool version, environment and target; an independent runner obtains short-lived identity. **State boundary:** Terraform/OpenTofu and Pulumi backends must enforce encryption, restricted access, versioning, locks and recovery. **Controller boundary:** GitOps reconciles application manifests; platform IaC manages its assigned infrastructure; Ansible owns only assigned host configuration. Two controllers must not write the same resource.

## 2. Enterprise architecture decisions

| Area | Control | SRE/DBRE failure prevented |
|---|---|---|
| Source | protected branches, signed commits, CODEOWNERS | unauthorized change |
| Supply chain | pinned runner/action/provider/module digests | malicious dependency |
| Identity | scoped OIDC, no static cloud secrets | credential leakage |
| Targets | explicit account, tenant, subscription, project, region, cluster, stack | wrong-environment apply |
| State | encrypted, versioned, locked and recoverable | corruption, concurrent writers |
| Preview | immutable, reviewed, target-bound plan/change set/what-if | unintended destroy |
| Policy | fail closed on deletes, replacements and missing approvals | unsafe rollout |
| DBRE | PITR, restore-tested backup, lag, quorum, RPO/RTO | unrecoverable data |
| Progressive delivery | serial/rolling/canary, PDB, SLO | broad outage |
| GitOps | explicit resource ownership and safe pruning | drift loop |
| DR | fencing, consistency, tested cutover and rollback decision | split brain |
| FinOps/audit | budgets, tags, retained evidence | untracked cost or change |

## 3. Tool-specific execution contracts

**Terraform/OpenTofu:** use `init`, `fmt -check`, `validate`, `plan -out` and `show -json` under protected backend/target scope. Detailed plan exit code 0 means no changes, 2 means changes, 1 means error. Treat saved plans and JSON as sensitive. Never disable state locking or assume saved plans eliminate cloud-side drift.

**Pulumi:** verify stack/backend, encrypted secrets provider, resource aliases/protection, plugin versions and Automation API preview. Partial updates require resource-state investigation, not blind retry.

**CloudFormation:** validate templates, review change sets and replacements, capabilities, stack policies, StackSets target scope and rollback status. Stack rollback is not database restore.

**Bicep:** compile and inspect Azure what-if, tenant/subscription, resource-group scope, Azure Policy and deployment stack deletion semantics. What-if is advisory, not a guarantee.

**Ansible:** pin collections, validate inventory/host limits, `become`, Vault, `serial`, handler ordering and idempotency. Check mode is not uniformly side-effect free or comprehensive.

**Kubernetes/Helm/Argo CD/Flux:** verify context, namespace, RBAC, immutable image digest, PDBs, PVCs, admission, CRD ownership, GitOps sync windows and prune policy. Git rollback cannot reverse a destructive schema migration.

## 4. Reliability engineering and disaster recovery

A production-ready pipeline defines SLI/SLOs for availability, latency, errors, throughput and saturation, plus deployment SLOs such as rollback/repair time. Protect error budgets: abort promotion if canary health or error-budget thresholds fail. Use OpenTelemetry traces, Prometheus RED/USE metrics, logs and change annotations to correlate releases with incidents.

DR planning requires explicit **RPO** (acceptable data loss) and **RTO** (recovery time), backup integrity, restore rehearsal, region/account isolation, encryption-key recovery and incident command. Cross-region or cross-cloud database recovery needs application-consistent replication, fencing, DNS/endpoint changes, write ownership and conflict resolution. Infrastructure recreation alone is not disaster recovery.

## 5. SRE/DBRE service controls

| Platform | High-risk change | Required evidence |
|---|---|---|
| PostgreSQL/RDS/Aurora | replacement, storage or parameter reboot | PITR, restore test, replica lag, DBRE sign-off |
| MongoDB | replica-set/shard reconfiguration | quorum, oplog, backup |
| Redis | persistence/failover change | durability, reconnect, p99 |
| Kafka/MSK | broker/partition change | ISR, replication, lag |
| OpenSearch/Elasticsearch | node/disk/index migration | shard size, IOPS, throughput, SLO |
| EKS/AKS/GKE | node, CSI or cluster upgrade | PDB, volumes, snapshots, rollback |
| GitOps | prune, CRD or Helm ownership change | explicit owner, preview, sync window |

## 6. Hands-on lab — complete offline capstone

### Lab A — Multi-tool evidence policy

~~~bash
cd infrastructure-as-code/labs/chapter-080
python3 capstone_gate.py fixtures/safe.json policy.json
python3 capstone_gate.py fixtures/unsafe.json policy.json  # expected nonzero
python3 -m unittest -v test_capstone_gate.py test_delivery.py test_dr.py
bash run-preflight.sh
~~~

The gate enforces a **declared** environment/target matrix, source/identity/plan controls, backup/restore evidence, approval, SLO and audit. This is **not** verification of real signatures, IAM, cloud state, backup restorations or provider-native plan semantics. Production requires independently sourced and cryptographically verified evidence.

### Lab B — Enterprise promotion simulator

`delivery.py` enforces `source -> scan -> preview -> policy -> approval -> backup -> canary -> health -> promote -> audit`. Inject failure at each gate, skipped stages and duplicate actions. Promotion must stop on any failed gate. The simulator never runs apply.

### Lab C — DR decision engine

`dr.py` evaluates declared RPO/RTO, backup integrity, restore drill, quorum/fencing, replication lag and owner authorization. Inject failed backups, lag breaches, absent fencing and RTO breach; every failure rejects recovery readiness. This is a decision aid, not an automated database failover.

### Lab D — CI templates

Review `gitlab-ci.yml.example` and `github-actions.yml.example`: both execute offline tests only. **No production deploy job is enabled.** Add real OIDC, protected environment approvals, native plan parsing, artifact signing, backend locking and cloud-specific restore evidence before considering deployment.

### Lab E — Incident game day

Simulate a multi-cloud partial rollout: AWS RDS replacement preview, Azure AKS node drain, GCP quota error, MongoDB election and OpenSearch IOPS pressure. Freeze changes; establish incident command; inspect state/plan/audit; verify DB backups, consistency, quorum and RPO/RTO; recover only after DBRE and SRE approval.

## 7. Production incident simulations

| # | Incident | Immediate containment |
|---|---|---|
| 1 | Wrong AWS account | Stop promotion; validate target, approvals and service health |
| 2 | Wrong Azure tenant or subscription | Stop promotion; validate target, approvals and service health |
| 3 | Wrong GCP project | Stop promotion; validate target, approvals and service health |
| 4 | Wrong Terraform workspace | Stop promotion; validate target, approvals and service health |
| 5 | Wrong Pulumi stack/backend | Stop promotion; validate target, approvals and service health |
| 6 | CloudFormation StackSet target mismatch | Stop promotion; validate target, approvals and service health |
| 7 | Bicep deployment scope mismatch | Stop promotion; validate target, approvals and service health |
| 8 | Ansible production inventory selected | Stop promotion; validate target, approvals and service health |
| 9 | Kubernetes wrong context | Stop promotion; validate target, approvals and service health |
| 10 | OIDC trust misconfiguration | Revoke or quarantine; preserve forensic evidence |
| 11 | Leaked CI credential | Revoke or quarantine; preserve forensic evidence |
| 12 | Compromised runner | Revoke or quarantine; preserve forensic evidence |
| 13 | Tampered provider plugin | Revoke or quarantine; preserve forensic evidence |
| 14 | Unpinned CI action | Revoke or quarantine; preserve forensic evidence |
| 15 | Terraform state lock contention | Freeze changes; preserve state and recovery evidence |
| 16 | Forced unlock during active apply | Freeze changes; preserve state and recovery evidence |
| 17 | State backend outage | Freeze changes; preserve state and recovery evidence |
| 18 | Corrupted checkpoint | Freeze changes; preserve state and recovery evidence |
| 19 | Lost encryption key | Stop promotion; validate target, approvals and service health |
| 20 | Saved plan stale or tampered | Stop promotion; validate target, approvals and service health |
| 21 | CloudFormation rollback failure | Freeze changes; preserve state and recovery evidence |
| 22 | Pulumi partial update | Stop promotion; validate target, approvals and service health |
| 23 | Bicep deployment stack deletion | Stop promotion; validate target, approvals and service health |
| 24 | Ansible non-idempotent rerun | Stop promotion; validate target, approvals and service health |
| 25 | GitOps dual resource ownership | Stop promotion; validate target, approvals and service health |
| 26 | Argo CD destructive prune | Stop promotion; validate target, approvals and service health |
| 27 | Flux source unavailable | Stop promotion; validate target, approvals and service health |
| 28 | Helm CRD upgrade failure | Stop promotion; validate target, approvals and service health |
| 29 | EKS PDB eviction blocked | Freeze changes; preserve state and recovery evidence |
| 30 | AKS node drain disrupts stateful pod | Freeze changes; preserve state and recovery evidence |
| 31 | GKE CSI snapshot missing | Stop promotion; validate target, approvals and service health |
| 32 | PostgreSQL PITR unavailable | Freeze changes; preserve state and recovery evidence |
| 33 | Aurora unintended replacement | Stop promotion; validate target, approvals and service health |
| 34 | MongoDB election/quorum loss | Stop promotion; validate target, approvals and service health |
| 35 | Redis failover latency regression | Stop promotion; validate target, approvals and service health |
| 36 | Kafka/MSK ISR shrink | Stop promotion; validate target, approvals and service health |
| 37 | OpenSearch disk IOPS saturation | Stop promotion; validate target, approvals and service health |
| 38 | Cross-region network partition | Stop promotion; validate target, approvals and service health |
| 39 | Database replication lag exceeds RPO | Stop promotion; validate target, approvals and service health |
| 40 | Canary error-budget breach | Stop promotion; validate target, approvals and service health |
| 41 | Partial cross-cloud promotion | Stop promotion; validate target, approvals and service health |
| 42 | Cost budget overrun | Stop promotion; validate target, approvals and service health |
| 43 | Audit chain incomplete | Stop promotion; validate target, approvals and service health |
| 44 | Restore drill fails checksum | Freeze changes; preserve state and recovery evidence |
| 45 | Security approval bypass | Revoke or quarantine; preserve forensic evidence |

## 8. Production runbooks

**R1 — Change intake:** Freeze changes until signed source, ticket, owners, blast radius and maintenance window are recorded.

**R2 — Workload identity:** Verify OIDC audience, subject, target account/subscription/project, expiry and least-privilege role.

**R3 — Supply-chain integrity:** Pin CLI/providers/modules/actions/images, inspect SBOM and quarantine tampered artifacts.

**R4 — Plan and preview:** Inspect resource creates/deletes/replacements, target binding, policy and immutable digest.

**R5 — State and locks:** Identify lock owner, preserve encrypted checkpoints and backups; never force-unlock blindly.

**R6 — Stateful DBRE:** Verify PITR, restore drill, replica quorum, lag, storage, RPO/RTO and DBRE approval.

**R7 — Progressive delivery:** Enforce concurrency limits, canary health and SLO/error-budget stop conditions.

**R8 — GitOps drift:** Compare Git desired state with Argo/Flux health; remove dual writers and unsafe prune.

**R9 — DR failover:** Establish incident command, validate consistency/fencing, restore and application cutover.

**R10 — Partial apply:** Freeze all promotions, capture checkpoints and resource reality; coordinate repair.

**R11 — Security incident:** Revoke credentials, isolate runners, preserve logs and rebuild signed provenance.

**R12 — Post-change acceptance:** Record metrics, audit evidence, restore readiness, FinOps and service-owner handover.

## 9. Troubleshooting

| Symptom | Investigate | Safe response |
|---|---|---|
| Pipeline approved wrong target | OIDC claims, target matrix, immutable artifact | abort and revoke session |
| State locked unexpectedly | operation owner, backend logs | preserve checkpoint, no blind unlock |
| CloudFormation rollback fails | stack events and dependencies | freeze, follow recovery procedure |
| Pulumi partial update | stack events, provider failures | reconcile actual resources |
| GitOps fights pipeline | resource ownership and desired Git state | remove dual writers |
| Canary p99 increases | RED/USE, traces, replica lag, IOPS | stop promotion |
| Backup appears successful but restore fails | checksums, key access, recovery chain | block acceptance |
| Cross-region failover risks split brain | fencing, write ownership, replication | incident command, no automatic cutover |

## 10. Final 100-point acceptance

| Domain | Points |
|---|---:|
| Architecture, tool boundaries and delivery lifecycle | 15 |
| Identity, supply chain, policy and approvals | 15 |
| State safety, previews and artifact integrity | 15 |
| Executable tests and negative scenarios | 15 |
| Stateful DBRE recovery and disaster readiness | 15 |
| GitOps, progressive delivery and SLO controls | 15 |
| Incident runbooks, audit, FinOps and handover | 10 |
| **Total** | **100** |

**Pass:** >=85/100 and zero critical findings, with signed SRE/DBRE/security acceptance. Critical failures: wrong target, unauthorized destructive action, leaked secret, unprotected state, missing restore evidence, split-brain risk, approval bypass or failed SLO. **Publication of curriculum content is complete; native cloud integration, backup restoration and production acceptance remain pending.**

## 11. Part 16 completion

Chapters 076–080 cover IaC CI/CD foundations, Terraform/OpenTofu delivery, Pulumi/CloudFormation/Bicep promotion, Ansible/Kubernetes/GitOps and this enterprise reliability capstone. Part 16 is **5/5 chapters published**, not operationally certified.

**Next proposed:** Chapter 081 — Infrastructure as Code Security Foundations, Threat Modeling, Identity and Secrets Management (Part 17 — Security and Policy).
