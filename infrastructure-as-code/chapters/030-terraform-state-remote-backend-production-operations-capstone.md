# Chapter 030 — Terraform State and Remote Backend Production Operations Capstone

**Part 06 — State and Remote Backends (final capstone)**  
**Audience:** SRE, DBRE, Platform Engineering, Cloud Security  
**Toolchain:** Terraform >= 1.5, Python >= 3.9, Bash; optional OpenTofu with compatibility validation  
**Execution model:** Local-only, zero-cloud-cost lab plus *illustrative* production backend examples. Publication does not imply tests or cloud recovery drills have run.

## 1. Mission and learning objectives

Operate a production-grade Terraform state service safely across normal changes, concurrent operations, drift, state migration, backup/restore and disaster recovery. This capstone integrates Chapters 026–029 into a single acceptance workflow with:

1. State identity, address, lineage and serial inspection.
2. Remote backend selection, least-privilege access, encryption, locking and versioning.
3. Safe import, move, remove and drift reconciliation decisions.
4. Backup integrity, migration and recovery with explicit RPO/RTO.
5. Automated, fail-closed operational policy and plan-action gates.
6. Incident response, DBRE data recovery separation and audit evidence.

**Boundary:** Terraform state is a map of managed infrastructure; it is not a PostgreSQL WAL archive, RDS snapshot, OpenSearch snapshot, Redis RDB/AOF, Kafka log or Kubernetes persistent volume backup.

## 2. Reference production architecture

~~~text
Git-reviewed HCL + pinned CLI/providers + ticket
                    |
     CI OIDC / workload identity + RBAC
                    |
       Preflight: validate + policy + plan
                    |
          Human change approval
                    |
    Remote state backend / exclusive lock
     |           |             |
  Encryption  Versioning    Audit events
     |           |             |
  Protected backup / DR copy (separate failure domain)
                    |
        Approved plan/apply or recovery
                    |
      Verify addresses, lineage, serial
                    |
   Verify real objects + DB data + application SLO
                    |
          Acceptance evidence / RCA
~~~

