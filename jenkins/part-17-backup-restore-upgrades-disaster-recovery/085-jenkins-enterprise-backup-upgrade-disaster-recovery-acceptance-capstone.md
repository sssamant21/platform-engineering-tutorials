# Chapter 085 — Jenkins Enterprise Backup, Upgrade and Disaster Recovery Acceptance Capstone

**Part 17 — Backup, Restore, Upgrades and Disaster Recovery (final capstone)**  
**Audience:** Jenkins SRE/DBRE, platform, security, cloud DR, change managers and service owners  
**Prerequisites:** Chapters 081–084, isolated Jenkins LTS, immutable verified backup, separate restore target, pinned image/plugins/JCasC and synthetic CI.

## Mission

Prove that Jenkins can be backed up consistently, upgraded safely, recovered across a failure domain and returned to service within approved recovery objectives—without violating single-writer safety or exposing credentials.

**Scope:** This is an executable **lab plan** and acceptance standard, not evidence that any environment has already passed. Run fault injection only in approved disposable infrastructure.

## 1. End-to-end reference architecture

```text
  SCM/webhooks → primary ingress → Jenkins controller A
                                       |
                                 single writable home
                                       |
                      consistent encrypted backup + manifest
                                       |
                        immutable/versioned storage
                                       |
                         cross-region/account copy
                                       |
                        isolated recovery storage
                                       |
                   controller B (normally stopped/fenced)
                                       |
                       DR agents + synthetic Pipeline
                                       |
                   measured RPO/RTO + audit + failback
```

Controller images, Jenkins core, Java, plugins and JCasC must be compatible as a tested set. The DR region must have functioning identity, DNS, SCM, artifact repository, secrets/key access and compute quotas.

**Never run two Jenkins controllers against the same writable `JENKINS_HOME`.** Jenkins OSS does not provide generic active-active shared-home HA. Network reachability loss is not proof of fencing.

## 2. Recovery objectives and success criteria

Illustrative objectives (service owner must approve actual values):

| Objective | Example | Evidence |
|---|---|---|
| RPO | <=15 minutes | latest verified durable marker |
| RTO | <=60 minutes | outage to validated critical CI |
| Backup freshness | within approved interval | last verified backup timestamp |
| Integrity | 100% selected objects pass SHA-256 | checksum logs |
| Encryption | at rest/in transit and key recovery | policy and decrypt test |
| Upgrade | critical synthetic Pipelines pass | staging/production smoke |
| Single-writer | exactly one authorized writer | infrastructure fencing proof |
| Security | positive and negative RBAC tests | audit evidence |

RTO includes decision, fencing, provisioning, restore, startup, dependency validation, agents, SCM, artifacts and synthetic Pipeline. RPO is **not** simply the nominal backup schedule; record actual recoverable state.

## 3. Required artifacts

- Recovery dependency inventory and RACI.
- Approved RPO/RTO and fault-injection scope.
- Pinned core/Java/plugin/JCasC/controller image manifest.
- Consistent backup ID, checksum, encryption/key custody and retention evidence.
- Restore procedure and independent isolated target.
- Upgrade compatibility matrix, staging tests and rollback checkpoint.
- Primary fencing proof and single-writer authority.
- DR DNS/webhook cutover and reconciliation ledger.
- Monitoring dashboards, error-budget view and cost report.
- Incident timeline, RCA/COA, scorecard and owner sign-off.

## 4. Capacity and timing model

Estimate restore duration from backup size and **measured effective** transfer and restore throughput. Add provisioning, encryption/decryption, controller boot, plugin loading, agent startup and synthetic validation; use p95 or conservative measurements rather than optimistic peak network bandwidth.

Illustrative estimate:

```text
backup = 120 GiB
effective restore throughput = 80 MiB/s
data transfer = (120 × 1024) / 80 = 1536 seconds = 25.6 minutes
other recovery steps = 24 minutes
estimated RTO = 49.6 minutes
```

