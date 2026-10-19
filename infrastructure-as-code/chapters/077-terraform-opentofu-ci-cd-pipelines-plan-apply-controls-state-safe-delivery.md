# Chapter 077 — Terraform and OpenTofu CI/CD Pipelines, Plan/Apply Controls and State-Safe Delivery

**Part 16 — IaC CI/CD · Chapter 077/120 · SRE/DevOps/DBRE**

## Learning objectives

Build governed CI/CD workflows for Terraform and OpenTofu with immutable saved plans, state-safe delivery, cloud identity verification, policy gates, database reliability controls, and GitOps boundaries. The accompanying executable lab is **offline and non-provisioning**; native plan/apply, cloud IAM, state backend locking and production acceptance are not validated by it.

## 1. Enterprise delivery architecture

~~~text
Signed PR + CODEOWNERS + protected branch
               |
fmt / validate / unit / SAST / provider pin checks
               |
short-lived OIDC identity + target verification
               |
terraform/tofu init -> plan -out=artifact
               |
plan -detailed-exitcode + plan JSON review
               |
policy / no destroy / no stateful replace
               |
encrypt saved plan + bind commit,target,tool,digest
               |
security + SRE + DBRE approval
               |
freshness + identity + artifact revalidation
               |
terraform/tofu apply saved plan under state lock
               |
canary / SLO / backup / audit / GitOps handover
~~~

CI jobs should not hold privileged production credentials. CD jobs should use narrowly scoped short-lived federation, environment protection and separation of duties. Use an immutable runner and pin Terraform/OpenTofu, providers, modules, actions and policy engines. A saved plan can contain sensitive values, even when CLI display redacts them: encrypt, restrict, expire and destroy artifacts after retention requirements.

## 2. Terraform and OpenTofu execution semantics

`terraform init` or `tofu init` initializes providers and backend. Validate HCL with `fmt -check` and `validate`; these are not security attestations. `plan -out=planfile -detailed-exitcode` returns 0 (no changes), 2 (changes), or 1 (error); CI must treat 1 as failure and 2 as a reviewable change, not as a generic failed job. For machine review, `show -json planfile` exposes resource changes, planned values and possibly secrets: handle it as sensitive. Never automatically approve destructive changes based solely on a human-readable diff.

`apply planfile` executes a saved plan rather than recalculating a fresh plan. Confirm exact commit, provider/plugin lockfile, workspace, backend, identity, artifact checksum and approvals. Even saved plans do not eliminate drift or cloud-side races; if assumptions changed, stop and regenerate. Avoid `-lock=false`, blind `force-unlock`, unreviewed `-auto-approve` and `destroy` in production.

## 3. State and backend reliability

Use encrypted, access-restricted, versioned remote state and a backend with appropriate concurrency/locking semantics. Different backends implement locks differently; test the selected backend rather than assuming global consistency. Maintain tested recovery procedures for checkpoints, access policies and encryption keys. A force-unlock during an active update can cause conflicting writers and state loss. Distinguish refresh-only changes, drift remediation, imports, moves, replacement, and destroy.

## 4. Enterprise CI/CD and GitOps boundaries

Use protected GitLab CI or GitHub Actions jobs for validate, plan, review and apply. Do not embed long-lived AWS/Azure/GCP credentials in YAML. GitOps controllers (Argo CD/Flux) should own application manifests, while Terraform/OpenTofu owns explicitly assigned cloud infrastructure. Never let two controllers reconcile the same Kubernetes resource. Promotion should preserve provenance and use environment-specific state and approvals.

## 5. DBRE safeguards

| Platform | Change hazard | Required gate |
|---|---|---|
| PostgreSQL/RDS/Aurora | replacement, reboot, PITR gap | restore test, lag, DBRE approval |
| MongoDB | quorum loss, replica reconfiguration | elections, oplog, backup |
| Redis | failover or data-loss window | persistence, clients, latency |
| Kafka/MSK | ISR shrink, broker replacement | replication and availability |
| Elasticsearch/OpenSearch | disk/IOPS pressure, reindex | shard size, storage and SLO |
| EKS/AKS/GKE | disruptive rollout | PDBs, topology, storage |

## 6. Executable hands-on labs

**Lab A — Offline governance gate.** From `infrastructure-as-code/labs/chapter-077`, run:

~~~bash
python3 gate.py fixtures/safe.json policy.json
python3 gate.py fixtures/unsafe.json policy.json  # expected rejection
python3 -m unittest -v test_gate.py test_pipeline.py
bash run-preflight.sh
~~~

The gate verifies **self-declared** controls for signed source, pinned toolchain, OIDC, plan digest, backend locking, no destroy, no stateful replacement, backup, DBRE approval and SLO. It is not a parser of real `terraform show -json`, cloud IAM evidence or signatures.

**Lab B — Stage machine.** Simulate `validate -> init -> plan -> policy -> approval -> backup -> revalidate -> apply -> health -> audit`. Inject stage skips, missing approval, backup failure, stale plan and failed health. The simulator never invokes Terraform/OpenTofu or a cloud.

**Lab C — Optional native local validation.** Inspect `examples/main.tf`, a no-cloud `terraform_data` resource, with `tofu fmt -check`, `tofu init -backend=false` and `tofu validate` in an isolated lab. Native tools are optional; the commands were not executed here. Do not deploy the example to production.

**Lab D — CI examples.** Review `gitlab-ci.yml.example` and `github-actions.yml.example`. They intentionally validate only; plan and apply jobs are inert placeholders until secure identity, signed artifacts, policies and approvals are implemented.

