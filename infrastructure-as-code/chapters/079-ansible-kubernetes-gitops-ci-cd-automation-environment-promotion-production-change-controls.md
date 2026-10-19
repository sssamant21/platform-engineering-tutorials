# Chapter 079 — Ansible, Kubernetes and GitOps CI/CD Automation, Environment Promotion and Production Change Controls

**Part 16 — IaC CI/CD · Chapter 079/120 · SRE/DevOps/DBRE**

## Objectives and prerequisites

Design safe, reproducible enterprise delivery spanning **Ansible automation**, **Kubernetes deployments** and **Argo CD/Flux GitOps**. Enforce workload identity, inventory/context isolation, immutable artifacts, controlled environment promotion, progressive delivery, SLO gates, database recovery requirements and auditability. Prerequisites: Chapters 051–065 and 076–078, Python 3.10+, Bash. Optional native tools: ansible-core, kubectl, Helm, Argo CD and Flux. The executable baseline is offline and **does not contact clusters, hosts or cloud accounts**.

## 1. Architecture

~~~text
Signed PR + CODEOWNERS + change ticket
              |
 lint / test / policy / supply-chain verification
              |
  immutable image, playbook, chart and manifest digest
              |
 inventory and kube-context target verification
              |
    workload identity + least-privilege RBAC
              |
  staging Ansible dry run / server-side dry run
              |
   GitOps sync diff and policy admission review
              |
      SRE / security / DBRE approvals
              |
     bounded canary / serial host rollout
              |
 Prometheus + OTel + RED/USE + SLO gate
              |
   GitOps production promotion and audit
              |
    recovery evidence and handover
~~~

Use separate deployment authorities: Ansible owns explicitly assigned host configuration; cluster infrastructure IaC owns networking/identity/control-plane dependencies; Argo CD or Flux owns application manifests and Helm releases. Avoid two controllers writing the same Kubernetes resource. CI pipelines should propose Git changes; GitOps controllers reconcile approved desired state.

## 2. Ansible CI/CD theory

Ansible is agentless and often imperative at task level. Idempotency depends on modules and task design, not simply on YAML. Validate inventory groups, host limits, `become` privilege, Vault, handler order, tags, collection pins and connection security. `ansible-playbook --check --diff` can provide useful preview but is **not guaranteed side-effect free or complete**; custom modules, commands, shell tasks and lookups may behave differently. Use `serial`, `max_fail_percentage`, `any_errors_fatal`, health checks and maintenance windows to bound blast radius. Prevent simultaneous playbooks from modifying the same fleet.

## 3. Kubernetes CI/CD and progressive delivery

Use immutable image digests, Pod Security Standards, admission policy, RBAC, NetworkPolicy, requests/limits, probes, PDBs and topology spread. Validate manifests with client/server dry run as appropriate; server dry run can invoke admission webhooks and requires API access. A Deployment rollout and a StatefulSet rollout have different availability and data-safety implications. Never assume `kubectl rollout undo` reverses schema or database changes. For Helm, review rendered templates, release history and CRD upgrade strategy.

## 4. Argo CD and Flux GitOps

Argo CD tracks Applications and sync policies; Flux uses Sources, Kustomizations and HelmReleases. Set explicit namespace/project scope, sync windows, pruning safeguards, drift alerts, image provenance and secret decryption controls. GitOps rollback means restoring desired Git state; reconcile application data separately. Production GitOps should enforce protected promotion branches, reviewed PRs and a documented emergency hotfix reconciliation path.

## 5. Environment promotion model

| Stage | Purpose | Required evidence |
|---|---|---|
| PR validation | syntax, policy, provenance | lint/test logs, digest |
| Dev | functional integration | health checks, rollback plan |
| Staging | production-like verification | PDB/quotas, smoke tests, DBRE backup |
| Canary | limited blast radius | SLO, latency, lag, errors |
| Production | approved desired state | signed change, target, freeze check |
| Handover | reliability acceptance | audit, DR evidence, owner |

**Promote identical immutable artifacts**, not mutable tags. Bind promotion to commit SHA, inventory/kube-context, GitOps app scope, chart/image digest, change ticket, backup evidence, approvers and SLO threshold.

## 6. Stateful SRE/DBRE guardrails