This does not guarantee a 60-minute RTO: cold-start variance, snapshot API delays, cloud quotas and concurrent dependency outages require measured drills and headroom.

## 5. Executable RTO estimate

```python
import math

backup_gib = 120
effective_mib_per_s = 80
other_minutes = 24
transfer_minutes = backup_gib * 1024 / effective_mib_per_s / 60
estimated_rto = transfer_minutes + other_minutes
print(f"Transfer: {transfer_minutes:.1f} minutes")
print(f"Estimated RTO: {estimated_rto:.1f} minutes")
print("Illustrative 60-minute target:", estimated_rto <= 60)
```

Run with `python3 rto_estimate.py`; replace assumptions with observed throughput and timings.

## 6. Capstone phases

### Phase A — Baseline and design
1. Inventory primary, agents, plugins, Java, JCasC, identity, SCM and storage.
2. Define failure domains and approved RPO/RTO.
3. Capture synthetic CI success, queue, agent and controller baseline.
4. Map privileged identities, encryption keys and artifact ownership.
5. Confirm isolated lab and rollback/abort thresholds.

### Phase B — Backup and recovery
6. Quiesce/stop **test** writer or use a proven application-consistent snapshot.
7. Generate encrypted backup and restricted manifest/checksum.
8. Verify retention, immutability and offsite copy.
9. Restore to isolated volume and validate credentials and jobs.
10. Measure durable marker recovery, backup age and restore time.

### Phase C — Upgrade and rollback
11. Pin target Jenkins LTS, Java, plugins, JCasC and agent images.
12. Resolve plugin dependencies and security advisories.
13. Test candidate against an isolated state copy.
14. Validate RBAC, SCM, agents, shared libraries and artifact digests.
15. Inject a staging upgrade failure; fence candidate and restore pre-change state to a clean volume.

### Phase D — Regional DR and failback
16. Declare simulated regional incident and obtain approval.
17. Prove primary fencing using authoritative infrastructure evidence.
18. Restore latest verified backup into DR region/cluster.
19. Start exactly one controller, validate synthetic CI and cut over **test** DNS/webhooks.
20. Reconcile duplicate/missing synthetic events and external side effects.
21. Freeze DR writes, back up authoritative DR state and fence DR writer.
22. Restore clean primary from authoritative state, validate and fail back.

### Phase E — Reliability acceptance
23. Calculate measured RPO/RTO, backup integrity, SLO impact and cloud cost.
24. Score controls, produce RCA/COA and secure reviewer sign-off.

## 7. Failure-injection matrix

| # | Fault | Expected detection and recovery |
|---|---|---|
| 01 | Backup scheduler missed | freshness alert |
| 02 | Snapshot inconsistent | restore validation |
| 03 | Checksum mismatch | quarantine invalid backup |
| 04 | Object deletion attempt | retention/immutability |
| 05 | KMS decrypt denied | approved key recovery |
| 06 | Cross-region copy lag | RPO recalculation |
| 07 | Storage restore quota | capacity escalation |
| 08 | Plugin dependency conflict | staged compatibility gate |
| 09 | Unsupported Java/core | runtime preflight |
| 10 | JCasC schema regression | rollback from tested state |
| 11 | RBAC privilege regression | negative auth test |
| 12 | Credential decryption failure | key custody |
| 13 | Agent remoting mismatch | agent version check |
| 14 | Pipeline DSL regression | synthetic CI |
| 15 | Controller crash during upgrade | fenced recovery |
| 16 | Original controller still writable | **block DR** |
| 17 | Regional DNS/ingress failure | dependency runbook |
| 18 | DR cloud quota exhaustion | alternative capacity |
| 19 | Artifact registry unavailable | dependency escalation |
| 20 | Duplicate webhook delivery | idempotency/reconciliation |
| 21 | RPO objective breached | owner escalation |
| 22 | RTO objective breached | incident/COA |
| 23 | Stale primary during failback | authoritative state guard |
| 24 | Key compromise suspicion | security incident protocol |

