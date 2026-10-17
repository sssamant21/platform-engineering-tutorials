# Chapter 088 — Hands-on Lab: Ansible Roles, Dynamic Inventory and Jenkins Configuration Automation

**Safety:** Run only against `localhost` and `/tmp/jenkins-ansible-lab`. Cloud inventory examples are read-only design exercises unless explicitly approved.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Check ansible-core version | Output |
| 02 | Create role directory layout | Tree |
| 03 | Define role defaults | YAML |
| 04 | Create lab inventory | YAML |
| 05 | Render managed template | File |
| 06 | Add guard assertion | Test |
| 07 | Create role tasks | YAML |
| 08 | Create playbook | YAML |
| 09 | Run syntax check | Result |
| 10 | Preview inventory graph | Graph |
| 11 | Inspect target hosts | Output |
| 12 | Run first convergence | Recap |
| 13 | Run second convergence | Idempotence |
| 14 | Run check mode and diff | Diff |
| 15 | Simulate manual marker drift | Change |
| 16 | Detect and repair drift | Recap |
| 17 | Review AWS dynamic inventory design | Checklist |
| 18 | Review Azure dynamic inventory design | Checklist |
| 19 | Review secret/privilege controls | Report |
| 20 | Complete 100-point scorecard and COA | Sign-off |

## 12 failure drills

1. Missing Ansible collection.
2. Empty dynamic inventory.
3. Wrong environment tag.
4. Cloud API throttling.
5. SSH authentication failure.
6. Privilege escalation denial.
7. Missing role.
8. Undefined template variable.
9. Leaked secret in diff.
10. Non-idempotent task.
11. Unexpected restart handler.
12. Configuration drift from competing owner.

## Executable lab files

`inventories/lab/hosts.yml`:

```yaml
all:
  children:
    jenkins:
      hosts:
        localhost:
          ansible_connection: local
```

`roles/jenkins_config/defaults/main.yml`:

```yaml
---
jenkins_lab_home: /tmp/jenkins-ansible-lab
jenkins_lab_owner: sre
```

`roles/jenkins_config/tasks/main.yml`:

```yaml
---
- name: Restrict to disposable lab path
  ansible.builtin.assert:
    that:
      - jenkins_lab_home == '/tmp/jenkins-ansible-lab'

- name: Create lab config directory
  ansible.builtin.file:
    path: "{{ jenkins_lab_home }}/casc"
    state: directory
    mode: "0700"

- name: Render managed marker
  ansible.builtin.template:
    src: managed.txt.j2
    dest: "{{ jenkins_lab_home }}/casc/managed.txt"
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
- name: Configure disposable Jenkins lab
  hosts: jenkins
  gather_facts: false
  roles:
    - jenkins_config
```

## Execute and validate

```bash
ansible-inventory -i inventories/lab/hosts.yml --graph
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml --syntax-check
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml --check --diff
```

## Drift injection and repair

```bash
printf 'manual drift\n' > /tmp/jenkins-ansible-lab/casc/managed.txt
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml --check --diff
ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml
cat /tmp/jenkins-ansible-lab/casc/managed.txt
```

The marker should return to the templated contents.

## Evidence template

```text
UTC / lab owner:
Ansible version:
Inventory graph and target count:
Role defaults and guard:
Syntax and first/second runs:
Check mode and drift repair:
AWS/Azure inventory security review:
Secret/privilege controls:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Role structure and defaults validated.
- [ ] Inventory targets only localhost.
- [ ] Syntax check passes.
- [ ] First run converges.
- [ ] Second run is idempotent.
- [ ] Drift detected and repaired.
- [ ] Cloud inventory security reviewed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 088 — Ansible Roles, Dynamic Inventory and Jenkins Configuration Automation](../088-ansible-roles-dynamic-inventory-jenkins-configuration-automation.md).
