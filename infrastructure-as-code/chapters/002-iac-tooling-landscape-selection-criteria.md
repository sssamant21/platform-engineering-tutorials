# Chapter 002 — IaC Tooling Landscape and Enterprise Selection Criteria

**Part 01:** Fundamentals and Architecture | **Audience:** SRE, DBRE, DevOps, Cloud and Platform Engineers | **Level:** Beginner to Intermediate | **Lab cost:** $0

## Learning objectives
After this chapter you can distinguish infrastructure provisioning, configuration management, application deployment and orchestration; evaluate Terraform, OpenTofu, Terragrunt, Ansible, Pulumi, AWS CloudFormation, Azure Bicep, and Kubernetes GitOps; use a reproducible scorecard; run safe local Terraform/OpenTofu and Ansible exercises; test idempotence and validate an IaC tool choice for production.

## 1. The problem and the categories
Infrastructure as Code (IaC) describes infrastructure in files that can be reviewed, versioned, tested, and deployed. It does not guarantee safety by itself. Infrastructure provisioning creates networks, compute, storage, IAM and managed databases. Configuration management changes software and OS settings inside existing hosts. Application deployment manages application release artifacts and runtime resources. GitOps continuously reconciles desired configuration from Git with a running platform.

**Declarative** systems express desired end state; **imperative** automation expresses a sequence of actions. These are design tendencies, not absolute labels: Ansible modules can be idempotent and Pulumi programs declare desired resources even though written in general-purpose languages.

| Tool | Main purpose | Configuration model | State / convergence | Typical strengths | Caveats |
|---|---|---|---|---|---|
| Terraform | Multi-cloud provisioning | HCL, declarative | Terraform state + plan/apply | Provider ecosystem, mature workflows | State security, provider quality, licensing review |
| OpenTofu | Multi-cloud provisioning | HCL, declarative | OpenTofu state + plan/apply | Open-source governance and familiar workflows | Verify compatibility before migration |
| Terragrunt | Orchestration / DRY layer | HCL wrapping Terraform/OpenTofu | Uses underlying engine states | Multi-environment composition and dependency orchestration | Added abstraction and version compatibility |
| Ansible | Configuration and task automation | YAML plays/tasks | Agentless execution, idempotence per module | OS configuration, patching, operational runbooks | Imperative task order, inventory and secret hygiene |
| Pulumi | Infrastructure provisioning | TypeScript, Python, Go, C#, Java, YAML | Managed state, preview/up | Shared languages, testing and abstractions | Runtime and dependency complexity |
| CloudFormation | AWS-native provisioning | JSON/YAML templates | AWS stack engine | AWS integration and change sets | AWS-specific; stack recovery |
| Bicep | Azure-native provisioning | Bicep templates compiled to ARM | Azure deployments | Azure-native modules, what-if | Azure-specific; deployment scopes |
| Kubernetes YAML/Helm | Cluster resources and packaging | YAML/templates | API-server desired state | Kubernetes native workloads | Not a substitute for cloud bootstrap |
| Argo CD / Flux | GitOps reconciliation | Git + K8s manifests | Continuous reconciliation | Drift detection and app delivery | Reconciliation and ownership boundaries |

**Licensing and governance:** Terraform's licensing terms changed from earlier open-source releases; verify the license for the version and intended commercial use. OpenTofu uses an open-source license. Terragrunt and other tools have their own licensing and support terms. Do not treat tooling as legally interchangeable without review.

## 2. Reference enterprise architecture
```text
Git repository / PR
   -> lint + unit tests + secret scanning + policy checks
   -> isolated plan/preview/what-if
   -> peer review + change ticket + approval
   -> CI runner with short-lived identity
        -> Terraform/OpenTofu/Pulumi/CFN/Bicep -> cloud resources
        -> Ansible -> operating system configuration
        -> Helm + Argo CD/Flux -> Kubernetes workloads
   -> state/backend/stack history (protected, versioned)
   -> observability, drift detection, audit and incident response
```

**Separation of responsibility:** Terraform may provision an EKS cluster and IAM roles; Ansible may configure bastion hosts; Helm packages Kubernetes applications; Argo CD reconciles application manifests. Avoid having multiple controllers own the same resource.

## 3. Enterprise evaluation framework
Score each tool from 1 (poor fit) to 5 (excellent fit) for your *specific workload*. Weights must sum to 100. Do not copy example scores as objective product rankings.