Do not mark blocked or unexecuted tests as passed.

## 8. Eight production runbooks

### A. Backup freshness failure
Identify scheduler/storage/auth root cause; obtain a verified consistent backup, check checksum and recalculate RPO exposure.

### B. Backup integrity or immutability failure
Quarantine affected object/version, preserve audit logs, verify last good copy, involve security and repair controls.

### C. Key/credential recovery failure
Escalate to approved key custodians, restore access without logging secrets and validate synthetic credential use.

### D. Upgrade compatibility failure
Stop rollout, identify first incompatible core/Java/plugin/JCasC dependency, revert via compatible pre-change restore when state changed.

### E. Production controller crash
Fence writer, preserve state, select verified recovery point, restore one compatible controller and verify synthetic CI.

### F. Cross-region failover
Obtain approval and authoritative fencing, restore DR state, validate dependencies and CI, cut over test routing and reconcile events.

### G. Controlled failback
Freeze DR mutations, capture authoritative DR state, fence DR writer, restore primary, validate and cut over routing.

### H. RPO/RTO or acceptance breach
Notify service owner, document observed timelines, assign COA, improve controls and repeat acceptance drill before approval.

## 9. 100-point enterprise acceptance

| Category | Points |
|---|---:|
| Architecture, dependencies, RACI and recovery objectives | 10 |
| Backup consistency, encryption, integrity and retention | 20 |
| Isolated restore and key recovery | 15 |
| Core/plugin/Java/JCasC upgrade compatibility | 15 |
| Safe rollback and single-writer fencing | 15 |
| Regional failover/failback and synthetic CI | 15 |
| RPO/RTO, observability, RCA/COA and sign-off | 10 |
| **Total** | **100** |

**Suggested pass:** 85/100 **plus every mandatory gate**:
- Verified consistent backup and recoverable encryption keys.
- Checksum/integrity and retention evidence.
- Restore to a separate isolated state volume.
- Approved single-writer fencing for both failover and failback.
- Critical CI and positive/negative authorization checks.
- Upgrade rollback from compatible pre-change state.
- Measured RPO/RTO with no unapproved breach.
- Reconciliation and incident sign-off.

A high numeric score cannot override failed mandatory gates.

## 10. Evidence worksheet

```text
Incident/change ID / UTC / approver:
Scope, abort conditions and cost cap:
Primary and DR controller inventories:
Core/Java/plugins/JCasC/image digest:
Backup ID/consistency/checksum/retention:
Encryption key custody and restore validation:
Primary fencing proof:
Isolated restore and credential checks:
Upgrade staging and rollback evidence:
SCM/agents/artifacts synthetic CI:
DNS/webhook cutover/reconciliation:
Failback authoritative state and fencing:
Actual RPO / RTO / SLO / cost:
24 drills completed or blocked:
Score / mandatory gates / RCA / COA / reviewer:
```

## 11. Completion checklist

- [ ] All 24 exercises attempted with evidence.
- [ ] All 24 failure scenarios executed or explicitly blocked.
- [ ] Eight runbooks reviewed and assigned owners.
- [ ] Backup consistency and integrity verified.
- [ ] Upgrade compatibility and rollback tested.
- [ ] Single-writer fencing proven.
- [ ] Isolated cross-region DR and failback tested.
- [ ] Synthetic CI, credentials and artifacts validated.
- [ ] Measured RPO/RTO and reconciliation recorded.
- [ ] 100-point scorecard and service-owner sign-off complete.

**Companion:** [Chapter 085 hands-on acceptance lab](labs/085-jenkins-enterprise-backup-upgrade-disaster-recovery-acceptance-capstone-check.md).  
**Part 17 complete:** Chapters 081–085.  
**Next:** Chapter 086 — Jenkins Infrastructure as Code with Terraform and Ansible.
