# Chapter 110 — Enterprise IaC Platform Engineering, Governance and Reliability Acceptance Capstone

**Part 22 — Enterprise Platforms · Chapter 110/120 · Enterprise SRE/DBRE**

> **Evidence boundary:** This chapter defines an enterprise acceptance framework and offline synthetic evaluator. It does not constitute proof of real identity enforcement, production state recovery, Kubernetes SLO compliance, DBRE restore testing or external security approval. Execute native drills and obtain independent sign-off separately.

## 1. Learning objectives and prerequisites
Combine Chapters 106–109 into a production-oriented enterprise platform capstone covering service catalog, self-service templates, multi-tenant governance, RBAC, Terraform/OpenTofu execution, GitOps, Kubernetes, DBRE, FinOps, observability, incident response and reliability acceptance.

**Prerequisites:** Chapters 106–109, cloud IAM, OIDC, policy-as-code, IaC state and recovery, Kubernetes/GitOps, SLO/error budgets, database backup/PITR and change management.

## 2. Capstone scenario
A platform engineering organization serves three independent application teams across AWS, Azure and GCP. The platform provides golden paths for stateless APIs and stateful databases, with Terraform/OpenTofu modules, isolated runners, versioned state, GitOps delivery, SLO dashboards and centrally reviewed policies.

The capstone must show that a tenant cannot reach another tenant's secrets or state, a production deployment cannot bypass review, a database service cannot go live without DBRE recovery evidence, and platform failures are observable and recoverable.

## 3. Target architecture
```text
SSO/OIDC + team directory
          |
Developer portal + service catalog + ownership
          |
Versioned golden paths + request validation
          |
PR -> static checks -> policy -> plan -> cost
          |
Scoped approvals bound to immutable plan hash
          |
Ephemeral CI workload identity + isolated state
          |
AWS/Azure/GCP + Kubernetes + database services
          |
GitOps + SLOs + audit + FinOps + DR
          |
Incident response + restore + remediation
```

Platform availability is not the same as application availability. Model control-plane dependencies including the IdP, artifact registry, policy engine, state backend, CI runners, KMS and cloud APIs.

## 4. Enterprise acceptance artifacts
Produce a catalog of owners and service tiers; architecture and threat model; tenant isolation matrix; RBAC/IAM and admission policy tests; module versions and plan hashes; IaC state recovery evidence; Kubernetes deployment and SLO evidence; DBRE backup/PITR and data-integrity evidence; cost allocations; incident timeline; and signed acceptance records.

Do not equate a successful pipeline with a compliant, secure or recoverable deployment.

## 5. Cross-cloud and IaC controls
**AWS:** account/OUs, SCPs, workload identity, IAM boundaries, CloudTrail, KMS and isolated state.

**Azure:** subscriptions, management groups, Azure RBAC/Policy, managed identity, Key Vault and Activity Logs.

**GCP:** organization/folder/project boundaries, IAM/org policies, workload identity federation, Cloud KMS and Audit Logs.

**Terraform/OpenTofu:** pinned modules/providers, encrypted locked state, protected backends, reviewable plan artifacts, drift detection, recovery snapshots and rollback documentation.

**Kubernetes/GitOps:** scoped namespaces/projects, Pod Security Admission, NetworkPolicy, quotas, probes, PDB, HPA, resource requests/limits, workload identity, admission controls and SLOs.

**DBRE:** database-specific least privilege, PITR/backup verification, data correctness, capacity, SLO, RPO/RTO, failover fencing and retention ownership.

## 6. Lab A — Offline 100-point platform acceptance gate

Create `infrastructure-as-code/labs/chapter-110/platform_acceptance.py`:

