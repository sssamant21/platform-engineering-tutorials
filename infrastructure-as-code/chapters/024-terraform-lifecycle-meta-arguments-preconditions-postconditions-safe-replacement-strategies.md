# Chapter 024 — Terraform Lifecycle Meta-Arguments, Preconditions, Postconditions and Safe Replacement Strategies

**Part 05 — Providers and Dependencies** · **Audience:** SRE, DBRE, Platform Engineering · **Core lab:** no cloud provider or billable infrastructure · **Status:** published; live execution evidence pending.

## Objectives

Explain \`create_before_destroy\`, \`prevent_destroy\`, \`ignore_changes\`, \`replace_triggered_by\`, preconditions, postconditions, and their limitations; inspect plan JSON for delete/replace actions; design fail-closed policy gates; perform safe local replacement simulations; and develop production change and rollback runbooks for stateful systems.

## 1. Production change architecture

~~~text
Git commit / approved identity / reviewed input
                    |
  HCL lifecycle and pre/postconditions
                    |
  terraform validate -> saved plan -> JSON
                    |
       policy and negative tests
                    |
       DBRE/SRE change approval
                    |
  apply exact reviewed plan / observe
                    |
   health, data and SLO verification
                    |
       audit / rollback decision
~~~

Lifecycle rules influence Terraform's resource graph and planned operations, but they cannot guarantee data integrity, health, capacity, or zero downtime. Always review cloud account/backend identity, backup/PITR evidence and restore readiness separately. A plan is not a backup.

## 2. Lifecycle meta-arguments

| Argument | Purpose | Production limitation |
|---|---|---|
| \`create_before_destroy\` | Request new object before old object is removed during replacement | Requires capacity and naming compatibility; propagation to dependencies may matter |
| \`prevent_destroy\` | Reject plans that destroy a protected resource while its configuration retains the rule | Removing the resource block removes the rule; not immutable protection |
| \`ignore_changes\` | Ignore selected remote differences during update planning | Can conceal configuration/security drift |
| \`replace_triggered_by\` | Trigger replacement when a referenced managed resource/attribute changes | May cascade disruptive replacements |
| \`precondition\` | Require an assumption before a resource operation | Must validate the actual safety property |
| \`postcondition\` | Require a condition after resource evaluation | Does not replace independent runtime verification |

Most lifecycle settings must be known statically. Do not use \`ignore_changes = all\` to suppress unexplained drift. Terraform \`check\` assertions can emit warnings rather than block, so critical production invariants need hard gates.

## 3. Safe replacement reasoning

~~~hcl
resource "terraform_data" "service" {
  input = { version = var.release }
  lifecycle {
    create_before_destroy = true
    precondition {
      condition = var.replicas >= 2
      error_message = "at least two replicas are required"
    }
    postcondition {
      condition = self.output.version != ""
      error_message = "release version must be nonempty"
    }
  }
}
~~~

This is an **illustrative lifecycle contract**, not an HA service. In the executable lab, \`terraform_data\` replacement is induced through \`triggers_replace\`. Terraform plan JSON exposes replacement as actions containing both \`delete\` and \`create\`, in an order affected by lifecycle rules. A replacement policy must not infer approval from ordering alone.

## 4. Preconditions, postconditions and unknowns

Preconditions can reference known input contracts and stop invalid plans early; if a value is unknown at plan time, evaluation may be deferred. Postconditions can validate resource results but do not prove application-level readiness, replication catch-up or recovery point objectives. Use explicit types, guard nulls and make messages actionable. Avoid placing credentials or secrets in error messages.

## 5. Replacement, drift and downtime

Before replacement, answer: Is this stateful? Is the name unique? Is there capacity to coexist? Is the change destructive or only a pointer migration? Is the backup recent and restorable? Is rollback technically possible? What are RPO/RTO and application connection semantics? Does a migration require dual-write, replica sync, DNS TTL, traffic drain or client retry? A zero-downtime claim requires demonstrated cutover and rollback testing, not just \`create_before_destroy\`.

## 6. Lab files

~~~text
labs/chapter-024/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  lifecycle-policy.json
  sample-safe-plan.json
  sample-replace-plan.json
  lifecycle_policy.py
  test_lifecycle_policy.py
  run-preflight.sh
  .gitignore
~~~

Prerequisites: Terraform >=1.5 or compatible OpenTofu, Python >=3.9, Bash/WSL2. No external providers or cloud credentials.

## 7. Lab A — Establish a protected local baseline

~~~bash
cd infrastructure-as-code/labs/chapter-024
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter024.tfplan
terraform show -json chapter024.tfplan > chapter024-plan.json
terraform apply chapter024.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: two terraform_data resources, a service record and an audit record, and a subsequent no-change exit code 0. The resource's \`prevent_destroy\` protects the audit record while the rule is present.

## 8. Lab B — Replacement simulation

In a **disposable separate copy** of the lab, change \`release\` from v1 to v2; plan with a new saved plan and inspect \`resource_changes[].change.actions\`. The service uses \`triggers_replace\`, so it should plan a replacement. \`create_before_destroy\` requests creation before deletion. Do not apply unless the replacement is explicitly intended in the disposable local lab. Restore the release and reconcile.

~~~bash
terraform plan -var-file=environments/dev.tfvars -var='release=v2' -out=replace.tfplan
terraform show -json replace.tfplan > replace-plan.json
python3 lifecycle_policy.py replace-plan.json lifecycle-policy.json
~~~

The policy is deliberately fail-closed: the replacement plan must be denied. The sample replacement fixture provides deterministic negative testing.

## 9. Lab C — Hard safety conditions

~~~bash
terraform plan -var-file=environments/prod.tfvars -var='replicas=1'
terraform plan -var-file=environments/prod.tfvars -var='backup_enabled=false'
terraform plan -var-file=environments/prod.tfvars -var='encryption_enabled=false'
terraform plan -var-file=environments/prod.tfvars -var='deletion_protection=false'
~~~

All should fail the production lifecycle precondition. Keep dev/prod states separate; do not apply prod inputs to a dev state. In a disposable copy, test \`terraform destroy\` with \`prevent_destroy\` retained and confirm rejection. Do not remove the guard on a production resource to force a destroy.

## 10. Lab D — Policy and tests

~~~bash
python3 lifecycle_policy.py sample-safe-plan.json lifecycle-policy.json
python3 -m unittest -v test_lifecycle_policy.py
bash run-preflight.sh
~~~

The policy inspects Terraform-style JSON action lists. It denies deletes/replacements, malformed changes and unapproved resource types; it cannot prove a real backup, identity, lock or external approval. Unit tests include destructive plans, replace orders, malformed action sets, invalid policy, missing resource changes, and no-op/update cases.

## 11. Lab E — Cleanup

The audit record has \`prevent_destroy\`, so a normal destroy will intentionally fail. In a disposable lab only, first **remove the audit resource block from configuration and perform a reviewed destroy plan**; note that removing the block also removes the guard and may permit deletion. For a cleaner training demonstration, temporarily disable the guard in a disposable copy and review the plan before destroying. Never do this to a production DB or stateful resource. Confirm \`terraform state list\` is empty after approved cleanup. Preserve sanitized evidence; do not commit state, plans, or secrets.

## 12. Production SRE/DBRE scenarios

**RDS/Aurora:** A forced replacement can destroy storage or sever clients. Require snapshots/PITR, replica sync, KMS compatibility, dual-running capacity, endpoint cutover and restore drill evidence.

**PostgreSQL:** Validate WAL, replication slots, failover topology, storage growth and connection pools before any parameter or instance replacement.

**Elasticsearch/OpenSearch:** Data-node replacement requires shard relocation, disk headroom, replica health and query SLO checks; \`create_before_destroy\` is insufficient.

**EKS:** Node group replacement must account for PDBs, draining, IP/instance quotas and rolling upgrade surge capacity.

**AKS:** Protect production node pools, identity and network resources; review subscription and node drain behavior.

**Redis:** Replacement/failover requires replication convergence, persistence policy, client retry and cache warming.

**Snowflake:** Warehouse and grant changes may affect availability, cost and privilege boundaries; inspect lifecycle drift rather than ignoring changes.

**Kafka/MSK:** Broker replacements require ISR/quorum checks, partition rebalance, consumer lag monitoring and rollback capacity.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Response |
|---|---|---|
| Plan shows delete/create | Immutable field or trigger | Stop and review replacement |
| prevent_destroy error | Protected resource being removed | Confirm intended change; do not bypass casually |
| create_before_destroy failure | Name/region/quota conflict | Stage migration and capacity |
| precondition failure | Invalid production control | Correct reviewed input |
| postcondition failure | Resource output contract violated | Inspect actual state and provider result |
| Unexpected drift | External change or ignored attribute | Investigate source of truth |
| Plan succeeds but app unhealthy | Terraform != readiness | Restore service, verify SLO |
| Stale saved plan | State changed since planning | Replan and reapprove |
| Partial apply | API or process interruption | Reconcile state and remote objects |
| Policy denies replacement | Safety gate working | Submit reviewed migration or redesign |

## 14. Runbooks

**Normal change:** verify commit/account/backend -> check backups -> fmt/init/validate -> plan and policy -> review actions and downtime -> DBRE approval -> apply reviewed plan -> validate data, SLOs and cost.

**Replacement request:** freeze unrelated changes -> identify forced-replacement attributes -> calculate coexistence and migration capacity -> verify restore drill -> design cutover and rollback -> approve -> execute in window.

**Unexpected destruction:** stop pipeline -> preserve state/logs -> recover service and data -> verify backup integrity -> reconcile Terraform -> RCA/COA.

**Lifecycle guard bypass request:** reject ad-hoc removal -> require explicit owner/DBRE authorization and recovery plan -> stage test -> audit configuration diff and plan.

**Drift incident:** compare remote object, HCL, state and ignored fields -> classify authorized vs unauthorized -> remediate via reviewed plan.

## 15. Acceptance rubric (100 points)

| Category | Points |
|---|---:|
| Lifecycle semantics and constraints | 20 |
| Preconditions/postconditions | 15 |
| Replacement and downtime analysis | 20 |
| Executable no-cloud lab | 15 |
| Policy and negative tests | 20 |
| Runbooks and evidence hygiene | 10 |

Pass 85+ and no critical failure. Capture sanitized CLI versions, plan action evidence, denied replacement, policy test results, state cleanup and owner approval. **Authored tests are not execution evidence.**

## 16. Knowledge check

Why is prevent_destroy not permanent? When can create_before_destroy fail? Why is ignore_changes dangerous? What triggers replacement? What does a precondition block? What does a postcondition prove? Why are plan JSON actions more useful than console color? How do you restore a stateful DB after partial apply? Why is a check warning insufficient as a hard gate? What evidence supports a zero-downtime claim?

**Next:** Chapter 025 — Terraform Providers, Dependencies and Lifecycle Production Capstone.
