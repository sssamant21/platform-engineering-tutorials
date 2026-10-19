# Chapter 103 — IaC Cross-Region Disaster Recovery Orchestration, Failover, Fencing and Split-Brain Prevention

**Part 21 — Disaster Recovery · Chapter 103/120 · Enterprise SRE/DBRE**

> **Safety:** The included Python code is a synthetic offline decision gate. It does not promote databases, modify DNS, revoke identities, execute Terraform/OpenTofu, or cause a real failover. Live disaster recovery drills and independent production acceptance remain pending.

## 1. Learning objectives
Design and rehearse cross-region recovery orchestration for AWS, Azure, GCP, Kubernetes and stateful services; distinguish planned switchover from emergency failover; prevent dual-primary split brain; measure RPO/RTO; implement IaC and GitOps recovery workflows; and enforce independent approvals.

**Prerequisites:** Chapters 101–102, database replication and consistency, Kubernetes networking, Terraform/OpenTofu state, cloud IAM/KMS and SLO incident response.

## 2. Reference architecture

```text
Business impact + recovery objectives + dependency inventory
                         |
     Primary region: app + database + IaC state
                         |
        independent monitoring and failure detection
                         |
      incident commander + SRE/DBRE authorization
                         |
       fence old primary / lease / quorum verification
                         |
   target region: IAM/KMS, network, IaC bootstrap, K8s
                         |
     recover data + validate replica lag / PITR
                         |
    promote single writer + reconcile state + warm apps
                         |
        traffic cutover + end-to-end transactions
                         |
    observe SLO, measure RPO/RTO, preserve evidence
                         |
       controlled failback only after reconciliation
```

**Non-negotiable:** DNS cutover alone does not fence a database writer. A network partition is not proof that the old primary is stopped. Promotion requires authoritative fencing and quorum/lease semantics appropriate to the data platform.

## 3. Cross-region design patterns

| Pattern | Recovery posture | Main risk |
|---|---|---|
| Cold restore | Rebuild and restore isolated backups | Longer RTO |
| Pilot light | Data/services partly warm | Bootstrap dependencies |
| Warm standby | Replicated data and ready compute | Lag and cost |
| Active/active | Both regions serve traffic | Conflict resolution and split brain |
| Active/passive database | One authoritative writer | Promotion and fencing |
| Multi-region object backup | Immutable recoverable copies | Key and access dependencies |

Document consistency semantics, replication mode, regional quotas, encryption keys, identity, certificates, container images, observability and third-party dependencies. The selected pattern does not guarantee RPO/RTO without observed drills.

## 4. Fencing and split-brain prevention

1. Identify authoritative membership and leadership source: consensus quorum, external lease, managed service control plane or storage fencing.
2. Stop old-primary writes through supported service-specific mechanisms; do not assume a failed health probe means the node is offline.
3. Verify old-primary fencing through an independent signal before granting write authority to the recovery target.
4. Confirm replica replay position and allowable data loss; if lag breaches RPO, require incident-level exception or reject.
5. Record a monotonically increasing leadership epoch or equivalent fencing token where the system supports it.
6. Restrict write credentials and network routes to the elected writer; avoid two independently writable endpoints.
7. Preserve write-ahead/operation logs and evidence for reconciliation and failback.
8. Block automatic promotion if quorum, fencing or recovery ownership is ambiguous.

For PostgreSQL, use a tested HA manager/consensus and STONITH or equivalent fencing; for MongoDB, respect replica-set election majority and avoid force reconfigurations without DBRE review; for Kafka, preserve controller quorum and ISR safety; for Redis, validate Sentinel/cluster promotion semantics and data-loss tolerance. Managed cloud database failover APIs have distinct guarantees: confirm provider behavior rather than applying generic commands.

## 5. Cloud, IaC and Kubernetes orchestration

**AWS:** Account and region separation, Route 53 health/routing, VPC connectivity, KMS grants, AWS Backup/RDS/Aurora regional capabilities, EKS, IAM and cross-region state bootstrap. Evaluate recovery-region quotas and service-specific failover behavior.

**Azure:** Azure DNS/Traffic Manager/Front Door as applicable, paired or chosen regions, Azure Site Recovery, Azure Backup, Azure Database failover groups where supported, AKS, Key Vault and managed identities.

**GCP:** Cloud DNS and load balancing, regional resource placement, Cloud SQL cross-region replicas where supported, GKE, Cloud KMS, IAM and project-level separation.

