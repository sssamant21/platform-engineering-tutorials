# Chapter 007 — IaC Repository Structure, Environment Isolation and Workspace Standards

**Part 02 — Development Environment and Tooling** | **Audience:** SRE, DBRE, DevOps and Platform Engineering | **Level:** Intermediate | **Lab cost:** $0

## Learning outcomes
Design a multi-team IaC repository; distinguish module sources, root modules, state and CLI workspaces; isolate dev/staging/prod credentials and state; implement naming and ownership conventions; validate stack inventories with executable policy tests; and recover safely from workspace or backend mistakes.

## 1. Architecture: repository, root module, state and workspace
A **repository** stores versioned infrastructure intent. A **reusable module** defines a parameterized collection of resources. A **root module/stack** is an independently initialized deployment unit. A **state backend** persists the mapping between resource addresses and managed infrastructure. A **Terraform CLI workspace** selects a state instance within a backend; it does not by itself isolate cloud accounts, credentials, RBAC or blast radius.

**Enterprise default:** separate production and nonproduction root modules, backend keys, identities and CI approval gates. Use CLI workspaces only when their operational constraints are explicitly understood. Production segregation should not depend solely on `terraform workspace select prod`.

### Reference architecture
```text
Git / Pull request / CODEOWNERS
  |
  +-- modules/ (versioned reusable contracts)
  |      network/     database/     kubernetes/
  |
  +-- live/
  |     aws/dev/network/       -> AWS dev role -> dev state
  |     aws/staging/eks/       -> AWS staging role -> staging state
  |     aws/prod/rds/          -> AWS prod DBRE role -> prod DB state
  |     azure/staging/aks/     -> Azure staging identity -> staging state
  |     azure/prod/platform/   -> Azure prod identity -> prod state
  |
  +-- policies/ and CI pipelines
         fmt -> validate -> test -> plan -> approval -> apply
                                     |
                           audit, SLO and drift checks
```
Keep each state small enough for safe ownership, review and recovery; split by environment, platform boundary and operational lifecycle, not arbitrarily by every individual resource.

## 2. Repository strategies
| Pattern | Strength | Limitation | Best use |
|---|---|---|---|
| Monorepo with live stacks and modules | Discoverable cross-team changes, shared CI | Access/ownership complexity | Small to medium platform |
| Separate modules and live repositories | Independent releases and permissions | Version coordination | Larger regulated teams |
| Repository per service | Team autonomy | Standards and duplication | Mature platform golden paths |
| Environment branches | Intuitive separation | Merge drift and promotion complexity | Only with explicit controls |
| Directories per environment | Clear state and approval boundaries | Some duplication | Recommended starting point |

Version reusable modules with tagged releases and pin module sources. Pin provider versions, commit dependency lockfiles, and evaluate breaking upgrades in staging. A local path module is fine for labs but a production module registry/Git source should be versioned.

## 3. Naming and metadata
Example convention: `<org>-<service>-<env>-<region>-<component>`. Define allowed lowercase characters, maximum lengths per provider, consistent environment names and ownership tags. Sample tags: `owner`, `service`, `environment`, `cost_center`, `managed_by`, `data_classification`. Avoid embedding secrets or sensitive customer data in names or tags.

Backend key example: `iac/aws/prod/database/terraform.tfstate`. The path is a logical example, not a backend configuration. Production backend needs encryption, versioning, locking, restricted access, backup and restore tests. Do not commit state or plan artifacts.

## 4. Workspaces: when to use and avoid
```bash
terraform workspace list
terraform workspace new dev
terraform workspace select dev
terraform workspace show
```
These commands select separate state namespaces **inside the same configured backend**. They do not switch IAM roles, provider accounts, variable files or production approval policies. A forgotten workspace selection can target the wrong state. Prefer separate root configurations/backends for production. If using workspaces, validate account/subscription identity and active workspace in the pipeline before any plan/apply.

## 5. Lab prerequisites
Terraform >=1.5 or compatible OpenTofu, Python 3.9+, Git. No cloud credentials required. Use the supplied files in `labs/chapter-007`. Use one engine consistently; replace `terraform` with `tofu` if chosen. The lab uses built-in `terraform_data` only.

## 6. Lab A — Reusable module and two independent root stacks
Directory structure:
```text
labs/chapter-007/
  modules/metadata/main.tf
  live/dev/main.tf
  live/staging/main.tf
  stacks.json
  validate_stacks.py
  test_validate_stacks.py
```
The reusable module accepts environment, owner and service and emits a local metadata object. Each root invokes the module with a distinct environment. Run from the repository root:
```bash
cd infrastructure-as-code/labs/chapter-007/live/dev
terraform init
terraform fmt -check -recursive ../../
terraform validate
terraform plan -out=dev.tfplan
terraform apply dev.tfplan
terraform output -json
terraform plan -detailed-exitcode
```
Expected: local metadata created; second plan exit 0. Repeat in a separate shell or directory for staging:
```bash
cd ../staging
terraform init
terraform validate
terraform plan -out=staging.tfplan
terraform apply staging.tfplan
terraform output -json
terraform plan -detailed-exitcode
```
Expected: two independent local state files in their respective root directories. **Do not share or copy state between the roots.** From each root, execute `terraform destroy` then `terraform state list` and confirm empty.