| Criterion | Weight | Evidence |
|---|---:|---|
| Cloud / resource coverage | 20 | Supported provider APIs, missing services |
| Security and identity | 15 | OIDC, least privilege, secret and state protection |
| Operational recovery | 15 | Locking, drift, backup, rollback, support |
| Testability and policy | 15 | Lint, tests, plan policies, approvals |
| Team skill / maintainability | 10 | Readability, onboarding, modules |
| Ecosystem / support | 10 | Documentation, integrations, lifecycle |
| Cost / licensing | 10 | Support, SaaS, runners, governance |
| Portability | 5 | Lock-in and migration complexity |

Weighted result = SUM(score × weight) / 100, yielding a value between 1 and 5. A high score does not override mandatory compliance or missing resource support.

### Selection heuristics
- Multi-cloud network, RDS, EKS, AKS and managed service provisioning: evaluate Terraform or OpenTofu first.
- AWS-only environments with strong AWS-native governance: compare CloudFormation with Terraform/OpenTofu.
- Azure-only organizations: evaluate Bicep alongside Terraform/OpenTofu.
- OS package updates and fleet remediation: use Ansible, often with a provisioning engine.
- TypeScript/Python-heavy developer platforms: evaluate Pulumi.
- Multiple Terraform/OpenTofu environments: consider Terragrunt if duplication and dependency orchestration justify it.
- Kubernetes app lifecycle: Helm/Kustomize with Argo CD or Flux, while keeping cluster bootstrap ownership clear.

## 4. Prerequisites and safe workspace
Install one of Terraform (version supporting terraform_data) or a compatible OpenTofu release; optionally install Ansible and Python 3. On Windows use WSL2 for Ansible; Terraform/OpenTofu work in PowerShell. Verify with `terraform version`, `tofu version`, `ansible --version`, `python3 --version`. This lab needs no cloud account or credentials. Run from `labs/chapter-002`, not an existing production state directory.

## 5. Lab A — Local provisioning with Terraform or OpenTofu
Create `main.tf` (also supplied in the repository):

```hcl
terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "Only lab or staging is allowed in this exercise."
  }
}

resource "terraform_data" "tool_selection" {
  input = {
    environment = var.environment
    tool_family = "declarative-provisioning"
    owner       = "sre-platform"
  }
}

output "selection" {
  value = terraform_data.tool_selection.output
}
```

Run with **one** engine only:
```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=selection.tfplan
terraform apply selection.tfplan
terraform output -json
terraform plan -detailed-exitcode
terraform destroy
```
For OpenTofu replace each `terraform` executable invocation with `tofu`; use a fresh directory/state when comparing engines, not both against the same live state. The exact CLI minimum-version requirement in this sample is Terraform-oriented; confirm your OpenTofu version supports the syntax. Expected: one resource created, output has `lab`, second plan exits 0, and destroy removes the resource. Exit 2 indicates planned changes; exit 1 indicates error.

## 6. Lab B — Ansible configuration-management simulation
Use `ansible-playbook -i inventory.ini playbook.yml --check --diff` to preview. Then `ansible-playbook -i inventory.ini playbook.yml` twice. The second run should report `changed=0` when the file is already correct.

**inventory.ini**
```ini
[local]
localhost ansible_connection=local
```

**playbook.yml**
```yaml
---
- name: Configure local SRE training artifact
  hosts: local
  gather_facts: false
  tasks:
    - name: Ensure lab directory exists
      ansible.builtin.file:
        path: /tmp/iac-chapter-002
        state: directory
        mode: "0755"

    - name: Render ownership record
      ansible.builtin.copy:
        dest: /tmp/iac-chapter-002/owner.txt
        content: "managed_by=ansible\nteam=sre-platform\n"
        mode: "0644"
```

Expected: first run creates the directory and file; second run makes no changes. Cleanup with `rm -rf /tmp/iac-chapter-002` only after verifying that path is the lab artifact. Do not run this lab with elevated privileges.

## 7. Lab C — Reproducible decision scorecard
The included `scorecard.py` uses Python's standard library. Run `python3 scorecard.py`; it prints weighted illustrative scores for three **hypothetical project profiles**. Scores are teaching examples, not authoritative tool rankings. Modify criteria, weights and scores based on your organization's measured evidence.

Run tests using `python3 -m unittest -v test_scorecard.py`. Acceptance: total weights equal 100; every score is between 1 and 5; result is within [1,5]; invalid weights/scores raise `ValueError`.