**PostgreSQL/Aurora:** validate PITR, replica lag, DDL compatibility and connection pool readiness. **MongoDB:** election quorum and oplog retention. **Redis:** persistence and client reconnect. **Kafka/MSK:** ISR and broker drain. **Elasticsearch/OpenSearch:** shard pressure, IOPS and index migration. **EKS/AKS/GKE:** PDBs, CSI snapshots, admission, network and node-drain budgets. Application rollback does not reverse irreversible data migrations; use expand/contract schema releases and verified restore rehearsals.

## 7. Hands-on labs

### Lab A — Offline policy gate

~~~bash
cd infrastructure-as-code/labs/chapter-079
python3 delivery_gate.py fixtures/safe.json policy.json
python3 delivery_gate.py fixtures/unsafe.json policy.json  # expected rejection
python3 -m unittest -v test_delivery_gate.py test_promotion.py
bash run-preflight.sh
~~~

The gate validates **declared evidence**, not actual Kubernetes RBAC, Ansible inventories, signed attestations or GitOps controllers. Safe fixture passes; unsafe fixture is rejected. Fail-closed checks include immutable digests, context, inventory, source provenance, approval, backups and SLO.

### Lab B — Offline promotion state machine

Run the tests for `validate -> inventory -> dryrun -> diff -> policy -> approve -> backup -> canary -> health -> promote -> audit`. Inject skipped stages, failed dry run, approval bypass, backup gaps and canary failures. A failed rollout must stop; it is not automatically rolled back.

### Lab C — Native syntax-only examples (optional)

Study `examples/playbook.yml` (localhost-only debug, no mutation) and `examples/deployment.yaml` (sample Deployment; **do not apply**). If Ansible is installed, run `ansible-playbook --syntax-check -i localhost, -c local examples/playbook.yml`. If kubectl is installed, inspect YAML offline; `kubectl apply --dry-run=client` may still need cluster discovery. CI YAML examples intentionally run **offline validation only**.

### Lab D — GitOps dual-writer incident

Simulate a CI job using `kubectl patch` on a Deployment also managed by Argo CD. Observe conceptual drift/reconciliation and design a remediation that restores single-writer ownership, PR-based promotion, sync windows and rollback safeguards. No cluster access required.

### Lab E — DBRE production game day

An Ansible rollout changes PostgreSQL connection pool configuration while an Argo CD sync deploys a new app image; a Redis failover and OpenSearch storage pressure occur. Freeze promotion, inspect SLO and replica lag, verify PITR/restore evidence and coordinate incident command.

## 8. Production incident simulations

| # | Scenario | Containment |
|---|---|---|
| 1 | Wrong Ansible inventory | Stop promotion, verify target and controller ownership |
| 2 | Ansible become privilege escalation | Revoke access and preserve forensic evidence |
| 3 | Unpinned collection supply-chain compromise | Revoke access and preserve forensic evidence |
| 4 | Ansible check mode misleading result | Stop promotion, verify target and controller ownership |
| 5 | Non-idempotent playbook rerun | Stop promotion, verify target and controller ownership |
| 6 | Concurrent playbook on same hosts | Stop promotion, verify target and controller ownership |
| 7 | Unbounded serial rollout | Stop promotion, verify target and controller ownership |
| 8 | Ansible Vault secret leak | Revoke access and preserve forensic evidence |
| 9 | Kubernetes wrong context | Stop promotion, verify target and controller ownership |
| 10 | Kubernetes wrong namespace | Stop promotion, verify target and controller ownership |
| 11 | Cluster-admin kubeconfig in CI | Stop promotion, verify target and controller ownership |
| 12 | ServiceAccount token exposure | Revoke access and preserve forensic evidence |
| 13 | Unreviewed CRD conversion | Stop promotion, verify target and controller ownership |
| 14 | Admission webhook outage | Stop promotion, verify target and controller ownership |
| 15 | PodDisruptionBudget eviction block | Stop promotion, verify target and controller ownership |
| 16 | Deployment rollout unavailable | Stop promotion, verify target and controller ownership |
| 17 | StatefulSet volume attachment conflict | Freeze rollout and obtain DBRE recovery evidence |
| 18 | PersistentVolume reclaim policy error | Freeze rollout and obtain DBRE recovery evidence |
| 19 | Argo CD dual ownership conflict | Stop promotion, verify target and controller ownership |
| 20 | Argo CD auto-sync destructive prune | Stop promotion, verify target and controller ownership |
| 21 | Flux reconciliation drift loop | Stop promotion, verify target and controller ownership |
| 22 | GitOps secret decryption failure | Revoke access and preserve forensic evidence |
| 23 | Helm chart value drift | Stop promotion, verify target and controller ownership |
| 24 | Helm release rollback fails | Stop promotion, verify target and controller ownership |
| 25 | Git branch promotion bypass | Stop promotion, verify target and controller ownership |
| 26 | Unsigned image tag mutation | Stop promotion, verify target and controller ownership |
| 27 | Wrong container registry digest | Stop promotion, verify target and controller ownership |
| 28 | OIDC workload identity mismatch | Revoke access and preserve forensic evidence |
| 29 | Canary SLO burn | Stop promotion, verify target and controller ownership |
| 30 | PostgreSQL PITR gap | Freeze rollout and obtain DBRE recovery evidence |
| 31 | MongoDB election/quorum failure | Freeze rollout and obtain DBRE recovery evidence |
| 32 | Redis failover latency spike | Stop promotion, verify target and controller ownership |
| 33 | MSK ISR shrink | Stop promotion, verify target and controller ownership |
| 34 | OpenSearch storage saturation | Stop promotion, verify target and controller ownership |
| 35 | EKS node drain blocked | Stop promotion, verify target and controller ownership |
| 36 | AKS network policy outage | Stop promotion, verify target and controller ownership |
| 37 | GKE quota exhaustion | Stop promotion, verify target and controller ownership |
| 38 | Missing audit trail | Stop promotion, verify target and controller ownership |