```python
"""Offline platform acceptance scorecard; no cloud, GitOps or database operations."""
from dataclasses import dataclass

WEIGHTS = {
    "catalog_ownership": 10,
    "golden_path_versioned": 10,
    "tenant_isolation": 15,
    "identity_least_privilege": 10,
    "policy_enforced": 10,
    "plan_hash_approved": 5,
    "state_restore_verified": 10,
    "kubernetes_slo_verified": 10,
    "database_recovery_verified": 10,
    "audit_complete": 5,
    "incident_rehearsed": 5,
}
assert sum(WEIGHTS.values()) == 100

@dataclass(frozen=True)
class PlatformAcceptance:
    platform: str
    catalog_ownership: bool
    golden_path_versioned: bool
    tenant_isolation: bool
    identity_least_privilege: bool
    policy_enforced: bool
    plan_hash_approved: bool
    state_restore_verified: bool
    kubernetes_slo_verified: bool
    database_recovery_verified: bool
    audit_complete: bool
    incident_rehearsed: bool
    security_signed: bool
    sre_signed: bool
    dbre_signed: bool
    database_in_scope: bool

MANDATORY = ("catalog_ownership", "tenant_isolation", "identity_least_privilege",
             "policy_enforced", "plan_hash_approved", "state_restore_verified",
             "kubernetes_slo_verified", "audit_complete")

def assess(e: PlatformAcceptance):
    if not e.platform.strip():
        raise ValueError("platform is required")
    checks = {name: getattr(e, name) for name in WEIGHTS}
    score = sum(points for name, points in WEIGHTS.items() if checks[name])
    failed = [name for name, ok in checks.items() if not ok]
    required = list(MANDATORY)
    if e.database_in_scope:
        required.append("database_recovery_verified")
    signatures = e.security_signed and e.sre_signed and (
        not e.database_in_scope or e.dbre_signed)
    ready = score >= 90 and signatures and all(checks[name] for name in required)
    return {"score": score, "decision": "REVIEW_READY" if ready else "NO_GO",
            "failed": failed, "signatures_complete": signatures}
```

The result `REVIEW_READY` means synthetic fields meet the modeled controls; it does not grant permission or certify the platform.

## 7. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-110/test_platform_acceptance.py`:

```python
import unittest
from dataclasses import replace
from platform_acceptance import PlatformAcceptance, assess

class PlatformAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.e = PlatformAcceptance("enterprise-platform",
            True, True, True, True, True, True, True, True,
            True, True, True, True, True, True, True)
    def test_valid(self):
        self.assertEqual(assess(self.e)["score"], 100)
        self.assertEqual(assess(self.e)["decision"], "REVIEW_READY")
    def test_mandatory_controls(self):
        for name in ("catalog_ownership", "tenant_isolation",
                     "identity_least_privilege", "policy_enforced",
                     "plan_hash_approved", "state_restore_verified",
                     "kubernetes_slo_verified", "audit_complete",
                     "database_recovery_verified"):
            with self.subTest(control=name):
                self.assertEqual(assess(replace(self.e, **{name: False}))["decision"], "NO_GO")
    def test_signatures(self):
        for name in ("security_signed", "sre_signed", "dbre_signed"):
            with self.subTest(signature=name):
                self.assertEqual(assess(replace(self.e, **{name: False}))["decision"], "NO_GO")
    def test_database_out_of_scope(self):
        self.assertEqual(assess(replace(self.e,database_in_scope=False,
            dbre_signed=False,database_recovery_verified=False))["decision"],"REVIEW_READY")
    def test_threshold(self):
        e=replace(self.e,golden_path_versioned=False,incident_rehearsed=False)
        self.assertEqual(assess(e)["score"],85)
        self.assertEqual(assess(e)["decision"],"NO_GO")
    def test_missing_platform(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,platform=" "))
if __name__=="__main__":
    unittest.main()
```

