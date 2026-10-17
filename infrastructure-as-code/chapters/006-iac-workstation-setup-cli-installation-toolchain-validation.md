# Chapter 006 — IaC Workstation Setup, CLI Installation and Toolchain Validation

**Part 02 — Development Environment and Tooling (006–010)** · **Audience:** SRE, DBRE, DevOps, Platform Engineering · **Cost:** $0 local lab · **Platforms:** Windows 11/WSL2, Ubuntu/Debian Linux

## Outcomes and prerequisites
Build a reproducible workstation for Git, VS Code, Terraform, OpenTofu, Python and optional Ansible. Diagnose PATH, architecture, shell, WSL integration, plugin/network and provider problems. Run a local no-cloud Terraform/OpenTofu exercise, execute an automated workstation audit, and document production SRE controls. Required: a non-production machine, permission to install approved tools, internet for initial package downloads, 4 GB free disk space recommended. Versions and installation commands change: use the vendors' current official documentation and your organization's pinned approved versions.

## 1. Why workstation consistency matters
Infrastructure changes pass through a chain: developer shell -> Git commit -> CI lint/tests -> plan -> approval -> deployment identity -> cloud API -> state backend. A different CLI version, platform architecture, provider lockfile or environment variable can change plan behavior. **Workstation setup is not production authorization**: use isolated credentials and a CI runner for approved production applies.

### Reference architecture
```text
Windows 11 Host
  ├── PowerShell / Windows Terminal
  ├── VS Code + Remote WSL extension
  └── WSL2 Ubuntu (recommended consistent Linux toolchain)
        ├── git, python3, pip/venv, curl, unzip
        ├── terraform OR tofu (separate state directories)
        ├── ansible (optional)
        └── ~/src/platform-engineering-tutorials/
              └── infrastructure-as-code/labs/chapter-006/
                    main.tf
                    validate_toolchain.py
                    test_validate_toolchain.py
                    workstation-manifest.json
                    .gitignore
```
Linux users can use the same commands directly without WSL. Prefer files under WSL's Linux filesystem (e.g. `~/src`) for Linux tooling instead of `/mnt/c` when permissions/performance matter. Keep shell environments and executable paths explicit.

## 2. Tool responsibility matrix
| Tool | Purpose | Check | Required for which lab? |
|---|---|---|---|
| Git | Version control | `git --version` | Git workflow |
| Terraform | Declarative provisioning | `terraform version` | Lab A, choose one engine |
| OpenTofu | Open-source provisioning engine | `tofu version` | Lab A alternative |
| Python 3 | Local test harness | `python3 --version` | Lab B |
| VS Code | Editing and integrated terminal | `code --version` | Optional editor |
| WSL2 | Linux environment on Windows | `wsl --status` | Windows recommended |
| Ansible | Configuration automation | `ansible --version` | Optional |
| Docker | Reproducible local runtimes | `docker version` | Optional future labs |

Terraform and OpenTofu share many concepts, but are separate products. Confirm licensing, supported syntax, provider compatibility and organizational approval. Never switch binaries against the same state without an explicit migration plan.

## 3. Windows 11 and WSL2 installation
Open PowerShell as Administrator **only for WSL installation** when required:
```powershell
wsl --status
wsl --list --verbose
wsl --install -d Ubuntu
```
Restart Windows if prompted; start Ubuntu and create your Linux username. If WSL is already installed, skip installation. Verify `wsl --list --verbose` shows version 2. On managed laptops, virtualization, Windows features and installation permissions may require IT approval.

Inside Ubuntu:
```bash
sudo apt-get update
sudo apt-get install -y git curl unzip ca-certificates python3 python3-venv python3-pip
git --version
python3 --version
mkdir -p ~/src
cd ~/src
git clone https://github.com/sssamant21/platform-engineering-tutorials.git
cd platform-engineering-tutorials/infrastructure-as-code/labs/chapter-006
```
If cloned already, use the existing directory and `git pull --ff-only` only when your working tree is clean. On native Linux, use the distro's package manager and equivalent steps.