## 9. Production runbooks

**R1 — Change preflight:** Verify signed source, branch protection, change ticket, inventory, kube-context, namespace and owner.

**R2 — Identity and secrets:** Validate OIDC claims, RBAC, Ansible become scope, Vault access and secret redaction.

**R3 — Ansible execution:** Check inventory, --check limitations, serial/batch settings, handlers and idempotency.

**R4 — Kubernetes rollout:** Inspect Deployment/StatefulSet readiness, PDBs, quotas, PVs and admission controls.

**R5 — Argo CD/Flux reconciliation:** Check desired Git revision, Application/Kustomization health, sync windows and pruning.

**R6 — Promotion gate:** Require immutable digest, staging evidence, security/SRE/DBRE approval and freeze checks.

**R7 — Database recovery:** Verify PITR, backup checksums, replica quorum, lag, RPO/RTO and restore drill.

**R8 — Partial deployment:** Freeze promotion, preserve logs, inspect actual state, and avoid blind rollback.

**R9 — Canary SLO:** Stop rollout on p99, availability, error-budget, queue lag or saturation regression.

**R10 — Handover:** Archive provenance, deployment diff, approval, monitoring, backup and incident timeline.

## 10. Troubleshooting

| Symptom | Diagnosis | Safe action |
|---|---|---|
| Ansible reports changed repeatedly | non-idempotent task | inspect module semantics, make task convergent |
| Ansible check mode succeeds but apply fails | unsupported check behavior | stage rehearsal and bounded rollout |
| Kubernetes pods Pending | quota, scheduler, storage, taints | inspect events; fix capacity or placement |
| GitOps constantly reverts CI changes | dual resource ownership | restore one source of truth |
| Argo CD sync blocked | policy, hooks, waves, CRDs | inspect app health and policy |
| Flux reconciliation suspended | source/controller errors | resolve source, review suspension reason |
| Canary SLO breached | p99, errors, lag, resource pressure | stop promotion, assess recovery |
| DB migration incompatible | schema/app mismatch | freeze, use expand/contract and DBRE runbook |

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Ansible architecture, inventory and safe execution | 20 |
| Kubernetes delivery and progressive rollout | 20 |
| GitOps ownership, policy and environment promotion | 20 |
| Offline labs and automated negative tests | 15 |
| SRE/DBRE incidents and recovery | 15 |
| Audit, SLO and handover | 10 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong inventory/cluster, unauthorized privileged action, leaked secret, destructive prune, missing restore evidence, approval bypass or failed SLO. The lab is a governance simulator, **not a production deployment test**.

**Next:** Chapter 080 — Enterprise IaC CI/CD Reliability, Security, Disaster Recovery and GitOps Production Capstone.