**Terraform/OpenTofu:** Keep recovery bootstrap independent of the failed remote backend. Protect provider lockfiles, module versions and state snapshots; run `plan` in isolated recovery environment, review drift and destructive changes, and avoid simultaneous writers to the same state. Use separate state backends/workspaces with clearly documented ownership.

**Kubernetes/GitOps:** Restore CNI/CSI, admission, CRDs, operators, secrets, PVs, controllers, workloads and ingress in dependency order. Prevent two clusters from reconciling the same singleton database writer or external resource. GitOps reconciliation must be paused or scoped during a failover if it would revert emergency traffic or role changes.

## 6. Hands-on lab A — Offline failover decision gate

Create `infrastructure-as-code/labs/chapter-103/failover_gate.py`:

```python
"""Offline failover authorization model; never controls production routing."""
from dataclasses import dataclass

@dataclass(frozen=True)
class FailoverEvidence:
    primary_fenced: bool
    quorum_verified: bool
    replica_lag_seconds: int
    max_lag_seconds: int
    backup_restorable: bool
    recovery_keys_ready: bool
    target_capacity_ready: bool
    dns_ready: bool
    incident_commander_approved: bool
    dbre_approved: bool
    rollback_plan_ready: bool

def decide(e: FailoverEvidence):
    if e.replica_lag_seconds < 0 or e.max_lag_seconds < 0:
        raise ValueError("negative lag is invalid")
    checks = {
        "fencing": e.primary_fenced,
        "quorum": e.quorum_verified,
        "lag": e.replica_lag_seconds <= e.max_lag_seconds,
        "backup": e.backup_restorable,
        "keys": e.recovery_keys_ready,
        "capacity": e.target_capacity_ready,
        "dns": e.dns_ready,
        "incident_approval": e.incident_commander_approved,
        "dbre_approval": e.dbre_approved,
        "rollback": e.rollback_plan_ready,
    }
    return {"decision": "REHEARSAL_READY" if all(checks.values()) else "BLOCK",
            "failed": [k for k, v in checks.items() if not v]}
```

`REHEARSAL_READY` authorizes **only further human-reviewed staging rehearsal**, never live promotion.

## 7. Hands-on lab B — Unit and negative tests

Create `infrastructure-as-code/labs/chapter-103/test_failover_gate.py`:

```python
import unittest
from dataclasses import replace
from failover_gate import FailoverEvidence, decide

class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.safe = FailoverEvidence(True,True,4,15,True,True,True,True,True,True,True)
    def test_ready(self):
        self.assertEqual(decide(self.safe)["decision"],"REHEARSAL_READY")
    def test_each_control_fail_closed(self):
        for field in ("primary_fenced","quorum_verified","backup_restorable",
                      "recovery_keys_ready","target_capacity_ready","dns_ready",
                      "incident_commander_approved","dbre_approved","rollback_plan_ready"):
            with self.subTest(field=field):
                self.assertEqual(decide(replace(self.safe,**{field:False}))["decision"],"BLOCK")
    def test_lag(self):
        self.assertIn("lag",decide(replace(self.safe,replica_lag_seconds=30))["failed"])
    def test_negative_lag(self):
        with self.assertRaises(ValueError):
            decide(replace(self.safe,replica_lag_seconds=-1))
if __name__=="__main__":
    unittest.main()
```

