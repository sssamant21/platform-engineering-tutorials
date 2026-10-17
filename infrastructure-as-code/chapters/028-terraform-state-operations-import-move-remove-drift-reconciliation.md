# Chapter 028 — Terraform State Operations, Import, Move, Remove and Drift Reconciliation

**Part 06 — State and Remote Backends** · **Audience:** SRE/DBRE/Platform Engineering · **Lab:** local, no cloud credentials · **Status:** published; live lab acceptance pending.

## Learning outcomes

Safely inspect Terraform state; distinguish state addresses from remote object IDs; migrate addresses using \`moved\` blocks and \`terraform state mv\`; adopt existing objects through import blocks or \`terraform import\`; remove bindings with \`removed\` blocks or \`terraform state rm\`; detect and reconcile drift; prevent orphaned resources, duplicate ownership and destructive recovery. Build a no-cloud operational lab, a state-operation change policy, automated tests and production runbooks.

## 1. Operational architecture

~~~text
 Git revision + verified identity/backend + change ticket
                         |
       backup/versioned state + acquire lock
                         |
         inspect addresses and real objects
                         |
    choose: moved / import / removed / reconcile
                         |
      fresh plan JSON -> destructive-action gate
                         |
       SRE/DBRE owner approval + apply
                         |
       resource identity, health and SLO checks
                         |
               audit + backup evidence
~~~

Terraform state is the mapping between configuration addresses and managed objects. A Terraform address such as \`module.database.terraform_data.record\` is not a cloud object ID. State operations can change Terraform's knowledge of resources without changing real infrastructure; they require a different risk review from an ordinary application deployment.

## 2. Core operations and risk boundaries

| Operation | Meaning | Critical caution |
|---|---|---|
| \`terraform state list\` | list addresses | output may expose infrastructure topology |
| \`terraform state show ADDRESS\` | inspect a bound object | may reveal sensitive attributes |
| \`terraform state pull\` | retrieve raw state | treat as secret; never commit |
| \`moved { from = ... to = ... }\` | declarative address migration | validate same object, one-to-one mapping and compatible types |
| \`terraform state mv\` | imperative address move | backup, lock and coordinate with Git changes |
| \`import { to = ... id = ... }\` | declarative import of existing object | must verify object identity, ownership and desired config |
| \`terraform import ADDRESS ID\` | imperative import | does not generate full desired configuration |
| \`removed { from = ... lifecycle { destroy = false } }\` | declaratively forget object without destroying it | object becomes unmanaged; ownership handoff required |
| \`terraform state rm ADDRESS\` | forget a binding | does **not** destroy remote object |
| \`terraform plan -refresh-only\` | inspect drift and state refresh | review resulting state changes before apply |
| \`terraform plan\` | compare desired configuration and refreshed state | classify unauthorized vs intentional drift |

\`moved\` blocks support resource and module address migrations, subject to Terraform version and resource compatibility. \`removed\` blocks require a compatible modern Terraform version (Terraform >=1.7). Do not infer that a successful import means the configuration accurately models all remote settings. Never import the same remote object into multiple active Terraform states.

## 3. State safety invariants

- Verify environment, cloud account/subscription/project, backend key, workspace, state lineage and current owner before changing bindings.
- Require exclusive locking, a versioned encrypted state backup and a tested recovery path.
- Require a one-to-one mapping between old/new addresses; detect duplicate target addresses and conflicting ownership.
- Distinguish **forget** from **destroy**. A forget operation is a deliberate handoff and requires an owner and inventory record.
- Replan after any state mutation; never apply a stale saved plan.
- Protect state and plan JSON from disclosure. Sensitive markings do not remove secrets from state.
- Drift can be caused by legitimate autoscaling, cloud defaults, manual emergency changes or unauthorized modifications. Classify it before remediation.

## 4. Lab files

~~~text
labs/chapter-028/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  examples/moved.tf.example
  examples/import.tf.example
  examples/removed.tf.example
  examples/state-commands.sh.example
  state-ops-policy.json
  sample-operations-safe.json
  sample-operations-unsafe.json
  sample-safe-plan.json
  sample-destructive-plan.json
  state_ops_policy.py
  test_state_ops_policy.py
  run-preflight.sh
  .gitignore
~~~

The executable core uses built-in \`terraform_data\`, not a real database, AWS instance or Kubernetes cluster. Example files are deliberately excluded from automatic Terraform loading and are for isolated exercises. Python evaluates educational operation manifests and Terraform-style plan action summaries; it does **not** execute \`state mv\`, \`state rm\` or cloud API calls.

## 5. Lab A — Establish a safe baseline

~~~bash
cd infrastructure-as-code/labs/chapter-028
terraform version
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter028.tfplan
terraform apply chapter028.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected addresses: \`terraform_data.network\`, \`terraform_data.database\`, \`terraform_data.application\`. The second plan should return exit code 0. Use a fresh disposable directory and state for each destructive drill; never switch dev/prod var-files against one state.

## 6. Lab B — Declarative moved block

In a **copy** of the lab, rename \`terraform_data.database\` to \`terraform_data.primary_database\` in configuration and update all references. Add the example \`moved\` block, adapting addresses to match. Run \`terraform plan\` and verify it reports an address move rather than delete/create. Apply only after review and inspect \`terraform state list\`. Keep moved blocks in source control until all relevant states have migrated.

~~~hcl
moved {
  from = terraform_data.database
  to   = terraform_data.primary_database
}
~~~

A \`moved\` block changes the address mapping, not the actual object's ID. If a provider requires replacement for other changed attributes, a move alone does not prevent it.

## 7. Lab C — Import and ownership

An import block requires the destination resource to be declared in configuration and the import ID to match an existing object in the relevant provider. **Do not attempt to import a fabricated terraform_data ID from a fixture.** Use the illustrative cloud import example only in a separately approved sandbox with an existing resource. Verify target account/region, object ID, owner, configuration completeness and post-import plan. Terraform import is not a backup or clone operation.

~~~hcl
# Illustrative only; not part of local executable lab.
import {
  to = aws_s3_bucket.existing
  id = "approved-existing-bucket"
}
~~~

## 8. Lab D — Forget without destroying

The \`removed\` block example is a declarative ownership handoff. In a disposable workspace, compare a removed block with \`destroy = false\` to deleting a resource block (which would normally plan destruction). Document the new owner and avoid duplicate management. An imperative \`terraform state rm\` also forgets the binding, but the real object remains and a subsequent plan may try to create it again if the resource block remains.

## 9. Lab E — Drift detection and reconciliation

~~~bash
terraform plan -refresh-only -var-file=environments/dev.tfvars
terraform plan -var-file=environments/dev.tfvars
terraform state list
~~~

Tabletop: a DBA changes a PostgreSQL parameter or an SRE changes OpenSearch node capacity outside Terraform. Compare remote configuration, Git desired state, state and application health. Choose one approved action: import/record legitimate change in HCL, revert unauthorized drift via reviewed plan, or transfer ownership. A refresh-only plan is **not** authorization to apply drift; it can update state to observed reality without reconciling desired config.

## 10. Lab F — Automated policy and negative tests

~~~bash
python3 state_ops_policy.py sample-operations-safe.json sample-safe-plan.json state-ops-policy.json
python3 state_ops_policy.py sample-operations-unsafe.json sample-destructive-plan.json state-ops-policy.json
python3 -m unittest -v test_state_ops_policy.py
bash run-preflight.sh
~~~

The safe fixture must pass; the unsafe fixture must be denied. The validator requires approved environment and change ticket, a recorded backup/lock, explicit operation type, unique source/target, import ownership verification, safe forget handoff, and rejects plan deletes/replacements. The manifest is a **declared-control fixture**, not proof that the backend lock, backup or remote object exists.

## 11. Failure injection

1. Duplicate two move targets; expect policy denial.
2. Move an address onto itself; expect denial.
3. Import without verified ownership; expect denial.
4. Forget a binding without handoff owner; expect denial.
5. Disable state backup or lock flag; expect denial.
6. Use a production operation without a change ticket; expect denial.
7. Inject \`["delete","create"]\` into plan JSON; expect denial.
8. Rename a resource without a moved block in a disposable copy; compare destructive plan to corrected migration.
9. Simulate a partial state operation and stale saved plan; stop, inspect authoritative state and replan.
10. Simulate a wrong-backend or wrong-account import; freeze and reconcile, never blindly apply.

## 12. Production SRE/DBRE scenarios

**RDS/Aurora:** importing a DB instance must not overwrite backup, encryption, KMS, subnet or deletion protection settings. DB snapshots/PITR remain separate from state recovery.

**PostgreSQL:** classify parameter drift, role/extension changes and connection settings; verify WAL/replication and application SLO before reconciliation.

**Elasticsearch/OpenSearch:** index or domain adoption requires ownership, shard health, snapshot and storage checks; state import does not copy index data.

**EKS/AKS:** module address moves for clusters/node pools must avoid accidental replacement; validate identity, PDBs, networking and workloads.

**Redis:** do not confuse state forgetting with Redis key deletion; verify persistence, failover and client reconnection.

**Snowflake:** role/grant import and drift reconciliation can affect privileges; confirm ownership and audit before apply.

**Kafka/MSK:** importing broker infrastructure does not import message data or consumer offsets; verify ISR and lag.

## 13. Troubleshooting matrix

| Symptom | Cause | Safe response |
|---|---|---|
| Delete/create after rename | no moved block | add reviewed moved mapping |
| Address already managed | duplicate import | identify authoritative owner/state |
| Import ID not found | wrong account/region/ID | verify remote identity |
| State rm followed by create | config still declares object | complete handoff/remove config |
| Lock acquisition fails | another operation | identify active owner |
| Stale saved plan | state changed | replan and reapprove |
| Drift persists | unmanaged external change | classify and fix source of truth |
| Unexpected replacement | immutable attribute changed | stop and review |
| Wrong backend | environment key mismatch | freeze; verify state lineage |
| Partial state mutation | interrupted operation | backup, reconcile, fresh plan |
| Sensitive state leak | raw state shared | contain, rotate, audit |
| Import succeeds but app fails | Terraform != health | restore service; run DBRE checks |

## 14. Production runbooks

**Import existing infrastructure:** verify identity/backend → inventory object and current owner → backup state → declare exact resource configuration → prepare import → inspect fresh plan → apply with approval → validate health and ownership.

**Address migration:** freeze competing changes → backup → map old/new addresses → add moved block → plan and deny unintended replacement → approve/apply → verify addresses and real IDs.

**Forget/handoff:** identify recipient owner → record inventory/contract → use removed block with \`destroy = false\` or approved state rm → replan → verify object still exists and is managed by the intended system.

**Drift incident:** verify source of truth and emergency changes → classify security/availability impact → preserve evidence → reconcile through approved plan → validate SLO/data and document RCA/COA.

**State corruption:** stop applies → identify authoritative backend/version/lineage → recover protected snapshot → verify real objects → replan → approve recovery. Do not directly edit raw state JSON.

## 15. Acceptance (100 points)

| Area | Points |
|---|---:|
| State operations semantics and safety | 20 |
| Import and address migration design | 20 |
| Drift and ownership reconciliation | 20 |
| Offline lab and automated policy tests | 20 |
| SRE/DBRE recovery runbooks and audit | 20 |

Pass 85+ and no critical failures. Critical: cross-environment import, duplicate active ownership, destructive unreviewed plan, unprotected state mutation, state leak or unsupported rollback claim. Record sanitized CLI versions, state addresses, policy/test results, drift decision, backup evidence and cleanup.

## 16. Cleanup

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Use only the original isolated no-cloud lab. Do not delete production state objects or remote infrastructure during tutorial cleanup. Never commit state, saved plans, raw \`state pull\` output or secrets.

## 17. Knowledge check

Why does state rm not destroy infrastructure? What is the advantage of moved blocks? What makes an import safe? Why must ownership be unique? What does refresh-only do? How does a saved plan become stale? When is a removed block preferable to state rm? How do you detect a wrong backend? Why is state backup not DB PITR? What evidence proves drift reconciliation succeeded?

**Next:** Chapter 029 — Terraform State Migration, Backup, Restore and Disaster Recovery.
