# Chapter 101 — IaC Disaster Recovery Foundations, RPO/RTO, Backup Architecture and Recovery Design

**Part 21 — Disaster Recovery · Chapter 101/120 · Enterprise SRE/DBRE**

> **Safety boundary:** Labs are offline and synthetic unless explicitly marked manual. They do not create infrastructure, delete backups, modify Terraform state, trigger failover or certify a production recovery. Authored tests and native DR acceptance must be independently verified.

## 1. Learning objectives

Design service-tier DR strategies for AWS, Azure, GCP, Kubernetes and database platforms; calculate and measure recovery point objective (RPO) and recovery time objective (RTO); distinguish HA from DR; protect IaC state and bootstrap dependencies; choose backup, replication and failover patterns; and implement evidence-based recovery acceptance.

**Prerequisites:** Chapters 026–030 (IaC state), 051–055 (Kubernetes), 081–090 (security/testing), 091–095 (SLOs), and familiarity with database PITR, DNS, KMS, IAM and object storage.

## 2. Recovery theory and terminology

- **RPO:** Maximum tolerable data loss measured as time between the last recoverable committed point and failure. An RPO of 15 minutes requires a recoverable point no more than 15 minutes before the event.
- **RTO:** Maximum tolerable time to restore the agreed service capability, not merely to boot a VM or promote a database.
- **MTTR:** Observed repair/recovery duration; historical MTTR is not an RTO guarantee.
- **HA:** Resilience to expected component failures within an availability domain; **DR** addresses broader domain loss, corruption, ransomware and systemic misconfiguration.
- **Backup:** A recoverable, integrity-checked copy; replication alone is not a backup because deletions and corruption may propagate.
- **PITR:** Point-in-time restore with base backups plus ordered log/WAL/oplog/archive coverage.
- **Recovery dependency:** Any identity, encryption, network, DNS, secret, registry, state, provider or human authorization required to restore service.

Calculate **observed RPO = failure time − timestamp of last successfully recoverable point**, and **observed RTO = business-impact start − end of restored-service validation**, with both expressed in the same UTC time basis. If the recovery point or end-to-end service validation is unknown, RPO/RTO must be marked **unverified**, not zero.

## 3. Enterprise reference architecture

```text
Criticality / BIA / service inventory / data ownership
                         |
          RPO + RTO + recovery dependency graph
                         |
   IaC Git + artifact registry + versioned state snapshots
                         |
     AWS / Azure / GCP + Kubernetes control plane
                         |
   immutable backups + cross-account / cross-region copies
                         |
      isolated IAM/KMS/secrets/DNS bootstrap capability
                         |
   PITR + app-consistent restore + replica/failover validation
                         |
     traffic switch + end-to-end service SLO verification
                         |
      reconciliation + evidence + DR acceptance record
```

**Trust boundaries:** A compromised production identity must not be able to delete immutable backup copies or revoke recovery keys. Separate backup administration, recovery operations, application ownership and final approval. Recovery environments require independent DNS, IAM, KMS and networking paths where feasible.

## 4. Select a recovery strategy

| Strategy | Typical fit | Major limitation |
|---|---|---|
| Backup and restore | Cost-sensitive workloads with longer RTO | Rebuild, data transfer and restore duration |
| Pilot light | Critical data with minimal warm compute | Scaling, bootstrap and dependency readiness |
| Warm standby | Shorter RTO with reduced duplicate capacity | Continuous replication and operating expense |
| Active/active | Very low service interruption targets | Split-brain, conflict resolution, consistency |
| Cross-region replica | Regional loss | Corruption/deletion may replicate |
| Immutable cross-account backup | Ransomware/credential compromise | Requires tested key and identity recovery |

Do not assign numeric RPO/RTO guarantees to a pattern without timed drills under realistic load and failure scope.

## 5. Cloud and IaC design controls

