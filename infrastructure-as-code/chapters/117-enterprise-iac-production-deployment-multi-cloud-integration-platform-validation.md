# Chapter 117 — Enterprise IaC Production Deployment, Multi-Cloud Integration and Platform Validation

**Part 24 — Final Enterprise Capstone · Chapter 117/120 · Enterprise SRE/DBRE**

> **Safety and verification:** All deployment instructions target disposable staging resources until independent production authorization. The offline gate assesses supplied evidence, not live identity, plan signatures or cloud state. A `REVIEW_READY` result is not deployment permission.

## 1. Objectives and prerequisites
Integrate Chapters 001–116 into a controlled multi-cloud delivery pipeline: AWS, Azure, GCP, Terraform/OpenTofu, CI/CD, Kubernetes/GitOps, observability, policy-as-code, SLOs and DBRE. Learn deployment ordering, immutable plans, progressive rollout, rollback and post-deployment evidence.

Prerequisites: protected Git branches, scoped OIDC identities, versioned encrypted state, Terraform/OpenTofu, GitOps, cloud networking, database backup/PITR and incident command.

## 2. Reference deployment architecture
```text
Protected Git / reviewed PR / pinned modules
                    |
   CI checks: tests, policy, SCA, provenance
                    |
     Plan in isolated environment and state
                    |
       Sign/hash immutable plan artifact
                    |
  Independent approval bound to exact plan
                    |
    Staged execution with scoped cloud IAM
          /           |           \\
        AWS         Azure          GCP
          \\           |           /
      Kubernetes + GitOps + DB services
                    |
   Smoke tests -> canary -> SLO verification
                    |
    Accept / halt / rollback / escalation
```

Cloud provider deployment is a separate trust boundary: AWS STS/OIDC, Azure managed identity/federated credentials and GCP workload identity federation must be scoped to specific environments, resources and tenants. Never use one unrestricted multi-cloud service principal.

## 3. Deployment dependency graph
1. Organization controls, accounts/subscriptions/projects, identity federation and audit.
2. Network, DNS, firewall, routing, encryption and private connectivity.
3. Terraform/OpenTofu backend, locking, versioning and isolated recovery snapshots.
4. Cloud foundation services, storage, compute and managed Kubernetes.
5. Admission policy, secrets, workload identity, ingress and GitOps controllers.
6. Database platform provisioning, backups, PITR and monitoring.
7. Application manifests, progressive delivery, service mesh or ingress routing.
8. SLO dashboards, alerts, on-call ownership, incident and rollback readiness.

Use an explicit dependency DAG. Never assume Terraform resource creation order establishes application-level readiness or database transaction safety.

## 4. Release and environment promotion
- Pin provider/module versions, verify artifact provenance and capture dependency SBOM where appropriate.
- Generate a plan against the intended environment and locked state backend.
- Record the immutable plan digest, state version, resource scope, environment and tenant.
- Apply only through a separately approved executor with least-privilege short-lived identity.
- Replan and reapprove whenever inputs, state, provider or approval scope changes.
- Stage deployment waves by failure domain; use canary traffic and rollback thresholds.
- Freeze rollout if SLO burn, data integrity, policy or audit evidence fails.

**Important:** A saved Terraform/OpenTofu plan can become stale as remote state or real infrastructure changes. Verify backend state, plan freshness and approval binding immediately before execution.

## 5. Kubernetes and GitOps integration
Use immutable container digests, namespace-scoped RBAC, network policy, Pod Security admission, resource requests/limits, readiness and startup probes, PDBs and topology spread. Prefer declarative GitOps changes to imperative edits. Validate Argo CD/Flux reconciliation health and detect controllers fighting each other.

## 6. Stateful workload and DBRE controls
Require explicit data ownership, encryption, backups, PITR, retention, replication lag, quorum/fencing, read/write cutover, schema compatibility and restore testing. PostgreSQL, MongoDB, Redis, Kafka and Elasticsearch have different recovery semantics. A successful pod rollout is not proof of durable data or database availability.

For production DB changes, collect DBRE approval, RPO/RTO and recovery evidence. Never auto-failover or delete data as part of this training lab.

## 7. Lab A — Offline deployment readiness gate

Create `infrastructure-as-code/labs/chapter-117/deployment_gate.py`:

