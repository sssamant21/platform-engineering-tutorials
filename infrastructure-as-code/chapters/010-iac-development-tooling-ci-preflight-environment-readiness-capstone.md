# Chapter 010 — IaC Development Tooling Integration, CI Preflight and Environment Readiness Capstone

**Part 02 capstone (006–010)** · **Audience:** SRE, DBRE, DevOps, Platform Engineering · **Level:** Intermediate/Advanced · **Cost:** $0 local; optional CI runner minutes · **Status:** Published content; learner execution evidence pending

## Learning outcomes
1. Integrate Git, Python, Terraform/OpenTofu, formatting, validation, tests and CI into one reproducible workflow.
2. Explain the distinction between a developer preflight, a CI gate, a plan approval and a production apply.
3. Validate environment boundaries, provider/CLI versions, credential hygiene, state/plan exclusions and ownership.
4. Execute a no-cloud Terraform lab and automated Python tests; deliberately trigger and resolve failed gates.
5. Produce an evidence-backed go/no-go decision for an SRE/DBRE infrastructure change.

## 1. Theory: preflight is an independent safety boundary
A workstation is not a production deployment environment. Preflight catches errors early; protected CI enforces the organization's approved controls; the production pipeline uses an independently authorized, short-lived deployment identity. Successful formatting and unit tests cannot prove that a cloud change is safe.

| Stage | Input | Gate | Evidence | Failure response |
|---|---|---|---|---|
| Developer | Branch and local tooling | fmt, syntax, unit tests | Local transcript | Fix before PR |
| PR CI | Immutable commit | policy, secrets scan, provider lock review | Check results | Block merge |
| Plan | Scoped backend and CI role | identity, drift, replacement review | Sanitized plan | Stop if unsafe |
| Approval | Change ticket and plan | owner, DBRE, security as needed | Approval record | Reject or defer |
| Apply | Approved artifact + protected runner | exact commit/identity and lock | Audit log | Abort on mismatch |
| Verify | Deployed infrastructure | SLO smoke tests, health and cost | Metrics | Roll back or recover |
| Close | Change evidence | drift reconciliation, documentation | Ticket/RCA | Follow up |