## 4. Install Terraform or OpenTofu safely
Use official installation guides:
- Terraform: https://developer.hashicorp.com/terraform/install
- OpenTofu: https://opentofu.org/docs/intro/install/
- Git: https://git-scm.com/downloads
- VS Code: https://code.visualstudio.com/docs/setup/setup-overview
- WSL: https://learn.microsoft.com/windows/wsl/install
- Ansible: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html

Prefer a vendor-signed package or a verified official repository with pinned approved versions. Avoid downloading arbitrary binaries or piping unknown internet scripts into a privileged shell. After installation:
```bash
command -v terraform || true
command -v tofu || true
terraform version   # if installed
tofu version        # if installed
```
On Windows PowerShell use `Get-Command terraform,tofu -ErrorAction SilentlyContinue` and `where.exe terraform` or `where.exe tofu`. Do not install both merely for this lab; one engine suffices.

## 5. VS Code and extensions
Install VS Code and the Remote - WSL extension on Windows. From Ubuntu, run `code .` to open the project in the WSL context; verify the bottom-left remote indicator. Add your organization's approved HCL/Terraform/OpenTofu, Python and YAML extensions. Use format-on-save only when its formatter is configured consistently with CI; do not let extensions auto-apply infrastructure.

Suggested workspace settings (`.vscode/settings.json`, optional):
```json
{
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,
  "editor.formatOnSave": false
}
```
Disable automatic credential collection and avoid pasting sensitive Terraform state or plans into editor assistants.

## 6. Environment, credentials and security
Use `git config --global user.name` and `git config --global user.email` for commit attribution, not authentication. GitHub SSH keys/tokens and cloud credentials are separate. Prefer SSO/OIDC and short-lived sessions; keep production roles off the developer machine when possible. Check `env | grep -E '^(AWS_|ARM_|GOOGLE_|TF_VAR_)'` only in a private shell; **never paste the values into logs**. Store secrets in approved credential stores, not shell profiles or `.tfvars` committed to Git.

Production guardrails: least privilege, isolated cloud profiles, no `sudo terraform apply`, pinned provider versions, protected state backend, policy gates, review of destructive plans, secure proxy/CA configuration, and an incident runbook for credential exposure.

## 7. Lab A — No-cloud IaC smoke test
Use `main.tf` in this lab directory; it uses built-in `terraform_data` and no cloud provider. From `labs/chapter-006`, select **one** engine and use it consistently:
```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=lab.tfplan
terraform apply lab.tfplan
terraform output -json
terraform plan -detailed-exitcode
terraform destroy
terraform state list
```
For OpenTofu replace `terraform` with `tofu` throughout. The first apply should create one local resource. The second plan should exit **0** (no changes); exit **2** indicates a diff and **1** an error. Confirm output contains `toolchain=ready` and `environment=lab`. After destroy, `state list` should be empty. PowerShell: inspect `$LASTEXITCODE` immediately after plan. Do not commit `lab.tfplan` or local state.

## 8. Lab B — Automated workstation audit
Run `python3 validate_toolchain.py workstation-manifest.json` (Windows native: `py -3 validate_toolchain.py workstation-manifest.json`). This stdlib-only audit checks declared tool names, checks for executables in PATH, runs safe version probes with timeouts, and emits PASS/WARN/FAIL. The manifest requires Git, Python and at least one of Terraform/OpenTofu; VS Code and Ansible are optional. An absent optional tool produces WARN, not failure. A missing required tool or missing IaC engine produces FAIL and exit code 1.

```bash
python3 validate_toolchain.py workstation-manifest.json
python3 -m unittest -v test_validate_toolchain.py
```
Use `python3 -m venv .venv` and `source .venv/bin/activate` for optional Python dependencies; do not install packages globally on managed Python environments. No third-party Python packages are required for this lab.

## 9. Lab C — Failure injection and recovery
1. **Missing binary:** change the manifest's optional VS Code command to `definitely-not-installed-ch006`. Expect WARN; restore it.
2. **Missing engine:** create a temporary manifest with `iac_engines` containing only a nonexistent command. Expect FAIL (exit 1); restore.
3. **Wrong PATH:** inspect `command -v terraform` and `echo "$PATH"` (PowerShell: `$env:PATH`); repair your shell profile or install location, not a system-wide unsafe symlink.
4. **Provider download failure:** test proxy, DNS, TLS certificates and vendor registry access; do not disable TLS verification.
5. **WSL2 unavailable:** inspect Windows feature status and virtualization settings; involve IT for managed hardware.
6. **Second plan differs:** check variable inputs, state directory, CLI version and files; do not apply blindly.

