# Chapter 026 — Terraform State Architecture, State Files, Metadata and Backend Fundamentals

**Part 06 — State and Remote Backends** · SRE/DBRE production tutorial · Terraform >=1.5, Python >=3.9 · Local-only lab · **Published ≠ executed**

## Objectives

Understand Terraform state as the mapping of configuration addresses to real remote objects, its lineage/serial and resource instances, sensitive values, local versus remote backends, locking and consistency, backups and recovery, safe inspection and drift investigation. Implement a reproducible no-cloud lab with \`terraform_data\`, a **redacted state metadata inventory**, fail-closed state policy, negative tests and incident runbooks.

## 1. Architecture

~~~text
Reviewed Git config + identity + variables
                  |
        Terraform Core + provider
                  |
     Plan graph / refresh / change
                  |
    Backend (local lab or remote prod)
       |           |           |
   State data   Locking*   Backup/versioning*
       |
  Object addresses, IDs, dependencies,
  outputs, lineage, serial, schema metadata
       |
  Sanitized metadata inventory --> policy/tests
       |
     Approval --> apply --> verify
~~~

*Capabilities depend on backend. Local state has no safe multi-writer coordination. Backend configuration and remote state permissions are a separate security boundary; Terraform state is not a source-code artifact.

## 2. State fundamentals

State records bindings between managed resource addresses and provider object identities. It may include attributes, outputs, schema metadata and sensitive values. A resource's **Terraform address** is not its cloud ID; module paths, \`count\` and \`for_each\` keys affect addresses. \`lineage\` identifies a state history and \`serial\` advances with state snapshots. Neither is a backup checksum or proof of current cloud health. State format is an internal implementation detail; do not edit it directly.

A saved plan captures assumptions about state and configuration. If state changes before apply, discard the stale plan and replan. Terraform \`state list\`, \`state show\`, \`show -json\`, \`output\`, \`plan -refresh-only\` and \`state pull\` are inspection tools with different sensitivity and side effects. **Treat raw state, pulled state, plan JSON and debug logs as secrets**. The lab's Python script reads raw state locally and emits only allowlisted metadata; its output still requires review before sharing.

## 3. State and backend comparison

| Dimension | Local backend | Remote backend |
|---|---|---|
| Storage | local terraform.tfstate | backend-specific managed object/service |
| Team collaboration | unsafe concurrent writers | usually centralized; verify locking support |
| Locking | local OS/filesystem semantics | backend-specific; verify |
| Encryption | depends on disk controls | configure at rest/in transit |
| Access | workstation/file ACL | scoped IAM/RBAC and audit |
| Versioning/backup | manual controlled copies | configure versioning/retention where supported |
| Recovery | local backup and state reconciliation | version restore plus live-resource verification |

Backends are initialized before provider operations. \`terraform init -migrate-state\` and \`terraform init -reconfigure\` are different operations; never use them interchangeably without an approved migration plan. Backend settings supplied with CLI flags or files may be copied into \`.terraform\` and plan artifacts; do not embed secrets in backend configuration. Remote state outputs are not a secret-isolation boundary.

## 4. State schema and metadata

A typical local state JSON may contain \`version\`, \`terraform_version\`, \`serial\`, \`lineage\`, \`outputs\`, \`resources\` and provider-specific instance attributes. The **internal state JSON schema is not a stable public API**. This chapter's validator intentionally reads a narrow educational subset, rejects unexpected or missing critical metadata, and never prints resource attributes. For robust automation prefer supported Terraform CLI JSON views where possible and test against pinned versions.

## 5. Hands-on lab layout

~~~text
labs/chapter-026/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  state-policy.json
  sample-safe-state.json
  sample-unsafe-state.json
  state_inventory.py
  test_state_inventory.py
  run-preflight.sh
  .gitignore
~~~

No cloud credentials, external providers or costs. Uses built-in \`terraform_data\` to simulate DBRE infrastructure metadata; **no database is provisioned**.

## 6. Lab A — Create and inspect isolated state

~~~bash
cd infrastructure-as-code/labs/chapter-026
terraform version
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter026.tfplan
terraform apply chapter026.tfplan
terraform state list
terraform output
terraform state pull > private-state.json
python3 state_inventory.py private-state.json state-policy.json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected addresses: \`terraform_data.network\`, \`terraform_data.database\`, \`terraform_data.application\`. The last plan should exit 0 (no changes). **Do not display, upload or commit private-state.json**. Delete the temporary pulled copy securely under your workstation's retention policy. Do not assume a deleted file is unrecoverable on SSD/cloud-synced storage.

## 7. Lab B — Inspect metadata without leaking attributes

~~~bash
python3 state_inventory.py sample-safe-state.json state-policy.json
python3 -m unittest -v test_state_inventory.py
bash run-preflight.sh
~~~

The policy checks supported state format, positive serial, UUID lineage, allowed Terraform version prefix, resource mode/type, distinct addresses, approved environment/owner from a **separate metadata fixture**, and forbids embedded secret-like output keys. A synthetic fixture is not a live state snapshot or backend permission proof.

## 8. Lab C — State movement and recovery tabletop

Do **not** use production state for these drills. After backing up a disposable local state, run \`terraform state list\` and \`terraform state show terraform_data.database\` locally (avoid sharing output). Explain why a rename in configuration without a \`moved\` block can appear as delete/create. In a disposable copy, add a \`moved\` block for a renamed resource and review a fresh plan. A \`moved\` block changes Terraform's address mapping, not a cloud object's identity.

For an approved import, confirm the existing object, ownership and resource address before \`terraform import\` or import blocks. \`terraform state rm\` only forgets a binding; it does **not** delete the real infrastructure, and can create unmanaged/orphaned resources. \`terraform state mv\` alters bindings and needs a state backup, lock and reviewed plan.

## 9. Lab D — Failure injection

1. Corrupt a **copy** of sample-safe-state.json by changing serial to -1; validator denies.
2. Replace lineage with a non-UUID; validator denies.
3. Duplicate a resource address; validator denies.
4. Add a password-like output key; validator denies.
5. Change a resource type to an unapproved provider; validator denies.
6. Simulate stale plan: create plan, change the local state with a separate approved apply, then discuss why applying the old plan must be stopped and replanned.
7. Simulate state loss **only in a disposable workspace**: preserve the backup, remove the disposable working state, inspect the resulting proposed actions, and restore through a documented reconciliation process. Do not run an unsafe apply while state is missing.

## 10. Production SRE/DBRE scenarios

**RDS/Aurora and PostgreSQL:** state may contain endpoint and credential-related attributes. Restore state snapshots separately from DB PITR. State recovery cannot recover deleted database rows.

**Elasticsearch/OpenSearch:** an IaC state restore cannot rebuild lost shards or indices; validate snapshot repositories, shard health and recovery.

**EKS/AKS:** cluster, IAM and network state require strict backend isolation; node replacement and PDB/drain validation remain runtime operations.

**Redis:** Terraform state is not an RDB/AOF backup. Validate replication, persistence and failover.

**Snowflake:** state may contain role, user, grants and connection metadata. Validate privilege drift and warehouse impact.

**Kafka/MSK:** state is not topic message retention; assess ISR, brokers, consumers and partition health independently.

## 11. Troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| Resource planned for creation but exists | lost binding/wrong backend | stop; verify identity and import/reconcile |
| Unexpected delete/create | address rename or immutable change | inspect moved blocks and plan |
| State lock held | concurrent operation or abandoned lock | identify owner; never force-unlock blindly |
| Serial/lineage mismatch | wrong state history | freeze; compare trusted backups |
| Backend access denied | IAM/RBAC or identity | verify caller, least privilege |
| Stale plan | state changed | discard plan, replan, reapprove |
| Sensitive value in state | provider behavior or outputs | restrict access, rotate if exposed |
| Partial apply | provider/API failure | inspect state and real objects before retry |
| Drift after manual hotfix | out-of-band changes | classify, reconcile via approved plan |
| Backend migration fails | credentials, locks or incompatible config | restore prior backend safely and audit |

## 12. Runbooks

**State backup:** freeze concurrent changes → verify backend/account/workspace → take protected versioned snapshot → verify readability/integrity/access → record change ticket and retention → test recovery in isolated workspace.

**State incident:** stop applies → preserve audit logs and latest good state → identify lineage/serial/backend → verify real infrastructure independently → restore/reconcile under change control → validate app/data/SLOs → RCA.

**Backend migration:** inventory workspaces/locks/ACLs → configure target encryption and versioning → backup → dry-run in staging → approved \`init -migrate-state\` → verify resources/lineage and lock behavior → replan → retire old access only after acceptance.

**Credential leak:** isolate state/plan artifacts → revoke/rotate affected credentials → review backend logs → remediate provider design and access.

**DB recovery:** distinguish Terraform state restoration from database PITR/snapshots and validate both paths separately.

## 13. Acceptance (100 points)

| Area | Points |
|---|---:|
| State architecture, addresses, lineage/serial | 20 |
| Backend/locking/security design | 20 |
| No-cloud plan/apply/idempotence | 20 |
| Metadata policy and negative tests | 20 |
| Recovery, migration and runbooks | 20 |

Pass 85+ with no critical failure. Critical failures: committed raw state/secrets, unverified backend identity, unsafe forced unlock, state restoration without live-resource validation, or cross-environment state reuse. Capture sanitized CLI versions, addresses, policy output, negative test results, recovery plan and cleanup evidence. **Publication does not establish test execution.**

## 14. Cleanup

~~~bash
terraform plan -destroy -var-file=environments/dev.tfvars
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Use only the isolated local lab. Keep approved evidence but not raw state or plans in Git. Protect \`private-state.json\` and delete per security policy.

## 15. Knowledge check

What is state lineage? Why can serial advance? How does an address differ from an object ID? What does \`state rm\` do? What does it not do? Why can remote-state access reveal secrets? When should \`init -migrate-state\` be used? What happens if a plan is stale? How does state restoration differ from database recovery? Why is a backend lock not proof of application health?

**Next:** Chapter 027 — Terraform Remote Backends, State Locking, Encryption and Access Control.
