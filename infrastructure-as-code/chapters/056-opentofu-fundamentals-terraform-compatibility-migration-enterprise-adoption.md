# Chapter 056 — OpenTofu Fundamentals, Terraform Compatibility, Migration and Enterprise Adoption

**Part 12 — OpenTofu and Terragrunt | Chapter 056/120**  
**Audience:** SRE, DBRE, DevOps, cloud platform, IaC governance and security.  
**Prerequisites:** Chapters 001–035, Terraform/OpenTofu CLI (for live labs), Python 3.9+, disposable workspace.  
**Chapter scope:** OpenTofu fundamentals and safe adoption; Terragrunt orchestration follows in later Part 12 chapters.

> **Safety and validation boundary:** The mandatory lab uses OpenTofu-compatible \`terraform_data\` resources to model governance contracts without cloud providers. It creates local state only. The migration policy gate checks declared evidence and a simplified plan fixture; it does not inspect a real state file, execute a provider upgrade or guarantee Terraform/OpenTofu compatibility. Never migrate a production state backend or switch executors without tested backups, exclusive locks, approved rollback and DBRE sign-off.

## 1. Objectives

By the end of this chapter you can:
1. Explain OpenTofu's lineage, governance, licensing context, CLI and provider/module model.
2. Compare Terraform and OpenTofu without assuming feature or state-format interchangeability across all releases.
3. Design a compatibility matrix for providers, modules, backends, functions, state formats and CI integrations.
4. Plan a reversible migration with isolated state, immutable toolchain pins and zero concurrent writers.
5. Run local OpenTofu contract labs and fail-closed Python policy tests.
6. Diagnose state locks, drift, provider schema changes, plugin resolution and accidental replacement plans.
7. Establish enterprise acceptance criteria and SRE/DBRE recovery runbooks.

## 2. Architecture and tool positioning

OpenTofu is an open-source infrastructure-as-code tool derived from Terraform's earlier open-source codebase. It uses HCL and a Terraform-like workflow, but each project evolves independently. Licensing, governance, release cadence, registry behavior and advanced features differ; evaluate versions and supported integrations rather than treating the tools as interchangeable binaries.

~~~text
 Git PR / change ticket
         |
    CI preflight
  /       |       \
HCL fmt  test    policy
  \       |       /
  approved executor selection
  /                       \
Terraform version pin     OpenTofu version pin
  |                       |
provider/module lockfile compatibility review
  |                       |
remote backend + exclusive state lock
  |                       |
plan JSON + destructive action policy
  |                       |
SRE/DBRE validation, observability, rollback
~~~

**Operating principle:** One state lineage must have one authorized writer at a time. Never let Terraform and OpenTofu apply concurrently to the same backend key. Segregate dev/staging/prod and maintain a tool-specific, version-controlled migration record.

## 3. Compatibility matrix and migration decisions

| Dimension | Required assessment | Failure mode |
|---|---|---|
| CLI/HCL | language syntax, functions, moved/import blocks | parser/behavior divergence |
| Providers | source addresses, versions, plugin protocol | schema upgrade or unavailable plugin |
| Modules | registry and Git sources, version pins | incompatible module dependencies |
| Lockfile | dependency selections and checksums | unintended provider replacement |
| State | state version, lineage, serial, resource schema | unreadable or destructive migration |
| Backends | encryption, locking, authentication, versioning | split-brain or lock loss |
| Plans | action JSON, unknown values, sensitive values | policy bypass |
| CI/CD | runner, OIDC, cache, credentials, approval | wrong executor/environment |
| Security | secret handling, state ACLs, audit logs | credential exposure |
| DR | backup, restore, rollback and freeze | data/control-plane loss |

Create a written **go/no-go matrix** for every production root. Do not assume a state written by a newer release can be safely consumed by an older tool. Check official compatibility notes for the exact versions before proceeding.

## 4. Enterprise migration strategy

### Phase A — Inventory

Collect all roots, backend addresses and keys, Terraform/OpenTofu versions, provider lockfiles, module sources, cloud identity, state serial/lineage, CI runners, policy integrations, workspace mappings, current drift and criticality. Classify database, Kubernetes, encryption and networking resources as high-risk.

### Phase B — Freeze and backup

Obtain change approval. Freeze all other applies, pause scheduled automation and verify exclusive lock ownership. Back up encrypted state to a restricted, versioned location; verify restore access and checksum. **State may contain secrets:** do not publish backups, raw state or credentials to GitHub or tickets.

### Phase C — Disposable validation

Copy a representative root to an isolated workspace and backend key. Pin OpenTofu CLI and providers, run formatting, initialization and validation. Compare **reviewed** plans using the intended executor. Investigate any unexpected create, replace or delete action. For database and storage resources, deny destructive actions unless separately approved.

### Phase D — Controlled production cutover

Use a change window with named owner, monitoring, rollback and incident commander. Ensure no Terraform process can write the same state while OpenTofu is active. Run the approved OpenTofu plan and post-apply checks. Validate cloud resource IDs, DB connectivity, Kubernetes health, encryption, SLOs and audit logs.

### Phase E — Recovery and rollback

A rollback is **not** simply replacing \`tofu\` with \`terraform\`. If OpenTofu changed state format, provider schema or infrastructure, restoring an old state blindly may create divergence. First freeze writers, reconcile actual resources and state, then execute an approved restore or forward repair. Verify state lineage, serial, resource addresses and backup integrity.

## 5. Hands-on Lab A — Offline OpenTofu governance contracts

Files: \`infrastructure-as-code/labs/chapter-056/\`.

~~~bash
cd infrastructure-as-code/labs/chapter-056
tofu version
tofu fmt -recursive
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu plan -var-file=environments/dev.tfvars -out=dev.tfplan
tofu apply dev.tfplan
tofu output -json
tofu state list
tofu destroy -var-file=environments/dev.tfvars
~~~

This lab contains only \`terraform_data\` resources and does not require a cloud account. Four contracts model compatibility inventory, state migration safety, CI/identity and operational acceptance. Production preconditions enforce declared backup, locking, rollback and approval controls. A passing contract proves the declaration was supplied, **not** that the external backup or lock actually exists.

**Dev/prod comparison:** \`environments/dev.tfvars\` and \`environments/prod.tfvars\` demonstrate policy metadata and separate state namespace naming. They do not create or configure remote state backends.

## 6. Hands-on Lab B — Fail-closed migration policy

~~~bash
python3 migration_gate.py fixtures/migration-safe.json fixtures/plan-safe.json migration-policy.json
python3 migration_gate.py fixtures/migration-unsafe.json fixtures/plan-destructive.json migration-policy.json
python3 -m unittest -v test_migration_gate.py
bash run-preflight.sh
~~~

The safe fixture must pass; unsafe and destructive fixtures must exit nonzero. Negative tests independently remove required controls, corrupt environment/state metadata, tamper with policy and introduce replacement actions. The simplified plan fixture is **not** native \`tofu show -json\`; production use requires a tested native-plan adapter and real backend/state checks.

## 7. Hands-on Lab C — Read-only toolchain and backend audit

Use \`examples/opentofu-readonly-audit.sh.example\` in an approved workspace. Record:
- \`tofu version\` and \`terraform version\` where both exist.
- Provider/module dependency tree, lockfile status and supported registry.
- Backend type, key, encryption, retention and lock ownership **without printing secrets**.
- Current state lineage and serial through an approved redacted inventory process.
- Expected vs actual plan action counts; record zero unapproved deletes/replacements.

Avoid executing \`state push\`, \`state rm\`, \`force-unlock\`, \`import\`, \`apply\` or \`destroy\` during read-only discovery.

## 8. Hands-on Lab D — Production incident simulations

| Scenario | Signal | Triage | Containment |
|---|---|---|---|
| Concurrent Terraform/OpenTofu writers | state serial mismatch | lock logs, CI jobs | freeze both, elect one owner |
| Provider version drift | unexpected replacement | lockfile, schema diff | restore pins, block apply |
| Backend permission denied | init/plan fails | OIDC, IAM, ACL | repair least-privilege identity |
| Stale lock | lock acquisition timeout | job status, lock metadata | verify owner before recovery |
| State migration incompatible | unsupported state | versions, lineage, serial | restore isolated copy, no blind downgrade |
| Missing registry artifact | init plugin error | mirror/cache/source | pin trusted source, retry |
| Secret leaked in plan/state | security alert | access audit | revoke/rotate, restrict state |
| Database replacement proposed | destructive plan | plan actions, dependencies | deny and involve DBRE |
| Workspace/backend key mismatch | wrong resources targeted | environment map | stop, verify backend identity |
| CI executor silently changed | inconsistent plans | runner logs, tool pins | lock versions and approvals |
| Cross-region backend outage | state unavailable | storage/lock health | fail closed, restore under DR |
| Policy parser misses unknown | false safe decision | fixture mutation | fail closed, repair parser |

## 9. Troubleshooting commands

~~~bash
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu providers
tofu state list
tofu plan -var-file=environments/dev.tfvars
python3 -m unittest -v test_migration_gate.py
~~~

\`tofu state list\` may expose resource addresses. Do not copy raw state or sensitive plan values into support tickets. For real backends, use an approved non-mutating inspection process with access logging.

## 10. Production SRE/DBRE runbooks

**R1 — Pre-change:** record executor/provider/module versions, root/backend key, state lineage/serial, lock owner, encryption, backup restore proof, ticket, SLO and DBRE/Security approvals. Deny unapproved replace/delete.

**R2 — Migration dry run:** clone into isolated backend, pin OpenTofu and providers, compare plan actions and outputs, verify DB/Kubernetes resource identity, document rollback.

**R3 — State lock conflict:** freeze all applies, identify owner and active CI job, preserve audit evidence, resolve safely. Never force-unlock an active writer.

**R4 — Provider or module incompatibility:** revert dependency pins, reproduce in disposable workspace, compare schema and plan, escalate high-risk replacements.

**R5 — Database or storage destructive plan:** block apply, inspect resource addresses and lifecycle, engage DBRE, preserve backups and use approved non-destructive migration.

**R6 — Secret/state incident:** restrict backend, revoke exposed credentials, rotate, audit access, verify encryption and retention.

**R7 — Backend outage/DR:** suspend changes, recover encrypted versioned backup to isolated backend, validate lineage/serial and resource inventory, resume one writer after approval.

**R8 — Post-cutover:** validate drift, SLO, DB connectivity, application traffic, backup and monitoring; update owner registry, runbooks and change record.

## 11. 100-point acceptance

| Domain | Points | Evidence |
|---|---:|---|
| OpenTofu architecture and compatibility inventory | 20 | toolchain/provider/backend matrix |
| State safety, locking, backup and rollback | 25 | verified isolated restore and exclusive writer |
| Terraform/OpenTofu parity and migration testing | 15 | reviewed plan comparison |
| Security, identity, policy and CI controls | 15 | OIDC, audit, negative tests |
| SRE/DBRE incidents and recovery | 15 | game-day evidence and RPO/RTO |
| Governance, FinOps and change approval | 10 | signed change and cost review |
| **Total** | **100** | |

**Pass >=85/100 with zero critical findings.** Critical failures: concurrent state writers, unapproved delete/replace, missing backup restore evidence, leaked secrets or inability to reconcile state and actual infrastructure. Code publication and authored unit tests are **not** production acceptance.

## 12. Chapter exit criteria

Deliver a tool/version inventory, compatibility matrix, encrypted state backup evidence, isolated plan comparison, CI policy logs, negative tests, incident timeline, recovery procedure and signed go/no-go decision. Keep real production migration pending until executed and reviewed.

**Part 12 — OpenTofu and Terragrunt: 1 of 5 chapters published after this chapter.**  
**Next proposed:** Chapter 057 — OpenTofu State, Providers, Modules and Advanced Terraform Compatibility.
