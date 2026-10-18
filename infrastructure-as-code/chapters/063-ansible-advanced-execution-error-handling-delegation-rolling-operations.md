# Chapter 063 — Ansible Advanced Execution, Error Handling, Delegation and Rolling Operations

**Part 13 — Ansible · Chapter 063/120 · SRE/DBRE operations**

## Objectives and scope

Master \`serial\`, forks, strategies, \`max_fail_percentage\`, \`any_errors_fatal\`, delegation, \`run_once\`, handlers, asynchronous tasks, \`block/rescue/always\`, retries, conditionals and controlled recovery. Implement safe canary orchestration, test idempotence and failure behavior, and develop production runbooks for stateful services. Prerequisites: Chapters 061–062, Python 3.9+, pinned ansible-core 2.16–2.19, local POSIX sandbox. No production inventory or cloud credentials are needed.

## 1. Enterprise architecture

~~~text
Protected Git -> CI lint/syntax/unit policy -> change/DBRE approval
                                             |
                                       Control node
                                             |
                           inventory + --limit + serial
                                             |
             preflight -> canary -> health gate -> next batch
                 |         |            |          |
              delegate  block/rescue   retries   handlers
                 |         |            |          |
             backup    incident log    SLO      audit/rollback
~~~

**Design principle:** Ansible's \`serial\` partitions target hosts into batches; \`forks\` controls concurrency within execution; \`strategy: linear\` synchronizes tasks per batch. \`run_once\` can execute once **per batch** with \`serial\`, not necessarily once per entire play. \`delegate_to\` changes where a task executes but does not automatically change the task's inventory ownership. Design delegated facts and \`delegate_facts\` carefully. \`block/rescue\` handles task failures but cannot undo external side effects or guarantee rollback.

## 2. Advanced execution controls

- **Batching:** \`serial: 1\` for sensitive canaries; percentages or lists for staged deployments. Ensure a load balancer and database quorum tolerate each batch.
- **Failure policy:** \`any_errors_fatal\` can abort further work after a fatal task; \`max_fail_percentage\` governs batch failure thresholds and uses strict comparison. Explicitly model unreachable hosts; rescue does not handle every unreachable or syntax error.
- **Retries:** \`until\` with \`retries\` and \`delay\` for bounded, observable transient failures. Avoid unbounded retry loops.
- **Async:** \`async\` plus \`poll\` for long operations; inspect async job status and timeouts, not just task launch.
- **Delegation:** delegate controller-side checks, load-balancer drain or approval checks with explicit authorization. Do not use \`delegate_to: localhost\` to bypass production inventory controls.
- **Handlers:** notify only on actual changes. A handler may not run if a host fails later; \`force_handlers\` has nuanced behavior and should not be used to conceal unhealthy hosts.
- **Error handling:** distinguish task errors, ignored errors, unreachable targets and rescued failures. Record partial state and require explicit recovery decisions.

## 3. Executable lab — Local canary with deliberate failure

The sandbox inventory defines two **logical** hosts, \`canary_a\` and \`canary_b\`, both using \`ansible_connection=local\`. The playbook uses \`serial: 1\`, a \`block/rescue/always\`, and writes host-specific files to \`sandbox/\`. The default \`inject_failure=false\` path succeeds and is idempotent. When \`inject_failure=true\`, the first host fails a deliberate assertion, rescue records a marker, then a final assertion stops the play. The second batch must not run when \`any_errors_fatal: true\` is applied to an unrescued failure. Do not interpret these logical localhost targets as real multi-host failover evidence.

~~~bash
cd infrastructure-as-code/labs/chapter-063
python3 -m pip install 'ansible-core>=2.16,<2.20'
ansible-inventory -i inventory.ini --list
ansible-playbook -i inventory.ini playbooks/rolling.yml --list-hosts
ansible-playbook -i inventory.ini playbooks/rolling.yml --syntax-check
ansible-playbook -i inventory.ini playbooks/rolling.yml --check --diff
ansible-playbook -i inventory.ini playbooks/rolling.yml
ansible-playbook -i inventory.ini playbooks/rolling.yml
# Deliberate negative test: expect nonzero, inspect sandbox markers
ansible-playbook -i inventory.ini playbooks/rolling.yml -e inject_failure=true
~~~

**Safety:** Run the failure-injection command only in this disposable local lab. Files are written under the lab's sandbox directory. Verify that second run reports \`changed=0\` before considering the lab complete. Inspect markers and changed counts rather than assuming a playbook's rescue path proves transaction rollback.

## 4. Policy and automated testing

~~~bash
python3 execution_gate.py fixtures/safe.json policy.json
python3 execution_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_execution_gate.py
bash run-preflight.sh
~~~

The Python gate checks **declared evidence**: inventory isolation, serial limits, explicit failure semantics, bounded retries, delegation review, approved rolling changes, DBRE readiness, backup and SLO controls. It is not an Ansible AST parser or proof of actual service health. Negative fixtures must fail closed.

## 5. SRE/DBRE operational scenarios

| Incident | Detection | Containment and recovery |
|---|---|---|
| Wrong inventory | unexpected \`--list-hosts\` | abort and restrict targets |
| Too many forks | API/SSH saturation | reduce forks and serial |
| Batch failure | failed hosts | halt subsequent batches; inspect partial state |
| Rescue masks failure | recap says rescued | add explicit post-rescue failure/health gate |
| Delegation targets wrong host | unexpected local action | review delegation and variables |
| \`run_once\` repeats | repeated per batch | explicit controller play or guarded condition |
| Handler restart storm | p99 and restarts | notify on changes; canary |
| Unreachable host | UNREACHABLE | treat separately from rescued task failures |
| Retry storm | repeated requests | bound attempts, jitter upstream, circuit break |
| Async orphan | lingering job | poll/cancel safely and audit |
| PostgreSQL connection exhaustion | active connections rise | stop rollout; pool budget and DBRE |
| MongoDB election churn | primary changes | preserve replica majority |
| Redis replication failure | stale replicas | stop parallel restarts |
| Kafka ISR shrink | under-replicated partitions | freeze broker rollout |
| Elasticsearch disk pressure | IO queue, high watermark | defer node restart |
| Kubernetes drain stall | PDB prevents eviction | pause and review disruption budget |
| Secrets in delegated logs | leaked credentials | revoke/rotate and restrict logs |
| Stale approval | change scope mismatch | reapprove revised plan |

## 6. Production design exercises

**PostgreSQL:** design a rolling parameter change with connection-budget checks, backup/PITR evidence, replica-lag gates, \`serial: 1\`, safe reload and post-change query latency. **MongoDB:** sequence secondary-first maintenance, preserve majority, verify election stability and oplog headroom. **Redis:** guard master/replica failover and client reconnect load. **Kafka:** preserve ISR, check controller/broker health between batches. **Elasticsearch/OpenSearch:** account for shard allocation, disk IO, write load and delayed rebalancing. These are review-only exercises; no production mutation commands are included.

## 7. Troubleshooting and operational runbooks

**R1 — Preflight:** verify pinned Ansible version, inventory, \`--list-hosts\`, \`--limit\`, syntax, check mode, backups, DBRE approvals and SLO.

**R2 — Canary failure:** stop future batches, record changed hosts, preserve logs, diagnose the first failure and obtain a reviewed recovery plan.

**R3 — Delegation:** confirm where delegated tasks run, variable context, credentials, authorization and any \`delegate_facts\` effects.

**R4 — Retry/async:** inspect retry budget, job IDs, timeouts and external side effects; do not launch duplicate destructive work.

**R5 — Rescue:** ensure rescue never silently marks a broken service healthy; assert readiness after recovery and fail the play if necessary.

**R6 — Database rollout:** verify quorum, replication lag, PITR, connection pools, latency SLO and a DBRE-approved stop condition.

**R7 — Security:** rotate leaked secrets, restrict CI artifacts, audit delegated credentials and prevent plaintext logs.

**R8 — Recovery:** restore last-known-good configuration, reconcile partially changed hosts, recheck SLO and document the incident.

**R9 — Post-change:** verify idempotence, host state, monitoring, backup success, drift and signed handover.

## 8. 100-point acceptance

| Domain | Points |
|---|---:|
| Execution architecture, serial/forks/strategy | 20 |
| Delegation, retries, async and handlers | 15 |
| Error handling, rescue and failure containment | 20 |
| Security, inventory and change controls | 15 |
| Automated tests and negative injection | 15 |
| SRE/DBRE game days, runbooks and recovery | 15 |
| **Total** | **100** |

Pass **>=85/100** with zero critical findings. Critical: unintended production targets, unapproved stateful restart, lost database quorum, secret leak, failure masked as success or missing restore plan. Acceptance requires actual local playbook logs, first/second-run idempotence, failure-injection evidence, policy test output and reviewed DBRE runbook. Publication alone does not satisfy live acceptance.

**Next proposed:** Chapter 064 — Ansible Security, Vault, Dynamic Inventory and Enterprise Automation Governance.
