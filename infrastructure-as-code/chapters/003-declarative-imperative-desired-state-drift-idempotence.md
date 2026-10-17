# Chapter 003 — Declarative vs Imperative IaC, Desired State, Drift and Idempotence

**Part 01:** Fundamentals and Architecture | **Audience:** DevOps, SRE, DBRE and Platform Engineers | **Level:** Beginner → Production Operations | **Cloud cost:** $0

## Learning objectives
- Compare declarative desired-state systems with imperative workflows.
- Explain convergence, idempotence, state, refresh, drift and controller ownership.
- Execute Terraform/OpenTofu and Ansible local labs safely.
- Write automated tests for a Python reconciliation loop.
- Diagnose and recover from drift without damaging production infrastructure.

## 1. Theory: desired vs actual state
**Desired state** is the configuration an operator intends (Git-managed code). **Observed/actual state** is what the provider or runtime reports. A reconciler compares the two and proposes or performs corrective actions. **State files** are not the same as actual state: Terraform state is an inventory of managed objects and attributes, and refresh/provider reads are needed to observe changes. **Drift** is a meaningful divergence between declared and observed infrastructure. Drift may be caused by console edits, emergency remediation, automation races, provider defaults, or unmanaged external systems.

**Declarative:** describe the end state and let an engine derive operations (Terraform, OpenTofu, Kubernetes manifests). **Imperative:** specify ordered steps (shell scripts, procedural API calls). Many real systems combine both: Ansible playbooks are ordered, but modules often enforce declarative resource properties.

**Idempotence:** running the same operation repeatedly produces the same effective result, without repeated side effects, assuming unchanged inputs and environment. It does not guarantee safety or correctness. **Convergence:** repeated reconciliation approaches the intended state. **Eventual consistency:** APIs may take time to reflect changes. **Drift detection:** read-only plan/compare and classification. **Drift remediation:** reviewed change to desired code or actual infrastructure.

## 2. Architecture
```text
                   Git / approved desired state
                               |
                         PR / CI checks
                               |
                  plan / diff / policy gates
                               |
                       approval boundary
                               |
            +------------------+------------------+
            |                                     |
     Terraform / OpenTofu                   Ansible modules
      state + provider reads                ordered task execution
            |                                     |
       cloud API resources                 host configuration
            +------------------+------------------+
                               |
                   observe / audit / monitor
                               |
                    drift triage + incident
                               |
                 code update OR safe remediation
```
Avoid competing reconcilers owning the same resource. For production, use versioned encrypted remote state, locking, least-privilege short-lived CI identity, policy checks, and change approvals. Never apply an unreviewed drift plan to a database or shared network.

## 3. Comparison and operational tradeoffs
| Dimension | Declarative | Imperative |
|---|---|---|
| Main input | Target state | Ordered operations |
| Typical diff | Plan or preview | Dry run / task output (tool dependent) |
| Repeatability | Engine seeks convergence | Author must ensure safe retries |
| Drift | Often first-class diff | Requires checks / desired-state modules |
| Failure recovery | Reconcile state + actual | Resume/retry with compensating steps |
| Main risk | Destructive inferred action | Partial execution / non-idempotent steps |

Example: `mkdir -p /tmp/example` is an idempotent imperative command; `mkdir /tmp/example` may fail on rerun. Terraform can be declarative yet propose destructive replacements. Do not equate declarative with automatically safe.

## 4. Lab prerequisites
Terraform >=1.5 or compatible OpenTofu, Python 3.9+, optional Ansible on Linux/macOS/WSL2. Verify `terraform version`, `python3 --version`, and `ansible --version`. Work in a new directory; no cloud account or secrets are needed. Use one IaC engine per state directory.