### AWS
Evaluate AWS Backup vault lock and cross-account/cross-region copies, S3 versioning/Object Lock, RDS/Aurora automated backups and PITR, EBS snapshots, EKS cluster configuration and workload backups, Route 53, KMS grants and IAM break-glass. Confirm regional service limits and key availability in the recovery account.

### Azure
Evaluate Azure Backup/Recovery Services vaults, immutable vault protection where supported, Azure Site Recovery, Azure Database PITR, AKS manifests/PVs, Key Vault, managed identities, Azure DNS and paired-region constraints. Validate backup policy and restore workflow per workload, not just vault status.

### GCP
Evaluate Backup and DR Service, Cloud Storage retention/lock, Cloud SQL PITR, Persistent Disk snapshots, GKE Backup for GKE, Cloud KMS, IAM and Cloud DNS. Verify project-level separation, supported region locations and restoration of service accounts and encryption keys.

### Terraform / OpenTofu
Store encrypted, versioned state with access logging and recovery snapshots. Keep backend bootstrap code and emergency credentials outside the failed state dependency. Pin provider/module versions; retain lockfiles, module artifacts and environment configuration. Never manually overwrite production state to make a drill pass. Test state recovery against an isolated staging backend.

### Kubernetes
Back up application configuration, CRDs, admission policies, namespace RBAC, secrets **with protected keys**, PV data and operators' custom resources. An etcd snapshot is relevant for self-managed control planes but is not a substitute for application-consistent database backups; managed control planes may not expose etcd. Restore CRDs/operators before dependent custom resources, then workloads and traffic. Verify storage classes, CSI snapshots, ingress, certificates, CNI, DNS and admission behavior.

### DBRE workload requirements
PostgreSQL: base backup, WAL archive continuity, PITR target, replication slots, extension/version compatibility, integrity checks and promotion fencing.

MongoDB: consistent replica/shard backup, oplog coverage, config-server/shard metadata, elections and read/write correctness.

Redis: RDB/AOF durability configuration, replication lag, persistence and application tolerance for lost writes.

Kafka: topic/partition metadata, broker configuration, replication/ISR, offsets, ACLs and recoverable data retention.

Elasticsearch: repository snapshots, cluster/index metadata, version compatibility, shard recovery and query correctness.

For all stateful workloads, verify consistency at the **application level**, not just that pods are Running.

## 6. Hands-on lab A — Offline DR acceptance gate

Create `infrastructure-as-code/labs/chapter-101/dr_gate.py`:

```python
"""Offline DR policy evaluator. No provider APIs or destructive actions."""
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class RecoveryEvidence:
    service: str
    tier: str
    rpo_target_minutes: int
    rto_target_minutes: int
    latest_recoverable_point: str
    outage_started: str
    service_restored: str
    backup_immutable: bool
    restore_test_passed: bool
    state_recoverable: bool
    secrets_recoverable: bool
    region_independent: bool
    owner_approved: bool

def parse_utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamps must be explicitly UTC")
    return parsed

def evaluate(e):
    if not e.service or e.rpo_target_minutes < 0 or e.rto_target_minutes < 0:
        raise ValueError("invalid recovery contract")
    backup = parse_utc(e.latest_recoverable_point)
    outage = parse_utc(e.outage_started)
    restored = parse_utc(e.service_restored)
    if backup > outage or restored < outage:
        raise ValueError("inconsistent recovery timeline")
    observed_rpo = (outage - backup).total_seconds() / 60
    observed_rto = (restored - outage).total_seconds() / 60
    checks = {
        "rpo": observed_rpo <= e.rpo_target_minutes,
        "rto": observed_rto <= e.rto_target_minutes,
        "immutable_backup": e.backup_immutable,
        "restore_test": e.restore_test_passed,
        "iac_state": e.state_recoverable,
        "secrets": e.secrets_recoverable,
        "failure_domain": e.region_independent,
        "approval": e.owner_approved,
    }
    return {
        "decision": "REVIEW_READY" if all(checks.values()) else "NO_GO",
        "observed_rpo_minutes": observed_rpo,
        "observed_rto_minutes": observed_rto,
        "failed_controls": [k for k, ok in checks.items() if not ok],
    }
```