```python
"""Offline deployment evidence assessment; never deploys infrastructure."""
from dataclasses import dataclass
from datetime import datetime, timezone

WEIGHTS={"identity_scope":10,"tenant_isolation":10,"plan_integrity":15,
 "policy_passed":10,"dependency_ready":10,"approval_bound":10,
 "observability_ready":10,"rollback_rehearsed":10,"slo_healthy":10,
 "database_recovery_ready":5}
assert sum(WEIGHTS.values())==100
MANDATORY=tuple(k for k in WEIGHTS if k!="database_recovery_ready")

@dataclass(frozen=True)
class DeploymentEvidence:
    change_id:str
    environment:str
    tenant:str
    approved_tenant:str
    submitted_plan_digest:str
    approved_plan_digest:str
    requester:str
    approver:str
    approval_expiry:str
    checked_at:str
    identity_scope:bool
    tenant_isolation:bool
    plan_integrity:bool
    policy_passed:bool
    dependency_ready:bool
    approval_bound:bool
    observability_ready:bool
    rollback_rehearsed:bool
    slo_healthy:bool
    database_recovery_ready:bool
    database_in_scope:bool
    dbre_approved:bool
    security_approved:bool
    sre_approved:bool
    critical_exception_open:bool

def utc_timestamp(value):
    try:
        result=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if result.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return result.astimezone(timezone.utc)

def assess(e:DeploymentEvidence):
    if not e.change_id.strip() or not e.tenant.strip():
        raise ValueError("change ID and tenant required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    now=utc_timestamp(e.checked_at)
    expires=utc_timestamp(e.approval_expiry)
    score=sum(weight for name,weight in WEIGHTS.items() if getattr(e,name))
    failed=[name for name in MANDATORY if not getattr(e,name)]
    if e.database_in_scope and not e.database_recovery_ready:
        failed.append("database_recovery_ready")
    if e.tenant!=e.approved_tenant: failed.append("tenant_binding")
    if not e.submitted_plan_digest or e.submitted_plan_digest!=e.approved_plan_digest:
        failed.append("plan_digest_binding")
    if not e.requester or not e.approver or e.requester==e.approver:
        failed.append("separation_of_duties")
    if now>=expires: failed.append("approval_expiry")
    if not e.security_approved: failed.append("security_approval")
    if not e.sre_approved: failed.append("sre_approval")
    if e.database_in_scope and not e.dbre_approved: failed.append("dbre_approval")
    if e.critical_exception_open: failed.append("critical_exception")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
```

The evaluator checks synthetic booleans, exact plan digest equality, approval expiry, tenant scope and separation of duties. It does not verify cryptographic signatures or authentic evidence.

## 8. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-117/test_deployment_gate.py`:

```python
import unittest
from dataclasses import replace
from deployment_gate import DeploymentEvidence,assess

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.e=DeploymentEvidence("CHG-117","prod","team-a","team-a",
          "sha256:abc","sha256:abc","requester","approver",
          "2026-11-01T00:00:00Z","2026-10-20T12:00:00Z",
          True,True,True,True,True,True,True,True,True,True,
          True,True,True,True,False)
    def test_ready(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_controls(self):
        for name in ("identity_scope","tenant_isolation","plan_integrity",
          "policy_passed","dependency_ready","approval_bound",
          "observability_ready","rollback_rehearsed","slo_healthy",
          "database_recovery_ready"):
            with self.subTest(name=name):
                self.assertEqual(assess(replace(self.e,**{name:False}))["decision"],"NO_GO")
    def test_binding(self):
        for changes in ({"approved_tenant":"team-b"},{"approved_plan_digest":"sha256:other"},
                        {"approver":"requester"},{"approval_expiry":"2026-10-19T00:00:00Z"}):
            with self.subTest(changes=changes):
                self.assertEqual(assess(replace(self.e,**changes))["decision"],"NO_GO")
    def test_approvals(self):
        for name in ("dbre_approved","security_approved","sre_approved"):
            self.assertEqual(assess(replace(self.e,**{name:False}))["decision"],"NO_GO")
    def test_exception(self):
        self.assertIn("critical_exception",assess(replace(self.e,critical_exception_open=True))["failed_controls"])
    def test_no_database(self):
        e=replace(self.e,database_in_scope=False,dbre_approved=False,database_recovery_ready=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
    def test_naive_time(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,checked_at="2026-10-20T12:00:00"))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-117 -p 'test_*.py' -v
```

