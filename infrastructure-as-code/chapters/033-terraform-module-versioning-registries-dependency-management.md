# Chapter 033 — Terraform Module Versioning, Registries and Dependency Management

**Part 07 — Reusable Modules · Chapter 033/120**  
**Audience:** Platform Engineering, SRE, DBRE, Security · **Prerequisites:** Chapters 001–032  
**Execution:** Offline Terraform >=1.5, Python >=3.9; no cloud credentials required. Publication does not imply tests or live production drills have run.

## 1. Mission and learning outcomes

Operate reusable Terraform modules as governed software artifacts: design semantic versions, publish to public/private registries, pin Git module sources, resolve dependency constraints, assess supply-chain provenance, promote releases safely and recover from incompatible upgrades. Produce a repeatable SRE/DBRE acceptance workflow that distinguishes **module source versions**, **provider plugin versions**, **Terraform CLI versions** and **state schema compatibility**.

## 2. Enterprise reference architecture

~~~text
Source repository -> PR review + code owners + security scanning
                -> contract tests + integration tests + change log
                -> immutable Git tag / SHA + signed provenance
                -> private module registry or approved Git source
                -> version catalog + policy + promotion manifest
                -> environment root (dev -> staging -> prod)
                -> init / validate / plan / approval / apply
                -> DBRE workload checks + rollback evidence
~~~

