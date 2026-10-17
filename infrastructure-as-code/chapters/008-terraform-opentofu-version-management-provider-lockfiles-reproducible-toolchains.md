# Chapter 008 — Terraform and OpenTofu Version Management, Provider Lockfiles and Reproducible Toolchains

**Part 02 — Development Environment and Tooling** | **Audience:** SRE, DBRE, DevOps, Platform Engineers | **Level:** Intermediate | **Lab cost:** $0

## Learning objectives
- Separate CLI, configuration-language, provider, module, and state compatibility.
- Pin approved Terraform/OpenTofu CLI versions and provider constraints.
- Generate, review, and commit provider dependency lockfiles where providers are used.
- Verify multi-platform checksums, mirrors, and CI reproducibility.
- Build an executable local no-cloud lab and Python policy gate with automated tests.
- Troubleshoot unexpected plans, registry failures, and version drift without risking production.

## 1. The five version layers
| Layer | Example | Governance |
|---|---|---|
| IaC CLI | Terraform 1.x or OpenTofu 1.x | Install approved exact version in CI; record binary checksum |
| Language/runtime | `required_version` | Declare compatible versions in root module |
| Provider plugin | `hashicorp/aws`, `hashicorp/azurerm` | Declare constraints; commit `.terraform.lock.hcl` |
| Reusable module | Git tag or registry version | Pin immutable approved releases |
| State/schema | Backend and provider-managed state | Backup, test migration and verify downgrade limitations |

**Important:** `required_version` is a compatibility constraint, not a package manager. A `~>` constraint allows compatible updates; exact CI image pinning controls the actual CLI. A provider constraint is not a lock: the lockfile records a selected provider version and hashes. Terraform/OpenTofu may have differing lockfile behavior and compatibility over time; use separate, reviewed migration procedures rather than alternating tools against a production state.

## 2. Architecture
```text
Git commit + toolchain policy + module sources
       |
  CI runner image pinned by digest
       |
  Terraform OR OpenTofu binary (approved version + checksum)
       |
  root required_version + required_providers
       |
  .terraform.lock.hcl (provider selections and checksums)
       |
  verified registry / private provider mirror
       |
  plan (identity + backend + environment + commit)
       |
  policy/approval -> apply -> SLO verification -> audit
```
The provider lockfile does not pin the Terraform/OpenTofu CLI or modules. Providers are downloaded during `init`; a provider's checksum must be verified, including platform-specific hashes. Module source changes can affect plans even when provider versions stay unchanged.

## 3. Version-management strategy
Use a supported version manager such as `tfenv`, `tfswitch`, `tenv`, or an approved container image, based on organizational policy. Do not blindly pipe third-party install scripts into a shell. Use official release artifacts, verified checksums and pinned CI images. On Windows/WSL2 keep binary architecture and PATH explicit; a Windows `terraform.exe` is not the Linux binary for Ubuntu WSL.

For production: update CLI/provider/module versions in separate scoped PRs, plan in a nonproduction environment, inspect drift and replacements, run integration tests, then promote with owner/DBRE approval. Capture CLI version, provider versions, lockfile diff, commit SHA, backend identity and sanitized plan evidence.

## 4. Terraform provider lockfiles: exact workflow
For a root module with a real provider:
```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
```
Use this **illustrative snippet**, not the offline lab's `main.tf`. It downloads a provider and requires registry/network access. From its own disposable directory:
```bash
terraform init
terraform providers
git diff -- .terraform.lock.hcl
terraform init -lockfile=readonly
terraform providers lock -platform=linux_amd64 -platform=windows_amd64
```
Commit `.terraform.lock.hcl` after review; do **not** commit `.terraform/`, state or saved plans. `terraform init -upgrade` explicitly reselects versions allowed by constraints and may update the lockfile. Always review the resulting provider diff and plans. Do not manually invent provider checksums or fabricate lockfile entries.

For a truly network-free lab, `terraform_data` is built into the Terraform/OpenTofu CLI; it needs no external provider plugin and therefore does **not** demonstrate a populated provider lockfile. The separate optional provider exercise above does.

## 5. Lab prerequisites
Python 3.9+, Git, Terraform >=1.5 or compatible OpenTofu. A provider-free local lab needs no cloud account or network access once the CLI is installed. Use a new directory, and use **one engine** consistently. For WSL2, run Linux binaries in the Linux filesystem; PowerShell may use `py -3` instead of `python3`.

## 6. Lab A — Reproducible local plan with no external provider
Use supplied `labs/chapter-008/main.tf`:
```bash
terraform version
terraform init
terraform fmt -check
terraform validate
terraform plan -out=lab.tfplan
terraform show -no-color lab.tfplan
terraform apply lab.tfplan
terraform output -json
terraform plan -detailed-exitcode
terraform destroy
terraform state list
```
Replace `terraform` with `tofu` consistently if using OpenTofu. Expected: one `terraform_data.toolchain` local resource; second plan exits 0; final state list empty. Exit 2 from `-detailed-exitcode` means changes proposed, not an execution error. Keep state/plan files out of Git. This lab intentionally does not populate a provider lockfile.

## 7. Lab B — Policy validation for pinned toolchain manifests
The included `toolchain.json` declares one approved engine, exact CLI version, approved provider version constraints, CI image digest, and lockfile expectations. `validate_toolchain.py` is a stdlib-only policy validator; it does not install software or parse a live provider lockfile.

