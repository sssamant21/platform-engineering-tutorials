# Chapter 015 — Terraform Language, Lifecycle, State and Change Management Capstone

**Part 03 — Terraform Language and Workflow (final capstone)** · **Audience:** SRE / DBRE / Platform Engineering · **Cost:** $0 core lab · **Status:** Published materials; execution evidence pending.

## Outcomes and assessment
Build, validate, plan, apply, inspect, audit, migrate, and destroy a local Terraform/OpenTofu workload. Demonstrate safe resource addressing, typed HCL, dependencies, drift triage, plan JSON policy, state protection, approval gates, and recovery. Passing requires an evidence package and a production change go/no-go assessment; publication alone is not execution.

## 1. Capstone architecture

~~~text
Git reviewed HCL (typed inputs, locals, for_each)
              |
      fmt / init / validate
              |
  Python policy + automated unit tests
              |
   saved plan -> JSON action inspection
              |
     owner + DBRE change approval
              |
      apply approved plan
              |
 state list / show / output / refresh-only
              |
 drift / address migration / recovery drills
              |
    destroy preview -> safe cleanup
~~~

### Separation of responsibilities
HCL expresses desired configuration. Providers perform reads/writes. State binds addresses to actual object IDs and may contain secrets. A plan describes proposed actions; a saved plan can contain sensitive values. CI validates, but human approval is still required for high-risk production database and cluster changes. State is **not** a backup of PostgreSQL, RDS, MongoDB or Elasticsearch data.

## 2. Theory synthesis: Chapters 011–014
**HCL:** Blocks, arguments, expressions, variables, locals, outputs, type validation, conditional expressions and for comprehensions. Use stable map keys and clear module interfaces.

**Graph:** Resource references create implicit dependencies; use explicit depends_on only when needed. for_each keys and count indices are part of state addresses. A rename without a moved block can cause delete/create proposals.

**Lifecycle:** init -> fmt/validate -> plan -> approval -> apply -> verify -> refresh-only review -> destroy. plan -detailed-exitcode returns 0 for no changes, 1 for errors and 2 for changes. A saved plan must be protected, tied to a reviewed commit/environment and regenerated when stale.

**State:** Compare desired Git, state and actual resources. Protect backends with encryption, versioning, locking and least privilege. State mv/rm/push, import and force-unlock are privileged operations. Prefer declarative moved blocks for refactoring.

**Change management:** Treat replacement and deletion as stop conditions until owner, DBRE, backup/restore and SLO gates are satisfied. A clean terraform validate or policy test is not proof that a production apply is safe.

## 3. Repository and prerequisites

~~~text
labs/chapter-015/
  versions.tf          CLI constraint
  variables.tf         typed inputs
  main.tf              built-in terraform_data resources
  outputs.tf           auditable outputs
  change-policy.json   example approval policy
  sample-plan.json     synthetic plan for offline testing
  capstone_policy.py   fail-closed plan and change-ticket validator
  test_capstone_policy.py automated unit tests
  run-preflight.sh     read-only preflight
  .gitignore           state/plan/secrets exclusions
~~~

Prerequisites: Terraform >=1.5 or approved compatible OpenTofu, Python 3.9+, Git; Windows/WSL2, Linux or macOS. Core lab uses only built-in terraform_data; no cloud account or provider downloads. Use one engine consistently.

## 4. Lab A — Build and validate a typed HCL workload
Review the supplied HCL. A seed resource holds non-sensitive environment metadata; a keyed service map creates stable resource addresses; an audit resource consumes service outputs. All inputs have explicit types and validations.

~~~bash
cd infrastructure-as-code/labs/chapter-015
terraform fmt -check
terraform init -input=false
terraform validate
terraform plan -out=chapter015.tfplan
terraform show -no-color chapter015.tfplan
terraform apply chapter015.tfplan
terraform output -json
terraform state list
terraform plan -detailed-exitcode
echo "exit=$?"
~~~

Expected: four managed objects (seed, two services and audit); second plan exits 0. Exit 2 means changes are proposed, not an error. In PowerShell use $LASTEXITCODE. Saved plans are sensitive and must remain uncommitted.

## 5. Lab B — Automated change-control policy
The Python validator inspects Terraform plan JSON actions and a fictional change ticket. It rejects deletions/replacements, missing ticket/owner, unapproved production changes, missing production DBRE approval, wrong environment, and malformed action data. It does not verify a real ticketing system, cloud account, backup or restore evidence.

~~~bash
python3 capstone_policy.py sample-plan.json change-policy.json
python3 -m unittest -v test_capstone_policy.py
bash run-preflight.sh
terraform plan -out=policy.tfplan
terraform show -json policy.tfplan > local-plan.json
python3 capstone_policy.py local-plan.json change-policy.json
~~~

Expected: fixture PASS; unit tests pass. Real local plan passes if it has only creates/updates and the lab ticket is valid. Never publish plan JSON or state.

## 6. Lab C — Change and drift investigation
~~~bash
terraform plan -var='replicas=4' -detailed-exitcode
echo "exit=$?"
terraform plan -refresh-only
terraform state show 'terraform_data.service["api"]'
~~~

Expected: changed input yields exit 2; refresh-only normally yields no remote drift because terraform_data is local. This exercise tests configuration difference and state inspection, **not true cloud drift**. Real drift requires authorized remote observation in an isolated environment.

