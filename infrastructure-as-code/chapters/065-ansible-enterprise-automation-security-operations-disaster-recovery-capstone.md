# Chapter 065 — Ansible Enterprise Automation, Security, Operations and Disaster Recovery Capstone

**Part 13 — Ansible · Chapter 065/120 · Enterprise SRE/DBRE capstone**

## Learning objectives

Integrate Chapters 061–064 into an enterprise-ready Ansible operating model: reusable roles, inventory trust, bounded rolling deployments, secret governance, change approval, automated policy, configuration drift, observability, backup/restore, incident response and operational handover. Design safe, auditable runbooks for PostgreSQL, MongoDB, Redis, Kafka, Elasticsearch/OpenSearch and Kubernetes platforms.

**Prerequisites:** Python 3.9+, ansible-core 2.16–2.19, POSIX shell, Chapters 061–064. **Scope:** all executable operations are confined to a disposable local sandbox. No production hosts, cloud credentials, root privileges or real secrets are required.

## 1. Enterprise reference architecture

~~~text
Git protected branch + change ticket + SRE/DBRE approval
                         |
         CI lint + test + policy + supply-chain gate
                         |
       pinned Ansible execution environment / runner
                         |
       trusted inventory snapshot + tenant allowlist
                         |
        secret broker / Vault (review-only integration)
                         |
     preflight -> canary -> health gate -> serial rollout
         |         |          |               |
     backup     handlers   SLO/quorum     audit/rollback
         |         |          |               |
     restore      drift      alert        handover
~~~

### Ownership boundaries
Terraform/OpenTofu provisions infrastructure; Ansible owns designated host configuration; GitOps controllers own their Kubernetes resources. Prevent simultaneous writers. Record inventory snapshot, owner, environment, change ticket, code revision, approval, artifact digest and recovery evidence.