A registry is a distribution and discovery mechanism, not a replacement for repository review or provenance checks. Terraform **registry module version** is configured with \`version\`; a Git module is pinned through a source URL \`?ref=\` (prefer a reviewed full commit SHA for immutability). Local module sources are suitable for this offline lab but are not evidence of a published registry release.

## 3. Versioning semantics and breaking changes

Use SemVer \`MAJOR.MINOR.PATCH\`: patch for compatible fixes, minor for backward-compatible features, major for breaking interface or behavior changes. A technically additive change may still require major-version treatment if it changes defaults, causes resource replacement, alters IAM or creates unacceptable operational impact.

| Change | Typical classification | Required acceptance |
|---|---|---|
| Documentation/test-only fix | patch | static and unit tests |
| Optional input with safe default | minor | contract regression and plan |
| Additional non-sensitive output | minor | consumer contract tests |
| Rename/remove required input | major | coordinated consumer migration |
| Rename/remove output | major | downstream compatibility tests |
| Resource address move | depends on compatibility | \`moved\` block and no-replace plan |
| Database engine or subnet change | operationally breaking | DBRE review, backup, failover |
| Tighten validation | potentially breaking | inventory all caller values |
| Provider major upgrade | potentially breaking | plugin compatibility, state and plan review |

Never equate \`terraform init -upgrade\` with a safe production deployment. It can update provider selections and module packages within configured constraints; always inspect dependency changes and a fresh plan.

## 4. Module source and registry fundamentals

### Public Terraform Registry

~~~hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
}
~~~

Illustrative only; review actual available versions and source before use. Registry addresses include namespace/name/provider. The \`version\` argument applies to registry-sourced modules, not local or generic Git modules.

### Private registry

~~~hcl
module "database" {
  source  = "app.terraform.io/example-org/database/aws"
  version = "2.4.1"
}
~~~

Illustrative: requires a configured registry, authentication and an existing module release. Authenticate through approved CLI credentials or workload identity; never commit tokens.

### Pinned Git source

~~~hcl
module "network" {
  source = "git::https://github.com/example/platform-modules.git//modules/network?ref=0123456789abcdef0123456789abcdef01234567"
}
~~~

The \`//\` selects a subdirectory; the query pins a full SHA. Review repository and commit provenance. A moving tag or branch is weaker than a verified immutable SHA.

### Local development source

~~~hcl
module "network" {
  source = "./modules/network"
}
~~~

The lab uses local modules and a separate version catalog fixture to simulate the registry/release gate. This deliberately avoids network calls.

## 5. Dependency resolution and lockfile boundaries

\`required_version\` constrains the Terraform CLI; \`required_providers\` constrains provider plugin versions. Root provider selection is recorded in \`.terraform.lock.hcl\`; **that lockfile does not lock child module source versions**. Module version selections must be constrained and governed explicitly in the root configuration and release manifest.

Provider versions should be selected to satisfy all child module constraints. A reusable child module usually specifies a compatible minimum provider version rather than forcing a single patch release. Root applications should pin versions more tightly and commit their provider lockfile. Run \`terraform providers\` to inspect requirements. Review lockfile hash changes as supply-chain changes.

## 6. Release governance and promotion

A production release requires code owner approval, contract tests, plan comparison, SBOM/provenance where available, policy checks, changelog, rollback path, environment-by-environment promotion and runtime SLO verification. Use separate state/identity per environment. Prefer an immutable catalog of approved releases; never auto-promote a new major version into production without DBRE sign-off.

The offline lab contains:
- \`modules/network\`, \`modules/database\`, \`modules/application\` with typed output contracts.
- Dev/prod root variables and \`terraform_data\` resources only.
- A release manifest, version policy, safe and unsafe fixtures, plan fixtures, Python gate and unit tests.
- An illustrative private registry consumer and Git pinning reference (not executable without external services).

## 7. Lab A — Run the offline composition

~~~bash
cd infrastructure-as-code/labs/chapter-033
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter033.tfplan
terraform apply chapter033.tfplan
terraform state list
terraform output -json
terraform providers
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected state addresses: \`module.network.terraform_data.network\`, \`module.database.terraform_data.database\`, \`module.application.terraform_data.application\`. A second unchanged plan should exit 0. **Never apply prod inputs to dev state**.

## 8. Lab B — Version policy and negative release tests

~~~bash
python3 release_gate.py fixtures/release-safe.json fixtures/plan-safe.json version-policy.json
python3 release_gate.py fixtures/release-unsafe.json fixtures/plan-destructive.json version-policy.json
python3 -m unittest -v test_release_gate.py
bash run-preflight.sh
~~~

Safe fixture should pass, unsafe fixture should fail. The policy checks approved versions, pinned source references, distinct environment identities, release owner and change ticket, SemVer, compatibility policy, provenance attestations, review and test flags, production DB safeguards, dependency graph and destructive plan actions. **Declared fixture flags are not cryptographic proof of signing, actual registry state or cloud IAM.**

## 9. Lab C — Upgrade and rollback simulation

1. Record the approved release catalog and provider lockfile.
2. Change a disposable fixture from a patch release to a minor release and confirm policy approval only if tests and provenance are present.
3. Change it to a new major version without an approved migration and verify rejection.
4. Replace a full Git SHA with \`ref=main\` and verify rejection.
5. Simulate a renamed module output, then update a consumer in a disposable checkout. Review a fresh plan for replacements.
6. Revert the release manifest and module reference, reinitialize, plan and verify; do not assume a Git revert restores state or deleted data.
7. For a stateful production module, require backup and DBRE approval before applying an upgrade.

## 10. Registry publication workflow

**Private registry:** choose approved VCS repository, enforce naming/version tagging rules for the provider's registry implementation, connect registry service, publish immutable release, grant consumer access, validate registry metadata and download, record provenance. Registry naming and tag semantics vary by platform; follow the selected registry's current documentation.

**Public registry:** validate repository naming convention, documentation, licensing, version tags and publishing requirements; test in an isolated consumer. Public release does not imply enterprise security approval.

**Git-only distribution:** pin reviewed commit SHAs; document source subdirectory, provenance and migration. A Git URL with \`ref=v1.2.3\` depends on tag governance and immutability controls.

## 11. SRE/DBRE production scenarios

| System | Module upgrade risk | Acceptance outside Terraform |
|---|---|---|
| PostgreSQL / Aurora / RDS | engine, storage, parameter or subnet replacement | PITR/WAL, replicas, backup and query health |
| Elasticsearch / OpenSearch | domain recreation, node changes | snapshots, shard health, latency |
| EKS / AKS | cluster or node group replacement | workload readiness, PDBs, storage |
| Redis | failover, endpoint or persistence changes | replication, RDB/AOF, client reconnect |
| Kafka / MSK | broker or networking changes | ISR, lag, availability |
| Snowflake | grants, integrations, warehouse config | privilege audit, queries, cost |
| MongoDB | topology or security changes | quorum, backups, application health |

## 12. Troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| Failed to download module | registry/network/auth | verify source, token scope, outage |
| Module version not found | tag or registry metadata | check immutable release catalog |
| Invalid module version constraint | incompatible SemVer range | inspect declared versions |
| Unsupported argument | breaking input change | pin old version or migrate caller |
| Unsupported attribute | output contract changed | restore compatible contract |
| Provider constraint conflict | child/root requirements incompatible | inspect \`terraform providers\` |
| Unexpected replacement | internal address/immutable argument | stop and review \`moved\` blocks |
| Drift after rollback | state differs from reverted HCL | fresh plan and reconcile |
| Suspicious source change | tag moved or supply-chain compromise | freeze, compare SHA, incident response |
| Apply succeeds but DB fails | infrastructure != data availability | invoke DBRE recovery and health checks |

## 13. Production runbooks

**Publish:** owner review → release notes and compatibility matrix → automated tests → source/provenance verification → immutable version → registry publication → isolated consumer test → promotion.

**Upgrade:** inventory roots and stateful dependencies → pin target release → compare manifests/provider locks → static and negative tests → fresh plan → approve replacements explicitly → backup → apply with lock → verify real services and SLO → audit.

**Compromised module:** freeze pipeline → revoke registry credentials → identify affected versions/consumers → pin trusted commit → inspect state and IAM → rotate secrets → incident RCA.

**Failed upgrade:** stop concurrent applies → preserve state/version evidence → restore compatible module version or reviewed migration → fresh plan → DBRE validation. Never force state push or assume Git revert restores data.

## 14. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Versioning and compatibility model | 20 |
| Registry and source pinning controls | 20 |
| Dependency/provider governance | 15 |
| Automated positive/negative tests | 20 |
| Upgrade, rollback and incident runbooks | 15 |
| SRE/DBRE production evidence | 10 |

Pass >=85 with zero critical failures. Critical: unpinned production module, unsigned/unreviewed artifact where required, credentials in source, unapproved destructive plan, cross-environment state reuse, missing DB backup or a false recovery claim.

## 15. Cleanup and review questions

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only disposable local resources. Keep provider lockfiles for application roots; never commit state or secrets.

Questions: Why does the provider lockfile not pin modules? What does \`version\` apply to? Why is \`?ref=main\` unsafe? How do registry and Git source differ? Which changes are breaking? What does \`init -upgrade\` do? Why do module tags need governance? How do you prove provenance? What are DBRE upgrade gates? Why is Git rollback not state/data rollback?

**Next: Chapter 034 — Terraform Module Testing, Mock Providers and CI Quality Gates.**