### Reference architecture
\`\`\`text
Developer: Git + editor + terraform/tofu + Python
    |
    +--> local preflight (format, validate, policy, tests)
    |
Pull request --> CI (pinned toolchain, trusted runner, no prod secrets)
    |
    +--> static checks / policy / secret scanning
    +--> nonprod plan --> human review --> approved promotion
    |
Protected prod deployment identity + isolated backend + state lock
    |
    +--> apply exact approved configuration
    +--> SLO verification / audit / drift monitoring
\`\`\`

**Core principles:** fail closed; use least privilege; separate dev/staging/prod identities and backends; pin CLI/provider/module versions; commit reviewed provider lockfiles; never commit state, plans or secrets; avoid \`-auto-approve\` for production; and preserve human review for data-impacting changes.

## 2. Toolchain and repo contracts
Use Git, Python 3.9+, and Terraform >=1.5 or a compatible approved OpenTofu. GitHub Actions is illustrated; equivalent gates can be implemented in GitLab CI/Jenkins. In production, pin third-party CI actions to reviewed full commit SHAs and runners to approved immutable images; the supplied sample uses only first-party checkout and a Python stdlib test path. Its no-cloud job intentionally does not perform a production plan/apply.

\`\`\`text
labs/chapter-010/
  main.tf                  # local terraform_data smoke test
  readiness.json           # fictional change inventory and gate policy
  preflight.py             # stdlib read-only policy and file checks
  test_preflight.py        # unit tests and negative cases
  run-preflight.sh         # optional local shell wrapper
  .gitignore               # state, plans, caches and secrets exclusions
  ci-preflight.yml.example # copy into .github/workflows/ after review
\`\`\`

### Identity and state separation
For each stack, verify **repository path, cloud account/subscription/project, CI role, backend key, environment, service owner and DBRE approval** independently. Terraform CLI workspaces do not provide IAM or account isolation. Do not rely on a workspace name to select a production cloud identity.

## 3. Prerequisites
- Windows 11 + WSL2 Ubuntu, native Linux or macOS; use a shell with Git, Python 3 and Terraform/OpenTofu available.
- Clone the repository and enter \`infrastructure-as-code/labs/chapter-010\`.
- No cloud account, remote backend, credentials or provider downloads are required for the core lab.
- Use one engine throughout a lab; do not switch Terraform and OpenTofu against a shared state.

\`\`\`bash
git --version
python3 --version
terraform version   # or tofu version
git status --short
\`\`\`

## 4. Lab A — Execute the local IaC lifecycle
\`main.tf\` uses built-in \`terraform_data\`; no external provider installation or cloud charges.

\`\`\`bash
cd infrastructure-as-code/labs/chapter-010
terraform init
terraform fmt -check
terraform validate
terraform plan -out=chapter010.tfplan
terraform show -no-color chapter010.tfplan
terraform apply chapter010.tfplan
terraform output -json
terraform plan -detailed-exitcode
terraform destroy
terraform state list
\`\`\`

Expected: one local resource; the second plan exits **0** (no change); after destroy, state list is empty. Exit **2** means a proposed change, not a successful no-op. Inspect \`$?\` in Bash or \`$LASTEXITCODE\` in PowerShell immediately after the plan. Avoid checking in state and plan files.

## 5. Lab B — Run the policy preflight and unit tests
The included \`readiness.json\` is an intentionally fictional inventory. It describes a nonproduction AWS EKS stack and a production AWS RDS stack; no cloud API is called.

\`\`\`bash
python3 preflight.py readiness.json
python3 -m unittest -v test_preflight.py
bash run-preflight.sh
\`\`\`

The validator checks:
- Unique stack IDs and state keys; allowed cloud/environment combinations.
- Nonempty service owner, cost center, approved state encryption/locking/versioning.
- Production requires \`auto_apply=false\`, service-owner approval, and DBRE approval for a production database.
- Protected CI identity and a distinct backend per stack.
- Exact CLI version declaration and immutable CI image digest.
- No forbidden state, plan, private key or credential artifacts in the lab tree (excluding \`.terraform\`/Python caches).
- Presence of a \`.gitignore\` covering state, plan and local cache artifacts.

The manifest validator **does not** authenticate to a cloud, verify the actual installed CLI version, parse a real lockfile or replace enterprise policy engines. Combine it with Chapters 006–009 for those checks.

## 6. Lab C — Negative and recovery drills
Copy the manifest to a temporary file before editing. Each mutation below must produce \`DENY\` and exit 1:
1. Set production \`auto_apply\` to \`true\`.
2. Remove the production database \`dbre\` approval.
3. Duplicate an existing backend key across two stacks.
4. Change \`state.encrypted\` to \`false\`.
5. Replace exact \`cli_version\` with \`latest\`.
6. Replace \`ci_image\` digest with a mutable tag.

Restore the original manifest and confirm PASS. Create a dummy \`unsafe.tfstate\` inside the lab directory and rerun preflight: the artifact check should fail; delete the dummy file and rerun. **Never use actual secrets or production state for this drill.**

## 7. Lab D — CI integration and evidence
Review \`ci-preflight.yml.example\` and copy it to \`.github/workflows/iac-chapter-010-preflight.yml\` only after confirming repository policy, action pinning, job permissions and path filters. The sample runs Python tests and manifest policy checks with **no cloud credentials**. Add Terraform/OpenTofu formatting and validation only after installing a verified approved binary in a pinned CI runner; do not assume a GitHub-hosted image has the correct version.

PR checklist:
- [ ] Scope and affected stacks documented
- [ ] Owner/DBRE approvals for stateful changes
- [ ] Local and CI tests passing
- [ ] Exact CLI and provider lockfile review completed
- [ ] Plan produced using intended identity and backend
- [ ] Destructive changes and data restore plan reviewed
- [ ] Smoke tests, rollback, monitoring and audit evidence ready

## 8. Lab E — Part 02 readiness assessment
Using Chapters 006–009, produce an evidence record containing:
1. Host OS/architecture, shell, Git, Python and IaC CLI versions.
2. Repository layout, root modules, environment/state boundaries.
3. Provider constraints, lockfile, checksum and approved mirror/cache strategy.
4. DNS/TLS/proxy diagnostics or documented offline limitation.
5. Preflight test output, no-change plan and cleanup.
6. Named owner, DBRE contact, escalation and incident runbook.

**Go/no-go:** fail if any production environment uses auto-apply, has missing state protection, ambiguous identity, unreviewed provider upgrade, unapproved database replacement, or unverified restore path.

## 9. Production SRE / DBRE scenarios
**EKS version upgrade:** A PR changes the EKS module and node groups. CI verifies toolchain, per-environment plans and rollback; platform team reviews PDBs, capacity, networking and cluster health before staged rollout.

**AKS identity mismatch:** Local CLI points at one subscription while CI identity targets another. Abort and compare subscription IDs, backend, service principal/workload identity and PR scope; do not use workstation credentials for production.

**RDS/Aurora replacement:** Provider update proposes \`-/+\` for a production DB. Halt; DBRE validates snapshots, PITR, RPO/RTO, cutover and data-integrity tests. Git revert alone cannot recover lost data.

**Elasticsearch disk incident:** Emergency IOPS hotfix causes drift. Preserve incident mitigation; temporarily suspend conflicting automation under change control; reconcile code after performance stabilizes.

**Provider registry outage:** CI \`init\` fails. Verify DNS/TLS, lockfile and approved mirror/cache; never disable checksum verification or blindly run \`init -upgrade\`.

**Shared state lock:** Two pipelines target one backend. Stop competing writers, identify ownership, wait for legitimate apply and coordinate any lock recovery. Never force-unlock without proof.

**FinOps orphan cleanup:** Preflight shows stale resources with missing cost center. Verify inventory and owners, retention, application dependency and backup policy before approved destroy.

**Compromised runner:** Suspected token exposure requires disabling deployments, revoking/rotating credentials, preserving logs, rebuilding trusted runners and auditing provider artifacts.

## 10. Troubleshooting
| Failure | Diagnosis | Safe response |
|---|---|---|
| Python preflight DENY | Missing owner/state control/approval | Correct inventory and rerun |
| CI passes but local fails | Version/path/platform drift | Compare exact binaries and environment |
| \`terraform fmt -check\` fails | Unformatted HCL | Run fmt and review diff |
| \`terraform validate\` fails | Syntax/module initialization | Inspect error, run init and fix |
| Plan exit 2 | Proposed changes | Review; not an idempotent no-op |
| Provider checksum mismatch | Wrong package or tampering | Quarantine; verify trusted source |
| Production auto-apply | Unsafe workflow | Disable; require approvals |
| Duplicate backend | State ownership conflict | Stop and design state separation |
| Database replacement | Immutable change or state drift | Block, DBRE-approved migration |
| Git state artifact detected | Sensitive file in working tree | Remove, assess exposure and history |

## 11. Operational runbooks
### Workstation-to-CI onboarding
Record approved tool versions → install from trusted sources → validate PATH/architecture → clone repository → run local fmt/validate/tests → verify backend/account boundaries → open PR → run protected CI.

### Failed preflight
Capture sanitized error and commit SHA → identify gate owner → remediate config/policy → rerun tests → update ticket → do not bypass mandatory checks.

### Unsafe production plan
Pause pipeline → verify cloud identity, backend and workspace → inspect plan for replacement/deletion → involve resource owner/DBRE → validate backups and rollback/restore → regenerate reviewed plan.

### Emergency break-glass
Declare incident and owner → use time-limited authorized identity → record manual changes → stabilize service and collect metrics → reconcile Git/state through approved PR → revoke elevation → complete RCA/COA.

### Recovery from exposed state or credentials
Contain access → preserve audit evidence → revoke exposed tokens → rotate credentials → review state versions and resource access → restore only with approval → validate application and data integrity.

## 12. Security, testing and FinOps
Prefer short-lived OIDC workload identity, least-privilege roles, separate production backends, encrypted/versioned state, signed or checksum-verified providers, pinned CI artifacts, secret scanning, cost tags and policy-as-code. Avoid leaking plan/state or credentials in CI logs. Track cost impact of changes before apply, especially storage class upgrades, database replacements and node scaling.

## 13. Acceptance matrix
| Check | Command | Expected |
|---|---|---|
| Python manifest gate | \`python3 preflight.py readiness.json\` | PASS |
| Unit tests | \`python3 -m unittest -v test_preflight.py\` | All pass |
| Terraform format | \`terraform fmt -check\` | Exit 0 |
| Terraform validate | \`terraform init && terraform validate\` | Exit 0 |
| Idempotence | \`terraform plan -detailed-exitcode\` after apply | Exit 0 |
| Cleanup | \`terraform destroy && terraform state list\` | No resources |
| Unsafe prod policy | Negative manifest mutation | DENY, exit 1 |
| Forbidden artifact | Dummy \`unsafe.tfstate\` | DENY, exit 1 |
| CI | Approved PR workflow | Checks green; approval evidence |

## 14. Part 02 final assessment
1. Explain the difference between developer validation and a protected CI gate.
2. Why does a provider lockfile not pin the CLI binary?
3. How do plugin cache and filesystem mirror differ?
4. Why do Terraform workspaces not guarantee production isolation?
5. Which identity and backend facts must be verified before applying?
6. Why is a no-change plan useful but insufficient as a production acceptance test?
7. How should a production DB replacement be reviewed?
8. What are the recovery steps for a compromised CI runner?
9. How do you document a DNS/TLS outage without disabling verification?
10. Which evidence proves the environment is ready for a controlled rollout?

**Part 02 complete on publication of Chapters 006–010; live execution evidence is separately required.**

**Next:** Chapter 011 — Terraform Configuration Language Fundamentals: Blocks, Arguments, Expressions and HCL Syntax.
