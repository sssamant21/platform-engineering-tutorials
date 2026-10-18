# Chapter 057 — OpenTofu State, Providers, Modules and Advanced Terraform Compatibility

**Part 12 — OpenTofu and Terragrunt · Chapter 057/120**  
**Audience:** SRE, DBRE, platform engineering, security and IaC owners.  
**Prerequisites:** Chapter 056, OpenTofu CLI >=1.7, Python 3.9+, disposable lab.  
**Risk classification:** State, backend and provider operations are high-risk; require production change control.

> **Lab boundary:** The executable root creates only local \`terraform_data\` contracts and uses no cloud credentials. Its state, provider and module assurances are declared inputs, not proof of a real remote backend. The optional read-only diagnostics must run against an approved sandbox. No state push, force-unlock, destroy, or production migration is authorized by this tutorial.

## 1. Outcomes and operational scope

Understand OpenTofu state lineage and serial, provider schema and source addresses, module interface/version contracts, backend isolation and locking, compatibility testing between Terraform and OpenTofu, and safe state recovery. Build a reproducible contract lab, a JSON plan policy gate, automated negative tests and production incident runbooks. Different OpenTofu/Terraform releases can diverge: do not assume that HCL syntax, state formats, encryption features, provider schemas or plan JSON are bidirectionally compatible.

## 2. Architecture

~~~text
 Git repository / protected branch / signed change
                  |
      OpenTofu pinned CLI + lockfile
                  |
       Modules and provider registry
         |                  |
    Root module       Reviewed child modules
         |                  |
         +------ plan -------+
                  |
     Native plan review + policy adapter
                  |
     Exclusive encrypted remote backend
          versioning + lock + audit
                  |
       State lineage/serial tracking
                  |
   SRE/DBRE drift, SLO, backup/restore
~~~

**Separation:** \`network/dev\`, \`network/prod\`, \`database/dev\`, and \`database/prod\` each have a distinct root, backend key, access boundary, pipeline and state lifecycle. Avoid relying solely on CLI workspaces for strong production isolation.

## 3. State model and backend guarantees

State maps configuration addresses to remote object identities, provider addresses, attributes and dependencies. Its **lineage** identifies a state history; **serial** advances on updates. Neither alone proves resource correctness. Backends must provide appropriate locking, versioning, encryption, IAM, audit logs and restore capability. Check whether a particular backend and OpenTofu version support each requirement. An object-store version is not equivalent to a tested recovery.

**State inventory:** capture root, environment, backend type/key, executor version, provider selections, lineage, serial, last successful apply, lock owner, backup identifier, state sensitivity and resource count. Do not print raw state into CI logs; state and plans may contain secrets.

**State repair:** prefer declarative \`moved\` and \`import\` blocks where supported, review plan, and verify actual resources. \`state mv\`, \`state rm\`, \`state push\`, and \`force-unlock\` require separate, audited procedures. Removing a state address does not delete the infrastructure object, but can lead to recreation or loss of management.

## 4. Provider compatibility

Provider **source address**, **version**, **lockfile checksums**, **schema version** and authentication behavior must be verified for each root. Use explicit \`required_providers\` and constrained versions; review provider upgrade guides. Provider aliases must be passed explicitly to child modules when required. Prefer OIDC/workload identity over long-lived credentials. Some providers are not published identically across registries and mirrors; test installation and checksums in the same CI runner architecture.

~~~hcl
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
# Illustration only: choose tested versions for the actual root.
~~~

A provider major-version upgrade can change defaults, computed fields and ForceNew behavior. Block unexpected replacements, especially RDS/Aurora, PostgreSQL, EKS, KMS keys, storage volumes and DNS.

## 5. Module contracts and compatibility

Modules expose inputs, outputs, version requirements, provider requirements and lifecycle assumptions. Pin immutable Git tags/commit SHAs or registry versions; review transitive modules and licenses. Design contracts with validated inputs, stable output names and backward-compatible changes. A module version bump can alter resource addresses or \`for_each\` keys and cause replacement even when cloud intent is unchanged.

**Testing layers:** \`tofu fmt\`, \`tofu validate\`, static security checks, module unit/contract tests, isolated plan review, sandbox integration and staged promotion. Compare **meaningful actions and identities**, not raw textual plan diffs. Unknown/sensitive values require conservative handling. A real policy engine must parse native \`tofu show -json\` and account for module paths, change actions, replace paths, deposed instances and provider-specific risk.

## 6. Compatibility matrix

| Boundary | Evidence | Failure | Recovery |
|---|---|---|---|
| Terraform ↔ OpenTofu CLI | pinned versions, release notes | syntax/state divergence | isolated reproduction |
| Provider registry | source, checksums, platform | download/signature failure | approved mirror/pin |
| Provider schema | schema diff, no replacement | database replacement | hold apply, revert pin |
| Module interface | input/output/addresses | unintended rename | moved blocks + review |
| Remote state | key, lineage, serial, lock | competing writer | freeze and reconcile |
| Backend restore | encrypted backup, tested restore | unreadable state | isolated restore |
| CI identity | OIDC, scoped role, audit | wrong account/permissions | revoke/repair identity |
| Native plan adapter | action/schema tests | policy bypass | fail closed |
| DBRE stateful workloads | snapshot + PITR and cutover | data loss | restore drill, DBRE approval |

## 7. Executable labs

Root: \`infrastructure-as-code/labs/chapter-057/\`.

### Lab A — Offline OpenTofu contracts

~~~bash
cd infrastructure-as-code/labs/chapter-057
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu plan -var-file=environments/dev.tfvars -out=dev.tfplan
tofu apply dev.tfplan
tofu output -json
tofu state list
tofu destroy -var-file=environments/dev.tfvars
~~~

Four \`terraform_data\` contracts validate declared **state**, **provider**, **module** and **operations** controls. The production tfvars file is illustrative; do not use it as a substitute for real remote backend controls. Production preconditions block missing declarations.

### Lab B — Policy and negative tests

~~~bash
python3 compatibility_gate.py fixtures/compatibility-safe.json fixtures/plan-safe.json compatibility-policy.json
python3 compatibility_gate.py fixtures/compatibility-unsafe.json fixtures/plan-destructive.json compatibility-policy.json
python3 -m unittest -v test_compatibility_gate.py
bash run-preflight.sh
~~~

Safe fixture must exit 0. Unsafe and destructive fixtures must exit nonzero. The policy validates **declared evidence** and a simplified JSON plan; it is **not** a production native-plan adapter.

### Lab C — Provider and module audit

In an approved sandbox, record \`tofu providers\`, \`tofu version\`, \`tofu init -backend=false\`, \`tofu validate\`, provider lockfile changes, module source hashes and compatibility. Compare sandbox plans with Terraform only when both tools and state formats are known compatible; never share a live state writer.

### Lab D — Migration game day

1. Duplicate a **disposable** state root with a separate backend key.
2. Pin OpenTofu/provider/module versions and snapshot the baseline.
3. Simulate a provider major upgrade and observe plan changes; deny replacement.
4. Simulate a module address change; compare \`moved\` vs destructive recreation.
5. Simulate a lock conflict and verify CI refuses to apply.
6. Restore a backed-up **isolated** state and reconcile actual object IDs.
7. Validate a PostgreSQL/RDS resource identity, encryption, DB connection and PITR eligibility without altering production.
8. Document timestamps, SLO impact, state serial/lineage, rollback and owner sign-off.

## 8. Production SRE/DBRE scenarios

| Incident | Symptoms | Investigation | Safe action |
|---|---|---|---|
| State lock contention | apply timeout | CI jobs, lock owner | freeze writers, never force-unlock active job |
| Backend wrong key | resources appear new | backend config, root | stop and correct isolation |
| Provider schema upgrade | unexpected replace | lockfile/schema diff | restore tested version |
| Module refactor | address replacement | module path and \`for_each\` | moved block with reviewed plan |
| Registry outage | init fails | mirror/proxy/checksum | approved cache/mirror |
| Credential expiry | 403/401 | OIDC token/role | rotate identity without exposing secrets |
| Corrupted state | parse failure | versioned backup, checksum | isolated restore and reconciliation |
| Concurrent executors | serial divergence | pipeline audit | halt, elect one writer |
| DB replacement plan | potential downtime | RDS/PG resource lifecycle | deny, engage DBRE |
| Secret in state | leak risk | state ACL/audit | rotate, restrict and investigate |
| Drift after hotfix | unexpected update | cloud inventory | review import/reconcile |
| Failed rollback | incompatible state | format, schema, actual IDs | forward repair or isolated restore |

## 9. Troubleshooting commands

~~~bash
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu providers
tofu state list
tofu plan -var-file=environments/dev.tfvars
python3 -m unittest -v test_compatibility_gate.py
~~~

Treat \`tofu state pull\` and plan JSON as sensitive. Do not attach their raw output to public issues.

## 10. Runbooks

**R1 — Baseline:** record tool versions, provider checksums, module revisions, backend key, state lineage/serial, lock owner, resource IDs, DB SLO and backup evidence.

**R2 — Provider upgrade:** freeze changes, review release notes, pin and validate in isolated backend, compare action/replace paths, block stateful deletion, promote through staging.

**R3 — Module refactor:** review address moves and outputs, use declarative moved blocks, run plan, verify IDs unchanged and preserve rollback.

**R4 — Lock/serial conflict:** stop CI writers, determine authoritative state, preserve encrypted versions, reconcile real infrastructure before any recovery.

**R5 — State disaster:** restore an encrypted version to isolated backend, validate checksum, lineage/serial and resource IDs, plan read-only, approve cutover.

**R6 — DBRE critical resource:** deny unapproved RDS/PG/KMS/PVC replacement, verify PITR/backups, require maintenance window and recovery owner.

**R7 — Security:** revoke exposed credentials, audit backend/CI access, review provider and module supply chain, rotate secrets.

**R8 — Post-change:** verify drift, SLO, database connectivity, audit trail, FinOps and handover.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| State architecture, isolation and locking | 25 |
| Provider compatibility, supply chain and schemas | 20 |
| Module contracts, refactors and versioning | 15 |
| OpenTofu/Terraform parity and automated policy | 15 |
| SRE/DBRE incident simulation and state restore | 15 |
| Security, governance, runbooks and FinOps | 10 |
| **Total** | **100** |

Pass **>=85/100** with no critical finding. Critical findings include concurrent writers, unapproved stateful replacement, exposed credentials, absent tested restore or undocumented provider/schema incompatibility. Authored labs and tests are not live operational acceptance.

## 12. Completion and next chapter

Submit the compatibility matrix, pinned toolchain, provider/module audit, state backup and restore proof, test logs, negative plan results, incident timeline, SLO evidence and DBRE/security approvals. Part 12 progresses to **2/5 chapters** when published.

**Next proposed:** Chapter 058 — Terragrunt Foundations, DRY Configuration, Includes and Multi-Environment Orchestration.
