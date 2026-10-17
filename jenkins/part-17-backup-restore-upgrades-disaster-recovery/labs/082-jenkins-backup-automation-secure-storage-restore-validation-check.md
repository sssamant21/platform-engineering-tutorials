# Chapter 082 — Hands-on Lab: Jenkins Backup Automation, Secure Storage and Restore Validation

**Environment:** Disposable Jenkins LTS, stopped test controller, restricted backup directory, synthetic credentials, optional test S3/Azure Blob and isolated restore target.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory backup scope and dependencies | Matrix |
| 02 | Capture core/Java/plugin/JCasC manifest | File |
| 03 | Define backup RPO/RTO and retention | Policy |
| 04 | Inspect test home permissions | Output |
| 05 | Stop test controller and verify no writer | Timeline |
| 06 | Create backup automation script | Script |
| 07 | Run guarded offline backup | Archive |
| 08 | Generate SHA-256 checksum | Digest |
| 09 | Validate archive integrity | Result |
| 10 | Generate nonsecret JSON manifest | Manifest |
| 11 | Review encrypted object storage controls | Checklist |
| 12 | Test least-privilege backup identity | IAM evidence |
| 13 | Inspect versioning/immutability | Policy |
| 14 | Simulate checksum mismatch on test copy | Failure |
| 15 | Verify integrity alert behavior | Alert |
| 16 | Provision clean isolated restore target | Volume |
| 17 | Restore compatible state and keys | Restore |
| 18 | Run synthetic Pipeline and artifact checksum | Build |
| 19 | Measure RPO/RTO and freshness | Worksheet |
| 20 | Record cleanup, runbook and approval | Sign-off |

## 12 troubleshooting drills

1. Missed backup schedule.
2. Overlapping backup attempts.
3. Inconsistent live filesystem copy.
4. Corrupted checksum.
5. Interrupted upload.
6. KMS/managed identity denial.
7. Excessive backup permissions.
8. Retention policy mistake.
9. Missing decryption keys.
10. Plugin/core mismatch.
11. Restore volume quota.
12. RTO/RPO breach.

## Lab automation

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${JENKINS_HOME:?}"
: "${BACKUP_DIR:?}"
: "${STOPPED_CONTROLLER_MARKER:?}"
[[ -f "$STOPPED_CONTROLLER_MARKER" ]] || { echo "Stop marker absent" >&2; exit 2; }
[[ -d "$JENKINS_HOME" ]] || exit 2
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
file="$BACKUP_DIR/jenkins-home-$stamp.tar.gz"
tar -C "$JENKINS_HOME" -czf "$file" .
sha256sum "$file" > "$file.sha256"
(cd "$BACKUP_DIR" && sha256sum -c "$(basename "$file").sha256")
```

This lab archive is unencrypted; do not use it for production or live Jenkins home. A marker alone is not proof of fencing.

## Executable backup freshness check

```python
from datetime import datetime, timezone, timedelta

now = datetime(2026, 10, 17, 2, 0, tzinfo=timezone.utc)
verified_backup = datetime(2026, 10, 17, 1, 42, tzinfo=timezone.utc)
max_age = timedelta(minutes=15)
age = now - verified_backup
print(f"Verified backup age: {age.total_seconds()/60:.0f} minutes")
print("RPO freshness risk:", age > max_age)
```

Expected: age 18 minutes, risk True. These are synthetic timestamps, not observed results.

## Evidence template

```text
UTC / change owner:
Core/Java/plugin/JCasC:
Backup consistency and fencing:
Archive/manifest/checksum:
Encryption/key custody:
IAM/RBAC and object retention:
Last verified backup age:
Restore destination:
Synthetic CI and artifact integrity:
Measured RPO/RTO:
Alert tests:
Cleanup/COA/reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] No live or shared writable backup copy.
- [ ] Checksum and manifest verified.
- [ ] Encryption and identity policy reviewed.
- [ ] Restore uses isolated state volume.
- [ ] Synthetic CI and artifacts verified.
- [ ] Freshness and RPO/RTO measured.
- [ ] No secrets exposed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 082 — Jenkins Backup Automation, Secure Storage and Restore Validation](../082-jenkins-backup-automation-secure-storage-restore-validation.md).
