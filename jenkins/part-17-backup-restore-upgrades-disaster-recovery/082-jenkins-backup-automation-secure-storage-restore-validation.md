# Chapter 082 — Jenkins Backup Automation, Secure Storage and Restore Validation

**Part 17 — Backup, Restore, Upgrades and Disaster Recovery**  
**Audience:** Jenkins SRE/DBRE, platform security, backup and recovery owners  
**Prerequisites:** Chapter 081, isolated Jenkins LTS, approved object storage, Kubernetes/EKS/AKS or VM test environment, backup encryption keys and a disposable restore target.

## Learning objectives

Automate **consistent** Jenkins state backups, protect secrets and encryption keys, implement retention/immutability and least-privilege access, monitor backup freshness and integrity, perform isolated restore verification and prove recovery through synthetic CI.

## 1. Architecture

```text
Controller + JENKINS_HOME (one writer)
               |
       quiesce / consistent snapshot
               |
       backup job (separate identity)
               |
       encryption + checksum + manifest
               |
     versioned object store / immutable copy
               |
       backup monitor + alerting
               |
    isolated restore + smoke/synthetic CI
               |
      RPO/RTO evidence and approval
```

**Important:** A successful upload is not a successful backup until integrity and recoverability are verified. A filesystem copy while Jenkins writes may be inconsistent. A cloud volume snapshot is not automatically application-consistent. Do not mount one writable Jenkins home into multiple active controllers.

## 2. Backup policy

| Control | Requirement |
|---|---|
| Consistency | approved quiesce, stopped writer or validated application-consistent snapshot |
| Confidentiality | encrypted in transit and at rest; restricted keys |
| Integrity | checksum and signed/attested manifest where appropriate |
| Retention | policy-driven daily/weekly/monthly versions |
| Immutability | object lock/retention with tested administrative controls |
| Isolation | separate backup principal/account where required |
| Restore | isolated target, compatible Jenkins core/Java/plugins/JCasC |
| Observability | freshness, failures, bytes, duration, integrity, restore age |
| Audit | change ticket, backup ID, timestamp, restore evidence |

Retention and immutability are different: lifecycle expiration must respect legal hold and lock policies. Cross-region replication alone does not protect against all logical corruption.

## 3. Backup manifest

Use a machine-readable manifest recording backup ID, UTC time, source environment, Jenkins version, Java runtime, plugin inventory checksum, JCasC Git SHA, state snapshot ID, archive SHA-256, encryption method/key reference, retention class and restore-test result. Never include raw secrets, passwords or private keys in a manifest.

Example:

```json
{
  "backup_id": "jenkins-lab-20261017T020000Z",
  "environment": "isolated-lab",
  "consistency": "controller-stopped",
  "state_archive": "jenkins-home.tar.gz",
  "sha256": "REPLACE_WITH_CALCULATED_DIGEST",
  "jenkins_core": "RECORD_ACTUAL_VERSION",
  "java_runtime": "RECORD_ACTUAL_VERSION",
  "plugin_manifest_sha256": "REPLACE_WITH_CALCULATED_DIGEST",
  "jasc_git_sha": "RECORD_ACTUAL_COMMIT",
  "encryption": "approved-provider-managed-or-client-side",
  "key_reference": "NON_SECRET_KEY_IDENTIFIER",
  "restore_verified": false
}
```

## 4. Executable lab backup automation

This script is **only for a disposable, stopped Jenkins controller**. It refuses to run unless the operator provides a separate marker confirming a stopped writer. The marker is a lab guard, not a production fencing mechanism.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${JENKINS_HOME:?Set isolated JENKINS_HOME}"
: "${BACKUP_DIR:?Set restricted BACKUP_DIR}"
: "${STOPPED_CONTROLLER_MARKER:?Set path to approved stop marker}"

