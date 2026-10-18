# Chapter 062 — Ansible Playbooks, Roles, Variables, Templates and Reusable Automation

**Part 13 — Ansible · Chapter 062/120 · Enterprise SRE/DBRE track**

## Outcomes and prerequisites
Build reusable roles with defaults, tasks, handlers, templates, and role interfaces. Understand playbook orchestration, inventory and variable precedence, handlers, loops, blocks/rescue/always, check mode, idempotence, vault and secret boundaries. Requires Python 3.9+, ansible-core >=2.16, localhost and a disposable lab. No cloud resources or root permissions required.

## Architecture
~~~text
Git/PR -> CI syntax/lint/test/policy -> protected approval
                                  |
                          Ansible control node
                           inventory (sandbox)
                                  |
                       playbooks/site.yml
                         roles/service_config
                 defaults -> tasks -> template -> handler
                                  |
                   localhost sandbox/service.conf
                                  |
                    idempotence + drift verification
~~~

**Ownership:** Terraform/OpenTofu provisions infrastructure; Ansible configures designated hosts; GitOps owns designated Kubernetes objects. No resource should have competing writers.

## Playbooks, roles and precedence
A play maps hosts to tasks and optionally roles. Roles package defaults, tasks, handlers, templates, files, vars and metadata for reuse. Defaults are intentionally low precedence; inventory, play, role and extra vars can override them under Ansible's detailed precedence rules. Avoid critical safety controls supplied as overridable extra vars. Name modules with FQCN \`ansible.builtin.*\`. Prefer declarative \`file\`, \`template\`, \`package\`, \`service\` to \`shell\` for convergence. Use \`notify\` handlers for actual changes, not every run. Use \`block/rescue/always\` for explicit failure handling; rescue does not magically roll back a partially completed play.

## Inventory and security
The runnable inventory is \`localhost ansible_connection=local\`. Inspect \`ansible-inventory --list\` and \`ansible-playbook --list-hosts\` before any run. Production requires separate inventory, \`--limit\`, SSH/WinRM identity, approval and \`serial\` rollout. Pin ansible-core/collections and dependencies. Secrets belong in vault or external secret managers, never in templates, group_vars plaintext or CI logs. \`--diff\` may expose secret values. \`become\` must be tightly scoped; the lab does not use it.

## Lab A — Role reuse and template
~~~bash
cd infrastructure-as-code/labs/chapter-062
python3 -m pip install 'ansible-core>=2.16,<2.20'
ansible-inventory -i inventory.ini --list
ansible-playbook -i inventory.ini playbooks/site.yml --syntax-check
ansible-playbook -i inventory.ini playbooks/site.yml --check --diff
ansible-playbook -i inventory.ini playbooks/site.yml
ansible-playbook -i inventory.ini playbooks/site.yml
~~~
The first run creates \`sandbox/service.conf\`; the second should report zero changes. The role's defaults define safe values; inventory can override service settings. A handler reports changes but does not restart a real service. The template is deterministic.

## Lab B — Idempotence, variables and drift
1. Record \`sha256sum sandbox/service.conf\`; rerun and confirm no changes.
2. Modify the sandbox file to simulate configuration drift.
3. Run \`--check --diff\` and review the proposed correction.
4. Apply the play and confirm the original hash returns.
5. Override \`service_port\` with a reviewed inventory value and verify template output.
6. Test an invalid privileged port and confirm the assertion rejects it.

## Lab C — Automated policy
~~~bash
python3 role_gate.py fixtures/safe.json policy.json
python3 role_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_role_gate.py
bash run-preflight.sh
~~~
The gate checks **declared evidence**, not the real playbook AST or host configuration. Safe must pass, unsafe must fail. The test suite mutates inventory, privilege, idempotence, role reuse, template security, approval and DBRE controls. A production CI gate must additionally run ansible-lint, vault checks, native playbook inspection, integration tests and review.

## Lab D — SRE/DBRE rolling automation design
Create a reviewed \`serial: 1\` canary plan for PostgreSQL config reload, MongoDB replica changes, Redis restart, Kafka broker configuration or Elasticsearch node settings. Require replication/quorum, backups/PITR, SLO, connection budget and rollback proof before executing any production change. Example \`examples/rolling-db.yml.example\` is **review-only** and performs no DB modifications. Use health checks between batches and stop on SLO burn-rate alert.

## Failure injection and troubleshooting
| Incident | Signal | Diagnosis | Containment |
|---|---|---|---|
| Wrong inventory | unexpected targets | list-hosts | stop and limit |
| Role not found | missing role | roles_path | pin location |
| Undefined variable | templating failure | defaults/inventory | fix contract |
| Variable precedence surprise | wrong rendered config | inventory/extra vars | remove unsafe override |
| Jinja escaping bug | invalid config | rendered output | template test |
| Handler restart storm | availability drop | notifications | change-only handler |
| Non-idempotent task | changed every run | task semantics | use module |
| Check mode misleading | differs from apply | module support | sandbox apply |
| Secrets in diff | CI leakage | artifact/log ACL | rotate/revoke |
| Privilege escalation | become denied | RBAC/sudo | least privilege |
| PostgreSQL reload outage | connection errors | PG logs/replication | stop and DBRE |
| MongoDB election storm | primary churn | replica health | one member at time |
| Redis failover | p99 spike | replication/pool | pause |
| Kafka ISR shrink | URP rises | broker status | freeze rollout |
| Elasticsearch IO pressure | search latency | shard/disk | defer restart |
| GitOps double ownership | repeated drift | controller audit | assign owner |

## Runbooks
**R1 Preflight:** pin Ansible/collections, review inventory/targets, syntax, check mode, backups, ticket and owner.

**R2 Variable incident:** inspect precedence and rendered config without revealing secrets; restore reviewed values.

**R3 Role failure:** verify role path, FQCN, handlers and dependencies; test in sandbox.

**R4 Idempotence/drift:** compare first/second runs, inject drift, reconcile and verify checksum.

**R5 DBRE change:** ensure quorum, PITR, replica lag, SLO and serial canary approval.

**R6 Secret incident:** revoke credentials, restrict logs, rotate and audit.

**R7 Partial rollout:** stop further batches, restore last-good config, check service and record changed hosts.

**R8 Post-change:** validate service SLO, drift, checksums, backups and handover.

## 100-point acceptance
| Domain | Points |
|---|---:|
| Playbook/role architecture and contracts | 20 |
| Inventory, variables and precedence | 15 |
| Templates, handlers and idempotence | 20 |
| Security, secrets and scope | 15 |
| Automated tests and negative cases | 15 |
| SRE/DBRE incidents and runbooks | 15 |
| **Total** | **100** |

Pass >=85 with no critical findings (wrong production target, leaked secret, unapproved DB restart, missing backup or uncontrolled privileged action). Evidence: inventory proof, syntax output, first and second playbook runs, drift correction, policy tests, DBRE game-day record. **Authored files are not evidence of live execution.**

**Next proposed:** Chapter 063 — Ansible Advanced Execution, Error Handling, Delegation and Rolling Operations.
