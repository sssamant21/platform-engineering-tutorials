# Chapter 114 — Enterprise IaC Automation Safety, Guardrails, Human-in-the-Loop and Governance

**Part 23 — Advanced Automation · Chapter 114/120 · Enterprise SRE/DBRE**

> **Verification boundary:** The offline Python gate checks synthetic evidence. It does not authenticate identities, verify cryptographic hashes, consult a live policy engine, issue credentials, execute Terraform/OpenTofu or approve production changes. `REVIEW_READY` is not authorization.

## 1. Learning objectives and prerequisites
Establish an enterprise control plane for automation: action allowlists, tenant isolation, least privilege, separation of duties, human-in-the-loop approvals, immutable plan binding, emergency access, kill switches, SRE/DBRE controls, evidence retention and safety acceptance.

**Prerequisites:** Chapters 106–113, IAM/OIDC, Terraform/OpenTofu plans and state, Kubernetes/GitOps, policy-as-code, incident response and database recovery.

## 2. Governance architecture
```text
Developer / CI / event / AI advisory recommendation
                         |
              Identity and tenant validation
                         |
          Deterministic policy and action allowlist
                         |
           Dry run + immutable plan hash + diff
                         |
     Human approval + separation of duties + expiry
                         |
        Scope-bound short-lived executor identity
                         |
      Kill switch + audit + SLO + rollback watchdog
                         |
             Post-change verification
                         |
               Accept / abort / escalate
```

AI output is untrusted advice. Do not allow prompts, incident logs, pull request comments or model-generated scripts to authorize privileged actions.

## 3. Mandatory automation invariants
1. Deny when the identity, policy service or audit sink is unavailable.
2. Match tenant, environment, resource scope, action and immutable plan hash to approval.
3. Separate requester and approver for sensitive changes.
4. Require explicit expiration and revocation of approvals.
5. Enforce least-privilege ephemeral credentials at the executor, not only in the portal.
6. Prevent cross-tenant state, secrets, network and database access.
7. Require dry-run, rollback readiness and change window where applicable.
8. Enforce an independent kill switch that halts queued and in-flight work safely.
9. Preserve tamper-evident logs, trace IDs and incident/change correlation.
10. Require SRE/DBRE/security approval for production, data and privileged security operations.

## 4. Human-in-the-loop operating model

| Change class | Examples | Minimum control |
|---|---|---|
| Observe | read-only plan, SLO query | scoped read identity |
| Low-risk recovery | disposable runner restart | approved allowlist and audit |
| Production infrastructure | apply, routing, cluster upgrade | SRE approval and policy |
| Privileged security | IAM, firewall, key changes | security approval and separation |
| Stateful data | failover, restore, schema, retention | DBRE approval, integrity and RPO/RTO |
| Emergency | break-glass incident response | time-bound ticket, dual review where feasible, retrospective |

A break-glass path is not a bypass of audit or identity controls. Record the incident, scope, expiry, justification and post-incident review.

## 5. Policy enforcement points
**Source control:** signed commits/PRs, protected branches, code owners, secret scanning and module version pinning.

**CI/CD:** pinned runner images, ephemeral identities, immutable plan artifacts, required checks and explicit approval.

**Terraform/OpenTofu:** encrypted state, locking, protected backends, reviewed plan hashes and no unauthorized force-unlock.

**Cloud:** AWS SCP/IAM boundaries, Azure Policy/RBAC and GCP org policy/IAM enforced natively.

**Kubernetes/GitOps:** admission policies, namespace isolation, RBAC, service-account scoping and Git as source of truth.

**DBRE:** backup/PITR and data integrity evidence, database-native least privilege, approved retention and recovery runbooks.

## 6. Approval integrity and time
Bind each approval to a canonical action, tenant, resource, environment, plan digest, identity, policy version and expiry. Use trusted UTC timestamps and verify against an authoritative clock. The sample lab compares strings and timestamps but does not verify signatures or live identities.

Avoid approval reuse after any plan change. A new plan requires a new approval.

## 7. Kill switches and safe rollback
Provide tenant-level, environment-level and global kill switches with independent authority. On activation, stop new dispatch, cancel safe-to-cancel queued work, reconcile uncertain in-flight operations, and alert incident command. Never assume a timed-out Terraform apply or database failover has not changed state.

Test kill switches in staging and verify they cannot be disabled by the same compromised executor.

## 8. Lab A — Offline governance gate

Create `infrastructure-as-code/labs/chapter-114/governance_gate.py`:

```python
"""Offline fail-closed automation governance decision gate. No infrastructure writes."""
from dataclasses import dataclass
from datetime import datetime,timezone

LOW_RISK={"retry_readonly_plan","restart_disposable_runner","reconcile_nonprod_catalog"}
@dataclass(frozen=True)
class ChangeRequest:
    change_id:str
    tenant:str
    authorized_tenant:str
    environment:str
    action:str
    requester:str
    approver:str
    approved_action:str
    approved_plan_hash:str
    submitted_plan_hash:str
    approval_expires_at:str
    evaluation_time:str
    emergency:bool
    break_glass_ticket:str
    kill_switch_enabled:bool
    policy_healthy:bool
    audit_healthy:bool
    identity_verified:bool
    dry_run_passed:bool
    rollback_verified:bool
    scope_limited:bool
    database_affected:bool
    dbre_approved:bool
    security_affected:bool
    security_approved:bool
    sre_approved:bool

def parse_utc(value):
    try:
        t=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO 8601 timestamp") from exc
    if t.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return t.astimezone(timezone.utc)

def evaluate(e:ChangeRequest):
    if not all((e.change_id.strip(),e.tenant.strip(),e.requester.strip(),e.approver.strip())):
        raise ValueError("missing change identity")
    now=parse_utc(e.evaluation_time)
    expiry=parse_utc(e.approval_expires_at)
    checks={
        "tenant_scope":e.tenant==e.authorized_tenant,
        "environment":e.environment in {"dev","stage","prod"},
        "action_allowlist":e.action in LOW_RISK,
        "separation_of_duties":e.requester!=e.approver,
        "action_binding":e.action==e.approved_action,
        "plan_binding":bool(e.submitted_plan_hash) and e.submitted_plan_hash==e.approved_plan_hash,
        "approval_not_expired":now<expiry,
        "break_glass":not e.emergency or bool(e.break_glass_ticket.strip()),
        "kill_switch":not e.kill_switch_enabled,
        "policy":e.policy_healthy,
        "audit":e.audit_healthy,
        "identity":e.identity_verified,
        "dry_run":e.dry_run_passed,
        "rollback":e.rollback_verified,
        "scope":e.scope_limited,
        "sre":e.environment!="prod" or e.sre_approved,
        "dbre":not e.database_affected or e.dbre_approved,
        "security":not e.security_affected or e.security_approved,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"decision":"REVIEW_READY" if not failed else "NO_GO","failed_controls":failed}
```

Only three low-risk actions are allowed in this example. Terraform apply/destroy and database mutations remain explicitly excluded.

## 9. Lab B — Negative unit tests

Create `infrastructure-as-code/labs/chapter-114/test_governance_gate.py`:

```python
import unittest
from dataclasses import replace
from governance_gate import ChangeRequest,evaluate

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.e=ChangeRequest("CHG-114","team-a","team-a","prod","retry_readonly_plan",
            "alice","bob","retry_readonly_plan","sha256:abc","sha256:abc",
            "2026-10-21T12:00:00Z","2026-10-20T12:00:00Z",
            False,"",False,True,True,True,True,True,True,False,False,False,False,True)
    def test_valid(self):
        self.assertEqual(evaluate(self.e)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_scope",evaluate(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_separation_of_duties(self):
        self.assertIn("separation_of_duties",evaluate(replace(self.e,approver="alice"))["failed_controls"])
    def test_expired_approval(self):
        self.assertIn("approval_not_expired",evaluate(replace(self.e,approval_expires_at="2026-10-19T12:00:00Z"))["failed_controls"])
    def test_plan_mismatch(self):
        self.assertIn("plan_binding",evaluate(replace(self.e,submitted_plan_hash="sha256:other"))["failed_controls"])
    def test_kill_switch(self):
        self.assertIn("kill_switch",evaluate(replace(self.e,kill_switch_enabled=True))["failed_controls"])
    def test_unsafe_action(self):
        self.assertIn("action_allowlist",evaluate(replace(self.e,action="terraform_destroy"))["failed_controls"])
    def test_critical_controls(self):
        for field in ("policy_healthy","audit_healthy","identity_verified",
                      "dry_run_passed","rollback_verified","scope_limited","sre_approved"):
            with self.subTest(field=field):
                self.assertEqual(evaluate(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_database_review(self):
        self.assertIn("dbre",evaluate(replace(self.e,database_affected=True))["failed_controls"])
    def test_security_review(self):
        self.assertIn("security",evaluate(replace(self.e,security_affected=True))["failed_controls"])
    def test_break_glass(self):
        self.assertIn("break_glass",evaluate(replace(self.e,emergency=True))["failed_controls"])
    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.e,evaluation_time="2026-10-20T12:00:00"))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-114 -p 'test_*.py' -v
```