The backend and application data stores are independent failure domains. An encrypted state object can still be read by an overprivileged principal. A successful lock does not prove an application is healthy. A successful \`terraform plan\` does not prove a database restore meets RPO/RTO.

## 3. State identity and authoritative source

State typically contains \`lineage\`, \`serial\`, resource instances, outputs and provider data. **Lineage** distinguishes a state history; **serial** identifies successive snapshots. Neither is a cryptographic integrity proof. Before any migration or restore, independently verify the account/project, backend bucket/container, key, workspace, lineage, serial, resource addresses and object IDs.

Do not manually edit internal state JSON. Do not assume \`terraform state pull\` is safe to share: it can expose sensitive provider attributes and outputs. Keep raw state, plans, debug logs and backup archives out of Git and general ticket systems. A redacted metadata summary is safer but still needs access review.

## 4. Backend reference and lock behavior

| Backend | Typical locking | Required production controls |
|---|---|---|
| S3 | native S3 lockfile on supported Terraform versions; older DynamoDB approaches exist | private bucket, scoped IAM, encryption, versioning, lock object permissions, audit |
| Azure Blob | blob lease | Entra identity/RBAC, encryption, versioning/soft delete, logs |
| GCS | backend-managed locking | scoped IAM, versioning, encryption, audit |
| HCP Terraform | workspace/run concurrency | workspace permissions, managed state versions, audit |

For S3, \`use_lockfile = true\` requires a sufficiently recent Terraform version (Terraform 1.10+); verify your pinned CLI. Never disable locking or force-unlock until an incident commander verifies no writer remains. \`terraform init -migrate-state\` migrates state; \`-reconfigure\` does not.

## 5. Change and recovery decision matrix

| Situation | Preferred path | Stop condition |
|---|---|---|
| Routine approved update | plan → review → apply → verify | unexpected delete/replacement |
| Address rename | \`moved\` block + plan | change to object identity |
| Existing object adoption | import block + ownership check | duplicate state ownership |
| Ownership transfer | \`removed\` block with \`destroy = false\` | no receiving owner |
| Drift | classify → update HCL or reconcile | unknown manual/security change |
| Backend migration | backup → freeze → migrate → verify | divergent state or active writers |
| Lost/corrupt state | freeze → identify authoritative version → restore → reconcile | unknown lineage or stale snapshot |
| Data outage | DB/platform restore runbook | attempting state restore as data recovery |

## 6. Capstone repository layout

~~~text
labs/chapter-030/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  policy/acceptance-policy.json
  fixtures/acceptance-safe.json
  fixtures/acceptance-unsafe.json
  fixtures/plan-safe.json
  fixtures/plan-destructive.json
  acceptance_gate.py
  test_acceptance_gate.py
  snapshot_summary.py
  run-preflight.sh
  examples/s3-backend.tf.example
  examples/migration-runbook.sh.example
  examples/ownership-transfer.tf.example
  .gitignore
~~~

The executable Terraform resources use only the built-in \`terraform_data\` provider and simulate network, database and application contracts. They **do not provision a real DB, cluster or remote backend**. The policy fixtures represent declared evidence, not independently verified cloud controls.

## 7. Lab 1 — Build the baseline

~~~bash
cd infrastructure-as-code/labs/chapter-030
terraform version
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter030.tfplan
terraform apply chapter030.tfplan
terraform state list
terraform output
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected addresses: \`terraform_data.network\`, \`terraform_data.database\`, \`terraform_data.application\`, \`terraform_data.audit\`. A second plan with identical inputs should return exit code 0. Use a separate directory and state for production-like variable tests.

## 8. Lab 2 — Backup and redacted inspection

~~~bash
umask 077
mkdir -p private-evidence
terraform state pull > private-evidence/state.json
python3 snapshot_summary.py private-evidence/state.json > private-evidence/summary.json
~~~

The summary tool reports only lineage, serial, version, count and SHA-256; no attributes or outputs. The checksum is useful for integrity comparisons, not authentication or proof of encryption. Store raw state in protected encrypted storage and remove it under retention policy. \`.gitignore\` is not a security boundary.

## 9. Lab 3 — Automated operational acceptance

~~~bash
python3 acceptance_gate.py fixtures/acceptance-safe.json fixtures/plan-safe.json policy/acceptance-policy.json
python3 acceptance_gate.py fixtures/acceptance-unsafe.json fixtures/plan-destructive.json policy/acceptance-policy.json
python3 -m unittest -v test_acceptance_gate.py
bash run-preflight.sh
~~~

The safe fixture passes and unsafe fixture is denied. The gate requires: approved change, state backup, frozen writers, exclusive lock, encryption, versioning, scoped identity, audit, restore drill, distinct source/DR destinations, positive RPO/RTO, state lineage/serial agreement, unique resource addresses, and no plan delete/replacement. This is an intentionally conservative **default-deny capstone gate**. Destructive changes require a separate reviewed exception workflow, not editing the gate to fail open.

## 10. Lab 4 — Concurrency and stale-plan incident

Tabletop two operators targeting the same backend. Record the active run, lock ID, backend object version and change ticket. Confirm the second writer waits or fails according to the backend; never use \`-lock=false\` as a workaround. If a saved plan predates a successful state update, discard and replan. A lock released after a failed apply is not evidence of full rollback: compare state with real resources.

## 11. Lab 5 — Import, move, forget and drift

- **Move:** rename \`terraform_data.database\` in a disposable copy and add a \`moved\` block; verify no unintended delete/create.
- **Import:** use a separately approved cloud sandbox and a real existing object ID. A fabricated \`terraform_data\` ID is not a valid demonstration of cloud import.
- **Forget:** use \`removed\` with \`destroy = false\` (Terraform >=1.7) or a controlled \`state rm\` with receiving-owner evidence; forgetting is not deleting.
- **Drift:** compare a \`plan -refresh-only\` with the desired-state plan, identify authorized manual changes, and choose reconciliation under approval.
- **Failure:** simulate an address conflict or duplicate ownership in a JSON fixture; require denial.

## 12. Lab 6 — Backup, migration and DR game day

1. Declare incident commander, change owner, rollback owner and freeze window.
2. Verify backend/account/workspace identity and active lock owner.
3. Take an encrypted, versioned state snapshot; capture lineage, serial, checksum and object version.
4. Verify independent DR destination, credentials and access logs.
5. Rehearse \`init -migrate-state\` only in an approved disposable remote-backend sandbox.
6. Inject source outage, 403, stale snapshot, mismatched lineage, serial regression and partial migration.
7. Determine authoritative state using evidence; never blindly overwrite with \`state push\` or bypass safety checks.
8. Restore state under exclusive ownership, create a **fresh** plan and review all changes.
9. Validate real infrastructure identities, DB data consistency, application SLO and RPO/RTO.
10. Record evidence, deviations, RCA, follow-up and cleanup.

No-cloud exercises validate process logic; they do not prove remote backend lock or cloud restore behavior.

## 13. Production SRE/DBRE failure scenarios

| Platform | Terraform concern | Independent acceptance |
|---|---|---|
| PostgreSQL / Aurora / RDS | state identity, parameter and subnet changes | WAL/PITR, replication, consistency, backups |
| Elasticsearch / OpenSearch | domain sizing and network drift | shard allocation, snapshots, search latency |
| EKS / AKS | cluster, IAM and node pool state | control plane, workloads, storage, PDBs |
| Redis | replication topology and security | persistence, failover, client reconnection |
| Kafka / MSK | broker/network changes | ISR, offsets, consumer lag |
| Snowflake | grants, integrations and warehouse config | privilege review, query health, spend |
| MongoDB | cluster topology and network state | replica set quorum, backup restore, data checks |

## 14. Troubleshooting and safe responses

| Symptom | Investigation | Action |
|---|---|---|
| All resources planned for creation | wrong backend, empty state | stop; verify identity/lineage |
| Unexpected replacement | address/config/provider change | stop; classify and reapprove |
| Lock acquisition fails | active operation/stale lock | verify owner; no blind force unlock |
| Migration leaves two states | partial transfer | freeze; compare versions, choose authority |
| Backend 403 | workload identity or IAM | verify caller, scope and logs |
| Serial mismatch | stale snapshot | stop; compare authoritative version |
| Lineage mismatch | wrong state history | isolate and investigate |
| Drift after emergency repair | out-of-band change | reconcile desired config |
| State restore succeeds, DB fails | state ≠ data backup | invoke DB PITR/restore runbook |
| Secret exposed in state artifact | excessive artifact access | contain, rotate, audit |

## 15. Production runbooks

**Normal change:** identity/backend check → backup/versioning check → validate/test → plan and policy → review approval → apply with lock → verify objects and SLO → audit.

**Lock incident:** freeze competing jobs → identify lock owner and active run → verify no writer remains → protected backup → authorized recovery/unlock with recorded ID → fresh plan.

**State migration:** review source/destination → freeze → backup → sandbox rehearsal → approved migrate-state → compare lineage/serial/addresses → verify permissions and lock → fresh plan → health acceptance → retire old access after rollback window.

**State corruption:** stop writers → preserve audit and state versions → select authoritative state → restore using CLI safety checks → reconcile actual resources → fresh plan → verify DB/application health.

**Security breach:** restrict state access → rotate exposed credentials → review access logs and versions → correct IAM and storage policies → incident RCA.

**Data DR:** execute platform-specific database/storage restore; Terraform state recovery is only a supporting infrastructure step.

## 16. Capstone acceptance (100 points)

| Area | Points |
|---|---:|
| Architecture, identity, state integrity | 15 |
| Backend IAM, encryption, versioning and locking | 20 |
| Safe state operations and drift handling | 15 |
| Automated lab, policy and negative tests | 20 |
| Backup, migration and DR game day | 20 |
| SRE/DBRE evidence, runbooks and audit | 10 |

**Pass:** >=85 and no critical failure. **Critical failure:** exposed state/credentials, public state, duplicate active ownership, unlocked concurrent writers, unverified lineage, unapproved destruction, no recoverable snapshot, or treating Terraform state recovery as data recovery.

Evidence pack: sanitized CLI versions, test output, state address summary, policy output, backup integrity metadata, restore timeline, authoritative-state decision, resource health checks, RPO/RTO observations and owner sign-off. Do not include raw state or secrets.

## 17. Cleanup

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the disposable local lab. Retain audit evidence securely and remove private state copies according to policy. Do not delete real backend objects as tutorial cleanup.

## 18. Review questions

1. How are lineage and serial used in recovery decisions?
2. Why is remote state encryption insufficient without IAM?
3. When is a \`moved\` block safer than \`state mv\`?
4. Why can \`state rm\` create orphaned infrastructure?
5. What distinguishes \`init -migrate-state\` from \`-reconfigure\`?
6. How does a stale plan threaten production safety?
7. What does a backend lock not protect?
8. Why are state RPO/RTO and database RPO/RTO separate?
9. What evidence proves a restored state is authoritative?
10. What are the acceptance criteria for returning to service?

**Part 06 complete upon publication of this capstone. Next: Chapter 031 — Terraform Module Architecture, Interfaces and Reusable Design Patterns, starting Part 07 — Reusable Modules.**