## 5. Lab A — Terraform desired state and idempotence
Use the supplied `labs/chapter-003/main.tf`:
```hcl
terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "Only lab and staging are allowed."
  }
}

resource "terraform_data" "desired" {
  input = {
    environment = var.environment
    owner       = "sre-platform"
  }
}

output "observed" {
  value = terraform_data.desired.output
}
```
Commands (run from `labs/chapter-003`):
```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=lab.tfplan
terraform show lab.tfplan
terraform apply lab.tfplan
terraform output -json
terraform plan -detailed-exitcode
```
The second plan should exit **0** (no changes). `-detailed-exitcode`: 0 no changes, 2 changes, 1 error. PowerShell: inspect `$LASTEXITCODE` immediately. Use `tofu` instead of `terraform` consistently if using OpenTofu; verify version compatibility.

### Controlled desired-state change
```bash
terraform plan -var='environment=staging' -out=staging.tfplan
terraform show staging.tfplan
terraform apply staging.tfplan
terraform output
terraform plan -var='environment=staging' -detailed-exitcode
```
Expect a proposed update to the local `terraform_data` input, then an idempotent no-change plan with the same variable. The action shape is engine-dependent; always inspect the actual plan. Reverting the input to `lab` proposes a change, illustrating that Git rollback is not an automatic runtime undo.

### Input guard
```bash
terraform plan -var='environment=production'
```
Expected: validation error. Do not apply. Finish by destroying using the same active input:
```bash
terraform destroy -var='environment=staging'
terraform state list
```
Expected: no managed resources listed. Protect the local state file even in a lab; production state may include secrets.

## 6. Lab B — Ansible convergence
Provided `inventory.ini` and `playbook.yml` configure only `/tmp/iac-chapter-003` on the local machine. Use WSL2/Linux/macOS:
```bash
ansible-playbook -i inventory.ini playbook.yml --check --diff
ansible-playbook -i inventory.ini playbook.yml
ansible-playbook -i inventory.ini playbook.yml
cat /tmp/iac-chapter-003/desired.txt
```
Expected first apply creates directory/file; second apply reports `changed=0`. Check mode may not predict file creation when the parent directory does not yet exist; a subsequent real apply and second idempotence run are the acceptance evidence. To simulate configuration drift:
```bash
printf 'owner=manual-edit\n' > /tmp/iac-chapter-003/desired.txt
ansible-playbook -i inventory.ini playbook.yml --check --diff
ansible-playbook -i inventory.ini playbook.yml
ansible-playbook -i inventory.ini playbook.yml
```
Expected: check reports correction, apply restores declared content, final run reports `changed=0`. Cleanup: `rm -rf /tmp/iac-chapter-003` **only after verifying the lab directory**. No elevated privileges required.

## 7. Lab C — Python drift detection and safe reconciliation
`reconcile.py` is a standalone stdlib tool with an explicit `--apply` flag. Without it, the tool is read-only and prints a drift report. It uses a sandbox path passed with `--path` and will refuse to write outside a directory named `iac-chapter-003-python`. Do not use this teaching script to manage production files.

```bash
python3 reconcile.py --path /tmp/iac-chapter-003-python/desired.txt
python3 reconcile.py --path /tmp/iac-chapter-003-python/desired.txt --apply
python3 reconcile.py --path /tmp/iac-chapter-003-python/desired.txt
printf 'owner=console-hotfix\n' > /tmp/iac-chapter-003-python/desired.txt
python3 reconcile.py --path /tmp/iac-chapter-003-python/desired.txt
python3 reconcile.py --path /tmp/iac-chapter-003-python/desired.txt --apply
python3 -m unittest -v test_reconcile.py
```
Exit codes: **0** desired state matches or apply succeeded; **2** drift detected in check mode; **1** invalid path or unexpected error. Read-only mode never writes. Cleanup only your dedicated lab directory.

## 8. Automated validation matrix
| Check | Command | Expected |
|---|---|---|
| Terraform syntax | `terraform validate` | exit 0 |
| Terraform idempotence | `terraform plan -detailed-exitcode` after apply | exit 0 |
| Terraform guard | plan with `environment=production` | nonzero |
| Ansible idempotence | second real playbook run | `changed=0` |
| Ansible drift correction | modify lab file then rerun | restored expected text |
| Python tests | `python3 -m unittest -v test_reconcile.py` | all pass |
| Python dry-run | check missing or changed lab file | exit 2, no writes |
| Python apply | `--apply` | exit 0, desired content |