### Production safeguards
Require least-privilege ephemeral credentials, pinned collections and roles, vault/external secrets, \`no_log\` for sensitive tasks, reviewed dynamic inventory, explicit \`--limit\`, check mode, canary \`serial: 1\`, bounded forks/retries, stop-on-failure, backups, PITR/restore drills, measured RPO/RTO, SLO and incident escalation. Check mode is not a guarantee and cannot replace sandbox integration testing.

## 2. Executable lab topology

~~~text
labs/chapter-065/
  ansible.cfg
  inventory/hosts.ini
  group_vars/all.yml
  playbooks/capstone.yml
  roles/capstone_config/
    defaults/main.yml
    tasks/main.yml
    handlers/main.yml
    templates/service.conf.j2
    meta/main.yml
  fixtures/{safe,unsafe}.json
  policy.json
  capstone_gate.py
  test_capstone_gate.py
  run-preflight.sh
  runbook.md
  acceptance.md
  sandbox/              # generated, ignored
~~~

The inventory defines two **logical hosts** \`canary_a\` and \`canary_b\`, both using \`ansible_connection=local\`. A role renders deterministic per-host configuration into \`sandbox/\`. A controlled failure injection on the first canary exercises rescue and fail-closed behavior. A backup/recovery simulation copies sandbox files to a separate local backup directory and verifies checksums; it is **not** proof of database PITR or remote disaster recovery.

## 3. Lab A — Preflight, safe apply and idempotence

~~~bash
cd infrastructure-as-code/labs/chapter-065
python3 -m pip install 'ansible-core>=2.16,<2.20'
ansible --version
ansible-inventory -i inventory/hosts.ini --list
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml --list-hosts
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml --syntax-check
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml --check --diff
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml
~~~

Capture first-run changes and verify the second run reports zero changes. Check that only the expected two sandbox files exist, and no external host or privilege escalation was used.

## 4. Lab B — Failure injection and rollback

~~~bash
# Deliberately fail canary_a; this must exit nonzero
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml -e inject_failure=true
# Inspect local failure marker and verify canary_b was not changed by the failing run
# Restore with an approved safe rerun
ansible-playbook -i inventory/hosts.ini playbooks/capstone.yml
~~~

Rescue records a failure marker then explicitly fails; it does not claim transaction rollback. The backup drill script snapshots configuration and restores only into the disposable sandbox. Verify checksums before and after restoration.

## 5. Lab C — Governance policy and unit tests

~~~bash
python3 capstone_gate.py fixtures/safe.json policy.json
python3 capstone_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_capstone_gate.py
bash run-preflight.sh
~~~

The gate validates **declared evidence**, not the Ansible AST, vault ciphertext, IAM policies, real host health or live database backups. Unsafe fixtures must fail closed. Production CI needs additional ansible-lint, collection provenance, secrets scanning, real inventory review, integration tests, SLO verification and approval checks.

## 6. Lab D — Recovery drill

~~~bash
bash backup-restore-drill.sh
~~~

The script checks for local sandbox files, copies them into an isolated temporary backup directory, verifies SHA-256 checksums, injects a local configuration drift and restores the original. It is deliberately limited to the local sandbox. For production RPO/RTO, separately test encrypted backup retrieval, database recovery and service readiness.

## 7. Production SRE/DBRE incident simulations

| Scenario | Trigger / signal | Containment and recovery |
|---|---|---|
| Wrong inventory | unexpected target count | abort, preserve inventory snapshot |
| Cross-tenant host | ownership mismatch | quarantine and review CMDB |
| Secret leak | token in CI output | revoke, rotate and restrict artifacts |
| Malicious collection | untrusted provenance | block runner, pin and audit |
| Stale inventory cache | missing/extra host | invalidate, re-review |
| Canary fails | health assertion | stop rollout, restore config |
| Handler storm | simultaneous restarts | serialize and verify SLO |
| Partial rollout | mixed host versions | reconcile inventory and plan |
| Retry storm | elevated API calls | bound attempts, circuit-break |
| Backup failure | missing restore artifact | block change, repair backup |
| PostgreSQL connection exhaustion | saturation | freeze rollout, DBRE |
| PostgreSQL replica lag | rising lag | halt reload/restart |
| MongoDB election storm | primary churn | preserve majority |
| Redis replication break | stale replica | stop and repair |
| Kafka ISR shrink | under-replicated partitions | freeze broker changes |
| Elasticsearch high disk watermark | IO pressure | defer restart |
| Kubernetes PDB blocks drain | eviction pending | review disruption budget |
| Vault credential compromise | audit alert | revoke and re-encrypt |
| CI identity compromise | anomalous runner | revoke OIDC trust |
| DR restore checksum mismatch | integrity failure | isolate backup and investigate |

## 8. Enterprise troubleshooting and runbooks

**R1 Preflight:** verify toolchain pins, inventory, owner, --list-hosts, change ticket, backup and SLO.

**R2 Security incident:** revoke compromised identities, rotate vault keys/secrets, quarantine CI artifacts, audit runner and collection provenance.

**R3 Canary failure:** stop later batches, record changed hosts, inspect failed assertion and obtain DBRE-approved recovery.

**R4 Partial rollout:** reconcile desired/current config, preserve audit evidence, re-plan with bounded serial batches.

**R5 Database recovery:** validate quorum, replication, backup/PITR, connection pools, RPO/RTO and service health before restart.

**R6 Drift:** detect unauthorized config change, review diff, apply reviewed source of truth, verify idempotence.

**R7 Backup/restore:** isolate recovery target, validate checksum, restore, measure RPO/RTO, and record approval.

**R8 Secrets:** use approved vault identities, restrict logs and artifacts, rotate and verify no residual disclosure.

**R9 Post-change:** verify service SLO, backups, cost, drift, monitoring and ownership handover.

**R10 Game-day escalation:** declare incident, establish incident commander, freeze automation, communicate blast radius and record COA/RCA.

## 9. Final 100-point assessment

| Domain | Points |
|---|---:|
| Architecture, roles, inventory and ownership | 15 |
| Security, Vault, supply chain and least privilege | 20 |
| Rolling orchestration, error handling and idempotence | 20 |
| Policy automation, tests and negative fixtures | 15 |
| Backup/restore, DR and RPO/RTO evidence | 15 |
| SRE/DBRE incidents, runbooks and handover | 15 |
| **Total** | **100** |

**Pass:** >=85/100, zero critical findings, signed SRE/DBRE/security acceptance. Critical failures include wrong production targeting, leaked credential, uncontrolled stateful restart, lost quorum, masked canary failure, unverified restore, or missing approval.

**Publication is not production acceptance.** The lab files and unit tests are authored; real Ansible execution, backup restore, DR metrics, SLO validation and game-day evidence must be collected independently.

## 10. Part 13 completion

Chapters 061–065 establish the Ansible enterprise track: fundamentals, reusable roles, rolling operations, security/dynamic inventory and a production reliability capstone. **Next:** Chapter 066 begins Part 14 — CloudFormation and Bicep (exact chapter title to be confirmed against the master roadmap).
