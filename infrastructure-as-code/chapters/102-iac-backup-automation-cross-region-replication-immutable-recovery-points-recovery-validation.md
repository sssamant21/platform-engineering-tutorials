# Chapter 102 — IaC Backup Automation, Cross-Region Replication, Immutable Recovery Points and Recovery Validation

**Part 21 — Disaster Recovery · Chapter 102/120 · Enterprise SRE/DBRE**

> **Evidence and safety boundary:** Included Python lab is an offline synthetic model. It does not call cloud APIs, access backups, change Terraform state or verify a real restore. Native restore drills and independent production acceptance remain pending.

## 1. Learning outcomes and prerequisites
Build policy-driven backup schedules, isolate copies across accounts and regions, enforce immutability, validate encryption and restore permissions, protect Terraform/OpenTofu state, recover Kubernetes PVs and database PITR, measure backup freshness and run a controlled recovery drill. Prerequisite: Chapter 101 and knowledge of IAM/KMS, Kubernetes CSI and DBRE backup fundamentals.

## 2. Architecture and control planes
```text
Git + IaC modules + backup policy as code
                  |
  workload discovery + tier + RPO/RTO mapping
                  |
 cloud-native snapshots / database PITR / app backups
                  |
 integrity + metadata + retention + immutability
                  |
 cross-account + cross-region isolated copy
                  |
 independent keys + break-glass recovery identity
                  |
 scheduled restore into isolated staging environment
                  |
 consistency, checksums, transactions, measured RPO/RTO
                  |
 audit evidence + SRE/DBRE approval + remediation
```

**Backup ≠ replication ≠ restore.** Replication can faithfully copy corruption and deletion. A successful snapshot API response does not establish that keys, dependencies, applications or databases can be restored.

## 3. Backup policy and recovery contracts
For each workload record service tier, data owner, failure domains, RPO, RTO, backup frequency, retention, recovery point timestamp, source region/account, destination region/account, immutability duration, encryption key, PITR coverage, restore test cadence and approval owner.

Freshness must be evaluated against **last verified recoverable point**, not last scheduler invocation. RPO is an end-to-end data-loss limit, and RTO includes environment reconstruction, data restore, identity/network setup, routing and transaction verification. Retention must satisfy legal holds and compliance; backup expiry or destructive cleanup must never be triggered by a synthetic lab.

### Cloud implementation patterns
- **AWS:** AWS Backup policies, backup vault isolation and Vault Lock where applicable, cross-account/cross-region copy, S3 Object Lock/versioning, RDS/Aurora PITR, EBS/EKS snapshots and KMS recovery grants. Confirm that the chosen resource type supports each cross-region or copy operation.
- **Azure:** Azure Backup policies and immutable vault protection where supported, cross-region restore eligibility, Azure Site Recovery, Azure Database PITR, AKS workload/PV recovery, Key Vault and managed identity permissions. Validate regional redundancy and vault restrictions before design approval.
- **GCP:** Backup and DR Service, Cloud Storage retention lock, Cloud SQL PITR, Backup for GKE, Persistent Disk snapshots, Cloud KMS and project separation. Check product-specific copy/location limitations.
- **Terraform/OpenTofu:** Encrypted remote state, versioned state snapshots, locked backend, independently recoverable backend bootstrap, pinned provider versions, protected plans and read-only verification of recovered state. Avoid `terraform state push` during exercises.
- **Kubernetes:** Back up namespace manifests, CRDs/operators, RBAC, secrets with independently recoverable keys, PVC/PV data, CSI snapshot objects, storage class mapping and application consistency. A CSI VolumeSnapshot alone may be crash-consistent rather than application-consistent.

### DBRE-specific backup design
**PostgreSQL:** full/base backup, WAL archive continuity, PITR, replication lag, extension and major-version compatibility, recovery timeline and write validation.

**MongoDB:** replica/shard-consistent backup, oplog coverage, config server metadata, auth, indexes and restored document consistency.

**Redis:** RDB/AOF integrity, persistence configuration, replication lag and maximum tolerated lost writes.

**Kafka:** replicated log retention, metadata, topics, ACLs, offsets and verified recovery strategy; replication is not independent backup.

**Elasticsearch:** snapshot repository access, index and cluster metadata, version compatibility, shard restore and query validation.

## 4. Lab A — Offline immutable backup gate
Create `infrastructure-as-code/labs/chapter-102/backup_gate.py`:

