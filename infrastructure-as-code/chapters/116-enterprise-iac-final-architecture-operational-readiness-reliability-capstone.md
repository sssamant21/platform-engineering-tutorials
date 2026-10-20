# Chapter 116 — Enterprise IaC Final Architecture, Operational Readiness and Reliability Capstone

**Part 24 — Final Enterprise Capstone · Chapter 116/120 · Enterprise SRE/DBRE**

> **Publication is not production certification.** This chapter defines a reference architecture and offline readiness assessment. Cloud, cluster and database exercises require isolated staging execution, native evidence and independent review.

## 1. Learning outcomes
Integrate the entire enterprise IaC curriculum into a multi-cloud reference architecture. Validate Terraform/OpenTofu state, CI/CD, Kubernetes/GitOps, identity, policy-as-code, observability, SLOs, cost/capacity, disaster recovery and DBRE data integrity. Produce auditable GO/NO-GO decisions.

**Prerequisites:** Chapters 001–115; cloud networking/IAM, GitLab/Jenkins CI, Terraform/OpenTofu, Kubernetes, GitOps, Prometheus/OpenTelemetry, database recovery and incident management.

## 2. Enterprise reference architecture

```text
                Protected Git + module registry
                            |
          PR review + SAST/SCA + signed provenance
                            |
        CI plan -> policy -> approval -> scoped apply
                            |
             Terraform/OpenTofu orchestration
                    /       |       \\
                 AWS      Azure      GCP
                  |          |         |
             Network/IAM/compute/storage/DB services
                            |
                Kubernetes + GitOps platform
                            |
          Observability + SLOs + incident command
                            |
            Backup/PITR + multi-region recovery
                            |
            Audit, FinOps and governance evidence
```

**Trust boundaries:** separate tenant accounts/projects/subscriptions; isolate Terraform/OpenTofu state and encryption keys; use OIDC workload federation; prohibit shared long-lived admin credentials; apply organization-level guardrails and Kubernetes admission controls.

## 3. Platform topology and ownership

| Plane | Enterprise ownership | Reliability contract |
|---|---|---|
| Source and module supply chain | Platform/Security | signed, reviewed immutable artifacts |
| IaC state and execution | Platform/SRE | locking, encryption, snapshots, recoverability |
| Cloud networking and IAM | Cloud/Security | tenant isolation, least privilege, tested deny rules |
| Kubernetes and GitOps | Platform/SRE | desired-state convergence, rollout SLOs |
| Observability and incident command | SRE | traces, metrics, alert quality, burn-rate response |
| Database data plane | DBRE | consistency, backup/PITR, RPO/RTO and fencing |
| Cost and capacity | FinOps/SRE | forecast, headroom, cost and availability balance |

## 4. Architecture design decisions
Document region selection, availability zones, tenancy model, blast-radius boundaries, account/subscription/project separation, state backend layout, encryption, key ownership, secrets, network egress, provider pinning, module provenance, GitOps ownership, change windows, dependency graph, failure domains and capacity headroom.

Create architecture decision records (ADRs) for contentious tradeoffs, including shared versus per-tenant clusters, centralized versus federated state, managed versus self-managed databases, and active-active versus active-passive recovery.

## 5. Reliability and DR requirements
- Define service SLOs, error budgets and change freeze rules.
- Map infrastructure dependencies to application critical paths.
- Establish capacity headroom for regional and AZ failure.
- Verify backups by restoring into an isolated environment; do not infer recovery from successful backup jobs.
- Define and measure RPO/RTO, recovery ordering, DNS propagation and database writer fencing.
- Preserve audit, plan hashes, state snapshots and change approvals.
- Ensure DBRE recovery maintains transactional integrity and does not reintroduce stale writers.

## 6. Security and policy
Enforce least-privilege OIDC federation, short-lived credentials, protected state, supply-chain attestations, branch protections, policy-as-code, secret scanning and human approval of privileged production changes. Test explicit deny rules and fail-closed behavior. AI-assisted operations remain advisory; no unrestricted production executor access.

## 7. Lab A — Offline architecture acceptance gate

Create `infrastructure-as-code/labs/chapter-116/architecture_gate.py`:

```python
"""Offline final architecture readiness evidence gate. No infrastructure operations."""
from dataclasses import dataclass

WEIGHTS={
 "architecture_review":10,"multi_cloud_boundaries":10,
 "tenant_isolation":10,"identity_least_privilege":10,
 "state_backup_and_locking":10,"policy_and_supply_chain":10,
 "gitops_reconciliation":10,"observability_and_slos":10,
 "recovery_drill":10,"dbre_integrity":10,
}
MANDATORY=("tenant_isolation","identity_least_privilege","state_backup_and_locking",
 "policy_and_supply_chain","observability_and_slos","recovery_drill")

@dataclass(frozen=True)
class ArchitectureEvidence:
    assessment_id:str
    environment:str
    architecture_review:bool
    multi_cloud_boundaries:bool
    tenant_isolation:bool
    identity_least_privilege:bool
    state_backup_and_locking:bool
    policy_and_supply_chain:bool
    gitops_reconciliation:bool
    observability_and_slos:bool
    recovery_drill:bool
    dbre_integrity:bool
    databases_in_scope:bool
    security_signoff:bool
    sre_signoff:bool
    dbre_signoff:bool
    critical_exception_open:bool

def assess(e:ArchitectureEvidence):
    if not e.assessment_id.strip():
        raise ValueError("assessment ID required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    score=sum(weight for key,weight in WEIGHTS.items() if getattr(e,key))
    required=list(MANDATORY)
    if e.databases_in_scope:
        required.append("dbre_integrity")
    failed=[key for key in required if not getattr(e,key)]
    if not e.security_signoff: failed.append("security_signoff")
    if not e.sre_signoff: failed.append("sre_signoff")
    if e.databases_in_scope and not e.dbre_signoff: failed.append("dbre_signoff")
    if e.critical_exception_open: failed.append("critical_exception")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
```

The evaluator treats evidence as synthetic booleans; it does not verify their authenticity. `REVIEW_READY` means eligible for independent review, not permission to deploy.

## 8. Lab B — Negative unit tests

Create `infrastructure-as-code/labs/chapter-116/test_architecture_gate.py`:

```python
import unittest
from dataclasses import replace
from architecture_gate import ArchitectureEvidence,assess

class ArchitectureGateTests(unittest.TestCase):
    def setUp(self):
        self.e=ArchitectureEvidence("ARCH-116","prod",True,True,True,True,True,
            True,True,True,True,True,True,True,True,True,False)
    def test_full_acceptance(self):
        self.assertEqual(assess(self.e),{"decision":"REVIEW_READY","score":100,"failed_controls":[]})
    def test_mandatory_fail_closed(self):
        for field in ("tenant_isolation","identity_least_privilege","state_backup_and_locking",
                      "policy_and_supply_chain","observability_and_slos","recovery_drill","dbre_integrity"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_critical_exception(self):
        self.assertIn("critical_exception",assess(replace(self.e,critical_exception_open=True))["failed_controls"])
    def test_signoffs(self):
        for field in ("security_signoff","sre_signoff","dbre_signoff"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_low_score(self):
        e=replace(self.e,architecture_review=False,multi_cloud_boundaries=False)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_no_db_scope(self):
        e=replace(self.e,databases_in_scope=False,dbre_integrity=False,dbre_signoff=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,environment="unknown"))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-116 -p 'test_*.py' -v
```

## 9. Lab C — Enterprise staging architecture deployment (manual)
1. Create an ADR and architecture diagram for a disposable staging environment.
2. Define separate cloud identities and tenant-scoped state backends with encryption, locking and versioning.
3. Pin Terraform/OpenTofu providers and modules; enable CI security and policy checks.
4. Execute read-only plans, review diffs and bind approvals to exact immutable artifacts.
5. Deploy only approved disposable resources using scoped staging identities.
6. Configure Kubernetes namespaces, RBAC, admission policies and GitOps reconciliation.
7. Instrument SLOs, OpenTelemetry traces, cloud audit and cost/capacity dashboards.
8. Exercise drift detection and a reviewed correction through Git.
9. Inject one staging fault and validate alert, incident command, rollback and SLO recovery.
10. Preserve sanitized native evidence and clean up approved staging resources.

