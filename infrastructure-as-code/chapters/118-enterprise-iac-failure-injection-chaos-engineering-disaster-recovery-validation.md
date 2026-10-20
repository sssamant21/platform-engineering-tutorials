# Chapter 118 — Enterprise IaC Failure Injection, Chaos Engineering and Disaster Recovery Validation

**Part 24 — Final Enterprise Capstone · Chapter 118/120 · Enterprise SRE/DBRE**

> **Safety boundary:** Failure injection is limited to disposable staging environments with documented blast radius, independent approvals, tested abort controls and no customer data. This chapter does not authorize production disruption or destructive experiments. The offline gate checks synthetic evidence only.

## 1. Learning objectives
Validate end-to-end resilience of multi-cloud IaC, Terraform/OpenTofu state, Kubernetes/GitOps, CI/CD, policy, telemetry, database backup/PITR and disaster recovery. Measure actual recovery time (RTO), recoverable data loss (RPO), SLO impact and integrity—not merely the presence of backup jobs.

Prerequisites: Chapters 001–117, isolated staging accounts/projects/subscriptions, Kubernetes fault-domain design, state backend snapshots, incident command, observability and DBRE recovery.

## 2. Failure-domain reference architecture
```text
              Change/fault experiment proposal
                            |
        Scope + tenant + risk + approval + abort plan
                            |
       Staging fault injector / fault-domain isolation
              /             |              \\
      Cloud network     Kubernetes      State/DB services
              \\             |              /
          Metrics + logs + traces + audit evidence
                            |
       Abort threshold -> incident command -> restore
                            |
    RTO/RPO + SLO + data integrity + state comparison
                            |
        Independent SRE / DBRE / security review
```

A fault experiment must specify a hypothesis, baseline, blast radius, injection method, duration, abort threshold, recovery owner and measurable steady-state conditions.

## 3. Experiment safety contract
- Restrict fault injection to allowlisted disposable resources and tenant-scoped credentials.
- Never run against production without a separate, organization-approved process.
- Use a short time window, budget, watchdog and independent kill switch.
- Freeze unrelated changes during recovery experiments.
- Record before/after Terraform/OpenTofu state and cloud resource inventory.
- Observe Kubernetes disruption budgets, quorum, placement and readiness.
- Protect database durability; do not destroy backups or delete customer data.
- Fail closed if telemetry, policy, identity or audit is unavailable.
- Verify that recovery is complete before releasing the change freeze.

## 4. Failure injection matrix

| Layer | Staging experiment | Validation |
|---|---|---|
| CI/CD | runner unavailable | retry cap, queue and recovery |
| Terraform/OpenTofu | backend temporarily unavailable | lock discipline and safe resumption |
| Cloud networking | isolated route/DNS failure | connectivity and rollback |
| Compute | single disposable node/pod loss | rescheduling and PDB behavior |
| GitOps | conflicting desired-state change | convergence and reconciliation |
| Identity/policy | deny simulated privileged action | fail-closed enforcement |
| Observability | remove synthetic metric stream | stop unobservable rollout |
| Database | isolate disposable replica | lag, quorum and integrity |
| Region | simulate region outage in test topology | RTO/RPO and routing |
| Automation | duplicate event or kill switch | idempotency and stop behavior |

## 5. Multi-cloud and platform considerations
**AWS:** test isolated AZ/region dependencies, IAM/ST​S failure behavior, Route 53 routing, state backends and recovery evidence.

**Azure:** test zone and region dependency, Azure Policy/identity outages, Azure Monitor coverage and storage snapshots.

**GCP:** test zone and region failure domains, organization policy, workload identity, Cloud Monitoring and storage recovery.

**Kubernetes/GitOps:** validate PodDisruptionBudgets, topology spread, readiness probes, etcd/control-plane dependencies, Git reconciliation and admission policy behavior.

**DBRE:** verify PostgreSQL WAL/PITR and single-writer fencing, MongoDB replica set recovery, Redis persistence/replication semantics, Kafka ISR and partition durability, Elasticsearch snapshot consistency and shard allocation. Use separate technology-specific runbooks.

## 6. Lab A — Offline disaster recovery acceptance gate

Create `infrastructure-as-code/labs/chapter-118/recovery_gate.py`:

