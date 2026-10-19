# Chapter 104 — IaC Disaster Recovery Automation, Chaos Engineering, Recovery Drills and Continuous Resilience Validation

**Part 21 — Disaster Recovery · Chapter 104/120 · Enterprise SRE/DBRE**

> **Safety and evidence boundary:** All supplied Python is a synthetic offline evaluation model. It does not inject failures, modify Terraform/OpenTofu state, restart pods, promote databases or change production routing. Native drill execution and independent acceptance must be separately evidenced.

## 1. Learning outcomes and prerequisites
Design a repeatable disaster recovery exercise program using controlled fault injection, preflight authorization, explicit blast-radius limits, stop switches, timed RPO/RTO evidence, SLO monitoring, data correctness checks, rollback and post-drill remediation. Integrate AWS, Azure, GCP, Terraform/OpenTofu, Kubernetes/GitOps and stateful DBRE platforms.

Prerequisites: Chapters 101–103; familiarity with Kubernetes PDBs, cloud failure domains, Prometheus/OTel, database PITR, Git-based change review and incident command.

## 2. Enterprise continuous-resilience architecture
```text
Service catalog + BIA + recovery tier + RPO/RTO + SLO
                      |
           versioned chaos experiment PR
                      |
     security + service owner + SRE + DBRE approval
                      |
  preflight: backups, stop switch, telemetry, blast radius
                      |
   staging-only fault injection / isolated failure domain
                      |
  traces, metrics, logs, events, replication and data probes
                      |
        recovery + single-writer + integrity checks
                      |
    timed RPO/RTO + rollback + service SLO validation
                      |
  evidence manifest + findings + remediation + next drill
```

Separate the **experiment controller** from infrastructure deployment credentials. An automated schedule may create a rehearsal request but must not bypass explicit change authorization or cause unreviewed production disruption.

## 3. Fault model and safety controls

| Fault family | Staging example | Safety invariant |
|---|---|---|
| Compute | terminate disposable worker | PDB and capacity preserved |
| Network | restrict one staging dependency | no cross-tenant impact |
| Availability zone | simulate AZ isolation | N-1 capacity validated |
| Region | disable staging regional endpoint | old writer fenced |
| Storage | inject test-volume latency | no production PV access |
| Database | stop synthetic replica | quorum and PITR protected |
| DNS | alter isolated test zone | production DNS unchanged |
| IAM/KMS | revoke disposable test identity | recovery keys independent |
| IaC backend | simulate unavailable test state store | production locks untouched |
| GitOps | pause test controller reconciliation | no global sync override |

Every experiment requires an owner, scope, duration, success condition, abort threshold, rollback procedure, backups, SLO baseline, audit trail and two-person authorization for high-risk stateful exercises.

### Chaos versus disaster recovery
Chaos engineering tests hypotheses about resilience under controlled failure. DR drills test the ability to restore business functionality and data after defined loss scenarios. A pod restart alone does not demonstrate regional recovery, and an available HTTP endpoint does not demonstrate application-consistent data.

## 4. Reliability measurements
- **RPO:** age of the last successfully recoverable acknowledged write relative to incident start.
- **RTO:** elapsed time from customer-impact start to verified business transaction restoration.
- **Detection time:** fault onset to alert; **decision time:** alert to authorized response; **recovery time:** action to verified service restoration.
- **SLO:** p95/p99 latency, availability, error budget burn, saturation and request success.
- **Data correctness:** checksums, transaction invariants, replication lag, consumer offsets and write fencing.
- **Experiment safety:** unexpected blast-radius growth, missing stop switch, lost quorum, excessive error budget burn or backup integrity failure triggers immediate abort.

Do not report a successful drill when telemetry is missing or time sources are inconsistent.

## 5. Cloud and platform implementation guidance
**AWS:** Use isolated test accounts and region-scoped AWS Fault Injection Service experiments where supported; constrain IAM, resource tags and experiment stop conditions. Rehearse EKS recovery, cross-region backups, Route 53 staging cutover and RDS/Aurora-specific failover procedures only with approved disposable workloads.

**Azure:** Use Azure Chaos Studio and supported fault types in dedicated test subscriptions, paired with Azure Backup/Site Recovery, AKS, Azure Monitor and Key Vault recovery validation.

**GCP:** Use isolated projects, controlled workload faults, Cloud Monitoring, GKE resilience exercises, backup/restore services and region-specific quota checks. Do not assume all AWS/Azure fault types have direct GCP equivalents.

**Terraform/OpenTofu:** Provision experiment scaffolding through reviewed plans; pin providers, protect state locks, isolate backends and retain plan hashes. Do not inject failures by editing production state or deleting managed resources.

