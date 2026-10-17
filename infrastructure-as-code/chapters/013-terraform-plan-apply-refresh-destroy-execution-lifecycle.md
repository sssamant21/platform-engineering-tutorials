# Chapter 013 — Terraform Plan, Apply, Refresh, Destroy and Execution Lifecycle

**Part 03 — Terraform Language and Workflow** | **Audience:** SRE / DBRE / DevOps / Platform Engineering | **Level:** Intermediate | **Core lab cost:** $0

> **Status:** Tutorial and lab artifacts published. Running the exercises and collecting acceptance evidence is a separate step.

## Learning objectives

- Describe configuration, state, provider refresh, dependency graph, plan, apply, and destroy as distinct lifecycle stages.
- Explain saved plans, state locks, plan exit codes, speculative vs non-speculative plans, and approval boundaries.
- Distinguish normal planning from refresh-only planning, and explain why \`terraform refresh\` is discouraged in favor of reviewed refresh-only plans.
- Safely reproduce local drift, import-free recovery, and destroy in a no-cloud lab.
- Implement automated, fail-closed plan JSON policy checks and negative tests.
- Apply production SRE/DBRE change controls to RDS, PostgreSQL, Elasticsearch, EKS, AKS, Redis, Snowflake and Kafka.

## 1. Execution lifecycle architecture

~~~text
Git / reviewed HCL + pinned CLI and providers
                  |
        init (backend, modules, providers)
                  |
          fmt / validate / policy
                  |
    plan: load state, refresh remote objects,
          evaluate config and dependencies
                  |
       proposed change + plan artifact
                  |
    peer / service owner / DBRE approval
                  |
      apply saved plan under state lock
                  |
   verify actual resources, SLOs, data, cost
                  |
       reconcile drift and audit evidence
~~~

Terraform maintains a mapping between resource addresses and real-world objects in state. The configuration expresses desired state; the provider reads and mutates infrastructure. Refresh during a normal plan observes remote objects and may discover drift. A **plan** is not a backup, a guarantee of zero downtime, or proof that the cloud API will accept an operation.

**Plan modes:** normal planning compares desired configuration and refreshed state; \`-refresh-only\` proposes updating state/output values to reflect actual remote objects without changing infrastructure; \`-destroy\` proposes removal of managed resources. \`-refresh=false\` skips ordinary remote refresh and can produce misleading plans. Use it only when justified, not to hide drift.

**Deprecated workflow:** \`terraform refresh\` is effectively an auto-approved refresh-only apply in current Terraform workflows; prefer \`terraform plan -refresh-only\` followed by reviewed \`terraform apply -refresh-only\` or an approved saved plan. Refresh-only can still update state and outputs, so review before apply.

## 2. Command contract

| Command | Purpose | Important guardrail |
|---|---|---|
| \`terraform init\` | Initialize backend, modules and providers | Confirm backend identity before state access |
| \`terraform fmt -check\` | Verify formatting | Not a safety scan |
| \`terraform validate\` | Validate HCL/provider schemas | Not a cloud plan |
| \`terraform plan\` | Preview changes | Review resource actions and unknowns |
| \`terraform plan -out=FILE\` | Write opaque saved plan | Treat as sensitive artifact |
| \`terraform show -json FILE\` | Inspect machine-readable plan | JSON can contain sensitive values |
| \`terraform apply FILE\` | Execute saved plan | Ensure same trusted artifact and environment |
| \`terraform plan -detailed-exitcode\` | CI no-change/change/error gate | 0=no changes, 1=error, 2=changes |
| \`terraform plan -refresh-only\` | Preview state-only reconciliation | Review state/output changes |
| \`terraform plan -destroy\` | Preview deletions | Requires owner and recovery approval |
| \`terraform destroy\` | Remove managed resources | Destructive; never casual in prod |
| \`terraform state list\` | List tracked resource addresses | Does not validate health |
| \`terraform force-unlock\` | Unlock a stale state lock | Only after verifying no active writer |

Saved plans capture configuration, variable values, and prior state context and can include secrets. Never commit them, publish them as unrestricted CI artifacts, or display raw JSON in public logs. The saved plan should be produced and applied within the same controlled environment and identity boundary. Do not reuse plans after out-of-band infrastructure changes or provider/toolchain drift.

## 3. Graph, state locks and concurrent execution

A normal plan computes a dependency graph, evaluates provider reads and proposes resource changes. Apply follows dependency ordering but may execute independent operations concurrently. \`-parallelism\` controls concurrency, not a guarantee of a safe database migration. State locking prevents simultaneous writers only when the backend supports and correctly configures it. Never bypass locking as a routine workaround.

\`terraform plan -target=...\` is an exceptional recovery tool, not an ordinary deployment strategy: targeting can omit dependent changes and leave partial configuration convergence. Prefer full plans and approved migration workflows.

## 4. Lab structure and prerequisites

~~~text
labs/chapter-013/
  versions.tf               # local-only CLI constraint
  variables.tf              # typed environment and workload inputs
  main.tf                   # built-in terraform_data resources
  outputs.tf                # safe lab outputs
  plan-policy.json          # educational policy settings
  plan_policy.py            # Terraform plan JSON policy validator
  test_plan_policy.py       # automated negative/positive tests
  sample-plan.json          # synthetic plan for offline tests
  run-lab.sh                # local lifecycle script
  .gitignore                # sensitive/local artifact exclusions
~~~

Install Terraform >=1.5 or an approved compatible OpenTofu, Python 3.9+, and Git. Run on Linux/WSL2/macOS; PowerShell users may run individual commands. No cloud credentials, external provider or cloud charges are required. Use **one** engine throughout the lab.

## 5. Lab A — Baseline plan, saved apply and idempotence

~~~bash
cd infrastructure-as-code/labs/chapter-013
terraform fmt -check
terraform init -input=false
terraform validate
terraform plan -out=chapter013.tfplan
terraform show -no-color chapter013.tfplan
terraform apply chapter013.tfplan
terraform output -json
terraform state list
terraform plan -detailed-exitcode
echo "plan_exit=$?"
~~~

Expected: \`terraform_data.workload\` and \`terraform_data.audit\` created. After apply, \`-detailed-exitcode\` returns **0**. Exit **1** is an error; exit **2** means a change is proposed. In Bash, inspect \`$?\` immediately after the plan; in PowerShell use \`$LASTEXITCODE\`. Avoid \`set -e\` when intentionally inspecting exit code 2 unless handled explicitly.

**State caveat:** This is local state, not a production backend. The \`terraform_data\` resource is built in and has no external cloud object to refresh.

## 6. Lab B — Simulate configuration drift and plan change

Change \`var.replicas\` without editing the canonical files:

~~~bash
terraform plan -var='replicas=4' -detailed-exitcode
echo "plan_exit=$?"
terraform plan -var='replicas=4' -out=replicas4.tfplan
terraform show -no-color replicas4.tfplan
~~~

Expected: exit **2** because the desired \`terraform_data.workload.input\` differs. The plan should update the local object in place rather than destroy a real cloud resource. Do not apply this optional plan if you intend to keep the baseline; remove the saved plan after inspection.

## 7. Lab C — Refresh-only semantics

~~~bash
terraform plan -refresh-only
terraform plan -refresh-only -out=refresh-only.tfplan
terraform show -no-color refresh-only.tfplan
~~~

Expected in this built-in-resource lab: normally no externally observable drift. This exercise demonstrates syntax and review flow, **not** a realistic remote drift test. For production, refresh-only can change tracked state/output values, and requires state protection, approval and audit evidence. Do not run refresh-only apply as an unreviewed repair.

## 8. Lab D — Plan JSON policy and automated tests

The policy validator reads \`resource_changes[].change.actions\` from \`terraform show -json\` output. It rejects any \`delete\` action (including replacement), any \`no-op\`-free change when \`require_no_changes\` is enabled, and unapproved production changes. It is deliberately a focused teaching policy: it **does not** prove the cloud identity, verify backup/PITR, parse provider-specific semantics or replace Sentinel/OPA/Conftest.

~~~bash
python3 plan_policy.py sample-plan.json plan-policy.json
python3 -m unittest -v test_plan_policy.py
terraform plan -out=policy.tfplan
terraform show -json policy.tfplan > local-plan.json
python3 plan_policy.py local-plan.json plan-policy.json
~~~

Expected: sample plan PASS; tests pass. The real plan policy permits non-destructive creates/updates in the lab, so it should pass when \`environment=lab\` and there are no delete actions. Do not upload \`local-plan.json\` or plan artifacts: they may contain sensitive data.

Negative drills in unit tests: deletion, replacement, missing actions, prod without approval, strict no-change mode, malformed document. Failure must exit nonzero.

## 9. Lab E — Destroy preview and cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
~~~

Expected: the two local resources are destroyed and state list is empty. Remove local plan files and \`local-plan.json\`; never commit local state or saved plans. Run \`git status --short\` to confirm only intended tracked changes.

## 10. CI preflight and promotion pattern

~~~text
PR:
  fmt -> init -backend=false -> validate -> unit tests
  -> authenticated plan in isolated nonprod backend
  -> plan JSON policy -> reviewer approval

Production:
  protected runner + short-lived workload identity
  -> verify account/subscription/project and backend key
  -> generate saved plan -> DBRE/owner approval
  -> apply exact approved plan -> verify health, data and SLO
~~~

Use immutable runner images and provider lockfiles, restrictive plan artifact permissions and short retention. For production databases, backup validity and restore rehearsal are separate acceptance gates. If the plan changes after approval, regenerate and reapprove; do not apply a different artifact under the old approval.

## 11. Production SRE/DBRE scenarios

**RDS/Aurora:** A provider change proposes replacement of a production instance. Stop apply; inspect \`delete\` actions in plan JSON; validate snapshots, PITR, replication, RPO/RTO, maintenance window and DBRE-approved cutover. Git revert cannot restore deleted data.

**PostgreSQL:** Parameter-group change may require restart. Review pending-reboot flags, connection drain, HA topology, backups, replication lag and application smoke tests.

**Elasticsearch/OpenSearch:** Emergency IOPS increase is detected as drift during plan. Do not let an automatic apply undo an incident mitigation. Stabilize query latency and queueing, then reconcile configuration through an approved PR.

**EKS:** Node-group replacement may violate PDBs and AZ capacity. Review surge capacity, drain ordering, cluster health and staged rollout.

**AKS:** A plan produced under the wrong subscription or backend can affect another environment. Verify tenant/subscription, role and state key before planning and again before applying.

**Redis:** Replica topology or instance class change may disrupt failover. Validate HA, memory headroom, client retry behavior and failover testing.

**Snowflake:** Grant changes can remove access even without resource deletion. Plan JSON deletion-only policies are insufficient; add domain-specific access tests and data-owner approval.

**Kafka/MSK:** Broker replacement and networking changes can threaten quorum and client availability. Review partition replication, broker maintenance and recovery paths.

## 12. Troubleshooting matrix

| Symptom | Diagnosis | Safe response |
|---|---|---|
| \`plan\` exits 2 | Desired change or drift | Review diff; do not treat as error |
| \`plan\` exits 1 | Syntax/provider/backend error | Inspect sanitized logs |
| Saved plan rejected | State or configuration changed | Replan and reapprove |
| Lock acquisition failed | Concurrent writer/stale lock | Identify owner; never force unlock blindly |
| Unexpected destroy | Replacement or removed address | Halt; assess state and backups |
| Refresh-only shows drift | Out-of-band changes | Validate actual infra; review state-only update |
| Provider auth error | Wrong role/token/scope | Verify intended identity, never use prod personal creds |
| CI passes but apply fails | API quota, IAM, drift, unknown values | Preserve evidence and recover |
| Policy flags replacement | \`delete\` + \`create\` actions | Require explicit DBRE/owner approval |
| Sensitive plan artifact exposed | Unrestricted CI/logging | Contain, rotate credentials and audit |

## 13. Operational runbooks

**Routine IaC change:** verify Git SHA, toolchain, provider lockfile, backend and cloud identity → fmt/validate/tests → plan → policy review → assess data/cost/replacement → obtain owner/DBRE approval → apply approved plan → verify SLO and data → archive sanitized evidence.

**Unexpected destructive plan:** stop pipeline → identify resource address and \`delete\` actions → inspect drift/provider/schema → verify backups and restore tests → DBRE/owner decision → regenerate plan; never use \`-target\` to conceal deletion.

**State lock incident:** identify active CI writer and lock owner → wait/coordinate → verify writer stopped → only then consider documented, approved unlock → run fresh plan and integrity checks.

**Emergency drift:** record incident mitigation → temporarily halt conflicting automation → restore SLO → assess desired vs actual → reconcile code/state under change control → close RCA/COA.

**Failed apply / partial changes:** freeze concurrent writers → inspect state and actual infrastructure → restore service before reapplying → generate fresh plan → use provider-specific recovery or backup/restore → document incident.

## 14. Acceptance criteria

- [ ] fmt/init/validate and baseline saved plan succeed.
- [ ] Apply creates two local resources; second plan exits 0.
- [ ] Changed replica input produces exit 2.
- [ ] Refresh-only plan inspected without modifying remote resources.
- [ ] Python policy and automated negative tests pass.
- [ ] Destroy preview reviewed and local state emptied.
- [ ] No plan, state, credentials or JSON plan artifact committed.
- [ ] Production runbooks cover backups, approvals, monitoring and rollback.

## 15. Knowledge check

What does normal plan refresh? Why is refresh-only not equivalent to restoring desired infrastructure? What do exit codes 0/1/2 mean? What is saved in a plan file? Why are state locks important? Why is \`-target\` unsuitable for routine CI? How do replacement actions appear in plan JSON? What must be reapproved after a stale plan? Why can an update be destructive for Snowflake grants? Why does Git revert not restore an RDS database?

**Next:** Chapter 014 — Terraform State Inspection, Drift Detection and Resource Address Management.