Use a synthetic service outage, immutable-backup evidence, IaC-state recovery evidence and independent approvals. The output `REVIEW_READY` means only that the modeled controls passed; it is not production authorization.

## 7. Hands-on lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-101/test_dr_gate.py`:

```python
import unittest
from dataclasses import replace
from dr_gate import RecoveryEvidence, evaluate

class DisasterRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.good = RecoveryEvidence(
            "orders-db", "tier-1", 15, 60,
            "2026-10-19T11:50:00Z", "2026-10-19T12:00:00Z",
            "2026-10-19T12:35:00Z",
            True, True, True, True, True, True)

    def test_valid_evidence(self):
        result = evaluate(self.good)
        self.assertEqual(result["decision"], "REVIEW_READY")
        self.assertEqual(result["observed_rpo_minutes"], 10)
        self.assertEqual(result["observed_rto_minutes"], 35)

    def test_rpo_breach(self):
        result = evaluate(replace(self.good, latest_recoverable_point="2026-10-19T11:30:00Z"))
        self.assertIn("rpo", result["failed_controls"])

    def test_rto_breach(self):
        result = evaluate(replace(self.good, service_restored="2026-10-19T13:30:00Z"))
        self.assertIn("rto", result["failed_controls"])

    def test_missing_controls_fail_closed(self):
        fields = ["backup_immutable", "restore_test_passed", "state_recoverable",
                  "secrets_recoverable", "region_independent", "owner_approved"]
        for field in fields:
            with self.subTest(field=field):
                result = evaluate(replace(self.good, **{field: False}))
                self.assertEqual(result["decision"], "NO_GO")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.good, outage_started="2026-10-19T12:00:00"))

    def test_future_backup_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.good, latest_recoverable_point="2026-10-19T12:01:00Z"))

    def test_negative_rpo_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.good, rpo_target_minutes=-1))

if __name__ == "__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-101 -p 'test_*.py' -v
```

The tests cover RPO and RTO breaches, missing backup/restore/state/secrets/region/approval controls, invalid timestamps and impossible recovery timelines.

## 8. Hands-on lab C — Recovery dependency inventory (manual)

1. Inventory service tier, owner, customer impact, regulatory retention, data stores, RPO/RTO targets and recovery region.
2. Map Git, Terraform state backend, object storage, IAM/SSO, KMS, DNS, CI/CD, container registry, secrets, network and observability dependencies.
3. Identify circular bootstrap dependencies: for example, restoring KMS access cannot depend on a Kubernetes service that itself requires that KMS key.
4. Capture backup policy, immutable retention, restore point timestamps, replica lag, encryption key access and regional separation.
5. Create an isolated recovery account/project/subscription and staging namespace; never test by deleting production resources.
6. Restore an approved nonproduction snapshot, rebuild IaC using a separate backend and compare against expected configuration.
7. Verify data checksums, read/write transactions, user authentication, service routing, p99 latency and error budget.
8. Record start/end timestamps, observed RPO/RTO, incident commander, DBRE owner, SRE reviewer and evidence hashes.

**Acceptance:** A successful API response without restored data correctness or dependency validation is insufficient.

## 9. Hands-on lab D — Failure injection and rollback (manual)

Run authorized drills for (a) a single node/AZ outage, (b) loss of the primary database, (c) a corrupted backup, (d) inaccessible KMS key, (e) unavailable Terraform backend, (f) DNS propagation delay and (g) compromised production credentials. Test with synthetic or isolated staging data. Use a documented stop condition, business owner approval and clean rollback. For each scenario, measure recovery milestones and record whether objectives were met.

## 10. Troubleshooting scenarios

