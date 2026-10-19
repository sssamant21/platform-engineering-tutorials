# Chapter 105 — Enterprise IaC Disaster Recovery, Multi-Region Resilience and Operational Acceptance Capstone

**Part 21 — Disaster Recovery · Chapter 105/120 · Enterprise SRE/DBRE**

> **Scope:** This is a capstone specification and offline validation model, not evidence of production DR readiness. The included code does not call cloud APIs, restore real databases, alter infrastructure, inject faults, promote writers or execute failover. Native drills, test execution and independent acceptance remain pending.

## 1. Capstone outcomes
Integrate Chapters 101–104 into a measurable disaster recovery program spanning AWS, Azure, GCP, Terraform/OpenTofu, Kubernetes/GitOps, PostgreSQL, MongoDB, Redis, Kafka and Elasticsearch. Demonstrate a recoverable IaC control plane, isolated immutable backups, application-consistent data restoration, single-writer fencing, regional recovery, measured RPO/RTO, rollback/failback and signed SRE/DBRE acceptance.

## 2. Enterprise scenario
An organization operates a Tier-1 payment API on Kubernetes, backed by PostgreSQL and Kafka, with Terraform-managed infrastructure, GitOps deployment, centralized secrets and multi-region cloud dependencies. A primary-region outage occurs during a planned backup window. The response team must decide whether to fail over, restore a point-in-time database, fence the old primary and reroute traffic without double writes.

**Recovery objectives (illustrative, not provider guarantees):** payment API RPO 15 minutes, RTO 60 minutes; noncritical analytics RPO 4 hours, RTO 24 hours. Teams must replace these with approved business impact analysis values and verify them under timed drills.

## 3. Recovery control plane architecture
```text
BIA + service catalog + owners + SLO/RPO/RTO
                    |
    GitOps / IaC plans / pinned provider artifacts
                    |
    Independent recovery identity and KMS access
                    |
 Immutable cross-account and cross-region backups
                    |
  Recovery region network + Kubernetes + DNS + PVs
                    |
  Database PITR + replication lag + quorum + fencing
                    |
  Service cutover + synthetic business transaction
                    |
 Timed RPO/RTO + data integrity + rollback/failback
                    |
 Independent evidence review + acceptance decision
```

An independent recovery region is insufficient if it depends on a failed source-region state backend, registry, KMS key, identity provider or DNS control plane. Map all dependencies before the exercise.

## 4. Required artifacts
- Approved business impact analysis and per-service RPO/RTO.
- Source/target region and account/subscription/project architecture.
- Versioned Terraform/OpenTofu state backup and backend bootstrap runbook.
- Backup manifest with immutable retention, verified keys, recovery points, checksum/integrity evidence and copy isolation.
- Kubernetes dependency graph, CRDs/operators, RBAC, secrets, PV and ingress recovery plan.
- Database-specific consistent backup/PITR and quorum/fencing procedures.
- Fault experiment plan with authorization, blast radius, abort thresholds and stop switch.
- End-to-end service transaction probes and telemetry dashboards.
- Timed incident and recovery evidence with approvers, audit trail and remediation backlog.

## 5. End-to-end recovery sequence
1. **Declare incident:** record UTC start, scope, customer impact, commander, change freeze and service tiers.
2. **Protect evidence:** retain logs, WAL/oplog/offsets, replication positions, backup manifests, state versions and audit trails.
3. **Check recoverability:** validate independent immutable copies, encryption keys, credentials, destination capacity and last known-good restore point.
4. **Establish authority:** inspect quorum/lease; fence the old writer before promoting a new one. Network unreachability is not fencing.
5. **Rebuild IaC bootstrap:** restore an isolated backend, pinned modules/providers and recovery identity; review Terraform/OpenTofu plan before applying.
6. **Restore Kubernetes:** provision recovery networking, cluster, CRDs/operators, RBAC, secrets, storage, workloads and ingress in dependency order.
7. **Recover databases:** validate PostgreSQL PITR/WAL, MongoDB replica/shard consistency, Redis durability, Kafka quorum/offsets and Elasticsearch snapshots as relevant.
8. **Switch staging traffic:** verify the sole writer and use isolated DNS/edge routes for a rehearsal.
9. **Validate business recovery:** run read/write transactions, checksums, idempotency, authentication, p99 and error-budget checks.
10. **Measure objectives:** calculate observed RPO from last recoverable acknowledged write and observed RTO from customer impact to successful business transaction.
11. **Rollback/failback:** reconcile divergent data, fence obsolete writers and switch back only after separate authorization.
12. **Close and improve:** archive evidence, score controls, record failures, assign remediation owners and schedule a repeat drill.

## 6. Lab A — Offline 100-point enterprise acceptance gate

Create `infrastructure-as-code/labs/chapter-105/acceptance_gate.py`:

```python
"""Offline enterprise DR capstone evidence gate. Never initiates failover."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Acceptance:
    service: str
    rpo_target_minutes: int
    rpo_observed_minutes: int
    rto_target_minutes: int
    rto_observed_minutes: int
    immutable_copy_verified: bool
    independent_keys_verified: bool
    state_restore_verified: bool
    kubernetes_restore_verified: bool
    database_integrity_verified: bool
    old_primary_fenced: bool
    quorum_verified: bool
    business_transaction_verified: bool
    rollback_verified: bool
    evidence_complete: bool
    sre_signed: bool
    dbre_signed: bool

WEIGHTS = {
    "rpo":10, "rto":10, "immutable_copy":10, "independent_keys":5,
    "state_restore":10, "kubernetes_restore":10, "database_integrity":15,
    "fencing":10, "quorum":5, "business_transaction":5,
    "rollback":5, "evidence":3, "sre_signoff":1, "dbre_signoff":1,
}
assert sum(WEIGHTS.values()) == 100

def assess(e: Acceptance):
    if not e.service or any(v < 0 for v in (
        e.rpo_target_minutes,e.rpo_observed_minutes,
        e.rto_target_minutes,e.rto_observed_minutes)):
        raise ValueError("invalid service or recovery objective")
    checks = {
        "rpo": e.rpo_observed_minutes <= e.rpo_target_minutes,
        "rto": e.rto_observed_minutes <= e.rto_target_minutes,
        "immutable_copy": e.immutable_copy_verified,
        "independent_keys": e.independent_keys_verified,
        "state_restore": e.state_restore_verified,
        "kubernetes_restore": e.kubernetes_restore_verified,
        "database_integrity": e.database_integrity_verified,
        "fencing": e.old_primary_fenced,
        "quorum": e.quorum_verified,
        "business_transaction": e.business_transaction_verified,
        "rollback": e.rollback_verified,
        "evidence": e.evidence_complete,
        "sre_signoff": e.sre_signed,
        "dbre_signoff": e.dbre_signed,
    }
    score = sum(WEIGHTS[k] for k, ok in checks.items() if ok)
    mandatory = ("rpo","rto","immutable_copy","independent_keys","state_restore",
                 "database_integrity","fencing","quorum","business_transaction",
                 "evidence","sre_signoff","dbre_signoff")
    failed = [k for k,v in checks.items() if not v]
    return {"score":score,
            "decision":"REVIEW_READY" if score >= 90 and all(checks[k] for k in mandatory) else "NO_GO",
            "failed":failed}
```

A result of `REVIEW_READY` means the **synthetic** evidence meets the modeled threshold. It never constitutes production approval.

## 7. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-105/test_acceptance_gate.py`:

```python
import unittest
from dataclasses import replace
from acceptance_gate import Acceptance, assess

class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.good=Acceptance("payments",15,5,60,25,
            True,True,True,True,True,True,True,True,True,True,True,True)
    def test_valid(self):
        self.assertEqual(assess(self.good)["score"],100)
        self.assertEqual(assess(self.good)["decision"],"REVIEW_READY")
    def test_all_mandatory_fail_closed(self):
        mandatory=("immutable_copy_verified","independent_keys_verified",
                   "state_restore_verified","database_integrity_verified",
                   "old_primary_fenced","quorum_verified","business_transaction_verified",
                   "evidence_complete","sre_signed","dbre_signed")
        for field in mandatory:
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.good,**{field:False}))["decision"],"NO_GO")
    def test_rpo_breach(self):
        self.assertIn("rpo",assess(replace(self.good,rpo_observed_minutes=16))["failed"])
    def test_rto_breach(self):
        self.assertIn("rto",assess(replace(self.good,rto_observed_minutes=61))["failed"])
    def test_score_threshold(self):
        e=replace(self.good,kubernetes_restore_verified=False,rollback_verified=False)
        self.assertEqual(assess(e)["score"],85)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_negative_time(self):
        with self.assertRaises(ValueError):
            assess(replace(self.good,rpo_target_minutes=-1))
if __name__=="__main__":
    unittest.main()
```