## 9. Production SRE / DBRE incidents
**Case A — RDS instance class manually resized:** Cloud audit records show emergency scaling. Do not immediately revert with Terraform. Assess DB load, failover and maintenance impact; approve either code update to new size or scheduled restoration. Verify backups and SLOs.

**Case B — Elasticsearch disk class drift:** Operator increases IOPS outside Git during an incident. Capture Azure/AWS volume metrics, identify intended disk baseline, update code through PR if permanent, and prevent an automated apply from undoing emergency remediation.

**Case C — EKS security group conflict:** Terraform and a Kubernetes controller manage the same ingress rule. Stop repeated apply/reconcile loops; identify authoritative owner and migrate ownership before cleanup.

**Case D — Terraform state lock:** A runner terminates mid-apply. Confirm no live writer, inspect backend lease, state version and resource reality. Only force-unlock after coordination; never delete state as a quick fix.

**Case E — Ansible repeated restart:** A task using shell always reports changed and restarts Redis on every run. Replace with an idempotent module and notify handler only when config actually changes; test canary and availability.

**Case F — Drift scan with destructive plan:** A subnet or DB replacement appears in a plan. Block auto-apply, assess dependencies and data loss, inspect state addresses and provider schema, and open a change request.

## 10. Operational runbooks
### Drift detection
1. Execute read-only plan/preview with controlled identity; store sanitized summary.
2. Classify drift: authorized emergency, unauthorized change, provider normalization, stale state, or tool ownership conflict.
3. Assess blast radius, data persistence, service SLOs and rollback/restore options.
4. Open PR/change ticket; obtain approval before reconciliation.
5. Apply in maintenance window if disruptive; verify service and audit trail.

### Failed reconciliation
1. Stop concurrent runs and preserve sanitized logs.
2. Confirm provider API and backend/state health.
3. Inspect actual resource state; distinguish partial apply from stale reads.
4. Regenerate plan with current inputs; do not reuse outdated plans.
5. Repair under approval; test application health and document RCA/COA.

### Rollback and recovery
Git revert changes desired configuration, not historical physical state. Re-plan; validate delete/replace actions. For databases, use PITR/backups and application consistency checks when necessary. Document RPO/RTO and run DR drills.

## 11. Security, compliance and cost
Enforce state encryption/versioning/locking, least privilege and workload identity, no secrets in Git or plans, policy-as-code for destructive changes, resource ownership tagging, budget alerts, drift alerts and audit logs. Treat Terraform state as sensitive even when outputs are marked sensitive. This chapter's exercises have no cloud spend.

## 12. Troubleshooting
| Symptom | Likely cause | Resolution |
|---|---|---|
| Terraform CLI missing | PATH/install | Install CLI and reopen shell |
| Plan exit 2 | Changes proposed | Review diff; not a command failure |
| Unexpected Terraform change | Different `-var` or state | Align inputs and inspect state |
| Ansible `changed>0` on rerun | Non-idempotent task or drift | Inspect diff, replace shell tasks with modules |
| Ansible check mode incomplete | Parent path absent | Validate with real apply in lab |
| Python exit 2 | Drift in check mode | Inspect; use explicit `--apply` |
| Permission denied | Wrong directory ownership | Use lab-owned paths, never sudo reflexively |
| Drift remediation destructive | Replacement in plan | Stop and escalate for approval |

## 13. Knowledge check
1. How does desired state differ from Terraform state?
2. Can an imperative script be idempotent?
3. Why can a declarative apply still be destructive?
4. How does eventual consistency affect drift checks?
5. Why must only one controller own a resource?
6. How should an emergency DB change be reconciled?
7. What is the safe response to a stale Terraform lock?
8. What does plan exit code 2 mean?

## 14. Acceptance and next chapter
Completion requires clean Terraform validate/plan/apply/destroy, zero-change second plan, Ansible second run `changed=0`, Python tests passing, a drift remediation decision record, and confirmed cleanup. Live evidence must be collected by the learner; publishing files is not proof of execution.

**Next: Chapter 004 — IaC Lifecycle, Version Control, Git Workflows and Change Management.**
