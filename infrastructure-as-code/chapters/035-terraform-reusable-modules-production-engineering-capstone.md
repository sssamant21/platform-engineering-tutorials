# Chapter 035 — Terraform Reusable Modules Production Engineering Capstone

**Part 07 — Reusable Modules · Final Capstone · Chapter 035/120**  
**Audience:** Platform Engineering, SRE, DBRE, DevSecOps and incident commanders  
**Prerequisites:** Chapters 001–034 · **Lab:** Terraform >=1.7, Python >=3.9, Bash; built-in \`terraform_data\` only  
**Publication != acceptance:** lab execution, provider integration, security review and production sign-off must be evidenced separately.

## 1. Capstone mission and success criteria

Design, release, test, deploy, observe and recover a reusable **network → database → application** Terraform module stack using governed interfaces, immutable release metadata, safe environment separation, native tests, CI gates and DBRE operational acceptance. The capstone integrates Chapters 031–034 into a single change-control workflow and produces a 100-point release readiness scorecard.

You will:
1. Design typed, versioned module interfaces and output contracts.
2. Build three independently owned reusable modules and compose them without leaking implementation details.
3. Govern module release provenance, version constraints and source immutability.
4. Implement native Terraform tests, negative tests and Python plan-policy checks.
5. Promote a release through dev, staging and production gates with separate state and identities.
6. Detect unexpected replacements, broken contracts, disabled backups and unsafe release metadata.
7. Exercise rollback, incident escalation and DBRE/SRE acceptance runbooks.
8. Record auditable evidence and reject unsafe deployments.

## 2. Reference architecture

~~~text
PR + CODEOWNERS + source provenance
      |
      +--> formatting / terraform validate
      +--> native terraform test / negative tests
      +--> contract policy / plan JSON deny rules
      +--> SAST / dependency scan / approval
      |
Immutable module release catalog
      |
      +--> DEV root / isolated state / CI identity
      +--> STAGING root / isolated state / CI identity
      +--> PROD root / isolated state / CI identity / DBRE approval
                   |
                   v
       module.network (CIDR, environment, owner)
                   |
                   v
       module.database (network contract, replicas, backup, encryption)
                   |
                   v
       module.application (database contract, owner)
                   |
                   v
       SLO checks + DB backup restore evidence + audit record
~~~

Module boundaries are **not** state, access-control or security boundaries. Separate state/backends and cloud identities by environment. Root configurations own provider configuration and backend credentials; child modules own narrow interfaces. Terraform state may contain sensitive data, even when outputs are marked sensitive.

## 3. Theory: module architecture and contract evolution

Each module publishes a \`contract\` output containing \`schema_version\` and stable fields. Consumers accept typed objects, validate versions and environment identity, and depend only on declared outputs. Optional attributes should use safe defaults. \`nullable = false\` protects required inputs from explicit null; \`validation\` checks syntactic and semantic ranges; \`precondition\` guards cross-input invariants. None of these replaces real cloud IAM, encryption or recovery testing.

Use SemVer for release communication. Adding an optional input is typically compatible; removing an output, tightening validation or changing defaults may be breaking. A resource address change may require a reviewed \`moved\` block. A Git revert changes configuration, **not** database contents or Terraform state history.

## 4. Theory: version, registry and dependency governance

Registry modules use \`source\` plus \`version\`; Git modules use \`source = "git::...?...ref=<reviewed full SHA>"\`. The root provider lockfile pins provider selections, **not** child module releases. Use reviewed immutable releases, provenance verification, vulnerability scans, dependency ownership, release notes, approved major versions and consumer compatibility tests. Registry publication is separate from successful production promotion.

The executable lab uses local modules so it works without registry access. The release catalog is a **declared educational fixture**; it does not cryptographically verify a signature, published registry artifact or Git SHA.

## 5. Theory: test and delivery gates

Testing layers:
- HCL format and static validation.
- Native \`.tftest.hcl\` plan assertions and negative \`expect_failures\` cases.
- Python policy tests for module ownership, release metadata, schema versions, dependency cycles, state isolation, backups and destructive actions.
- Plan JSON inspection: deny \`delete\` and replacement actions unless a separate reviewed production policy explicitly permits them.
- Disposable integration testing against actual providers.
- Production DBRE acceptance: snapshots/PITR, replication, data integrity, query health, failover, RPO/RTO and SLO checks.

CI must **fail closed** if a required test, approval, scanner or artifact is missing. Mocked provider tests and fixture flags are useful for fast feedback but cannot establish real infrastructure safety.

## 6. Hands-on lab directory

~~~text
labs/chapter-035/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  modules/network/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/database/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/application/{versions.tf,variables.tf,main.tf,outputs.tf}
  tests/{contracts.tftest.hcl,negative.tftest.hcl}
  fixtures/{release-safe.json,release-unsafe.json,plan-safe.json,plan-destructive.json}
  capstone-policy.json, capstone_gate.py, test_capstone_gate.py
  ci/{github-actions.yml.example,gitlab-ci.yml.example}
  run-preflight.sh, runbook.md, acceptance.md, .gitignore
~~~

All Terraform resources are \`terraform_data\` and require no cloud account. The lab models infrastructure **contracts**, not real networks or databases.

## 7. Lab 1 — Bootstrap and static acceptance

~~~bash
cd infrastructure-as-code/labs/chapter-035
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform providers
~~~

Expected: valid configuration and only the built-in Terraform provider. Do not apply dev and prod variable files against the same local state.

## 8. Lab 2 — Native contract and negative tests

~~~bash
terraform test -verbose
python3 -m unittest -v test_capstone_gate.py
~~~

Native tests validate schema versions, dependency contract flow, production safety requirements and rejection of invalid input. Tests use \`command = plan\` so no infrastructure is applied. Confirm negative tests fail for the intended variable or precondition.

## 9. Lab 3 — Policy, release and plan gates

~~~bash
python3 capstone_gate.py fixtures/release-safe.json fixtures/plan-safe.json capstone-policy.json
python3 capstone_gate.py fixtures/release-unsafe.json fixtures/plan-destructive.json capstone-policy.json
bash run-preflight.sh
~~~

Expected: safe fixture passes, unsafe fixture denied. Deliberately mutate: missing owner, missing ticket, floating Git ref, mismatched major version, missing provenance, missing native test attestation, module cycle, cross-environment state namespace, backup disabled, replica count below three, or replacement action. Each must be rejected. **Do not treat self-reported test flags as independent CI evidence.**

## 10. Lab 4 — Disposable deployment and plan inspection

~~~bash
terraform plan -var-file=environments/dev.tfvars -out=chapter035.tfplan
terraform show -json chapter035.tfplan > chapter035-plan.json
terraform apply chapter035.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expect network, database and application resource addresses. An unchanged second plan should exit 0. Saved plans and state are sensitive and must not be committed or uploaded to untrusted CI artifacts.

## 11. Lab 5 — Promotion simulation and change governance

1. Inventory consumer roots, state backends, owners, module source revisions and provider lockfiles.
2. Record the release catalog SHA, change ticket, approval and environment.
3. Run all tests in dev and inspect the actual plan.
4. Re-run in staging with separate backend and credentials.
5. Require DBRE backup/restore evidence and maintenance window before production.
6. Compare planned address and replacement changes across environments.
7. Promote only the exact reviewed release.
8. Validate service SLO, database replication, backups and audit trail after apply.

**Safety:** this repository does not configure real remote backends. Treat the promotion steps as a runbook, not as permission to apply production resources.

## 12. Lab 6 — Failure injection tabletop

| Injected failure | Expected control | Recovery |
|---|---|---|
| Registry tag moved | provenance/pin review | freeze, pin reviewed SHA |
| Output schema v2 introduced | consumer contract test | compatible release or migration |
| Database backup disabled | precondition/policy deny | restore backup setting |
| Production replicas reduced | precondition/policy deny | capacity review |
| Module dependency cycle | validation/policy deny | repair dependency graph |
| Replacement of stateful resource | plan gate deny | stop, DBRE impact review |
| Provider version mismatch | init/validate failure | resolve compatible constraints |
| Cross-environment state | policy deny | isolate backend and identity |
| Test job skipped | CI must fail closed | restore required job |
| Secrets exposed in logs | security incident | contain, rotate, audit |
| Apply succeeds but DB unavailable | runtime acceptance failure | DBRE incident runbook |
| Git rollback with changed state | drift/plan mismatch | reconcile with approved plan |

## 13. Production SRE/DBRE scenarios

**PostgreSQL/RDS/Aurora:** engine upgrades, replica topology and storage replacement require PITR/WAL verification, failover and read/write acceptance.  
**Elasticsearch/OpenSearch:** index/data tier changes require snapshots, shard health, latency and search correctness.  
**EKS/AKS:** node group/cluster module changes require PDB checks, workload readiness, persistent volume safety and rollback.  
**Redis:** verify persistence, failover and client reconnection.  
**Kafka/MSK:** inspect ISR, consumer lag, endpoint and ACL changes.  
**Snowflake:** verify least-privilege grants, query execution, warehouse cost and audit.  
**MongoDB:** verify replica quorum, backup restore and read/write continuity.

## 14. Troubleshooting decision tree

~~~text
CI failure?
  |-- fmt/validate --> syntax, types, provider/module constraints
  |-- terraform test --> assertion, unknown value, precondition
  |-- Python gate --> policy, provenance, plan actions, state isolation
  |-- integration --> provider auth, quota, connectivity, data behavior
  |-- post-apply --> service SLO, DB backup, replication, client health
  +-- ambiguous --> freeze promotion, capture evidence, escalate owner
~~~

Never disable a guard to make a red pipeline green. Preserve sanitized logs, exact tool versions, commit hashes, state lineage and approval evidence. Escalate production data risks to DBRE.

## 15. Production runbooks

**Release approval:** code owner review → contract and compatibility matrix → unit/native tests → real integration test → policy gate → immutable release → signed provenance → staging plan → DBRE approval → production plan → apply → SLO evidence.

**Unexpected delete/replace:** freeze pipeline → retain plan and state snapshot securely → identify resource address/provider change → assess backup and RPO → approve migration or revert change → fresh plan.

**Failed deployment:** stop concurrent applies → verify backend lock → preserve state → check actual resources and DB health → use reviewed rollback or forward-fix → validate data integrity. Never assume reverting Git restores data.

**Module compromise:** revoke credentials and publication rights → quarantine affected versions → inventory consumers → pin trusted source → inspect IAM and state access → rotate secrets → incident review.

**DR:** recover Terraform state only through approved backend procedures; separately restore actual database/application data, validate RPO/RTO, reconcile drift and confirm SLOs.

## 16. 100-point capstone acceptance

| Domain | Points |
|---|---:|
| Module architecture and typed contracts | 20 |
| Versioning, registry and provenance governance | 15 |
| Native tests, negative cases and policy gate | 25 |
| CI, state isolation and change approval | 15 |
| DBRE/SRE recovery, observability and runbooks | 15 |
| Audit evidence and rollback exercise | 10 |

Pass >=85, with **zero critical failures**: production destructive plan without approval, missing backup, secret leakage, cross-environment state, unverified module source, bypassed tests or false recovery claims. Record each criterion in \`acceptance.md\` with real evidence before declaring operational readiness.

## 17. Cleanup and next steps

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the disposable local lab. Keep secrets, state and plan files out of Git.

**Part 07 complete on publication of Chapters 031–035.** Completion of content is not proof of live lab or production acceptance.

**Next: Chapter 036 — AWS Infrastructure as Code Foundations and Terraform AWS Provider.**