[[ -f "$STOPPED_CONTROLLER_MARKER" ]] || { echo "Refusing: stopped controller not confirmed" >&2; exit 2; }
[[ -d "$JENKINS_HOME" ]] || { echo "Missing test Jenkins home" >&2; exit 2; }
mkdir -p -- "$BACKUP_DIR"
chmod 700 -- "$BACKUP_DIR"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$BACKUP_DIR/jenkins-home-$stamp.tar.gz"
tar -C "$JENKINS_HOME" -czf "$archive" .
sha256sum "$archive" > "$archive.sha256"
(cd "$BACKUP_DIR" && sha256sum -c "$(basename "$archive").sha256")
printf 'Backup complete: %s\n' "$archive"
```

The output archive is **not encrypted by this script**; keep it strictly inside the disposable lab. Production requires a validated encryption/upload workflow, atomic completion markers, locked-down temporary files, reliable fencing and restore testing. Never infer process state solely from a marker.

## 5. Object storage security

**AWS S3:** use least-privilege IAM, SSE-KMS or approved client-side encryption, bucket versioning, Object Lock where required, bucket policies denying public access, CloudTrail/audit logging, and a separate restore role. Test KMS decrypt permission and cross-account recovery.

**Azure Blob Storage:** use managed identity, RBAC, private endpoints where required, encryption with approved keys, blob versioning/immutability policies, diagnostic logs and a separate restore identity. Test key access and regional recovery.

Do not embed cloud credentials in Jenkinsfiles or shell scripts. Build agents should not inherit backup deletion or decryption permissions.

## 6. Kubernetes automation choices

- CronJob with isolated backup identity for a **documented** consistent snapshot workflow.
- CSI VolumeSnapshot with a supported snapshot class and proven consistency.
- Provider backup service with scoped access and restore validation.
- Dedicated backup service outside Jenkins controller to survive controller outages.

Use `concurrencyPolicy: Forbid` for backup CronJobs to avoid overlapping jobs, bounded retries, `activeDeadlineSeconds`, resource limits and failure alerts. This does **not** automatically make snapshots consistent.

## 7. Monitoring and alerts

Candidate metrics:
- Age of newest **verified recoverable** backup.
- Backup success/failure and duration.
- Integrity check failures.
- Backup size growth and storage cost.
- Retention/immutability violations.
- Last successful **isolated restore** age.
- RPO exposure based on backup frequency and replication lag.

Metric names vary by exporter and integration. Define clear ownership, alert severity and runbook links. A stale backup should page only according to the approved recovery risk policy.

## 8. Restore verification pipeline

1. Select backup by manifest and checksum.
2. Verify access rights, encryption keys and immutable object version.
3. Restore into a fresh isolated volume.
4. Start **one** compatible controller with matching core/Java/plugins/JCasC.
5. Verify credential decryption without printing secrets.
6. Validate jobs, RBAC, agent registration and SCM connectivity.
7. Run synthetic Pipeline with artifact digest check.
8. Compare durable marker and measure RPO/RTO.
9. Destroy isolated restore environment safely and retain evidence.
10. Update last-verified-restore timestamp only on successful acceptance.

## 9. Twenty troubleshooting scenarios

| # | Failure | Check |
|---|---|---|
| 01 | CronJob never runs | schedule/controller |
| 02 | Overlapping backups | concurrency policy |
| 03 | Snapshot inconsistent | quiesce method |
| 04 | Archive truncated | size/checksum |
| 05 | Upload partial | atomic completion |
| 06 | KMS decrypt denied | key policy |
| 07 | Backup principal too broad | IAM/RBAC |
| 08 | Object lock misconfigured | retention policy |
| 09 | Lifecycle deletes early | policy precedence |
| 10 | Cross-region copy lag | replication |
| 11 | Restore target lacks capacity | PVC/quota |
| 12 | Storage class mismatch | CSI |
| 13 | Encryption keys missing | key custody |
| 14 | Plugin/core incompatibility | version lock |
| 15 | JCasC startup error | Git/config |
| 16 | Credentials fail to decrypt | secret keys |
| 17 | SCM/artifact service unavailable | dependencies |
| 18 | Backup freshness alert false positive | verified timestamp |
| 19 | Restore test exceeds RTO | timeline |
| 20 | Two active writers detected | fencing |

## 10. Six production runbooks

### A. Backup schedule failure
Check job history, controller-independent scheduler, quota, IAM and storage; retry safely and validate checksum, manifest and recoverability.

### B. Integrity failure
Quarantine invalid object, preserve audit trail, select last verified backup and investigate source consistency, transfer and storage.

### C. KMS/key access failure
Escalate to key custodian, validate approved decrypt role and key availability, restore access without exposing plaintext secrets.

### D. Retention/immutability incident
Stop destructive automation, audit policy changes, verify unaffected versions and offsite copies, correct controls with security approval.

### E. Isolated restore failure
Capture first error, verify version manifest, keys, PVC and dependencies, retry against a clean target; do not overwrite the source home.

### F. RPO/RTO breach
Compute measured objectives, notify service owner, assess impact and improve backup frequency, transfer throughput or restore automation; retest.

## 11. Acceptance gates

- [ ] Consistency strategy tested and documented.
- [ ] Backup identity least-privileged.
- [ ] Encryption/key recovery verified.
- [ ] Manifest and checksum generated.
- [ ] Retention and immutability validated.
- [ ] Freshness and integrity alerts configured.
- [ ] Restore performed in isolated state copy.
- [ ] Synthetic CI, credentials and artifacts validated.
- [ ] Measured RPO/RTO recorded.
- [ ] Audit evidence and reviewer sign-off completed.

**Companion:** [Chapter 082 hands-on lab](labs/082-jenkins-backup-automation-secure-storage-restore-validation-check.md).  
**Next:** Chapter 083 — Jenkins Core, Plugin and Java Upgrades with Compatibility Testing and Rollback.