| Failure | Investigation | Safe recovery |
|---|---|---|
| Backup exists but restore fails | format, permissions, encryption, integrity | restore known-good point |
| RPO breach | log archive gap, lag, snapshot age | stop promotion, repair pipeline |
| RTO breach | bootstrap bottleneck, restore throughput | increase tested recovery capacity |
| Terraform state unavailable | backend region, IAM, locks | isolated versioned state recovery |
| Recovery key inaccessible | KMS/IAM grants | break-glass key procedure |
| DNS switch ineffective | TTL, resolver caches | validated traffic steering |
| Split-brain after failover | fencing and leader ownership | fence old primary |
| PostgreSQL WAL missing | archive continuity | select valid PITR boundary |
| MongoDB inconsistent restore | shard/replica consistency | restore consistent set |
| Redis stale persistence | RDB/AOF timestamp | assess tolerated loss |
| Kafka ISR collapse | replicas, disk, network | restore quorum/replicas |
| Kubernetes PV unavailable | CSI, zone, class | restore to compatible storage |
| CRD restoration blocked | operator ordering | restore CRDs first |
| Container registry down | image availability | use verified mirrored images |
| Backup deletion attempt | immutable policy | isolate credentials, audit |
| Observability blind spot | telemetry independence | use out-of-band probes |
| App writes fail after DR | secrets, permissions, routing | repair dependencies |
| Data checksum mismatch | restore consistency | quarantine and re-restore |
| Recovery site underprovisioned | quotas and capacity | pre-reserve resources |
| Recovery drill no evidence | missing timestamps/owner | classify as unverified |

## 11. Production runbooks

**RB-01 Declare disaster:** confirm scope, customer impact, incident commander, change freeze, communication and recovery objectives.

**RB-02 Restore IaC state:** validate immutable/versioned state, restore to isolated backend, compare plans, approve controlled reconciliation.

**RB-03 Recover encryption and identity:** use audited break-glass, validate least privilege and revoke emergency credentials after recovery.

**RB-04 Restore Kubernetes platform:** validate cluster, CNI/CSI, CRDs, operators, RBAC, workloads, ingress and external dependencies.

**RB-05 Restore database:** select verified recovery point, run application-consistent restore, validate checksums and replication, obtain DBRE approval.

**RB-06 Regional failover:** verify fencing, activate recovery region, switch traffic, confirm end-to-end transactions and SLO.

**RB-07 RPO/RTO evidence:** record UTC outage start, latest recoverable commit, restored business transaction, gaps and reviewer.

**RB-08 Failback:** assess data divergence, reconcile, schedule reversible migration and preserve audit evidence.

**RB-09 Compromised backup identity:** quarantine credentials, verify immutable copies and independently accessible keys.

**RB-10 Post-incident:** reconcile lost writes, document impact, create remediation owners and schedule a new recovery drill.

## 12. Enterprise DR acceptance (100 points)

| Domain | Points |
|---|---:|
| Business impact and RPO/RTO contracts | 10 |
| Backup integrity, immutability and isolation | 15 |
| IaC state and bootstrap recovery | 15 |
| Cloud and Kubernetes dependency recovery | 10 |
| DBRE consistent restore and PITR | 20 |
| Regional failover, fencing and failback | 10 |
| Observed RPO/RTO and service SLO evidence | 10 |
| Runbooks, approval, audit and security | 10 |
| **Total** | **100** |

**Production acceptance:** at least 90/100 **and** all mandatory gates: recoverable state, successful application-consistent restore, observed RPO/RTO within target, verified fencing, accessible independent recovery credentials and signed SRE/DBRE approval. A failed mandatory gate is **NO-GO** regardless of score.

## 13. Cleanup and evidence

Preserve sanitized test reports, state/backup hashes, UTC timeline, restore validation, approval records, incident notes and RPO/RTO calculations. Delete only explicitly authorized disposable staging resources. Do not delete production backups, rotate live KMS keys or alter production state during this exercise.

**Next:** Chapter 102 — IaC Backup Automation, Cross-Region Replication, Immutable Recovery Points and Recovery Validation.
