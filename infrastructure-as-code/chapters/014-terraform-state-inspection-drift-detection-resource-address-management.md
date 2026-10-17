# Chapter 014 — Terraform State Inspection, Drift Detection and Resource Address Management

**Part 03 — Terraform Language and Workflow** · **Audience:** SRE, DBRE, Platform Engineering · **Lab:** local-only, $0 · **Status:** Published; execution evidence pending

## Learning outcomes
Explain the relationship between desired configuration, state and actual infrastructure; inspect state safely; recognize resource addresses and instance keys; distinguish configuration drift from state drift; use refresh-only plans, moved blocks and imports appropriately; understand the risk of \`state mv\`, \`state rm\`, \`state push\` and force-unlock; implement a read-only state-inventory audit and automated tests; create an auditable SRE/DBRE drift-response runbook.

## 1. Architecture and mental model

~~~text
                  Git / HCL (desired configuration)
                                |
                   terraform plan / provider reads
                                |
State backend (address ↔ object ID) <----> Actual cloud/database resources
  versioning, encryption, locks                AWS / Azure / GCP / K8s
                                |
                  drift / import / refactor decisions
                                |
                     approved plan and apply
                                |
                  post-change health verification
~~~

Terraform state tracks resource addresses, provider bindings, object IDs, attributes and dependency metadata. It is **not** a complete backup of a database, Elasticsearch index or Kubernetes cluster. State can contain secrets, even when CLI output redacts sensitive fields. Treat state snapshots, \`terraform show -json\` and plan files as confidential artifacts.

**Three separate questions:** What does Git declare? What does state believe exists? What actually exists? Disagreement can arise from out-of-band changes, failed or partial applies, provider/API behavior, refactoring, deletion, imports or stale plans.

### State addressing
Examples:
- \`terraform_data.database\` — unkeyed resource
- \`terraform_data.node[0]\` — count index
- \`terraform_data.node["az-a"]\` — for_each key
- \`module.network.aws_subnet.private["a"]\` — nested module address

A resource **address** is not a cloud resource ID. Refactoring a resource name without preserving the address mapping can make Terraform propose deletion and creation. Prefer a reviewed \`moved\` block for declarative address changes; \`terraform state mv\` is a surgical imperative operation requiring special controls.

## 2. Inspection and safety commands

| Command | Purpose | Guardrail |
|---|---|---|
| \`terraform state list\` | Enumerate managed addresses | Read-only, but output may reveal names |
| \`terraform state show ADDRESS\` | Inspect tracked attributes | May display sensitive values |
| \`terraform show -json\` | Machine-readable current state | Treat JSON as sensitive |
| \`terraform state pull\` | Retrieve raw backend state | Never send to public logs |
| \`terraform plan -refresh-only\` | Preview state reconciliation with remote objects | Not a config remediation |
| \`terraform plan -detailed-exitcode\` | Distinguish no change/error/change | 0/1/2 |
| \`terraform plan -out=FILE\` | Save reviewed plan | Confidential; limited retention |
| \`terraform state mv\` | Change binding address | Coordinate lock and backup |
| \`terraform state rm\` | Stop tracking object | **Does not delete real object** |
| \`terraform import ADDRESS ID\` | Adopt existing object into state | Requires matching configuration and review |
| \`terraform state push\` | Replace state snapshot | High-risk; never routine |
| \`terraform force-unlock ID\` | Clear state lock | Only if owner and writer verified |

Do not edit state JSON by hand, disable locking or use \`-refresh=false\` to hide an unexpected plan. The legacy \`terraform refresh\` behavior can update state without a review; prefer \`plan -refresh-only\` and a controlled apply if state reconciliation is actually intended.

## 3. Drift taxonomy and decision tree

1. **Benign metadata drift:** Tags or descriptions updated manually. Identify owner and decide whether to adopt or revert.
2. **Operational drift:** Elasticsearch disk IOPS, RDS instance sizing or Redis failover settings changed during an incident. Preserve the fix until SLOs stabilize; reconcile through change control.
3. **Security drift:** IAM, network policies, Snowflake grants or public endpoints changed. Escalate immediately; assess exposure and restore least privilege.
4. **Address drift:** Refactor changes Terraform address while object is unchanged. Use \`moved\` blocks, then inspect plan.
5. **Orphan:** Cloud resource exists but is not tracked. Determine ownership, cost, risk and import/delete decision.
6. **Phantom:** State tracks object deleted outside Terraform. Inspect backup, application health and desired replacement before applying.
7. **Partial apply:** Some operations completed before error. Freeze writers, inspect state and remote reality, and generate a fresh plan.

**Decision:** Halt automatic reconciliation when the drift is unexplained, security-sensitive, or destructive; collect evidence, identify accountable owner, classify data impact, select adopt/revert/import/move/recover, and obtain approval.

## 4. Lab setup (no cloud credentials)

Repository: \`infrastructure-as-code/labs/chapter-014/\`.

~~~text
versions.tf           CLI version constraint
variables.tf          typed environment and workload
main.tf               terraform_data resources with stable for_each keys
outputs.tf            public lab outputs
state_policy.py       read-only state JSON inventory validator
test_state_policy.py  unit tests and negative cases
sample-state.json     synthetic safe fixture
state-policy.json     expected managed addresses and metadata
run-preflight.sh      checks that do not apply changes
.gitignore            excludes state, plan and local secrets
~~~

Prerequisites: Terraform >=1.5 or compatible approved OpenTofu; Python 3.9+; Git. Use one engine throughout; WSL2/Linux/macOS Bash examples, or equivalent PowerShell commands.

## 5. Lab A — Create state and inspect addresses

~~~bash
cd infrastructure-as-code/labs/chapter-014
terraform fmt -check
terraform init -input=false
terraform validate
terraform plan -out=chapter014.tfplan
terraform apply chapter014.tfplan
terraform state list
terraform state show 'terraform_data.service["api"]'
terraform output -json
terraform show -json > local-state.json
python3 state_policy.py local-state.json state-policy.json
~~~

Expected: \`terraform_data.seed\`, \`terraform_data.service["api"]\`, \`terraform_data.service["worker"]\`. The validator checks the managed address inventory and metadata but does not parse or modify raw backend state. \`local-state.json\` may contain sensitive values in other modules; the example uses fictional metadata only. Never upload state JSON to unrestricted CI artifacts.

## 6. Lab B — Detect configuration change versus actual drift

~~~bash
terraform plan -detailed-exitcode
echo "baseline_exit=$?"
terraform plan -var='replicas=4' -detailed-exitcode
echo "changed_input_exit=$?"
terraform plan -refresh-only
~~~

Expected: baseline exit 0; changed input exit 2; refresh-only typically reports no change because built-in \`terraform_data\` has no external cloud object to drift. **This is a configuration-difference exercise, not a true cloud-drift simulation.** To test remote drift, use an isolated nonproduction cloud resource and compare API observation with plan output under authorized credentials.

## 7. Lab C — Declarative resource address migration

In a **disposable copy** of the lab (with its own local state), first apply the baseline. Then rename \`resource "terraform_data" "seed"\` to \`resource "terraform_data" "foundation"\` and update all references. Add:

~~~hcl
moved {
  from = terraform_data.seed
  to   = terraform_data.foundation
}
~~~

Run \`terraform plan\`. Expected: address move recorded, without destroy/recreate of the seed resource. Do not perform this exercise against a shared backend. To restore the original lab, revert the copy or add a reverse move in a new migration; avoid repeatedly editing production state manually.

**Contrast:** \`terraform state mv 'terraform_data.seed' 'terraform_data.foundation'\` performs a direct state address change and requires serialized, authorized access and backups. Prefer declarative \`moved\` blocks because they are reviewed and versioned.

## 8. Lab D — State inventory policy and automated tests

~~~bash
python3 state_policy.py sample-state.json state-policy.json
python3 -m unittest -v test_state_policy.py
bash run-preflight.sh
~~~

The validator accepts Terraform \`show -json\` state format (top-level \`values.root_module.resources\` and nested child modules), not the internal raw \`terraform.tfstate\` schema. It checks expected addresses, duplicate addresses, allowed managed modes, missing owners and environment metadata; it never writes state. The fixture is synthetic and contains no credentials.

Negative tests cover missing expected addresses, unexpected managed resources, duplicate addresses, missing metadata, mismatched environment, invalid schema and nested modules. It is **not** a replacement for cloud drift detection, plan review, policy-as-code or secret scanning.

## 9. Lab E — Safe cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expected: empty resource list. State and plans remain local and ignored. Do not commit them or claim they represent production backup evidence.

## 10. Production SRE/DBRE scenarios

**RDS/Aurora:** A manually enlarged production volume differs from HCL. Before any apply, inspect storage settings, IOPS, backup/PITR and downtime implications; DBRE decides whether to adopt the change or schedule a safe migration.

**PostgreSQL:** A parameter group is changed during an incident. Reverting blindly may restart the database; review replication, locks, application latency and pending reboot flags.

**Elasticsearch/OpenSearch:** An IOPS/throughput hotfix was made to address query latency. Treat it as protected incident drift until performance is stable, then reconcile HCL with measured capacity.

**EKS:** Renamed \`for_each\` keys suggest node group replacements. Use \`moved\` blocks where valid, inspect PDBs and node drain/capacity before rollout.

**AKS:** A wrong subscription/backend can make a legitimate resource appear missing. Verify tenant, subscription, identity and backend before any state operation.

**Redis:** Manual failover/topology changes may not match declared replicas. Preserve availability, validate memory and failover health, then reconcile.

**Snowflake:** Grants changed outside IaC create access drift. Review role membership, privilege blast radius and audit trail; a state-only fix is not an access-control fix.

**Kafka/MSK:** Broker/security group changes affect quorum and clients. Review actual topology, state binding and plan before changes; coordinate maintenance.

## 11. Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| Address missing from state | Not applied, moved or removed | Verify config, backend, workspace and import history |
| Plan proposes replacement after rename | Address not migrated | Use reviewed moved block |
| State lock failure | Concurrent writer or stale lock | Identify writer; coordinate; avoid blind force-unlock |
| Refresh-only output differs | Out-of-band change | Verify actual resource and state impact |
| Resource exists but is untracked | Orphan/import candidate | Establish ownership, import with approval |
| State tracks missing resource | Out-of-band deletion | Validate restore/replace impact |
| Wrong account/subscription | Provider identity mismatch | Stop and verify scope |
| Sensitive state output | Unsafe log/artifact | Contain, rotate if exposed, audit |
| Unexpected destroy | Address change or desired config removal | Block; DBRE review |
| Policy reports duplicate/missing address | Inventory mismatch | Inspect nested modules and expected manifest |

## 12. Runbooks

### Drift triage
Freeze unsafe automation → record commit, workspace, backend and identity → collect sanitized \`state list\`, plan and cloud observation → classify drift → identify owner and data/security impact → decide adopt/revert/import/recover → approve → apply controlled remediation → verify SLO and audit.

### State address refactor
Backup/version state under approved procedure → inspect current addresses → add \`moved\` block → plan and review no unintended destroy → apply in staging → promote under maintenance control → retain migration documentation.

### Missing or orphaned resource
Verify cloud identity and region → inspect state and actual API → determine ownership → restore from backup if data loss → use import only with correct HCL and reviewed plan → verify health.

### State lock contention
Find active writer and CI job → wait or stop it safely → confirm no writer remains → consider authorized unlock only if truly stale → regenerate plan and verify state.

### Security drift
Declare incident → preserve audit evidence → contain privilege/network exposure → rotate credentials if necessary → reconcile IaC after containment → document RCA/COA.

## 13. Security, FinOps and acceptance

Protect remote state with encryption, least-privilege access, versioning, locking, backup and retention. Separate dev/staging/prod backends and identities; track owner and cost-center tags. State is not a data backup; production RDS, PostgreSQL and Elasticsearch need independent recovery plans.

- [ ] State list/show and JSON inventory reviewed without exposing secrets.
- [ ] Baseline plan exit 0; changed input exit 2.
- [ ] Refresh-only limitations explained.
- [ ] Declarative moved-block refactor demonstrated in disposable state.
- [ ] Python policy and automated tests pass; negative tests fail closed.
- [ ] No unapproved state mv/rm/push/force-unlock.
- [ ] Production DBRE recovery and drift runbooks reviewed.
- [ ] Lab resources destroyed and local artifacts ignored.

## 14. Knowledge check

What is the difference between an address and a cloud object ID? Why isn't state a database backup? How does refresh-only differ from normal apply? When should moved blocks be preferred? What does state rm actually do? How can a wrong backend look like resource deletion? Why can a plan be destructive after a simple rename? What is the safe response to emergency storage drift? How do you inspect nested module addresses? What evidence should a DBRE require before approving reconciliation?

**Next:** Chapter 015 — Terraform Language, Lifecycle, State and Change Management Capstone.
