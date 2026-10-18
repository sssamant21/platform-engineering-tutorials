# Chapter 064 — Ansible Security, Vault, Dynamic Inventory and Enterprise Automation Governance

**Part 13 — Ansible · Chapter 064/120 · Enterprise SRE/DBRE**

## Outcomes and prerequisites

Design a defensible Ansible automation control plane with least-privilege identities, Vault and external secrets, dynamic inventory trust boundaries, signed/reviewed collections, CI/CD gates, protected execution environments, inventory tenancy, auditability and safe database change governance. Prerequisites: Chapters 061–063, Python 3.9+, ansible-core 2.16–2.19 and a local disposable sandbox. The runnable lab requires no cloud credentials, production inventory or real secrets.

## 1. Reference architecture

~~~text
Git protected branch / PR / change ticket
               |
     CI lint + tests + security scan
               |
   signed/pinned execution environment
               |
    short-lived runner identity + RBAC
               |
      inventory plugin / CMDB / tags
               |
     inventory scope + policy gate
               |
       Ansible control node
               |
   Vault/external secret injection (runtime)
               |
      canary -> health -> serial rollout
               |
     audit / SLO / backup / DBRE approval
~~~

**Trust boundaries:** the inventory source and filters determine the blast radius; credentials determine effective privilege; collection/module provenance determines code trust; logs, facts, callback plugins and diff output can disclose secrets. Every boundary requires independent controls. Never treat a user-supplied inventory file, a dynamic inventory script or a policy fixture as authoritative proof of production safety.

## 2. Ansible Vault and secrets lifecycle

