# Chapter 061 — Ansible Foundations, Architecture, Inventory and Configuration Management

**Part 13 — Ansible (061–065) · Chapter 061/120**  
**Audience:** SRE, DBRE, DevOps, infrastructure and platform engineers.  
**Prerequisites:** Python 3.9+, ansible-core, a local POSIX shell; no cloud credentials required.  
**Execution boundary:** Labs target \`localhost\` with local connection and write only into a dedicated sandbox. Do not point examples at production without change approval and reviewed inventory.

## 1. Learning objectives

Explain Ansible's agentless architecture, control node, inventory, SSH/WinRM connection model, modules, collections, playbooks, tasks, handlers, variables, facts, templates, idempotence, check mode, diff, vault, roles and privilege escalation. Build reproducible inventories and run configuration changes safely, verify convergence, test unsafe changes, and prepare incident-response runbooks.

## 2. Architecture and operating model

~~~text
Git + PR + policy / CI
        |
 Ansible control node
 ansible-core + pinned collections
        |
 static/dynamic inventory
 groups, host vars, limits
        |
 transport: local / SSH / WinRM
        |
 managed hosts: Linux, Windows, Kubernetes jump hosts
        |
 service config + handler -> verification -> audit
~~~

Unlike Terraform/OpenTofu, Ansible is primarily procedural configuration and orchestration automation. It has no central resource state equivalent to Terraform state. Desired outcomes must be enforced by idempotent modules and tested assertions. Avoid overlapping ownership with Terraform, Kubernetes controllers and GitOps.

## 3. Core concepts

**Inventory:** host/group membership and connection settings; prefer explicit environments, ownership tags and inventory validation. Dynamic inventory plugins must be pinned and authenticated with least privilege. Do not mix prod and lab targets in the same default invocation.

**Variables and precedence:** define defaults in roles, environment values in inventory, and narrow runtime overrides; document precedence and avoid accidental extra-var overrides. Never put secrets in plaintext group_vars.

**Tasks and modules:** use \`ansible.builtin\` fully qualified names, explicit \`changed_when\`/\`failed_when\` when needed, and module arguments rather than shell commands for common operations. Tasks are sequential per host, but strategies, forks and serial affect execution.

**Handlers:** notify on a real change, restart services only when necessary. Verify readiness and rollback plans for stateful systems.

**Check mode and diff:** use as a preflight, not a guarantee; modules may not support check mode completely, and diff may leak secrets. Disable diff for sensitive tasks and protect CI logs.

**Security:** pin ansible-core and collection versions; use SSH certificates or short-lived identity, restricted \`become\`, vault/external secret manager, signed reviews and scoped inventory. No unattended production root privilege.

## 4. Repository layout

~~~text
labs/chapter-061/
  ansible.cfg
  inventory.ini
  playbooks/site.yml
  templates/service.conf.j2
  group_vars/all.yml
  policy.json
  fixtures/safe.json
  fixtures/unsafe.json
  ansible_gate.py
  test_ansible_gate.py
  run-preflight.sh
  runbook.md
  acceptance.md
~~~

## 5. Lab A — Ansible control node and inventory

~~~bash
cd infrastructure-as-code/labs/chapter-061
python3 -m pip install 'ansible-core>=2.16,<2.20'
ansible --version
ansible-inventory -i inventory.ini --list
ansible -i inventory.ini all -m ansible.builtin.ping
ansible-playbook -i inventory.ini playbooks/site.yml --syntax-check
ansible-playbook -i inventory.ini playbooks/site.yml --check --diff
ansible-playbook -i inventory.ini playbooks/site.yml
ansible-playbook -i inventory.ini playbooks/site.yml
~~~

Expected: inventory includes only local sandbox host; ping succeeds; first run creates a configuration file under \`./sandbox/\`; second run is idempotent (\`changed=0\`), unless a template or variable changed. The playbook uses a managed file and validation assertions, with no root access and no external services.

## 6. Lab B — Idempotence and drift

1. Record the SHA-256 of \`sandbox/service.conf\` after the first apply.
2. Run the playbook again and verify no changes.
3. Manually edit the sandbox file to simulate drift.
4. Run \`--check --diff\` and inspect proposed changes (safe here because no secrets).
5. Re-run the playbook and verify the original hash returns.
6. Change a variable in \`group_vars/all.yml\`; confirm the template is updated and handler fires only on change.

## 7. Lab C — Automated policy tests

~~~bash
python3 ansible_gate.py fixtures/safe.json policy.json
python3 ansible_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_ansible_gate.py
bash run-preflight.sh
~~~

The Python gate validates **declared** inventory, least privilege, scope, idempotence, approval, secrets and DBRE controls. A safe fixture passes; unsafe fails. This gate does not inspect actual Ansible AST or prove real SSH, host state, vault configuration or backup restoration.

## 8. Lab D — Production SRE/DBRE design exercise

Design a two-phase rolling configuration change: \`serial: 1\` for canary hosts, health verification, approved rollout, monitoring and rollback. For PostgreSQL, validate replication/backup before changes to \`postgresql.conf\`; for MongoDB, protect replica majority; for Redis, avoid simultaneous master/replica restarts; for Kafka, preserve ISR; for Elasticsearch, avoid disruptive rolling restarts during high disk watermarks. Use explicit \`--limit\` and approved inventory. Do not execute these exercises against live systems from this chapter.

## 9. Production incidents and troubleshooting

| Failure | Detection | Investigation | Safe response |
|---|---|---|---|
| Wrong inventory | unexpected host targets | \`--list-hosts\` | abort and restrict limit |
| SSH authentication failure | UNREACHABLE | identity/sshd/network | restore scoped access |
| Privilege escalation denied | permission error | become rules | request least privilege |
| Variable precedence error | wrong config | hostvars and group_vars | fix override source |
| Template syntax error | Jinja failure | syntax-check | repair and test |
| Non-idempotent shell task | repeated changed | task design | replace with module |
| Handler restart storm | service disruption | notifications/serial | canary and rollback |
| Secrets leaked in diff | CI alert | logs/artifacts | revoke/rotate |
| Ansible collection mismatch | module missing | requirements/version | pin and reinstall |
| Python interpreter mismatch | module failure | remote interpreter | set approved interpreter |
| PostgreSQL outage | DB health alert | restart/replication | stop rollout, DBRE |
| MongoDB election storm | primary changes | rolling strategy | preserve majority |
| Redis cache unavailability | latency/errors | failover/restarts | stop parallel restarts |
| Kafka ISR reduction | under-replicated partitions | broker health | freeze rollout |
| Elasticsearch slow search | queue/IOPS | storage/shard pressure | pause disruptive changes |
| Kubernetes GitOps drift | reconciliation loop | ownership | choose single writer |

## 10. Operational runbooks

**R1 Preflight:** pin toolchain/collections, validate inventory, \`--list-hosts\`, syntax-check, check mode, change approval and backups.

**R2 Authentication:** stop rollout, diagnose SSH/WinRM identity and privilege, restore scoped access without broad credentials.

**R3 Idempotence:** reproduce twice in sandbox, inspect changed status and module semantics, repair convergence.

**R4 Drift:** compare Git desired state to host, isolate unauthorized changes, review diff, reconcile by approved playbook.

**R5 DBRE change:** check quorum, replication, backup/PITR, connection pool and service SLO; use canary and serial rollouts.

**R6 Secret incident:** revoke leaked credential, remove logs/artifacts, rotate secret and audit vault use.

**R7 Rollback:** stop further hosts, restore last known-good config, validate health, document partial completion.

**R8 Post-change:** verify SLO, logs, config checksum, backup status, owner sign-off and incident notes.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Architecture, inventory and scoping | 20 |
| Playbooks, modules, variables and templates | 20 |
| Idempotence, check mode and drift recovery | 20 |
| Security, secrets and privilege controls | 15 |
| Automated tests and failure cases | 10 |
| SRE/DBRE scenarios, runbooks and handover | 15 |
| **Total** | **100** |

Pass >=85/100 and zero critical findings. Critical failures: wrong production target, leaked secret, uncontrolled restart, unapproved DB change or untested recovery. Publication and authored tests do not equal operational acceptance.

## 12. Exit criteria

Submit local playbook output, second-run idempotence evidence, negative tests, inventory scope proof, incident simulation record and reviewed runbook. Live multi-host, cloud and DBRE acceptance remain pending.

**Next proposed:** Chapter 062 — Ansible Playbooks, Roles, Variables, Templates and Reusable Automation.