## 10. Production SRE / DBRE cases
**Case 1 — AWS EKS provisioning fails on one laptop:** Compare Terraform version, provider lockfile, AWS profile and OIDC role. Reproduce on a clean CI runner; do not patch production IAM to satisfy a local setup issue.

**Case 2 — Azure AKS CI succeeds but Windows shell fails:** Check WSL path, Azure CLI login context, subscription, proxy and CA certificates. Never embed a service principal secret in a `.tfvars` file.

**Case 3 — RDS plan unexpectedly replaces DB:** Stop. Confirm engine/provider versions, workspace and backend; inspect immutable fields and resource addresses. DBRE must approve migration and tested PITR/restore before any destructive action.

**Case 4 — Elasticsearch storage configuration drift:** A console hotfix changes IOPS. Capture metrics and incident decision, reconcile desired code through review; prevent automated reversal during incident mitigation.

**Case 5 — Git credentials leaked in logs:** Revoke token, rotate credentials, inspect audit events and scrub retained logs per incident policy. Git commit author email is not a secret; access tokens are.

**Case 6 — Provider registry outage:** Preserve dependency lockfile, use approved provider mirror/cache and retry; never bypass checksum verification.

## 11. Troubleshooting quick reference
| Symptom | Check | Safe remediation |
|---|---|---|
| `terraform: command not found` | `command -v terraform` | Install approved binary, fix PATH |
| `tofu: command not found` | `command -v tofu` | Install OpenTofu or use Terraform |
| `code .` fails in WSL | VS Code WSL integration | Open VS Code, install Remote WSL |
| `wsl --install` blocked | Windows features/IT policy | Request admin/virtualization enablement |
| `terraform init` TLS failure | CA, proxy, DNS | Install trusted CA / approved proxy |
| `terraform validate` fails | Syntax, CLI version | `fmt`, inspect error, fix config |
| `terraform plan` exits 2 | Changes detected | Review plan; not a failure |
| Python audit fails | PATH or missing required engine | Inspect FAIL output, reinstall safely |
| Git unsafe repository warning | File ownership | Fix ownership; don't blanket trust directories |
| State lock | Another active run | Coordinate before any unlock |

## 12. Operational runbooks
**New workstation:** verify OS/architecture → install WSL2 if needed → install approved tools → validate PATH and versions → clone repo → run audit/tests → run no-cloud smoke test → destroy → record versions.

**Broken toolchain:** capture `--version` and OS details without secrets → compare approved manifest and CI image → inspect PATH/proxy/CA → reinstall verified tool → rerun tests → document change.

**Credential exposure:** revoke and rotate → audit activity → update secret store → validate least privilege → document RCA/COA.

**Unsafe infrastructure plan:** stop pipeline → confirm correct account/workspace/state → compare plan to intended ticket → involve resource owner/DBRE → regenerate approved plan.

## 13. Acceptance and evidence
- [ ] Windows WSL2 or native Linux environment verified
- [ ] Git and Python installed and versions recorded
- [ ] Terraform or OpenTofu installed and version recorded
- [ ] VS Code/Remote WSL tested if used
- [ ] Workstation audit passes; optional WARNs documented
- [ ] Unit tests pass
- [ ] Terraform/OpenTofu init, validate, apply, no-change plan and destroy complete
- [ ] No credentials, state or plan artifacts committed
- [ ] Screenshot/log of versions and sanitized test outputs retained locally

Publication of this chapter does **not** imply its labs have been executed on the learner's workstation.

## 14. Knowledge check
Why prefer short-lived credentials? What is the difference between CLI, provider and module versions? Why protect the dependency lockfile? Why must production plans run under approved CI identity? What does plan exit 2 mean? Why is WSL2 useful for Ansible? Why are saved plans sensitive? What evidence is needed before an SRE change?

**Next:** Chapter 007 — IaC Repository Structure, Environment Isolation and Workspace Standards.
