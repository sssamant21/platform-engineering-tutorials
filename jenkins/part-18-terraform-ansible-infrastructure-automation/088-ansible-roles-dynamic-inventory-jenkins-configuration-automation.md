# Chapter 088 — Ansible Roles, Dynamic Inventory and Jenkins Configuration Automation

**Part 18 — Terraform, Ansible and Infrastructure Automation**  
**Audience:** SRE/DBRE, DevOps, platform and security engineers  
**Prerequisites:** Chapters 086–087, Python 3, ansible-core, disposable Linux or WSL lab, Git and optional Jenkins LTS test controller.

## Learning objectives

Design reusable Ansible roles, discover Jenkins infrastructure through inventory plugins, converge controller configuration idempotently, secure secrets, test changes and troubleshoot failed automation without jeopardizing controller state.

## 1. Architecture and ownership boundaries

```text
Git PR → ansible-lint / syntax / policy / approval
                        |
        inventory (Terraform outputs / cloud plugin)
                        |
                 inventory groups
                        |
      roles: baseline → java → controller → jasc
                        |
          handlers + validated templates
                        |
            Jenkins LTS (single writer)
                        |
         synthetic CI + drift + audit
```

Terraform provisions infrastructure; Ansible configures operating systems and services; JCasC configures Jenkins internals. Do not manage the same settings from multiple competing controllers.

## 2. Repository structure

```text
jenkins-ansible/
  ansible.cfg
  inventories/
    lab/hosts.yml
    aws/aws_ec2.yml
    azure/azure_rm.yml
  group_vars/jenkins.yml
  roles/
    jenkins_config/
      defaults/main.yml
      tasks/main.yml
      handlers/main.yml
      templates/managed.txt.j2
  playbooks/site.yml
  tests/
    verify_lab.py
  requirements.yml
```

Pin ansible-core, collections and roles to reviewed versions. Inventory files may expose internal hostnames and topology; treat them as sensitive operational metadata.

## 3. Inventory models

Static inventory:

```yaml
all:
  children:
    jenkins:
      hosts:
        localhost:
          ansible_connection: local
```

Dynamic inventory discovers hosts using cloud APIs or Terraform-produced metadata. Prefer collection-supported inventory plugins over ad hoc shell scraping. Tag or label hosts with environment, role and ownership and require explicit filtering.

AWS EC2 inventory **illustrative**:

```yaml
plugin: amazon.aws.aws_ec2
regions:
  - us-east-1
filters:
  tag:Role: jenkins-controller
  instance-state-name: running
keyed_groups:
  - key: tags.Environment
    prefix: env
```

Azure RM inventory **illustrative**:

```yaml
plugin: azure.azcollection.azure_rm
include_vm_resource_groups:
  - REPLACE-JENKINS-RG
auth_source: auto
conditional_groups:
  jenkins_controller: "'jenkins-controller' in (tags.Role | default(''))"
```

Check the exact inventory-plugin schema and version before use; cloud plugin capabilities and authentication vary. Use short-lived cloud identity, least privilege, API rate limits and explicit environment scoping. Avoid accidental production targeting.

## 4. Reusable role interface

`roles/jenkins_config/defaults/main.yml`:

```yaml
---
jenkins_lab_home: /tmp/jenkins-ansible-lab
jenkins_lab_marker: managed.txt
jenkins_lab_owner: sre
```

`roles/jenkins_config/tasks/main.yml`:

```yaml
---
- name: Guard against unsafe lab path
  ansible.builtin.assert:
    that:
      - jenkins_lab_home == '/tmp/jenkins-ansible-lab'
      - jenkins_lab_marker == 'managed.txt'
    fail_msg: "This lab role may write only to the disposable lab path."

- name: Create Jenkins lab config directory
  ansible.builtin.file:
    path: "{{ jenkins_lab_home }}/casc"
    state: directory
    mode: "0700"

- name: Render managed marker
  ansible.builtin.template:
    src: managed.txt.j2
    dest: "{{ jenkins_lab_home }}/casc/{{ jenkins_lab_marker }}"
    mode: "0600"
```

`roles/jenkins_config/templates/managed.txt.j2`:

```jinja2
Managed by Ansible
Owner: {{ jenkins_lab_owner }}
```

`playbooks/site.yml`:

```yaml
---
- name: Converge disposable Jenkins lab configuration
  hosts: jenkins
  gather_facts: false
  roles:
    - jenkins_config
```

This role is **intentionally local and non-destructive**. It does not install, restart or configure a real Jenkins controller.

## 5. Execute and prove idempotence

```bash
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml --syntax-check
ansible-inventory -i inventories/lab/hosts.yml --graph
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml --check --diff
cat /tmp/jenkins-ansible-lab/casc/managed.txt
```

Expected: the second run reports no changes for converged tasks. A role that always reports changed without a real state difference undermines drift detection and handler safety.

## 6. Role composition for production