## 7. Lab B — Workspace behavior demonstration (separate disposable root)
Copy the `live/dev` root and `modules` tree into a new disposable sandbox preserving relative paths, or use the supplied `workspace-demo/main.tf` standalone root:
```bash
cd infrastructure-as-code/labs/chapter-007/workspace-demo
terraform init
terraform workspace new sandbox-a
terraform workspace show
terraform apply -auto-approve
terraform workspace new sandbox-b
terraform plan -detailed-exitcode
```
Expected: `sandbox-b` has separate state and proposes a new local resource (exit 2). **Important:** the configuration and execution identity are unchanged. Cleanup:
```bash
terraform apply -auto-approve
terraform destroy
terraform workspace select sandbox-a
terraform destroy
terraform workspace select default
terraform workspace delete sandbox-a
terraform workspace delete sandbox-b
```
Use auto-approve only here because this is a disposable, no-cloud lab. Never generalize this to production.

## 8. Lab C — Inventory policy and automated tests
`stacks.json` is a fictional AWS/Azure inventory. The Python validator checks unique stack IDs, distinct backend keys, explicit owner/service/cost center, approved environments, isolation of production, and required state controls. It rejects a production stack with `auto_apply=true` or missing approvals.

```bash
cd infrastructure-as-code/labs/chapter-007
python3 validate_stacks.py stacks.json
python3 -m unittest -v test_validate_stacks.py
```
Expected: PASS and all unit tests pass. Copy the inventory to a temporary file; duplicate a backend key or set production auto-apply true. Expect exit 1 and actionable denial. Do not edit a live inventory for negative testing.

## 9. Lab D — Git review and policy ownership
1. Create a feature branch for a dev-only change.
2. Review `git diff` to ensure no prod root or state files changed.
3. Run formatting, validation and inventory policy checks.
4. Open a PR with stack owner, environment, blast radius, plan summary and rollback.
5. Require platform approval for shared modules and DBRE approval for database changes.
6. Promote a pinned module version through dev, staging and production with independent plans.

## 10. Production SRE/DBRE scenarios
**RDS replacement risk:** An unpinned database module upgrade changes a property that forces replacement. Block the plan, obtain DBRE approval, validate backups/PITR and design migration or restore before any apply.

**EKS and AKS account mix-up:** A CLI workspace says `prod`, but provider credentials target staging. Confirm actual account/subscription, CI identity, backend key and tags; never infer cloud identity from workspace name.

**Elasticsearch disk hotfix:** Emergency storage throughput increase drifts from Git. Document incident ownership and performance evidence; reconcile desired code after stabilization without auto-reverting a live mitigation.

**Shared network state contention:** A single state manages many teams' networks and creates long locks. Split along ownership boundaries with supported state-move/import procedures, backups and approved migration—not manual JSON edits.

**Cross-region DR:** Separate region stacks and identities; validate state backup access, keys, RPO/RTO, database restore and DNS cutover. A replicated Git repo alone is not disaster recovery.

**Kubernetes dual ownership:** Terraform and Argo CD both manage a ConfigMap. Assign a single controller, stop reconciliation conflict and plan a safe handoff.

**FinOps orphaned resources:** Compare inventory and actual cloud resources; use owner tags, drift scans and retention review before deletion. Never destroy solely because a tag is missing.

## 11. Troubleshooting
| Symptom | Likely cause | Safe response |
|---|---|---|
| Module not found | Incorrect relative source path | Check `source` and directory layout |
| Wrong state selected | Wrong working directory/workspace/backend | Stop; inspect `pwd`, workspace and backend |
| Duplicate backend key | Two roots share state | Block deploy; plan controlled state separation |
| Unexpected replacement | Module upgrade/immutable attribute | Stop; assess data loss |
| Provider access denied | Wrong account or CI role | Validate identity and least privilege |
| Stale lock | Active job or abandoned lease | Coordinate before unlock |
| Different plan on second run | Drift or changed inputs | Inspect plan; do not auto-apply |
| Missing owner | Inventory violation | Assign accountable team before deploy |

## 12. Operational runbooks
**New stack onboarding:** allocate owner and service → choose environment/account → create isolated root and backend → assign short-lived CI role → register inventory/tags → validate policy → plan/approve → apply → verify SLO and audit.

**Wrong environment prevention:** verify cloud identity, backend key, root path, active workspace and commit SHA; enforce prod approval and protected runner; abort on mismatch.

**State migration:** freeze writers → back up state → map old/new addresses and backend → use supported state migration/moved blocks/import → refresh/plan → confirm no unintended destroy → re-enable pipelines.

**Incident recovery:** preserve sanitized logs and state versions → assess blast radius → block competing applies → repair or restore with owner approval → verify services and document RCA/COA.

## 13. Security, testing and acceptance
- [ ] Dev/staging roots initialize and validate independently
- [ ] Local module resolves and produces expected environment outputs
- [ ] Each root's second plan exits 0
- [ ] Workspace demonstration confirms separate states but shared configuration
- [ ] Inventory validator and unit tests pass
- [ ] Negative tests reject duplicate backend and unsafe prod auto-apply
- [ ] Cleanup destroys local lab resources and leaves no stateful resources
- [ ] No state, credentials or plan artifacts committed

## 14. Knowledge check
Why is a workspace not an account boundary? When split root modules? What is the risk of a shared state? Why pin module versions? Who approves DB replacement? How does a Git revert differ from a restore? How should two reconcilers' ownership conflict be resolved? Which metadata is essential for incident response?

**Next:** Chapter 008 — Terraform and OpenTofu Version Management, Provider Lockfiles and Reproducible Toolchains.