Run from the repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-103 -p 'test_*.py' -v
```

## 8. Hands-on lab C — Isolated regional switchover drill (manual)

1. Inventory service tier, RPO/RTO, current writer, database topology, replication lag, network routes, DNS TTL, IaC state backend and recovery identities.
2. Establish an isolated staging primary and recovery region with synthetic data. Capture last acknowledged writes and checksums.
3. Verify independently recoverable IAM/KMS, state, secrets, container registry, observability and backup copies.
4. Run a reviewed Terraform/OpenTofu `plan` for recovery infrastructure; check region, quotas, access policy and state locking.
5. Simulate loss of the primary endpoint, then **explicitly fence the staging primary** with a platform-supported mechanism.
6. Verify fencing from a second independent observer; if inconclusive, stop the drill.
7. Confirm target replica position and permitted data loss; promote only using approved DBRE procedures.
8. Reconcile Kubernetes resources, deploy application dependencies and switch staging traffic.
9. Execute read/write business transactions and validate single-writer invariants, p99, error budget, integrity and customer-facing routing.
10. Record outage start, last recoverable write and successful transaction times; calculate observed RPO/RTO.
11. Reconcile divergence and rehearse controlled failback only after owner approval.
12. Restore original staging topology, revoke temporary access and preserve evidence.

**Abort criteria:** dual-writer possibility, unverified fencing, lost quorum, missing keys, replica lag beyond approved RPO, unexpected Terraform replacement, broken backups, or missing on-call ownership.

## 9. Hands-on lab D — Chaos and failure matrix (manual)

Test these cases in disposable environments: primary-region outage, isolated network partition, stale DNS cache, inaccessible KMS key, replica lag spike, Terraform backend loss, Kubernetes controller reconciliation conflict, unavailable container registry, restore point corruption, and recovery-region capacity exhaustion. For each case document trigger, blast radius, detection, safe decision, rollback, observed RPO/RTO and reviewer.

## 10. Troubleshooting scenarios

| Scenario | Evidence | Safe action |
|---|---|---|
| Old writer still reachable | independent write probe | block promotion; fence |
| Lost quorum | membership/lease logs | halt elections |
| Replica lag exceeds RPO | replay timestamp | use alternate restore point |
| DNS cutover delayed | resolver traces | verify TTL and routing |
| Two GitOps controllers conflict | reconciliation events | suspend conflicting sync |
| Terraform state lock held | backend lock owner | investigate; never force blindly |
| Recovery KMS denied | key grants | audited break-glass |
| DR region quota exceeded | capacity errors | reserve approved capacity |
| PostgreSQL split-brain risk | leader epoch, writes | fence old primary |
| MongoDB minority election | replica majority | restore quorum |
| Redis stale replica | offsets/AOF | assess lost writes |
| Kafka ISR shrink | broker lag, ISR | restore replicas |
| PVC in wrong zone | CSI events | rebind supported storage |
| Ingress routes to old region | edge logs | correct staged routing |
| Restore checksum mismatch | data validation | quarantine restore |
| Secret version mismatch | auth errors | reconcile approved secret |
| Certificate invalid in DR | TLS checks | renew/recover trust chain |
| Backup copy inaccessible | account permissions | recover independent identity |
| RTO breached | timeline | document breach and remediation |
| Failback duplicates writes | reconciliation ledger | stop writes and repair |

## 11. Production runbooks

**RB-01 Declare regional incident:** incident commander, blast radius, communication, SLO and RPO/RTO decision.

**RB-02 Establish authority:** inspect quorum/lease and verify independent old-primary fencing.

**RB-03 Prepare recovery region:** validate IAM, KMS, network, DNS, IaC state, quotas and registry.

**RB-04 Recover DBRE writer:** verify replay point, backups and single-writer promotion.

**RB-05 Restore Kubernetes:** apply dependency ordering, protect singleton operators and validate PVs.

**RB-06 Switch traffic:** stage routing, monitor TTL, validate business transactions and error budget.

**RB-07 Roll back unsafe cutover:** stop new writes, preserve logs, choose consistent writer and recover.

**RB-08 Controlled failback:** reconcile divergent data, validate target, fence old writer and approve switch.

**RB-09 RPO/RTO evidence:** record UTC event times, last acknowledged write and verified service restoration.

**RB-10 Post-incident acceptance:** archive plans, approvals, audit logs, checksums, remediation owners and drill results.

## 12. Enterprise reliability acceptance (100 points)

| Control | Points |
|---|---:|
| BIA, service inventory and RPO/RTO | 10 |
| Fencing, quorum and single-writer proof | 20 |
| Replication and DBRE data integrity | 15 |
| IaC state and recovery bootstrap | 10 |
| Cloud/Kubernetes regional readiness | 10 |
| Traffic cutover and SLO verification | 10 |
| Rollback and failback | 10 |
| Observed recovery objectives and evidence | 10 |
| Independent approvals and security | 5 |
| **Total** | **100** |

**GO/NO-GO:** 90+ points **and** verified fencing, quorum, DB consistency, observed RPO/RTO, rollback, security and SRE/DBRE approvals. Missing any mandatory control is **NO-GO** regardless of score.

## 13. Cleanup and evidence
Preserve sanitized change records, leadership evidence, replication offsets, plan hashes, UTC recovery timeline, application transaction proof, approvals and failback logs. Clean up only disposable staging resources after explicit owner approval; never perform destructive production fencing in a tutorial lab.

**Next:** Chapter 104 — IaC Disaster Recovery Automation, Chaos Engineering, Recovery Drills and Continuous Resilience Validation.