## 8. Production SRE / DBRE scenarios

### Case 1: AWS RDS provisioning
Use Terraform/OpenTofu or CloudFormation for instance class, subnet groups, parameter groups and monitoring. Use migration tooling for schema changes, not blind replacement of a database. Gate destructive plans and document backups, PITR, RPO/RTO and rollback. A plan proposing `-/+` for a database requires explicit data-loss analysis.

### Case 2: EKS/AKS cluster bootstrap
Provision cluster and IAM/identity with IaC; install cluster add-ons with clear ownership; deliver workloads with Helm and GitOps. Avoid Terraform and Argo CD independently managing the same Kubernetes objects. Validate cluster reachability and break-glass recovery.

### Case 3: OS fleet hardening
Ansible configures SSH, packages and monitoring agents on already provisioned instances. Stage changes, use `--check --diff`, limit hosts, canary, and verify compliance. Some modules cannot predict all check-mode behavior; test on staging before production.

### Case 4: State lock during incident
An apply fails and state remains locked. Verify active runs and backend leases, capture sanitized diagnostics, coordinate with on-call owner; force-unlock only after confirming the original run is terminated. Never delete state to fix a lock.

### Case 5: Drift after emergency hotfix
Compare actual infrastructure and code; determine if emergency change should become desired state. Generate a fresh plan and review impact. Automated reconciliation can reverse emergency changes, so define incident ownership and freeze procedures.

### Case 6: Cross-cloud disaster recovery
Do not assume portability means identical semantics. Compare RDS/Aurora vs Azure Database services, network models, IAM, quotas, encryption and backup recovery. Test restore, failover, DNS cutover and application integrity, not only provisioning success.

## 9. Troubleshooting
| Symptom | Likely cause | Safe investigation |
|---|---|---|
| `terraform` / `tofu` not found | CLI missing or PATH | Verify install and shell PATH |
| Provider init fails | Proxy, registry, version constraints | Inspect lockfile, DNS and version requirements |
| `ansible-playbook` missing | Ansible not installed | Install in Linux/WSL Python environment |
| Ansible check reports changes | Initial state differs | Apply in lab then rerun; inspect diff |
| Second Terraform plan has changes | Changed vars or drift | Check inputs and state; don't apply blindly |
| Cloud API 403 | Wrong role/scope/tenant | Inspect federation and least-privilege grants |
| Stack rollback failed | Resource dependency / policy | Examine events; use service-specific recovery |
| Pulumi preview differs from apply | Concurrent or external change | Refresh carefully and rerun reviewed preview |
| Two controllers fight over resource | Overlapping ownership | Define single writer and migration plan |

## 10. Production change runbooks
**Standard change:** ticket and ownership → PR → formatting and tests → static security scan → plan/preview/what-if → independent approval → short-lived identity → apply → health/SLO checks → evidence and audit.

**Failed apply:** stop concurrent jobs; inspect state and real infrastructure; identify partial resources; protect data; regenerate plan; obtain approval; reconcile; verify SLOs; write RCA/COA.

**Rollback:** reverting Git does not guarantee a safe rollback. Generate and review a new plan. Database deletion/replacement may require a tested backup restore and separate cutover procedure.

## 11. Security and FinOps acceptance
Protect state as sensitive, encrypt and version remote backends, require locking, segregate prod/staging identities, enforce policy-as-code, scan secrets, use workload identity federation, tag resources, set budget alerts, and validate teardown. Never commit `*.tfstate`, real secrets, plan artifacts or credentials.

## 12. Knowledge check
1. Why is Ansible not always a replacement for Terraform?
2. When is CloudFormation or Bicep preferable?
3. What additional complexity can Terragrunt introduce?
4. Why does an idempotent Ansible run matter?
5. What is the risk of two controllers owning one resource?
6. Why are example weighted scores not universal product rankings?
7. Why is Git rollback insufficient for a deleted database?
8. Which tests would you require before provisioning production RDS?

## 13. Completion criteria
- [ ] Terraform/OpenTofu `init`, `validate`, `plan`, `apply`, idempotence and `destroy` verified locally
- [ ] Ansible second run `changed=0`
- [ ] Python scorecard tests pass
- [ ] Tool decision documented with actual workload evidence
- [ ] Lab artifacts removed and sensitive output excluded

## Next
**Chapter 003 — Declarative vs Imperative IaC, Desired State, Drift and Idempotence.**