Run:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-110 -p 'test_*.py' -v
```

Tests cover mandatory security/reliability controls, sign-off failures, database scope, threshold and invalid inputs.

## 8. Lab C — Full staging platform build (manual)
1. Provision a disposable staging platform account/project/subscription and isolated IaC backend.
2. Integrate enterprise test SSO/OIDC, tenant identities and catalog ownership.
3. Publish versioned golden paths for a stateless Kubernetes API and a database-backed service.
4. Run a tenant request through schema, policy, cost, plan and approval workflows.
5. Verify plan-hash binding, short-lived runner identity and state locking before apply.
6. Deploy the approved workload through GitOps and verify SLO, logs, traces and alerts.
7. Attempt cross-tenant state and secret reads with test identities; require explicit deny evidence.
8. Exercise policy rejection for unsupported region, public data storage and privileged IAM.
9. Trigger a staging runner or policy-service failure and verify fail-closed behavior and recovery.
10. Capture change IDs, logs, plans, metrics, cost tags and reviewer evidence.

## 9. Lab D — Stateful DBRE and DR capstone (manual)
1. Request a synthetic PostgreSQL service with approved RPO/RTO, data classification, ownership and retention.
2. Verify isolated credentials, encryption, private connectivity, PITR and backup copies.
3. Generate synthetic transactions and record consistency markers.
4. Restore into an isolated recovery instance; validate transactions and actual RPO/RTO.
5. Test DBRE rejection of missing backups or incompatible data-retention settings.
6. Recover a disposable Terraform/OpenTofu backend from a verified snapshot.
7. Validate application recovery through Kubernetes/GitOps and service transactions.
8. Review database-specific alternatives for MongoDB, Redis, Kafka and Elasticsearch.
9. Document rollback/failback, audit records and independent DBRE/SRE approval.
10. Clean up only approved disposable resources, preserving evidence.

## 10. Troubleshooting scenarios
| Failure | Detection | Safe action |
|---|---|---|
| Catalog ownership missing | schema check | reject request |
| Unauthorized tenant access | IAM audit | revoke and investigate |
| OIDC token mismatch | identity logs | correct trust |
| Privileged runner | IAM review | restrict permissions |
| Unpinned module | dependency scan | pin approved version |
| Plan hash mismatch | CI evidence | require new review |
| State lock contention | backend lock | identify owner |
| State corruption | checksum/version | restore isolated copy |
| Policy engine unavailable | decision timeout | fail closed |
| Unsupported cloud region | policy denial | approved alternative |
| Public network exposure | security scan | block apply |
| Kubernetes admission failure | admission events | remediate manifest |
| GitOps drift | sync mismatch | reconcile source |
| Runner saturation | queue latency | protect capacity |
| SLO budget breach | burn alert | risk review |
| Audit log gap | evidence check | block acceptance |
| Database PITR missing | archive check | DBRE NO-GO |
| DB integrity mismatch | checksum failure | quarantine restore |
| DR RTO exceeded | recovery timeline | record breach |
| Decommission retention violation | data inventory | data-owner review |

## 11. Production runbooks
**RB-01 Platform incident:** declare severity, incident commander, affected tenants and communications.

**RB-02 Unauthorized access:** isolate principal, revoke credentials, preserve evidence and notify security.

**RB-03 State recovery:** verify backups and locks, restore isolated state, compare plans and reconcile safely.

**RB-04 Policy outage:** fail closed, queue approved requests and recover decision service.

**RB-05 CI runner outage:** inspect queue, credentials, idempotency and safe retries.

**RB-06 Kubernetes/GitOps incident:** inspect admission, controllers, namespaces, PDB, HPA, routing and rollback.

**RB-07 DBRE recovery:** validate backup/PITR, single-writer authority, integrity, RPO/RTO and credentials.

**RB-08 SLO error budget:** inspect burn, pause risky releases and record approved exceptions.

**RB-09 Platform rollback:** pin prior approved template/module, replan and verify deployed service.

**RB-10 Final acceptance:** reconcile scorecard, evidence, signatures, exceptions and remediation owners.

## 12. Enterprise acceptance scorecard (100 points)
| Domain | Points |
|---|---:|
| Service catalog ownership | 10 |
| Versioned golden paths | 10 |
| Tenant isolation | 15 |
| Least-privilege identity | 10 |
| Policy enforcement | 10 |
| Plan approval binding | 5 |
| Terraform/OpenTofu state recovery | 10 |
| Kubernetes SLO verification | 10 |
| DBRE recovery validation | 10 |
| Audit completeness | 5 |
| Incident rehearsal | 5 |
| **Total** | **100** |

**Acceptance threshold:** 90/100 with mandatory catalog ownership, tenant isolation, least privilege, policy enforcement, approved plan binding, state recovery, Kubernetes SLO, audit evidence, and DBRE restore evidence when databases are in scope. Security and SRE sign-off are mandatory; DBRE sign-off is mandatory for database services. Any missing mandatory control yields **NO-GO**.

## 13. Closure and next chapter
The curriculum publication milestone does not equal independent production acceptance. Retain reproducible lab artifacts, policy test results, state recovery evidence, SLO dashboards and review records.

**Part 22 — Enterprise Platforms publication complete (Chapters 106–110).**

**Next:** Chapter 111 — Enterprise IaC Advanced Automation, Intelligent Operations and Autonomous Remediation.
