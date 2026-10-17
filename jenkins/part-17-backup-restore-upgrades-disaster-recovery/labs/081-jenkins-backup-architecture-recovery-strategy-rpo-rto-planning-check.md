# Chapter 081 — Hands-on Lab: Jenkins Backup Architecture and RPO/RTO

**Environment:** Disposable Jenkins LTS with synthetic jobs, isolated test home, separate restore target and restricted backup storage. No production restores or shared writable homes.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory Jenkins state and dependencies | Matrix |
| 02 | Capture core/Java/plugin/JCasC versions | Manifest |
| 03 | Map backup scope and excluded disposable data | Policy |
| 04 | Define business RPO/RTO | Approval |
| 05 | Inspect test home permissions | Output |
| 06 | Verify only one controller writer | Deployment |
| 07 | Stop/quiesce test controller safely | Timeline |
| 08 | Create controlled offline archive | Archive |
| 09 | Generate SHA-256 integrity manifest | Checksum |
| 10 | Verify archive integrity | Result |
| 11 | Document encrypted storage controls | Checklist |
| 12 | Record last durable synthetic marker | Marker |
| 13 | Provision isolated restore directory/PVC | Evidence |
| 14 | Inspect archive paths before extraction | Review |
| 15 | Restore into isolated copy | Output |
| 16 | Start compatible isolated controller | Startup |
| 17 | Verify jobs, plugins, RBAC and credentials | Checks |
| 18 | Run synthetic Pipeline and artifact validation | Build |
| 19 | Calculate measured RPO/RTO | Worksheet |
| 20 | Complete restore acceptance and COA | Sign-off |

## 12 troubleshooting drills

1. Missing backup.
2. Stale backup.
3. Checksum mismatch.
4. Inconsistent live copy.
5. Restore permissions.
6. Encryption key mismatch.
7. Plugin/Java mismatch.
8. JCasC schema error.
9. Unsupported CSI snapshot.
10. Volume topology conflict.
11. Missing artifact dependency.
12. RTO/RPO breach.

## Executable RTO/RPO calculator

```python
from datetime import datetime, timezone

disaster = datetime(2026, 10, 17, 2, 0, tzinfo=timezone.utc)
last_verified_state = datetime(2026, 10, 17, 1, 52, tzinfo=timezone.utc)
verified_recovery = datetime(2026, 10, 17, 2, 43, tzinfo=timezone.utc)

rpo_minutes = (disaster - last_verified_state).total_seconds() / 60
rto_minutes = (verified_recovery - disaster).total_seconds() / 60
print(f"Measured RPO: {rpo_minutes:.0f} min")
print(f"Measured RTO: {rto_minutes:.0f} min")
```

Expected: RPO 8 minutes, RTO 43 minutes. These are synthetic timestamps for practice, not observed results.

## Lab backup example

Only after confirming the test controller is stopped:

```sh
export JENKINS_HOME=/srv/jenkins-lab-home
export BACKUP_DIR=/srv/jenkins-lab-backups
mkdir -p "$BACKUP_DIR"
tar -C "$JENKINS_HOME" -czf "$BACKUP_DIR/jenkins-home-test.tar.gz" .
sha256sum "$BACKUP_DIR/jenkins-home-test.tar.gz" > "$BACKUP_DIR/jenkins-home-test.tar.gz.sha256"
(cd "$BACKUP_DIR" && sha256sum -c jenkins-home-test.tar.gz.sha256)
```

Local tar archive is **unencrypted** and for an isolated lab only; production backups require secure encrypted storage and verified consistency.

## Evidence template

```text
UTC / owner / approval:
Core/Java/plugin/JCasC versions:
Backup scope and consistency method:
Backup timestamp and checksum:
Encryption/key custody:
Last durable state marker:
Original controller fencing:
Isolated restore destination:
Start/end of outage and restore:
Measured RPO/RTO:
RBAC/credentials/SCM/artifact checks:
Synthetic CI result:
Rollback and cleanup:
COA and reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Consistent backup approach demonstrated.
- [ ] Integrity verified before restore.
- [ ] Single-writer safety maintained.
- [ ] Restore uses separate copy.
- [ ] Synthetic CI validates recovery.
- [ ] Measured RPO/RTO recorded.
- [ ] Security and cleanup reviewed.
- [ ] Reviewer sign-off completed.

**Related:** [Chapter 081 — Jenkins Backup Architecture, Recovery Strategy and RPO/RTO Planning](../081-jenkins-backup-architecture-recovery-strategy-rpo-rto-planning.md).