## 10. Lab D — DBRE reliability and multi-region recovery (manual)
1. Define a synthetic database-backed service with explicit data correctness criteria.
2. Establish backup retention, PITR coverage, restore credentials and RPO/RTO targets.
3. Restore a staging backup into an isolated region or fault domain.
4. Validate data integrity, transaction ordering, application queries and read/write access.
5. Test old-writer fencing and verify that failback cannot create split brain.
6. Confirm Kubernetes/GitOps controllers do not undo intentional recovery actions.
7. Record measured RPO/RTO, replication lag, recovery dependencies and cloud costs.
8. Obtain independent DBRE/SRE/security acceptance before any production rehearsal.

## 11. Twenty troubleshooting scenarios

| # | Failure | Safe response |
|---|---|---|
| 1 | Identity federation fails | block privileged deployment and inspect OIDC trust |
| 2 | Cross-account privilege drift | deny and review IAM boundaries |
| 3 | Tenant state exposure | isolate backend and rotate credentials |
| 4 | Terraform state lock stuck | verify owner before approved recovery |
| 5 | State backup missing | NO-GO until restore proven |
| 6 | Provider version incompatibility | pin and rehearse upgrade |
| 7 | Module supply-chain compromise | quarantine and verify provenance |
| 8 | Policy engine unavailable | fail closed |
| 9 | CI runner compromised | revoke ephemeral credentials |
| 10 | Plan digest mismatch | invalidate approval |
| 11 | GitOps reconciliation conflict | restore single source of truth |
| 12 | Kubernetes admission failure | inspect policy and rollback |
| 13 | Cluster capacity exhaustion | protect SLO and scale safely |
| 14 | Cloud quota breach | throttle and escalate |
| 15 | Telemetry blind spot | halt unobservable rollout |
| 16 | SLO error-budget burn | stop change and recover |
| 17 | Database replication lag | DBRE assess consistency and lag |
| 18 | Backup/PITR corruption | test alternate recovery chain |
| 19 | Cross-region failover ambiguity | fence old writer and verify |
| 20 | Audit retention gap | freeze sensitive changes and repair evidence |

## 12. Ten production runbooks

**RB-01 — Enterprise incident command:** establish incident commander, affected services and change freeze.

**RB-02 — Identity isolation:** revoke scoped identities and validate tenant boundaries.

**RB-03 — State recovery:** preserve locks and restore versioned encrypted state in isolation.

**RB-04 — IaC rollback:** reconcile actual resources, reviewed plan and immutable artifacts.

**RB-05 — Policy failure:** deny privileged actions until enforcement recovers.

**RB-06 — Supply-chain incident:** quarantine runner and module dependencies, verify signatures.

**RB-07 — GitOps restoration:** stop competing controllers and restore authoritative Git state.

**RB-08 — SLO incident:** track burn, abort rollout and validate user-facing recovery.

**RB-09 — DBRE disaster recovery:** verify backup, fencing, RPO/RTO and data integrity.

**RB-10 — Operational acceptance:** collect native evidence, reviewer sign-offs and final NO-GO exceptions.

## 13. Enterprise 100-point readiness assessment

| Domain | Points |
|---|---:|
| Architecture review | 10 |
| Multi-cloud trust boundaries | 10 |
| Tenant isolation | 10 |
| Identity and least privilege | 10 |
| State backup and locking | 10 |
| Policy and supply-chain integrity | 10 |
| GitOps reconciliation | 10 |
| Observability and SLOs | 10 |
| Recovery drill | 10 |
| DBRE integrity | 10 |
| **Total** | **100** |

**Acceptance:** at least 90/100 with all mandatory controls, independent security and SRE sign-off, and DBRE sign-off when databases are in scope. Any unresolved critical exception is **NO-GO**.

## 14. Completion and next chapter
Publish ADRs, dependency maps, runbooks, native staging logs, policy decisions, state recovery results, SLO measurements and DBRE data-integrity evidence. Separate authored controls from actually tested controls.

**Next:** Chapter 117 — Enterprise IaC Production Deployment, Multi-Cloud Integration and Platform Validation.