## 7. Lab D — Address migration without replacement
In a disposable copy with its own local state, rename terraform_data.seed to terraform_data.foundation and update all references. Add:

~~~hcl
moved {
  from = terraform_data.seed
  to   = terraform_data.foundation
}
~~~

Run terraform plan. Verify a moved-address action rather than a delete/create replacement. Do not manually edit state JSON or use state mv as the default approach. Record before/after addresses and plan evidence.

## 8. Lab E — Failure injection and recovery
Run negative tests only against synthetic JSON or a disposable copy:
1. Set production environment without approval -> DENY.
2. Set service kind database in production without DBRE approval -> DENY.
3. Add delete/create replacement action -> DENY.
4. Remove ticket ID or owner -> DENY.
5. Insert malformed plan action -> DENY.
6. Rename for_each key in a disposable Terraform copy -> inspect proposed address churn.
7. Simulate state lock contention by explaining how to identify the active writer; **do not** force-unlock a live backend.

Recovery: restore the fixture/configuration, rerun tests, inspect plan and record the root cause. Never treat a policy bypass as remediation.

## 9. Lab F — Destroy and verify cleanup
~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expected: empty managed resource list. Remove saved plans and local JSON; verify ignored state files are not staged.

## 10. Production SRE/DBRE scenarios
**RDS/Aurora storage migration:** Replacement or instance-size change requires snapshot/PITR, maintenance, data integrity, cost and DBRE approval.

**PostgreSQL HA failover:** Terraform graph ordering does not replace controlled promotion, fencing, connection draining or replica-lag checks.

**Elasticsearch/OpenSearch performance:** Manual emergency IOPS/throughput change causes drift; preserve mitigation and reconcile only after latency and disk queue stabilize.

**EKS node groups:** Stable for_each keys, PDBs, AZ headroom and rollback determine safe rollout.

**AKS subscription separation:** Verify tenant/subscription, backend and workload identity independently of HCL environment labels.

**Redis HA:** Replica topology changes require failover testing, memory headroom and client retry validation.

**Snowflake access grants:** An update can revoke privileges without a delete action; add domain-specific access tests and owner approval.

**Kafka/MSK brokers:** Broker changes threaten quorum and partitions; validate maintenance sequencing, replica health and client error budgets.

## 11. Troubleshooting matrix
| Symptom | Cause | Safe response |
|---|---|---|
| fmt/validate fails | Invalid HCL/schema | Fix and rerun |
| plan exit 2 | Proposed changes | Review diff |
| plan exit 1 | Error | Inspect sanitized logs |
| Unexpected replacement | Address or immutable field changed | Halt, moved block or migration review |
| Policy DENY | Missing approval, destructive action | Correct change evidence, do not bypass |
| State lock error | Concurrent writer | Identify owner; coordinate |
| Wrong backend/account | Environment identity mismatch | Stop, verify scope |
| Refresh-only drift | Manual/API change | Classify and reconcile under change control |
| Saved plan stale | State changed after plan | Regenerate and reapprove |
| Apply partially fails | API/provider interruption | Freeze writers, inspect reality, recover |

## 12. Operational runbooks
**Standard change:** confirm owner/ticket/commit, toolchain, backend and identity -> fmt/validate/tests -> plan/policy -> DBRE review if stateful -> apply approved plan -> SLO/data verification -> audit.

**Destructive DB plan:** halt -> inspect resource addresses and actions -> verify backup/PITR/restore rehearsal -> decide migrate/reject -> regenerate plan -> approval.

**Drift incident:** stop conflicting automation -> preserve incident mitigation -> compare HCL/state/API -> owner decision -> reconcile after SLO stabilization -> RCA/COA.

**Partial apply:** prevent concurrent writes -> inspect state and remote resources -> restore service/data -> create new plan -> approve -> verify.

**Security exposure:** restrict leaked state/plan access -> rotate credentials where needed -> audit logs and runner identity -> remediate controls.

## 13. Acceptance rubric (100 points)
| Area | Points |
|---|---:|
| Typed HCL and graph correctness | 15 |
| fmt/init/validate/plan/apply | 15 |
| Idempotence and state inspection | 15 |
| Automated tests and policy negative cases | 20 |
| Drift/refactor investigation | 15 |
| DBRE approval, recovery and audit evidence | 15 |
| Cleanup and artifact hygiene | 5 |

**Pass:** 85+ with no critical failure. Automatic failure for unsafe production auto-apply, unreviewed destructive database plan, leaked secrets/state, bypassed locks or absent backup/restore strategy for data-impacting changes.

## 14. Evidence package
Capture sanitized CLI versions, Git commit, test summary, fmt/validate results, plan exit codes, resource addresses, moved-block plan, policy decisions, approval record, cleanup and incident runbook. Never attach raw state, plans, secrets or private keys to public issues.

## 15. Final knowledge assessment
Explain HCL references vs depends_on; count vs for_each; saved-plan trust; plan exit codes; state vs backup; refresh-only; moved blocks; state rm risks; DB replacement go/no-go; partial apply recovery.

**Part 03 complete on publication of Chapters 011–015; live lab acceptance evidence remains a separate requirement.**

**Next:** Chapter 016 — Terraform Input Variables, Type Constraints, Defaults and Validation.