## 9. Lab C — Multi-cloud staging integration (manual)
1. Create an architecture decision record with a disposable per-cloud staging scope and cost budget.
2. Configure cloud OIDC/federated identities with explicit deny tests for cross-tenant access.
3. Establish encrypted versioned state backends and recovery snapshots.
4. Pin Terraform/OpenTofu providers/modules and generate read-only plans for AWS, Azure and GCP.
5. Run policy, secret and supply-chain scans; bind independent approvals to exact plan digests.
6. Deploy only approved staging foundations in dependency order.
7. Provision a disposable Kubernetes workload via GitOps, using immutable image digests.
8. Verify admission, RBAC, network connectivity, probes, audit and observability.
9. Shift staging canary traffic, inject a safe SLO failure and confirm rollback.
10. Reconcile state and cloud resources, preserve sanitized evidence and remove disposable resources.

## 10. Lab D — Database-backed release and recovery (manual)
1. Deploy a synthetic staging application backed by a disposable database.
2. Define data-integrity invariants, schema compatibility, RPO/RTO and recovery owners.
3. Verify backup freshness and perform an isolated restore before deployment.
4. Generate a non-destructive schema change plan; obtain DBRE approval before execution.
5. Observe replication lag, transaction integrity, latency and error-budget impact.
6. Simulate a safe failure, pause promotion and execute the approved rollback procedure.
7. Confirm no stale database writer remains active and compare post-recovery data checksums.
8. Record actual recovery times, integrity evidence and remaining exceptions.

## 11. Twenty troubleshooting scenarios

| # | Failure | Safe response |
|---|---|---|
| 1 | OIDC federation failure | stop rollout and inspect trust claims |
| 2 | Cross-tenant credentials | deny and revoke identity |
| 3 | State backend unavailable | stop plan/apply; preserve locks |
| 4 | Plan hash mismatch | invalidate approval |
| 5 | Provider checksum mismatch | quarantine dependency |
| 6 | Policy engine timeout | fail closed |
| 7 | Stale approval | request fresh review |
| 8 | Cloud quota exceeded | abort affected wave |
| 9 | Network route overlap | isolate and redesign CIDR |
| 10 | DNS propagation delay | verify before traffic shift |
| 11 | Load balancer unhealthy | halt promotion |
| 12 | Kubernetes admission deny | fix manifest and retest |
| 13 | GitOps drift loop | resolve conflicting controller |
| 14 | Secrets not mounted | check scoped secret identity |
| 15 | Image signature invalid | block workload |
| 16 | Telemetry missing | pause promotion |
| 17 | Error budget burn | stop canary and roll back |
| 18 | Terraform lock contention | inspect lock owner |
| 19 | Database replication lag | DBRE review before promotion |
| 20 | PITR restore fails | NO-GO and repair backup chain |

## 12. Ten production runbooks

**RB-01 — Preflight authorization:** verify signed plan, tenant, scope, approvals and change window.

**RB-02 — Cloud foundation rollout:** validate IAM, network, state and policy per cloud.

**RB-03 — IaC execution interruption:** reconcile provider operations and state before retry.

**RB-04 — Kubernetes promotion:** pause Argo CD/Flux wave and verify rollout probes.

**RB-05 — Security policy failure:** freeze deployment and restore enforcement.

**RB-06 — Canary SLO regression:** stop traffic shift and execute approved rollback.

**RB-07 — State corruption:** restore isolated versioned snapshot and compare actual resources.

**RB-08 — Database cutover:** check replication, fencing, data integrity and DBRE approval.

**RB-09 — Cross-region recovery:** validate DNS, routing, RPO/RTO and old-writer isolation.

**RB-10 — Release acceptance:** collect evidence, approvals, exceptions and GO/NO-GO.

## 13. Enterprise 100-point acceptance

| Domain | Points |
|---|---:|
| Identity scope | 10 |
| Tenant isolation | 10 |
| Immutable plan integrity | 15 |
| Policy validation | 10 |
| Dependency readiness | 10 |
| Human approval binding | 10 |
| Observability readiness | 10 |
| Rollback rehearsal | 10 |
| SLO health | 10 |
| Database recovery readiness | 5 |
| **Total** | **100** |

**GO/NO-GO:** at least 90/100 plus all mandatory controls, correct tenant/plan binding, non-expired independent approval, security/SRE sign-off and DBRE approval when databases are in scope. Unresolved critical exceptions are **NO-GO** regardless of score.

## 14. Evidence and cleanup
Archive sanitized CI logs, plan digests, state versions, cloud audit, GitOps reconciliation, SLO graphs, rollback timings, database integrity and reviewer sign-offs. Do not equate authored tests with executed tests.

**Next:** Chapter 118 — Enterprise IaC Failure Injection, Chaos Engineering and Disaster Recovery Validation.