Ansible Vault encrypts files/variables **at rest**; it is not a secrets manager, key-rotation service, access broker or guarantee against runtime disclosure. Use an approved vault identity mechanism or an external secret manager, with key ownership, rotation, backup and break-glass controls. Avoid plaintext passwords, token-bearing \`--extra-vars\`, environment leaks and world-readable vault password files. Use \`no_log: true\` on sensitive tasks, minimize registered data and disable diff for secrets. Be aware \`no_log\` does not protect arbitrary custom callbacks or privileged host access.

**Safe rehearsal:** create a disposable encrypted example only with a locally supplied password file stored outside the repository; do not commit encrypted production material, the password file or decrypted outputs. The included executable lab deliberately uses a **non-secret placeholder** and does not create vault ciphertext.

## 3. Dynamic inventory security and tenancy

Use approved collection inventory plugins and pinned versions; restrict cloud API identity to read-only discovery. Filter by explicit account, region, environment, tenant and owner. Inventory cache must have TTL, access control and invalidation strategy. Validate host count, naming and group membership before running; require \`--limit\`, approval and allowlist. Protect against tag spoofing, account drift, cross-tenant discovery, stale cache and malformed JSON. The lab's \`inventory/dynamic_inventory.py\` is a deterministic local script (not cloud discovery) and rejects unknown arguments; it returns two logical local targets.

## 4. Supply-chain, execution and governance

Pin ansible-core, collections, roles and Python dependencies. Verify trusted artifact provenance, signatures or digests as appropriate, scan collections and execution environments, restrict callback/plugins, protect CI runners, use workload identity and enforce environment approvals. Prefer immutable, reviewed execution images. Use dedicated service identities, least privilege \`become\`, host key verification and controlled privilege escalation. Segregate duties: author, reviewer, deployer, DBRE approver and incident commander. Log change ticket, exact inventory snapshot, commit, artifact digest, target count, plan/check output, execution result and recovery evidence.

## 5. Executable Lab A — Dynamic inventory and read-only preflight

~~~bash
cd infrastructure-as-code/labs/chapter-064
python3 -m pip install 'ansible-core>=2.16,<2.20'
python3 inventory/dynamic_inventory.py --list
ansible-inventory -i inventory/dynamic_inventory.py --list
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml --list-hosts
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml --syntax-check
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml --check
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml
ansible-playbook -i inventory/dynamic_inventory.py playbooks/security.yml
~~~

The playbook targets only two local logical hosts with \`connection: local\`, \`serial: 1\`, and creates host-specific, non-secret policy markers in \`sandbox/\`. The second apply should be idempotent. The playbook validates scope and never escalates privileges.

## 6. Executable Lab B — Policy and negative tests

~~~bash
python3 governance_gate.py fixtures/safe.json policy.json
python3 governance_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_governance_gate.py
bash run-preflight.sh
~~~

The policy gate evaluates **declared evidence** for inventory trust, secret hygiene, execution identity, approvals, provenance and DBRE recovery. It does not parse the real playbook, decrypt Vault files, verify IAM permissions or prove actual backup restores. Unsafe and cross-tenant fixtures must fail closed.

## 7. Lab C — Threat model and game-day

Create a threat model for: compromised CI runner; stolen vault password; malicious collection; inventory tag spoofing; stale inventory cache; cross-account targeting; \`become\` escalation; untrusted PR workflow; secrets in callback output; partial database rollout; backup restore failure. For each, identify detection, blast radius, credential revocation, containment, rollback and audit owner. Simulate these in the offline fixtures, not by using live credentials.

## 8. Production SRE/DBRE scenarios

| Scenario | Detection | Containment and recovery |
|---|---|---|
| Dynamic inventory expands into prod | target count mismatch | stop, freeze inventory snapshot |
| Inventory cache stale | absent/new hosts | invalidate cache and re-review |
| Tag spoofing | unexpected tenant group | verify account/owner against CMDB |
| Vault password leaked | audit alert | revoke/rotate, re-encrypt secrets |
| \`no_log\` omitted | token in CI output | restrict logs, rotate secret |
| Collection supply-chain compromise | digest mismatch | block execution, quarantine |
| CI runner compromised | anomalous identity use | revoke workload identity |
| Privilege escalation | unexpected sudo | remove privilege and audit |
| SSH host key mismatch | connection refused | investigate MITM or rebuild |
| Cross-tenant inventory | host count deviation | reject environment |
| Untrusted PR obtains credentials | access log | revoke, isolate runner |
| PostgreSQL config leak | credentials exposed | rotate DB credentials |
| MongoDB replica rollout | election storm | halt, preserve majority |
| Redis restart storm | p99 latency | freeze batch, check replicas |
| Kafka broker changes | ISR shrink | stop and restore broker health |
| Elasticsearch disk pressure | queue/IOPS | defer restart, capacity remediation |
| Failed backup/PITR | restore drill fails | block deployment, repair backup |
| Ansible callback exfiltration | outbound traffic | disable plugin, rotate identity |

## 9. Troubleshooting and runbooks

**R1 Inventory preflight:** capture inventory JSON, validate account/tenant/region, host count, owner, --list-hosts, --limit and approval.

**R2 Vault incident:** stop execution, revoke compromised keys, rotate dependent secrets, audit logs and re-encrypt using approved process.

**R3 CI identity incident:** revoke OIDC/runner trust, isolate artifact access, inspect provenance and restore signed runner image.

**R4 Supply-chain:** pin and verify collection/role digests, quarantine untrusted dependencies and reproduce in sandbox.

**R5 Privilege escalation:** inspect become rules, host identity and task scope; remove excess rights before retry.

**R6 DBRE rollout:** verify backups/PITR, replication/quorum, connection pool, SLO and canary approvals; stop on health regression.

**R7 Secrets in logs:** restrict artifacts, revoke/rotate credentials, review callback/no_log settings and retention.

**R8 Cross-tenant targeting:** freeze playbook, inventory snapshot and access; reconcile ownership and approval.

**R9 Post-change:** verify host state, SLO, backup, drift, credential audit, incident notes and owner handover.

## 10. 100-point assessment

| Domain | Max |
|---|---:|
| Identity, RBAC, privilege and secret design | 20 |
| Vault lifecycle and secret disclosure prevention | 15 |
| Dynamic inventory trust, scope and tenancy | 20 |
| Supply chain, CI/CD and governance | 15 |
| Automated tests and negative scenarios | 15 |
| SRE/DBRE incidents, runbooks and recovery | 15 |
| **Total** | **100** |

Pass >=85/100 and zero critical findings. Critical: leaked production credential, cross-tenant execution, unreviewed privilege escalation, untrusted collection execution, unapproved DB restart or missing verified backup. Evidence requires real test logs, inventory proof, negative scenarios, credential rotation drill and reviewer sign-off.

**Next proposed:** Chapter 065 — Ansible Enterprise Automation, Security, Operations and Disaster Recovery Capstone.
