# Chapter 081 — Jenkins Backup Architecture, Recovery Strategy and RPO/RTO Planning

**Part 17 — Backup, Restore, Upgrades and Disaster Recovery**  
**Audience:** Jenkins SRE/DBRE, platform engineers, security and disaster recovery owners  
**Prerequisites:** Chapters 076–080, isolated Jenkins LTS, approved backup storage, disposable restore target and a test Pipeline.

## Objectives

Inventory Jenkins state and dependencies, design consistent encrypted backups, define recovery objectives, prevent split-brain during restore, automate verification and prove recovery by executing a representative Pipeline.

## 1. Jenkins state architecture

```text
SCM + JCasC + plugin lock + controller image
                      |
                Jenkins controller
                      |
           JENKINS_HOME (single writer)
             /          |          \
        jobs/builds  secrets/keys   plugin state
                      |
         encrypted backup / immutable copy
                      |
           isolated restore controller
                      |
       smoke tests + synthetic CI + RTO/RPO
```

A controller restart is not a backup. Storage replication is not a point-in-time restore strategy: corruption, accidental deletion or compromised credentials may replicate.

## 2. What must be recoverable?

| Component | Recovery approach | Critical consideration |
|---|---|---|
| Jenkins home | consistent snapshot/backup | single active writer |
| Job and Pipeline configuration | backup plus source control | verify drift |
| Credentials and encryption keys | encrypted restricted backup | restore keys with data |
| Plugin binaries/configuration | tested version manifest | core/Java compatibility |
| JCasC | Git-pinned configuration | secrets externalized |
| Controller image/Java | immutable artifact | reproducible runtime |
| Build logs and metadata | policy-based retention | storage and audit |
| Artifacts | external immutable repository | checksum/retention |
| Agent workspaces | disposable, reconstructible | avoid treating as authoritative |
| SCM/webhooks/SSO/DNS | dependency recovery runbooks | external service SLO |

Do not place unencrypted `secrets/` or credential exports in Git, CI logs or broad-access object storage.

## 3. Backup consistency

Filesystem copy while Jenkins is writing can capture inconsistent state. Prefer a documented application-consistent approach: approved Jenkins backup integration, coordinated quiesce or controller shutdown with snapshot, or a storage snapshot workflow proven by restore tests. The correct method depends on storage and Jenkins deployment.

Always validate:
1. Backup timestamp, scope and integrity.
2. Version manifest and JCasC Git SHA.
3. Encryption keys and access permissions.
4. Object versioning/immutability and retention.
5. Offsite or cross-account/cross-region copy where required.
6. Restore into a **separate** state volume, never a running production home.

## 4. RPO/RTO mathematics

- **RPO:** maximum acceptable age of recovered durable state.
- **RTO:** maximum acceptable elapsed time from declared outage to verified service recovery.

Illustrative targets: RPO 15 minutes, RTO 60 minutes. If snapshots are hourly, the design cannot normally claim a 15-minute RPO without additional validated recovery mechanisms. RTO includes detection, decision, fencing, volume provisioning, restore, key recovery, plugin compatibility, agents and successful synthetic CI.

```text
Measured RPO = disaster_time - timestamp_of_latest_verified_recoverable_state
Measured RTO = verified_recovery_time - disaster_start_time
```

Backup age is only a proxy for actual lost writes; record the last durable known test marker when feasible.

## 5. Backup tiering

| Tier | Example scope | Validation |
|---|---|---|
| Frequent state snapshots | Jenkins home + key material | automated integrity |
| Daily protected copy | full recoverable state | isolated restore sampling |
| Weekly offsite copy | region/account resilience | periodic full drill |
| Before changes | plugin/core/JCasC upgrades | rollback checkpoint |

These are example cadences; set them from business RPO, cost and data retention requirements. Encrypt, restrict and audit every tier. Test immutability against unauthorized deletion.

## 6. Kubernetes, EKS and AKS design

- Identify PVC provisioner, volume snapshot support and zone/region constraints.
- Verify CSI VolumeSnapshotClass and provider backup semantics.
- Treat snapshots as crash-consistent unless application-level consistency is demonstrated.
- Keep backup IAM/managed identity separate from agent/build identities.
- Document restore namespace, storage class, node topology, DNS and ingress.
- Fence the original controller before production cutover.
- Do not run multiple controllers against one writable `JENKINS_HOME`.

For EKS, validate EBS snapshot/restore and AWS permissions. For AKS, validate Azure Disk snapshot/restore and Azure permissions. Storage and snapshot features depend on driver, SKU and deployment.

## 7. Safe backup/restore lab commands

Use an isolated disposable Jenkins instance. Example offline archive after stopping the test controller and confirming no writer:

```sh
export JENKINS_HOME=/srv/jenkins-lab-home
export BACKUP_DIR=/srv/jenkins-lab-backups
mkdir -p "$BACKUP_DIR"
test -d "$JENKINS_HOME" || exit 1
tar -C "$JENKINS_HOME" -czf "$BACKUP_DIR/jenkins-home-test.tar.gz" .
sha256sum "$BACKUP_DIR/jenkins-home-test.tar.gz" > "$BACKUP_DIR/jenkins-home-test.tar.gz.sha256"
(cd "$BACKUP_DIR" && sha256sum -c jenkins-home-test.tar.gz.sha256)
```

This example creates a **local unencrypted archive** for an isolated lab only. It is **not** a production-ready backup design. Production requires encrypted storage, restricted access, retention, integrity verification and a consistent snapshot or stopped writer. Avoid exposing sensitive backup content.

Restore only into a newly created isolated directory:

```sh
export RESTORE_DIR=/srv/jenkins-lab-restore
mkdir -p "$RESTORE_DIR"
tar -tzf "$BACKUP_DIR/jenkins-home-test.tar.gz" | head
tar -C "$RESTORE_DIR" -xzf "$BACKUP_DIR/jenkins-home-test.tar.gz"
```

Before extraction of untrusted archives, validate entries for path traversal and symlink risks. The archive above must be generated from the operator-controlled test home. Do not use this generic tar example for a live controller.

## 8. Restore acceptance workflow

1. Declare disaster and capture UTC timestamp.
2. Identify latest verified backup and immutable manifest.
3. Confirm original controller fenced or isolated.
4. Provision a separate clean volume and restricted restore target.
5. Restore state and keys with correct ownership/permissions.
6. Start exactly one compatible controller.
7. Verify Jenkins login, RBAC, JCasC, plugins, credentials and jobs.
8. Execute representative Pipeline with SCM checkout and artifact checksum.
9. Compare last durable marker to establish actual data loss.
10. Record RTO/RPO, deviations, cost and owner sign-off.

## 9. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Backup archive missing | schedule/storage |
| 02 | Backup too old | RPO alert |
| 03 | Backup checksum mismatch | integrity |
| 04 | Snapshot incomplete | quiesce/consistency |
| 05 | Restore fails due to permissions | ownership/ACL |
| 06 | Credentials cannot decrypt | key mismatch |
| 07 | Plugin fails on restored core | version manifest |
| 08 | Java incompatibility | runtime pin |
| 09 | JCasC startup failure | schema/config |
| 10 | PVC snapshot unsupported | CSI capability |
| 11 | Cross-zone volume attach fails | topology |
| 12 | Cloud snapshot API denied | IAM/identity |
| 13 | Restore slow | storage throughput |
| 14 | Backup contains secrets in logs | access/audit |
| 15 | Old controller still writing | fencing |
| 16 | Missing job history | backup scope |
| 17 | Artifact missing | external dependency |
| 18 | SCM webhook misrouted | DNS/routing |
| 19 | Restored SSO unavailable | IdP |
| 20 | RTO/RPO objective missed | timeline and COA |

## 10. Six production runbooks

### A. Backup failure
Identify failed job/storage/auth; preserve logs without secrets; rerun safely, verify checksum and alert on RPO exposure.

### B. Jenkins home corruption
Stop/fence writer, capture evidence and snapshots, select verified restore point, recover into isolated target and validate state.

### C. Encryption key loss
Escalate to security and backup custodians; locate approved encrypted key backup; do not rotate blindly or expose secrets; restore and verify decryption.

### D. Kubernetes volume recovery
Validate CSI/snapshot compatibility, permissions, zone placement and attach status; recover to separate PVC and test controller.

### E. Cross-region DR
Verify regional dependencies, network/DNS, identity and copy lag; fence original writer; restore, validate and authorize traffic cutover.

### F. Quarterly restore drill
Select backup, time all phases, verify synthetic CI and durable marker, score RTO/RPO, clean up and assign corrective actions.

## 11. Production acceptance checklist

- [ ] State/dependency inventory complete.
- [ ] RPO/RTO approved by service owner.
- [ ] Consistency method documented and restore-tested.
- [ ] Backup encrypted, access restricted and immutable where required.
- [ ] Keys recoverable via controlled procedure.
- [ ] Single-writer fencing verified.
- [ ] Cross-zone/region storage constraints tested.
- [ ] Synthetic CI and artifacts validated after restore.
- [ ] Actual RTO/RPO recorded.
- [ ] Alerting, retention, cost and COA owners documented.

**Companion:** [Chapter 081 hands-on lab](labs/081-jenkins-backup-architecture-recovery-strategy-rpo-rto-planning-check.md).  
**Next:** Chapter 082 — Jenkins Backup Automation, Secure Storage and Restore Validation.