**Kubernetes:** Define namespace and label boundaries, PDB, HPA, topology spread, service accounts, NetworkPolicy and workload SLO probes. Prefer staged chaos frameworks such as Chaos Mesh or LitmusChaos only after evaluating their cluster permissions and security boundaries.

**GitOps:** Keep the experiment manifests in a protected branch with approvals; avoid a reconciliation loop that unintentionally recreates the failure or undoes an emergency recovery action.

**DBRE:** PostgreSQL WAL/PITR and promotion fencing; MongoDB replica majority and oplog continuity; Redis RDB/AOF and eviction/data-loss tolerance; Kafka ISR, controller quorum and consumer offset recovery; Elasticsearch snapshot consistency and shard restore. A stateful chaos test is unacceptable without independent backup and restore proof.

## 6. Lab A — Offline drill acceptance engine

Create `infrastructure-as-code/labs/chapter-104/chaos_gate.py`:

```python
"""Offline chaos drill acceptance gate. Does not inject faults or call APIs."""
from dataclasses import dataclass

@dataclass(frozen=True)
class DrillEvidence:
    service: str
    blast_radius: str
    authorized: bool
    staging_only: bool
    stop_switch_verified: bool
    baseline_slo_ok: bool
    fault_observed: bool
    recovery_verified: bool
    data_integrity_verified: bool
    rollback_verified: bool
    rpo_observed_seconds: int
    rpo_target_seconds: int
    rto_observed_seconds: int
    rto_target_seconds: int
    dbre_approved: bool
    sre_approved: bool

def assess(d: DrillEvidence):
    if not d.service or not d.blast_radius:
        raise ValueError("service and blast radius required")
    metrics=(d.rpo_observed_seconds,d.rpo_target_seconds,
             d.rto_observed_seconds,d.rto_target_seconds)
    if any(x < 0 for x in metrics):
        raise ValueError("negative recovery times are invalid")
    checks={
        "authorization":d.authorized,
        "staging_boundary":d.staging_only,
        "stop_switch":d.stop_switch_verified,
        "baseline_slo":d.baseline_slo_ok,
        "fault_observed":d.fault_observed,
        "recovery":d.recovery_verified,
        "data_integrity":d.data_integrity_verified,
        "rollback":d.rollback_verified,
        "rpo":d.rpo_observed_seconds<=d.rpo_target_seconds,
        "rto":d.rto_observed_seconds<=d.rto_target_seconds,
        "dbre_approval":d.dbre_approved,
        "sre_approval":d.sre_approved,
    }
    return {"decision":"REVIEW_READY" if all(checks.values()) else "NO_GO",
            "failed":[key for key,ok in checks.items() if not ok]}
```

`REVIEW_READY` indicates only that the supplied synthetic evidence meets the model. It is not authorization for live chaos testing.

## 7. Lab B — Automated negative tests

Create `infrastructure-as-code/labs/chapter-104/test_chaos_gate.py`:

```python
import unittest
from dataclasses import replace
from chaos_gate import DrillEvidence, assess

class ChaosGateTests(unittest.TestCase):
    def setUp(self):
        self.good=DrillEvidence("orders","one staging namespace",True,True,
            True,True,True,True,True,True,60,300,240,900,True,True)
    def test_valid(self):
        self.assertEqual(assess(self.good)["decision"],"REVIEW_READY")
    def test_boolean_gates_fail_closed(self):
        fields=("authorized","staging_only","stop_switch_verified","baseline_slo_ok",
                "fault_observed","recovery_verified","data_integrity_verified",
                "rollback_verified","dbre_approved","sre_approved")
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.good,**{field:False}))["decision"],"NO_GO")
    def test_rpo_breach(self):
        self.assertIn("rpo",assess(replace(self.good,rpo_observed_seconds=400))["failed"])
    def test_rto_breach(self):
        self.assertIn("rto",assess(replace(self.good,rto_observed_seconds=1000))["failed"])
    def test_negative_time(self):
        with self.assertRaises(ValueError):
            assess(replace(self.good,rto_target_seconds=-1))
    def test_missing_scope(self):
        with self.assertRaises(ValueError):
            assess(replace(self.good,blast_radius=""))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-104 -p 'test_*.py' -v
```

## 8. Lab C — Kubernetes staging fault drill (manual)

1. Establish a disposable namespace with synthetic data, restricted service account and known owner.
2. Record baseline availability, p99, error budget, CPU/memory, PV health, HPA and PDB configuration.
3. Review fault manifest and verify selectors cannot match production workloads.
4. Verify backups, test restore, stop switch and rollback procedure before injecting any fault.
5. Inject a controlled single-pod or single-node workload failure within the approved namespace.
6. Observe rescheduling, service traffic, trace spans, alert delivery and SLO burn.
7. Verify transaction integrity, recovery time and cleanup of injected conditions.
8. Record UTC timestamps, experiment ID, telemetry links, approvals and signed evidence.
9. Re-run after remediation and compare the results to the prior baseline.