## 10. Lab C — Human approval and kill-switch rehearsal (manual)
1. Provision disposable staging CI runners, a protected IaC backend and a test policy service.
2. Configure two test identities with distinct requester and approver permissions.
3. Produce a read-only plan and bind an approval to the plan digest, tenant, scope and expiry.
4. Change the plan artifact and verify the prior approval cannot be reused.
5. Attempt self-approval and cross-tenant execution; require native denial evidence.
6. Simulate policy service and audit sink outages; verify the executor fails closed.
7. Activate the kill switch during a staged workflow; inspect queued and in-flight work.
8. Restore the policy/audit services and reconcile actual infrastructure state before retrying.
9. Capture identity logs, policy decisions, plan digests, trace IDs and incident records.
10. Remove only disposable staging resources and retain sanitized evidence.

## 11. Lab D — DBRE and emergency governance (manual)
1. Model a synthetic PostgreSQL recovery request with RPO/RTO and data classification.
2. Verify a proposed automated failover is denied without DBRE approval.
3. Inspect backup/PITR, single-writer fencing, data integrity and recovery runbooks.
4. Simulate a break-glass request with incident ticket, scoped access and expiry.
5. Verify emergency access is logged, reviewed and revoked after use.
6. Repeat the review pattern for MongoDB, Redis, Kafka and Elasticsearch.
7. Obtain independent SRE/DBRE/security review before any real recovery exercise.

## 12. Troubleshooting scenarios

| Failure | Signal | Safe response |
|---|---|---|
| Missing identity | auth failure | deny |
| Cross-tenant request | scope mismatch | deny |
| Self-approval | requester=approver | deny |
| Expired approval | timestamp | reapprove |
| Plan hash mismatch | digest comparison | stop |
| Policy service outage | missing decision | fail closed |
| Audit sink outage | missing receipt | halt |
| Overprivileged runner | IAM audit | revoke |
| Credential leak | secret scan | rotate |
| Unpinned module | dependency scan | pin version |
| State lock contention | lock record | investigate |
| Kill switch fails | execution continues | isolate executor |
| In-flight apply uncertain | timeout | reconcile state |
| GitOps conflicts | drift loop | fix source of truth |
| SLO regression | burn alert | abort/rollback |
| Break-glass abuse | unusual privilege | incident escalation |
| Missing DBRE approval | change record | deny |
| PITR unavailable | backup audit | block |
| Incomplete evidence | audit gap | NO-GO |
| Approval policy drift | version mismatch | revalidate |

## 13. Production runbooks
**RB-01 Unauthorized automation:** disable executor, revoke identity, preserve evidence.

**RB-02 Policy outage:** fail closed and restore policy service.

**RB-03 Approval mismatch:** stop action, regenerate plan and request fresh approval.

**RB-04 Kill-switch activation:** halt dispatch, reconcile in-flight effects and alert on-call.

**RB-05 Credential compromise:** revoke/rotate, audit scope and assess data exposure.

**RB-06 Terraform state incident:** preserve locks, verify snapshot and reconcile through reviewed plan.

**RB-07 GitOps conflict:** identify competing controllers and restore Git authority.

**RB-08 DBRE unsafe operation:** preserve database state, backup and fencing evidence; escalate.

**RB-09 Break-glass review:** expire emergency access, collect evidence and perform retrospective.

**RB-10 Governance acceptance:** audit policies, negative tests, sign-offs and exception expiry.

## 14. Enterprise acceptance (100 points)

| Domain | Points |
|---|---:|
| Identity, tenant isolation and least privilege | 15 |
| Deterministic policy and action allowlist | 15 |
| Approval binding, expiry and separation | 15 |
| Audit, evidence integrity and traceability | 10 |
| Kill switch and failure containment | 15 |
| Terraform/OpenTofu and GitOps safeguards | 10 |
| DBRE and emergency governance | 10 |
| Negative tests, rollback and drills | 10 |
| **Total** | **100** |

**Acceptance:** at least 90/100 and mandatory native proof of identity/tenant isolation, no self-approval, immutable plan binding, fail-closed policy/audit behavior, kill-switch effectiveness, scoped executor credentials and DBRE approval for data-impacting changes. Any missing mandatory evidence is **NO-GO**.

## 15. Cleanup and next chapter
Preserve sanitized audit events, signed approval records, plan hashes, negative test results and independent reviewer decisions. Do not use production credentials or customer data in synthetic labs.

**Next:** Chapter 115 — Enterprise IaC Advanced Automation, AI Safety and Operational Acceptance Capstone.