```python
"""Offline chaos and disaster recovery acceptance gate. Never injects failures."""
from dataclasses import dataclass

WEIGHTS={"blast_radius":10,"abort_controls":10,"baseline_slos":10,
 "failure_observability":10,"state_restore":10,"gitops_recovery":10,
 "identity_and_policy":10,"rto_met":10,"rpo_met":10,"data_integrity":10}
assert sum(WEIGHTS.values())==100
MANDATORY=("blast_radius","abort_controls","baseline_slos","failure_observability",
 "state_restore","identity_and_policy","rto_met","rpo_met")

@dataclass(frozen=True)
class DrillEvidence:
    drill_id:str
    environment:str
    tenant:str
    authorized_tenant:str
    approved_fault:str
    proposed_fault:str
    measured_rto_seconds:int
    target_rto_seconds:int
    measured_rpo_seconds:int
    target_rpo_seconds:int
    blast_radius:bool
    abort_controls:bool
    baseline_slos:bool
    failure_observability:bool
    state_restore:bool
    gitops_recovery:bool
    identity_and_policy:bool
    data_integrity:bool
    database_in_scope:bool
    dbre_approved:bool
    security_approved:bool
    sre_approved:bool
    kill_switch_active:bool
    critical_exception_open:bool

def assess(e:DrillEvidence):
    if not e.drill_id.strip() or not e.tenant.strip():
        raise ValueError("drill and tenant required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    if any(v<0 for v in (e.measured_rto_seconds,e.target_rto_seconds,
                         e.measured_rpo_seconds,e.target_rpo_seconds)):
        raise ValueError("negative recovery time")
    if e.target_rto_seconds==0 or e.target_rpo_seconds==0:
        raise ValueError("RTO/RPO targets must be positive")
    rto=e.measured_rto_seconds<=e.target_rto_seconds
    rpo=e.measured_rpo_seconds<=e.target_rpo_seconds
    checks={key:getattr(e,key) for key in WEIGHTS if key not in ("rto_met","rpo_met")}
    checks.update(rto_met=rto,rpo_met=rpo)
    score=sum(points for key,points in WEIGHTS.items() if checks[key])
    failed=[key for key in MANDATORY if not checks[key]]
    if e.database_in_scope and not e.data_integrity: failed.append("data_integrity")
    if e.tenant!=e.authorized_tenant: failed.append("tenant_scope")
    if not e.approved_fault or e.proposed_fault!=e.approved_fault:
        failed.append("fault_binding")
    if e.environment=="prod": failed.append("production_drill_requires_separate_process")
    if not e.sre_approved: failed.append("sre_approval")
    if not e.security_approved: failed.append("security_approval")
    if e.database_in_scope and not e.dbre_approved: failed.append("dbre_approval")
    if e.kill_switch_active: failed.append("kill_switch")
    if e.critical_exception_open: failed.append("critical_exception")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
```

The gate enforces staging-only drill eligibility, tenant and fault binding, approvals, RTO/RPO targets and critical safeguards. It cannot measure real recovery or verify evidence authenticity.

## 7. Lab B — Negative unit tests

Create `infrastructure-as-code/labs/chapter-118/test_recovery_gate.py`:

```python
import unittest
from dataclasses import replace
from recovery_gate import DrillEvidence,assess

class RecoveryGateTests(unittest.TestCase):
    def setUp(self):
        self.e=DrillEvidence("DR-118","stage","team-a","team-a","pod_termination",
            "pod_termination",240,300,15,60,True,True,True,True,True,True,
            True,True,True,True,True,True,False,False)
    def test_ready(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_failures(self):
        for key in ("blast_radius","abort_controls","baseline_slos","failure_observability",
                    "state_restore","identity_and_policy","data_integrity"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_rto_breach(self):
        self.assertIn("rto_met",assess(replace(self.e,measured_rto_seconds=301))["failed_controls"])
    def test_rpo_breach(self):
        self.assertIn("rpo_met",assess(replace(self.e,measured_rpo_seconds=61))["failed_controls"])
    def test_fault_binding(self):
        self.assertIn("fault_binding",assess(replace(self.e,proposed_fault="region_failure"))["failed_controls"])
    def test_tenant_isolation(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_prod_denied(self):
        self.assertEqual(assess(replace(self.e,environment="prod"))["decision"],"NO_GO")
    def test_kill_switch(self):
        self.assertIn("kill_switch",assess(replace(self.e,kill_switch_active=True))["failed_controls"])
    def test_approvals(self):
        for key in ("sre_approved","security_approved","dbre_approved"):
            self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_invalid_rpo(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,target_rpo_seconds=0))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-118 -p 'test_*.py' -v
```

## 8. Lab C — Kubernetes, IaC and GitOps fault drill (manual)
1. Provision disposable staging cloud resources and a separate test Kubernetes namespace.
2. Define steady-state SLOs, an experiment hypothesis, blast radius and rollback.
3. Capture encrypted state snapshots, Kubernetes manifests and Git revision.
4. Confirm native IAM/policy deny rules, independent approval and kill-switch ownership.
5. Terminate one disposable workload pod; measure rescheduling and user-facing latency.
6. Simulate loss of a disposable CI runner or read-only state backend access.
7. Validate Terraform/OpenTofu lock handling and reconcile state before resuming.
8. Test GitOps convergence after a reviewed staging change.
9. Activate abort controls when a synthetic SLO threshold is crossed.
10. Restore baseline, verify metrics and preserve sanitized logs, traces and approvals.