Typical roles:
- `jenkins_os_baseline`: users, filesystem, time sync, TLS trust, audit and patch controls.
- `jenkins_java`: supported Java runtime, pinning and JVM settings.
- `jenkins_controller`: pinned Jenkins package/image, service unit, ownership and health.
- `jenkins_plugins`: reviewed plugin manifest and dependency validation.
- `jenkins_jasc`: validated JCasC file and secure secret references.
- `jenkins_monitoring`: metrics, logs and alerting.
- `jenkins_backup`: consistent backup integration and restore evidence.

Use handlers for controlled restarts, with explicit maintenance windows and single-writer checks. Never trigger a production restart merely because a harmless template timestamp changed.

## 7. Dynamic inventory validation

```bash
ansible-inventory -i inventories/lab/hosts.yml --list
ansible-inventory -i inventories/lab/hosts.yml --graph
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml --list-hosts
```

For cloud inventory, run `ansible-inventory -i inventories/aws/aws_ec2.yml --graph` or Azure equivalent only after credentials and collection configuration are approved. Verify target counts and environment tags before running any mutating playbook.

## 8. Secrets and privilege boundaries

Use a cloud secret manager or approved Ansible Vault workflow; do not store Jenkins administrator passwords or private keys in inventory. `no_log: true` protects task output but does not sanitize remote temporary files, callback plugins or all external logs. Prefer workload identity and delegated permissions over static access keys. Restrict `become` and allowlisted commands.

## 9. Safe rollout strategy

1. Run syntax, lint and secret scans.
2. Preview inventory and target count.
3. Execute check mode and review diff.
4. Verify backup/restore readiness.
5. Converge canary staging controller.
6. Run synthetic login, SCM, Pipeline and agent checks.
7. Obtain approval for production.
8. Apply to one controller at a time with writer fencing.
9. Monitor health and roll back compatible configuration when required.
10. Record change evidence, RCA/COA and reviewer sign-off.

Check mode is a useful preview, not a guarantee that a real apply will succeed.

## 10. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Inventory plugin unavailable | collection install |
| 02 | Cloud inventory empty | region/filter/identity |
| 03 | Wrong environment targeted | tags/groups |
| 04 | API throttling | inventory cache/rate |
| 05 | SSH handshake fails | identity/network |
| 06 | Host key mismatch | host authenticity |
| 07 | Become denied | sudo policy |
| 08 | Role not found | roles_path |
| 09 | Variable precedence surprise | group/host/extra vars |
| 10 | Template undefined variable | defaults |
| 11 | Template exposes secret | diff/no_log |
| 12 | File permissions too broad | mode/owner |
| 13 | Repeated changed status | idempotence |
| 14 | Handler restarts unexpectedly | notifications |
| 15 | Jenkins Java unsupported | compatibility matrix |
| 16 | Plugin dependency failure | pinned versions |
| 17 | JCasC schema invalid | config validation |
| 18 | Controller starts twice | fencing |
| 19 | Agent fails to connect | remoting/TLS |
| 20 | Drift recurs after apply | competing owner |

## 11. Six production runbooks

### A. Dynamic inventory discovery failure
Inspect plugin/collection version, cloud identity, region, filters, cache and API throttling; block playbook until targets are verified.

### B. Unexpected host targeting
Stop rollout, preserve inventory output and change logs, validate tags and host limits, correct scoping and rerun approval.

### C. Role convergence failure
Identify first failed task, privileges and variable sources; repair idempotently, rerun check and apply in staging.

### D. Jenkins restart or JCasC regression
Pause rollout, preserve logs and config, validate single writer and restore compatible known-good configuration or backup.

### E. Secret disclosure
Revoke/rotate affected secrets, preserve audit evidence, fix logging/template handling and escalate security incident.

### F. Configuration drift
Identify authoritative source, detect manual edits or competing controllers, reconcile with owner approval and revalidate synthetic CI.

## 12. Acceptance scorecard

| Domain | Points |
|---|---:|
| Role design and reusable interfaces | 20 |
| Inventory security and target scoping | 20 |
| Idempotence, check mode and validation | 20 |
| Jenkins compatibility and safe restart | 15 |
| Secrets, privilege and policy controls | 15 |
| Runbooks, drift and audit evidence | 10 |
| **Total** | **100** |

Suggested pass 85/100 plus mandatory gates: verified inventory scope, no secrets in output, idempotent convergence, no unsafe controller restart, and synthetic CI acceptance.

## 13. Evidence template

```text
UTC / change owner:
ansible-core and collection versions:
Inventory source, target count and scope:
Role version and defaults:
Syntax/lint/check/diff:
First and second apply changes:
Secret/privilege review:
Jenkins core/Java/plugins/JCasC:
Backup and restart guard:
Synthetic CI/agents/RBAC:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 088 hands-on lab](labs/088-ansible-roles-dynamic-inventory-jenkins-configuration-automation-check.md).  
**Next:** Chapter 089 — Jenkins GitOps Infrastructure Pipelines, Drift Detection and Automated Compliance.