Run from the repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-105 -p 'test_*.py' -v
```

These tests check mandatory-control failures, RPO/RTO breaches, score threshold and invalid inputs. Tests are authored; successful execution must be separately recorded.

## 8. Lab C — Isolated multi-region disaster recovery capstone (manual)
1. Establish a disposable staging primary region and recovery region using approved quotas and budgets.
2. Seed synthetic PostgreSQL and Kafka data with immutable record IDs and checksums; capture acknowledged writes and offsets.
3. Verify backup isolation, immutability, restore key availability, recovery identity, IaC state and container artifacts.
4. Capture baseline application SLO, database replication lag, quorum state, Kubernetes capacity and backup freshness.
5. Simulate primary-region unavailability only in staging; trigger incident communications and stop-condition checks.
6. Confirm old-primary fencing and quorum independently before any write promotion.
7. Recover IaC backend and region infrastructure; restore or promote databases using platform-supported procedures.
8. Recover Kubernetes resources and application secrets in dependency order.
9. Cut over staging traffic; verify exactly one writer and execute representative payment-like idempotent transactions.
10. Compare checksums, Kafka offsets, WAL positions and business invariants; measure RPO/RTO with UTC timestamps.
11. Exercise controlled rollback and failback after data reconciliation.
12. Preserve logs, plans, change IDs, approvals, screenshots and signed acceptance evidence; destroy only authorized staging resources.

## 9. Failure injection and troubleshooting matrix
| Failure | Key signal | Safe action |
|---|---|---|
| Regional outage | failed regional probes | declare DR, verify recovery dependencies |
| Split-brain risk | two writable primaries | stop promotion, fence |
| Quorum loss | election/member state | restore majority |
| Stale replica | lag exceeds RPO | select valid recovery point |
| WAL/PITR gap | missing archive segment | reject target point |
| MongoDB inconsistent shard restore | integrity mismatch | restore consistent set |
| Redis stale AOF/RDB | persistence age | classify lost writes |
| Kafka ISR loss | under-replicated partitions | restore replicas |
| Elasticsearch snapshot error | restore failure | choose compatible snapshot |
| IaC backend unavailable | state API errors | isolated state recovery |
| Terraform state conflict | unexpected plan drift | halt apply and review |
| GitOps overwrites DR change | reconciliation events | scope/pause controller |
| KMS key inaccessible | decrypt denial | audited break-glass |
| Registry unavailable | image pull errors | verified image mirror |
| Kubernetes PV mismatch | PVC Pending | restore supported class |
| DNS cutover delayed | resolver cache | verify traffic routing |
| Immutable backup missing | retention policy absent | NO-GO |
| Restore succeeds but writes fail | business transaction error | recover application dependencies |
| RTO exceeded | incident timeline | record breach, remediate |
| Rollback cannot complete | divergence or missing plan | preserve writer and escalate |

## 10. Production runbooks
**RB-01 DR declaration:** establish incident command, communications, service tiers, freeze and change authority.

**RB-02 Backup recovery:** validate isolated immutable copies, recovery point, key access and restore integrity.

**RB-03 IaC state bootstrap:** recover state into separate backend, pin artifacts and review plan.

**RB-04 Kubernetes recovery:** restore cluster services, CRDs/operators, secrets, PVs, workloads and ingress.

**RB-05 DBRE PITR:** choose consistent point, validate replay/log chain and transaction correctness.

**RB-06 Writer fencing:** verify authoritative lease/quorum, disable old writer and record evidence.

**RB-07 Regional traffic cutover:** switch approved routes, validate authentication, SLO and transactions.

**RB-08 Emergency rollback:** stop unsafe writes, preserve logs, restore known-good single writer.

**RB-09 Failback:** reconcile divergence, obtain separate approval and validate recovery after return.

**RB-10 Enterprise acceptance:** calculate RPO/RTO, score controls, archive audit trail and sign decision.

## 11. 100-point acceptance and hard gates

| Domain | Points |
|---|---:|
| Observed RPO within approved objective | 10 |
| Observed RTO within approved objective | 10 |
| Immutable isolated recovery copy | 10 |
| Independent encryption key access | 5 |
| Terraform/OpenTofu state restore | 10 |
| Kubernetes application restore | 10 |
| Database data integrity | 15 |
| Old-primary fencing | 10 |
| Quorum verification | 5 |
| Verified business transaction | 5 |
| Rollback proof | 5 |
| Complete audit evidence | 3 |
| SRE and DBRE sign-off | 2 |
| **Total** | **100** |

**Score threshold:** 90/100. **Mandatory gates:** RPO, RTO, immutable copy, independent keys, state recovery, database integrity, fencing, quorum, business transaction, evidence and both sign-offs. A missing mandatory gate produces **NO-GO** regardless of score. The offline gate omits live evidence authenticity; reviewers must independently verify source artifacts.

## 12. Security, cleanup and final acceptance
Never run destructive chaos experiments against production without a separate approved change, tested stop mechanism and on-call coverage. Never delete production backups, manually overwrite live Terraform state, force database elections or bypass KMS controls as a tutorial exercise. Clean only disposable staging resources and retain legally required backup and audit artifacts.

**Part 21 publication completion does not imply production DR certification.** Real cloud provider restore tests, data correctness, timed failover/failback, security review and independent SRE/DBRE acceptance are outstanding until evidenced.

**Next:** Chapter 106 — Enterprise IaC Platform Architecture, Multi-Team Operating Models and Golden Paths.