```bash
python3 validate_toolchain.py toolchain.json
python3 -m unittest -v test_validate_toolchain.py
```
Expected: `PASS` and all tests pass. Negative drills: copy `toolchain.json`, replace the exact CLI version with `latest`, remove the CI image digest, or set `lockfile_committed=false` for a declared external provider. Each must fail. Do not use a lab policy manifest as evidence that the local CLI or downloaded provider actually matches the declaration.

## 8. Lab C — Detect local CLI version drift
Use the supplied `check_cli.py`:
```bash
python3 check_cli.py toolchain.json
```
It locates the chosen binary and runs its version command, then compares the reported semantic version with the manifest's approved exact version. This check may fail on a workstation with a different installed version; that is useful drift evidence. To run the test suite without a particular binary installed:
```bash
python3 -m unittest -v test_check_cli.py
```
The tests use fake command output and require no Terraform installation.

## 9. Lab D — Controlled provider upgrade (optional online)
In a disposable test root with the `hashicorp/random` provider example, run `terraform init`, inspect the generated `.terraform.lock.hcl`, run `terraform init -lockfile=readonly`, then `terraform init -upgrade` after changing the provider constraint in a PR. Record selected version/hash changes and compare plans. Never copy a generated lockfile from a different provider configuration without validating the result. If registry access is blocked, skip the optional online lab and record why.

## 10. Production SRE/DBRE scenarios
**A — RDS/Aurora replacement after provider upgrade:** A provider schema change proposes replacement of a production database. Halt deployment; inspect provider lockfile diff, schema and state, validate PITR/backups and require DBRE-approved migration.

**B — EKS plan differs across CI runners:** One runner resolves a newer provider because the lockfile was not committed. Pin the lockfile and CLI image, rerun plan, inspect changes before apply.

**C — Azure AKS tool mismatch:** Windows native and WSL2 invoke different Terraform versions. Compare `where.exe terraform`, `command -v terraform`, `terraform version` and architecture; standardize via approved tooling.

**D — Elasticsearch storage emergency drift:** Disk IOPS increased manually during an incident. Do not let an automated provider upgrade revert the change; reconcile code after stabilization.

**E — Provider registry outage:** Use an approved checksum-verified mirror/cache; do not disable TLS or checksum validation. Existing plugins may be usable only if they match the lockfile and platform.

**F — Terraform/OpenTofu migration:** Before changing engines, review license, language, providers, state compatibility and rollback. Back up state, freeze writes, test a cloned nonproduction stack, and obtain approval. Do not casually switch the same production state.

**G — Security advisory:** A vulnerable provider version requires an upgrade. Coordinate risk-based rollout, inspect plan diffs and application SLOs; a lockfile alone does not remediate a vulnerability.

## 11. Troubleshooting
| Symptom | Likely cause | Safe response |
|---|---|---|
| Unsupported Terraform version | CLI outside `required_version` | Install approved CLI |
| Lockfile readonly error | Provider constraints differ from lock | Review change and regenerate in controlled PR |
| Provider checksum mismatch | Corrupt artifact, wrong platform or tampering | Stop; verify source and official checksums |
| Registry unavailable | Proxy, DNS, TLS or outage | Use approved mirror, preserve verification |
| Unexpected replacement | Provider schema/module upgrade | Block; owner/DBRE review |
| Windows/WSL binary mismatch | PATH or architecture | Confirm binary location and version |
| CI and local plans differ | CLI/provider/env/state mismatch | Compare pinned versions and inputs |
| Provider upgrade changes lockfile | Explicit `init -upgrade` | Review diff and test |
| State incompatibility | Unsupported engine/provider downgrade | Restore tested backup under runbook |

## 12. Runbooks
**New project baseline:** choose engine → pin CLI in CI → declare `required_version` and providers → initialize → review/commit provider lockfile → validate across OS targets → register ownership and upgrade policy.

**Provider upgrade:** ticket/security advisory → change constraint → `init -upgrade` → review lockfile → tests and staging plan → production impact review → approved apply → verify SLOs → audit.

**Unexpected plan:** stop → confirm account/backend/workspace/commit → compare CLI and provider versions → inspect lockfile/module changes → get owner approval → regenerate plan.

**Supply-chain incident:** freeze downloads/applies → validate binary and provider checksums → inspect CI and registry logs → revoke compromised credentials if needed → restore approved artifacts → retest.

## 13. Security, FinOps and acceptance
Use verified binaries, signed artifacts when available, least-privilege CI identity, approved mirrors, dependency scanning, locked provider versions, immutable runner images, state encryption and versioning. Track provider upgrade work as maintenance, and quantify replacement/cost risk before rollout.

Acceptance:
- [ ] CLI version captured and compared to policy
- [ ] Terraform/OpenTofu local lab init/validate/apply/no-change/destroy succeeds
- [ ] Manifest policy tests pass and negative tests fail closed
- [ ] Optional online provider lab generates a real reviewed lockfile
- [ ] No state, plan, credentials or `.terraform/` artifacts committed
- [ ] SRE change ticket, plan review and recovery path documented

## 14. Knowledge check
1. What does `required_version` constrain?
2. Does a provider lockfile pin modules?
3. Why is `init -upgrade` a controlled change?
4. How are provider checksums different across platforms?
5. Why can a valid provider upgrade still be destructive?
6. Why must Terraform/OpenTofu migration include state compatibility?
7. How do CI image digests improve reproducibility?
8. How should a provider registry outage be handled?

**Next:** Chapter 009 — Provider Installation, Plugin Caching, Registries and Network Troubleshooting.