## 9. Lab D — Multi-region and DBRE recovery drill (manual)

1. Set up two isolated staging regions and synthetic stateful workloads; preserve independent keys and backups.
2. Verify single-writer authority and an independently observable fencing mechanism.
3. Simulate loss of a staging region or primary database endpoint; stop if fencing or quorum is ambiguous.
4. Promote a verified recovery replica through the supported database-specific process, or restore from a consistent backup.
5. Recover Terraform/OpenTofu backend bootstrap, Kubernetes dependencies, secrets, PVs, ingress and observability.
6. Re-route **staging** traffic and execute end-to-end reads/writes with integrity assertions.
7. Measure observed RPO/RTO and compare to the documented tier objectives.
8. Reconcile and fail back only after independent approval; preserve any divergent-write evidence.

## 10. Failure scenarios and troubleshooting

| Failure | Diagnosis | Safe response |
|---|---|---|
| Fault escapes namespace | labels/RBAC | abort and isolate controller |
| Stop switch unavailable | controller state | block experiment |
| No SLO baseline | missing telemetry | cancel drill |
| Alert delayed | routing/paging | fix alert chain |
| PDB prevents recovery | disruption constraints | restore capacity |
| HPA insufficient | saturation | revert workload change |
| Node pressure spreads | eviction events | stop and scale |
| Network partition persists | policy/routing | remove staged fault |
| Region quota exhausted | capacity errors | pre-provision |
| DNS TTL stalls cutover | resolver evidence | validate traffic path |
| GitOps undoes recovery | sync logs | pause scoped reconciliation |
| Terraform state lock held | backend owner | investigate; no forced unlock |
| KMS unavailable | grants and key policy | approved recovery identity |
| Backup corrupt | checksum/restore | select verified point |
| PostgreSQL WAL gap | archive coverage | reject PITR target |
| MongoDB loses majority | election status | restore quorum |
| Redis data-loss breach | RDB/AOF offset | classify RPO breach |
| Kafka ISR shrink | broker and ISR | recover replicas |
| Elasticsearch shard recovery fails | snapshot/cluster logs | re-restore safely |
| RTO target exceeded | event timeline | record failure and remediate |

## 11. Production runbooks

**RB-01 Experiment approval:** validate change ID, owner, safety hypothesis, blast radius, approvals and on-call coverage.

**RB-02 Preflight:** verify backups, restore, telemetry, stop switch, SLO baseline, capacity and rollback.

**RB-03 Abort:** halt fault injection, restore known-good state, verify customer-facing SLO and record incident.

**RB-04 Kubernetes recovery:** inspect PDB/HPA, events, PV, scheduling, ingress and application transactions.

**RB-05 DBRE recovery:** validate quorum, fencing, replication, PITR, checksums and write authority.

**RB-06 Regional recovery:** verify IAM/KMS, state, networking, target capacity and traffic cutover.

**RB-07 IaC reconciliation:** review plan and state drift; use approved Git changes, never ad hoc state edits.

**RB-08 RPO/RTO verification:** collect UTC event timestamps, last recoverable write and restored transaction.

**RB-09 Evidence preservation:** archive experiment definition, approvals, metrics, logs, checksums and stop decisions.

**RB-10 Remediation:** assign action owner, deadline, acceptance criteria and next scheduled drill.

## 12. Enterprise acceptance scorecard (100 points)

| Domain | Points |
|---|---:|
| Experiment scope, ownership and authorization | 15 |
| Blast-radius constraints and stop switch | 15 |
| Baseline SLOs, alerts and telemetry | 10 |
| Backup, restore and state recovery | 15 |
| Kubernetes and cross-region recovery | 10 |
| DBRE quorum, fencing and data integrity | 15 |
| Observed RPO/RTO and rollback | 10 |
| Evidence, findings and remediation | 10 |
| **Total** | **100** |

**Acceptance:** 90+ points plus every mandatory gate: explicit authorization, limited blast radius, functioning stop switch, recovery evidence, data correctness, observed RPO/RTO within objectives and independent SRE/DBRE sign-off. Any missing gate is **NO-GO**.

## 13. Cleanup and next chapter
Remove only approved staging fault objects and disposable resources; confirm the absence of residual network rules, taints or fault controllers. Retain audit evidence and legally required backups.

**Next:** Chapter 105 — Enterprise IaC Disaster Recovery, Multi-Region Resilience and Operational Acceptance Capstone.