## 9. Lab D — Database recovery and regional resilience (manual)
1. Create synthetic database data and document integrity checksums/row counts.
2. Record backup, PITR, replica state, replication lag, writer fencing and RPO/RTO.
3. Perform a separately approved isolated restore into disposable infrastructure.
4. Inject a non-destructive staging replica or availability-zone fault.
5. Measure recovery completion and recovered data timestamp; calculate RTO/RPO.
6. Verify there is exactly one writable leader after recovery and no split brain.
7. Confirm application transactions and data-integrity checks pass.
8. Reconcile GitOps and Terraform/OpenTofu state against recovered resources.
9. Record any RPO/RTO breach as a failed acceptance criterion.
10. Preserve independent DBRE/SRE/security sign-off and cleanup evidence.

## 10. Twenty troubleshooting scenarios

| # | Failure | Safe response |
|---|---|---|
| 1 | Pod termination exceeds budget | abort and restore workload |
| 2 | Node drain stalls | inspect PDB and scheduler |
| 3 | AZ failure exposes single point | halt and redesign topology |
| 4 | Region outage routing fails | restore safe route and inspect DNS |
| 5 | Terraform backend unavailable | freeze writes and preserve state |
| 6 | State snapshot corrupted | select verified earlier backup |
| 7 | Lock force-unlock requested | deny without owner investigation |
| 8 | GitOps reconciliation conflict | pause competing controller |
| 9 | Admission webhook outage | fail closed and restore policy |
| 10 | Cloud IAM federation outage | revoke uncertain sessions |
| 11 | Audit sink unavailable | stop privileged operations |
| 12 | Queue replay causes duplicate | enforce idempotency |
| 13 | SLO monitoring gap | abort unobservable experiment |
| 14 | Canary rollback fails | incident command and reconcile |
| 15 | Database replica lag spikes | DBRE assess durability |
| 16 | PITR target missing | NO-GO and repair backups |
| 17 | Split-brain writer detected | fence unsafe writer |
| 18 | RTO target exceeded | record failure and remediate |
| 19 | RPO target exceeded | investigate WAL/oplog/replication |
| 20 | Kill switch ineffective | isolate executor and halt drills |

## 11. Ten production runbooks

**RB-01 — Chaos preflight:** validate scope, approvals, SLO baseline and abort conditions.

**RB-02 — Experiment abort:** activate kill switch, isolate fault and notify incident command.

**RB-03 — Kubernetes recovery:** restore replicas, PDB and scheduler health.

**RB-04 — Cloud AZ/region recovery:** verify routing, capacity and fault-domain separation.

**RB-05 — Terraform state recovery:** preserve lock and restore isolated versioned snapshot.

**RB-06 — GitOps recovery:** reconcile Git authority and eliminate conflicting controllers.

**RB-07 — Policy/IAM outage:** deny privileged writes and restore trust services.

**RB-08 — Database PITR:** restore isolated copy and verify transaction/data integrity.

**RB-09 — Split-brain prevention:** fence old writer and validate single-writer safety.

**RB-10 — Acceptance and follow-up:** compare measured RTO/RPO, SLOs and signed evidence.

## 12. Enterprise 100-point DR acceptance

| Domain | Points |
|---|---:|
| Blast-radius isolation | 10 |
| Abort controls | 10 |
| Baseline SLOs | 10 |
| Failure observability | 10 |
| State restoration | 10 |
| GitOps recovery | 10 |
| Identity and policy | 10 |
| RTO achieved | 10 |
| RPO achieved | 10 |
| Data integrity | 10 |
| **Total** | **100** |

**Acceptance:** at least 90/100 plus mandatory controls, measured RTO/RPO, exact approved fault/tenant binding, independent security/SRE approval and DBRE approval plus data integrity when a database is in scope. Production fault injection requires a separate approval process and is **NO-GO** under this lab gate.

## 13. Evidence, cleanup and next chapter
Preserve experiment hypothesis, fault IDs, scope, timestamps, native logs, state versions, SLO graphs, backup/restore evidence, RTO/RPO calculations, database integrity and reviewer decisions. Document all unresolved failures rather than marking a drill successful.

**Next:** Chapter 119 — Enterprise IaC Security, Compliance, Cost and Reliability Final Audit.