```python
"""Synthetic backup inventory and restore-readiness gate. No cloud API calls."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

@dataclass(frozen=True)
class RecoveryPoint:
    id: str
    workload: str
    created_utc: str
    checksum_sha256: str
    source_region: str
    replica_region: str
    isolated_account: bool
    immutable_until_utc: str
    restore_verified: bool
    encryption_key_accessible: bool
    state_manifest_present: bool

def utc(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset() != timezone.utc.utcoffset(d):
        raise ValueError("explicit UTC required")
    return d

def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()

def validate(point, now_utc, max_age_minutes):
    if max_age_minutes < 0 or not point.id or not point.workload:
        raise ValueError("invalid backup contract")
    now, created, until = utc(now_utc), utc(point.created_utc), utc(point.immutable_until_utc)
    if created > now or until < created:
        raise ValueError("invalid backup timeline")
    age = (now-created).total_seconds()/60
    checks = {
        "freshness": age <= max_age_minutes,
        "checksum_format": len(point.checksum_sha256)==64 and all(c in "0123456789abcdef" for c in point.checksum_sha256),
        "regional_separation": point.source_region != point.replica_region,
        "account_isolation": point.isolated_account,
        "immutability": until > now,
        "restore": point.restore_verified,
        "key_access": point.encryption_key_accessible,
        "state_manifest": point.state_manifest_present,
    }
    return {"decision":"REVIEW_READY" if all(checks.values()) else "NO_GO",
            "age_minutes":age,
            "failed":[k for k,v in checks.items() if not v]}
```

This contract checks metadata and the **format** of a checksum, not the integrity of actual backup bytes. A real restore drill must independently hash and validate recovered data.

## 5. Lab B — Automated negative tests
Create `infrastructure-as-code/labs/chapter-102/test_backup_gate.py`:

```python
import unittest
from dataclasses import replace
from backup_gate import RecoveryPoint, validate, digest

class BackupGateTests(unittest.TestCase):
    def setUp(self):
        self.p=RecoveryPoint("rp-001","payments-postgres","2026-10-19T11:45:00Z",
            digest(b"synthetic"),"us-east-1","us-west-2",True,
            "2026-11-19T12:00:00Z",True,True,True)
        self.now="2026-10-19T12:00:00Z"
    def check(self,p):
        return validate(p,self.now,30)
    def test_valid(self):
        self.assertEqual(self.check(self.p)["decision"],"REVIEW_READY")
    def test_expired(self):
        self.assertIn("freshness",validate(self.p,self.now,10)["failed"])
    def test_isolation(self):
        for field,value in [
            ("replica_region","us-east-1"),("isolated_account",False),
            ("immutable_until_utc","2026-10-19T11:50:00Z"),
            ("restore_verified",False),("encryption_key_accessible",False),
            ("state_manifest_present",False),("checksum_sha256","bad")]:
            with self.subTest(field=field):
                self.assertEqual(self.check(replace(self.p,**{field:value}))["decision"],"NO_GO")
    def test_future_backup_rejected(self):
        with self.assertRaises(ValueError):
            self.check(replace(self.p,created_utc="2026-10-19T13:00:00Z"))
    def test_naive_utc_rejected(self):
        with self.assertRaises(ValueError):
            self.check(replace(self.p,created_utc="2026-10-19T11:45:00"))
    def test_negative_age_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.p,self.now,-1)
if __name__=="__main__":
    unittest.main()
```