**Lab E — Incident game day.** Simulate a planned Aurora replacement while PostgreSQL PITR is failing and a state lock is held. Freeze the rollout; preserve plan, state and logs; verify restore evidence and identity; require DBRE/SRE approval before recovery.

## 7. Production SRE/DBRE incident scenarios

| # | Scenario | Immediate containment |
|---|---|---|
| 1 | Wrong AWS account | Stop promotion; validate target and service health |
| 2 | Wrong Azure subscription | Stop promotion; validate target and service health |
| 3 | Wrong GCP project | Stop promotion; validate target and service health |
| 4 | Incorrect Terraform workspace | Stop promotion; validate target and service health |
| 5 | Backend URL mismatch | Stop promotion; validate target and service health |
| 6 | OIDC audience mismatch | Quarantine or revoke; revalidate provenance |
| 7 | Leaked CI static token | Quarantine or revoke; revalidate provenance |
| 8 | Compromised runner | Quarantine or revoke; revalidate provenance |
| 9 | Tampered provider plugin | Quarantine or revoke; revalidate provenance |
| 10 | Unpinned GitHub Action | Quarantine or revoke; revalidate provenance |
| 11 | Concurrent state lock | Freeze apply; preserve state and evidence |
| 12 | Force unlock during active apply | Freeze apply; preserve state and evidence |
| 13 | Missing state backup | Freeze apply; preserve state and evidence |
| 14 | Corrupt state snapshot | Freeze apply; preserve state and evidence |
| 15 | Stale plan artifact | Freeze apply; preserve state and evidence |
| 16 | Plan bound to wrong commit | Freeze apply; preserve state and evidence |
| 17 | Plan target changed | Freeze apply; preserve state and evidence |
| 18 | Plan digest mismatch | Freeze apply; preserve state and evidence |
| 19 | Policy engine outage | Stop promotion; validate target and service health |
| 20 | Approval bypass | Stop promotion; validate target and service health |
| 21 | Unauthorized destroy | Stop promotion; validate target and service health |
| 22 | RDS instance replacement | Stop promotion; validate target and service health |
| 23 | Aurora parameter reboot | Stop promotion; validate target and service health |
| 24 | PostgreSQL PITR gap | Freeze apply; preserve state and evidence |
| 25 | MongoDB election instability | Stop promotion; validate target and service health |
| 26 | Redis failover regression | Stop promotion; validate target and service health |
| 27 | Kafka/MSK ISR shrink | Stop promotion; validate target and service health |
| 28 | OpenSearch storage IOPS bottleneck | Stop promotion; validate target and service health |
| 29 | EKS PDB eviction failure | Stop promotion; validate target and service health |
| 30 | AKS node drain disruption | Stop promotion; validate target and service health |
| 31 | GitOps controller ownership conflict | Stop promotion; validate target and service health |
| 32 | Cloud API rate limiting | Stop promotion; validate target and service health |
| 33 | Partial apply | Freeze apply; preserve state and evidence |
| 34 | Canary SLO breach | Stop promotion; validate target and service health |
| 35 | Missing audit trail | Stop promotion; validate target and service health |
| 36 | FinOps budget spike | Stop promotion; validate target and service health |

## 8. Production runbooks

**R1 — PR provenance and provider pin validation.** Record change ticket and source revision; fail closed on missing provenance.

**R2 — OIDC account/tenant/project identity verification.** Verify workload identity, least privilege and expiry before any privileged job.

**R3 — Backend encryption and state lock triage.** Identify active operation; preserve state; never force-unlock blindly.

**R4 — Saved plan creation and digest verification.** Inspect creates/deletes/replacements; verify encrypted plan digest and target.

**R5 — Protected approval and separation of duties.** Confirm independent approvals and immutable plan binding.

**R6 — Stateful DBRE backup/PITR/restore evidence.** Verify PITR, backup checksum, replica quorum, RPO/RTO and restore drill.

**R7 — Partial apply and checkpoint preservation.** Freeze pipeline, capture events, assess actual resource state and recovery.

**R8 — GitOps drift and controller ownership.** Compare Git desired state and controller health; resolve ownership.

**R9 — Canary SLO and rollback decision.** Stop promotion on SLO regression and coordinate rollback/forward-fix.

**R10 — Post-deployment audit and handover.** Archive change, plan, execution, state, metrics and owner acceptance.


## 9. Troubleshooting and failure taxonomy

A `plan` exit 1 is an error; 2 means changes. Backend lock conflicts demand owner investigation, not disabling locking. Provider checksum failures demand dependency quarantine. Unexpected resource replacement requires graph, lifecycle, provider and DBRE review. A partial apply is not automatically rolled back. A successful pipeline does not prove service reliability or recoverability.

## 10. 100-point acceptance assessment

| Domain | Points |
|---|---:|
| Pipeline architecture and plan/apply separation | 20 |
| Identity, supply chain and artifact integrity | 20 |
| State locking, backend recovery and drift | 20 |
| Offline lab and automated negative tests | 15 |
| SRE/DBRE incident recovery and runbooks | 15 |
| GitOps, SLO and audit handover | 10 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical failures: wrong target, unauthorized destroy/replacement, unverified approval, plaintext secret leakage, absent recovery evidence or failed SLO. **57 offline unit tests passed locally; safe fixture passed, unsafe fixture rejected.** No cloud changes or native Terraform/OpenTofu integration tests were performed.

**Next:** Chapter 078 — Pulumi, CloudFormation and Bicep CI/CD Pipelines, Policy Gates and Safe Deployment Promotion.