Run from the repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-102 -p 'test_*.py' -v
```

The unit tests cover backup age, region/account isolation, immutability, restore evidence, key access, state manifest, checksum metadata and malformed timestamps.

## 6. Lab C — Backup policy as code (manual)
1. Inventory workloads and define recovery tiers, owners, retention and legal holds.
2. Author Terraform/OpenTofu resources for a **staging** backup vault/bucket, separate recovery account/project/subscription, backup schedule and cross-region copy where supported.
3. Run `terraform fmt -check`, `terraform validate`, and a reviewed `terraform plan`; confirm no production deletion or privilege escalation.
4. Validate encryption-at-rest, KMS key policy, least-privilege copy identity, audit logs and immutability configuration.
5. Trigger a staging backup; record API job ID, status, size, UTC recovery point, checksums where supported and copy completion.
6. Simulate loss of production credentials; verify the recovery identity can still enumerate and restore protected copies.
7. Prove source-account deletion permissions cannot remove immutable recovery copies during the required retention window **without actually attempting destructive deletion in production**.
8. Record evidence, plan diff, approvals and cleanup ownership.

## 7. Lab D — Restore validation and DBRE acceptance (manual)
1. Select a nonproduction recovery point with known application-consistent data.
2. Restore into an isolated staging VPC/VNet/project/cluster with restricted egress.
3. Recover IaC backend configuration, providers, modules, secrets and keys through the documented bootstrap path.
4. Restore CRDs/operators before Kubernetes custom resources; remap PV storage classes and validate workloads.
5. For PostgreSQL, verify WAL/PITR continuity, consistency queries, write transactions and replication. For MongoDB, validate oplog/shard consistency; for Redis/Kafka/Elasticsearch, validate workload-specific durability and data correctness.
6. Record last recoverable write, incident start, completed end-to-end transaction and observed RPO/RTO.
7. Inject a controlled failed restore (missing key, incomplete log archive or invalid snapshot) and demonstrate **NO-GO** escalation.
8. Tear down only disposable resources after owner approval; retain evidence and legally required backups.

## 8. Troubleshooting scenarios
| Scenario | Signal | Recovery |
|---|---|---|
| Backup schedule skipped | recovery point age | repair scheduler; re-run |
| Backup job partial | object count mismatch | retry and verify |
| Copy lag | source/destination timestamps | pause DR acceptance |
| Destination region unsupported | provider API error | redesign supported copy |
| Backup key inaccessible | KMS denial | approved break-glass |
| Immutable retention absent | delete permissions | stop acceptance |
| Lock configured incorrectly | retention mismatch | security review |
| Restore test stale | no recent proof | schedule drill |
| Snapshot corrupted | checksum/restore error | alternate known-good point |
| PITR log gap | WAL/oplog missing | choose valid point; fix archiving |
| Terraform state missing | backend object/version absent | isolated state recovery |
| Terraform provider missing | plugin lock mismatch | retrieve pinned artifact |
| Kubernetes PV zone mismatch | PVC Pending | restore compatible volume |
| Kubernetes CRD missing | unknown resource | restore CRDs/operators |
| Secrets cannot decrypt | key dependency | restore recovery key access |
| PostgreSQL WAL divergence | recovery timeline | fence and re-restore |
| MongoDB shard inconsistency | validation failure | consistent restore set |
| Redis RDB/AOF stale | data-loss estimate | assess RPO breach |
| Kafka metadata unavailable | topic/ACL mismatch | restore metadata |
| Elasticsearch snapshot incompatible | version error | supported target version |

## 9. Production runbooks
**RB-01 Backup freshness:** validate scheduler, provider job, source and destination recovery point, alert on stale RPO.

**RB-02 Cross-region copy:** confirm account isolation, encryption, destination integrity and copy latency.

**RB-03 Immutable retention:** verify object/vault lock policy, legal holds and separation of duties.

**RB-04 Key recovery:** validate independent KMS access and audited break-glass without exposing key material.

**RB-05 IaC state recovery:** restore versioned state into isolated backend; compare drift and obtain approval.

**RB-06 Kubernetes recovery:** restore CRDs, operators, RBAC, secrets, PVCs and applications in dependency order.

**RB-07 Database PITR:** choose consistent recovery point, verify log chain and application transactions.

**RB-08 Failed restore:** declare NO-GO, isolate failed environment, select alternate recovery point and preserve evidence.

**RB-09 RPO/RTO evidence:** capture UTC timestamps and independently validate business transactions.

**RB-10 Backup compromise:** quarantine credentials, confirm isolated copies and initiate incident response.

## 10. Enterprise acceptance assessment (100 points)
| Control | Points |
|---|---:|
| Workload inventory, RPO/RTO and ownership | 10 |
| Policy-as-code and schedule coverage | 10 |
| Cross-account/region isolation | 15 |
| Immutable retention and key independence | 15 |
| IaC state and Kubernetes recoverability | 15 |
| DBRE application-consistent restore/PITR | 15 |
| Timed restore drill and observed RPO/RTO | 10 |
| Audit, incident runbooks and approvals | 10 |
| **Total** | **100** |

**Go/no-go:** 90+ points and every mandatory gate passing: valid recoverable point, isolation, immutability, key access, successful restore, observed RPO/RTO, owner and SRE/DBRE sign-off. Missing any mandatory gate is **NO-GO** regardless of score.

## 11. Evidence, security and cleanup
Retain sanitized backup job IDs, policy diffs, UTC timestamps, destination-copy proof, recovery hashes, restore transaction results, RPO/RTO calculations, approval records and cleanup manifest. Never delete production backups or alter production KMS policies as part of a lab.

**Next:** Chapter 103 — IaC Cross-Region Disaster Recovery Orchestration, Failover, Fencing and Split-Brain Prevention.
