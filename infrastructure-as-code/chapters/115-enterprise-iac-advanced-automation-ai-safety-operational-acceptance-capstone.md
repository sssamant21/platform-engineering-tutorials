# Chapter 115 — Enterprise IaC Advanced Automation, AI Safety and Operational Acceptance Capstone

**Part 23 — Advanced Automation · Chapter 115/120 · Enterprise SRE/DBRE**

> **Verification boundary:** This chapter and its offline evaluator provide a reproducible training artifact, not production certification. Native cloud IAM, event authentication, approval cryptography, database restore and independent acceptance remain to be tested.

## 1. Objectives and prerequisites

Integrate Chapters 111–114 into one end-to-end enterprise automation acceptance exercise: intelligent operations, event-driven workflow orchestration, predictive drift/change-risk analysis, human-in-the-loop approvals, emergency controls, audit and rollback. Prerequisites: Terraform/OpenTofu, cloud IAM, Kubernetes/GitOps, observability, SLOs, policy-as-code, DBRE and incident response.

## 2. Capstone scenario

A multi-tenant platform operates AWS, Azure and GCP infrastructure, Kubernetes workloads, and PostgreSQL/MongoDB/Redis/Kafka/Elasticsearch services. A staging incident triggers a signed event, read-only drift analysis and an AI-assisted explanation. A deterministic controller assesses policy, scope, approvals, plan digest, retry budget, kill switch, rollback and audit readiness. Only a preapproved low-risk staging action can be dispatched. Production applies, database failovers, IAM escalation and destructive changes require a separate explicitly approved process.

## 3. Reference architecture

```text
Cloud audit + OTel + GitOps + CI + DBRE alerts
                     |
Authenticated ingress -> durable queue -> deduplication
                     |
Correlation -> drift/capacity evidence -> AI advisory
                     |
Deterministic policy -> tenant/IAM -> approval/plan hash
                     |
Kill switch + scoped executor + retry budget
                     |
Read-only plan or approved low-risk remediation
                     |
SLO verification + audit + rollback/escalation
                     |
Independent security / SRE / DBRE acceptance
```

**Hard boundary:** AI-generated commands and event payloads are untrusted. Never grant an LLM direct cloud credentials or let it bypass deterministic policy and change management.

## 4. Acceptance controls

| Control | Evidence |
|---|---|
| Event authentication | provider-native signature/identity and source allowlist |
| Replay and idempotency | duplicate-event drill, durable idempotency records |
| Tenant isolation | cross-tenant IAM and state negative tests |
| Least privilege | scoped, short-lived executor credentials |
| Deterministic policy | fail-closed decision and denied destructive action |
| Human approval binding | action, tenant, environment, resource, plan digest, expiry |
| Kill switch | tested dispatch stop and in-flight reconciliation |
| Audit | complete immutable event-to-change correlation |
| Rollback | restored service, state and integrity checks |
| SLO validation | before/after error-budget and latency evidence |
| DBRE recovery | backup/PITR, fencing, data integrity, RPO/RTO |

## 5. Cloud and platform integration

**AWS:** CloudTrail/EventBridge, scoped STS roles, Organizations/SCPs, CloudWatch and state encryption/locking.

**Azure:** Event Grid/Activity Logs, managed identity, Azure Policy/RBAC, Azure Monitor and protected backends.

**GCP:** Eventarc/Pub/Sub, Audit Logs, workload identity federation, organization policy and Cloud Monitoring.

**Terraform/OpenTofu:** immutable reviewed plan, isolated state, lock discipline, versioned recovery snapshots and explicit apply approval.

**Kubernetes/GitOps:** namespace-scoped identity, admission controls, reconciliation health, workload SLOs and Git as source of truth.

**DBRE:** PostgreSQL, MongoDB, Redis, Kafka and Elasticsearch require technology-specific consistency, backup, failover and rollback procedures. Never equate a healthy automation workflow with verified data correctness.

## 6. Lab A — Offline 100-point acceptance gate

Create `infrastructure-as-code/labs/chapter-115/acceptance_gate.py`:

```python
"""Offline advanced automation acceptance gate; no external actions."""
from dataclasses import dataclass

WEIGHTS={
 "event_authentication":10,"replay_and_idempotency":10,
 "tenant_isolation":15,"least_privilege":10,"deterministic_policy":10,
 "human_approval_binding":10,"kill_switch_tested":10,
 "audit_complete":5,"rollback_rehearsed":10,"slo_validation":5,
 "dbre_recovery_evidence":5,
}
MANDATORY=("event_authentication","replay_and_idempotency","tenant_isolation",
 "least_privilege","deterministic_policy","human_approval_binding",
 "kill_switch_tested","audit_complete","rollback_rehearsed","slo_validation")
assert sum(WEIGHTS.values())==100

@dataclass(frozen=True)
class Evidence:
    change_id:str
    tenant:str
    environment:str
    event_authentication:bool
    replay_and_idempotency:bool
    tenant_isolation:bool
    least_privilege:bool
    deterministic_policy:bool
    human_approval_binding:bool
    kill_switch_tested:bool
    audit_complete:bool
    rollback_rehearsed:bool
    slo_validation:bool
    dbre_recovery_evidence:bool
    database_in_scope:bool
    security_approved:bool
    sre_approved:bool
    dbre_approved:bool
    unsafe_ai_instruction_detected:bool

def assess(e:Evidence):
    if not e.change_id.strip() or not e.tenant.strip():
        raise ValueError("change ID and tenant required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    score=sum(points for key,points in WEIGHTS.items() if getattr(e,key))
    required=list(MANDATORY)
    if e.database_in_scope:
        required.append("dbre_recovery_evidence")
    failed=[key for key in required if not getattr(e,key)]
    if e.unsafe_ai_instruction_detected:
        failed.append("unsafe_ai_instruction")
    if not e.security_approved: failed.append("security_approval")
    if not e.sre_approved: failed.append("sre_approval")
    if e.database_in_scope and not e.dbre_approved:
        failed.append("dbre_approval")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
```

The scorecard returns `REVIEW_READY` or `NO_GO`. `REVIEW_READY` is only synthetic evidence eligibility, **not** authorization to run automation.

## 7. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-115/test_acceptance_gate.py`:

```python
import unittest
from dataclasses import replace
from acceptance_gate import Evidence,assess

class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.e=Evidence("CHG-115","team-a","prod",True,True,True,True,
            True,True,True,True,True,True,True,True,True,True,True,False)
    def test_pass(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
        self.assertEqual(assess(self.e)["score"],100)
    def test_mandatory_failures(self):
        for key in ("event_authentication","replay_and_idempotency","tenant_isolation",
                    "least_privilege","deterministic_policy","human_approval_binding",
                    "kill_switch_tested","audit_complete","rollback_rehearsed",
                    "slo_validation","dbre_recovery_evidence"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_approvals(self):
        for key in ("security_approved","sre_approved","dbre_approved"):
            with self.subTest(key=key):
                self.assertEqual(assess(replace(self.e,**{key:False}))["decision"],"NO_GO")
    def test_ai_injection(self):
        self.assertIn("unsafe_ai_instruction",assess(replace(self.e,
            unsafe_ai_instruction_detected=True))["failed_controls"])
    def test_database_out_of_scope(self):
        e=replace(self.e,database_in_scope=False,dbre_approved=False,
            dbre_recovery_evidence=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
    def test_invalid_identity(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,tenant=" "))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-115 -p 'test_*.py' -v
```

## 8. Lab C — Event-driven safe automation rehearsal

1. Provision disposable staging identities, an isolated state backend, queue, DLQ, workflow store and test Kubernetes namespace.
2. Produce a synthetic signed event with tenant, trace ID, resource, action and idempotency key.
3. Verify native producer authentication and replay rejection.
4. Correlate Git revision, cloud audit, read-only Terraform/OpenTofu plan and SLO telemetry.
5. Generate an optional sanitized AI explanation; inject adversarial text and confirm no execution authority.
6. Bind a low-risk action to exact scope, immutable plan digest, expiry and independent approval.
7. Attempt unauthorized production apply, cross-tenant access and privilege escalation; confirm native denial.
8. Exercise one approved disposable-runner recovery, verify idempotency and collect before/after SLOs.
9. Trigger policy outage, kill switch and retry exhaustion; verify fail-closed, DLQ and incident escalation.
10. Preserve audit evidence and clean up only approved staging resources.

## 9. Lab D — DBRE and disaster recovery safety

1. Request a synthetic database-backed service with owner, tier, RPO/RTO and data classification.
2. Confirm automation refuses unapproved database failover, retention changes and backup deletion.
3. Capture backup/PITR coverage, restore plan and transaction consistency markers.
4. Conduct a separately approved isolated restore; measure actual RPO/RTO and integrity.
5. Test Terraform/OpenTofu backend restore and compare the recovered state against authoritative resources.
6. Verify GitOps reconciliation does not overwrite recovery actions unexpectedly.
7. Revoke emergency identities, review break-glass evidence and obtain independent DBRE/SRE/security sign-off.
8. Record unresolved exceptions as NO-GO, even when the numeric score exceeds 90.

## 10. Twenty troubleshooting scenarios

| # | Failure | Safe response |
|---|---|---|
| 1 | Forged event | reject untrusted producer |
| 2 | Replayed event | verify durable deduplication |
| 3 | Missing idempotency key | deny dispatch |
| 4 | Wrong tenant | deny and alert |
| 5 | Cross-account role | revoke executor |
| 6 | Excessive privileges | reduce IAM scope |
| 7 | Policy engine unavailable | fail closed |
| 8 | Approval expired | request new approval |
| 9 | Plan hash changed | invalidate approval |
| 10 | Self-approval | enforce separation |
| 11 | AI prompt injection | ignore untrusted instructions |
| 12 | Hallucinated remediation | reject nonallowlisted action |
| 13 | Kill switch unresponsive | isolate executor |
| 14 | Retry storm | disable trigger and cap retries |
| 15 | Queue poison message | quarantine in DLQ |
| 16 | Audit sink unavailable | halt privileged work |
| 17 | Terraform state locked | inspect lock owner |
| 18 | GitOps conflict | reconcile Git authority |
| 19 | SLO regression | abort and escalate |
| 20 | DB failover unsafe | require DBRE fencing and restore evidence |

## 11. Ten production runbooks

**RB-01 — Incident command:** classify impact, establish commander and freeze unsafe automation.

**RB-02 — Event replay:** quarantine source, inspect idempotency records and deduplicate.

**RB-03 — Identity compromise:** revoke workload credentials and review cross-tenant access.

**RB-04 — Policy outage:** deny all privileged actions and restore policy authority.

**RB-05 — AI unsafe output:** isolate model advice from executor and record incident.

**RB-06 — Kill switch:** stop dispatch and reconcile uncertain in-flight operations.

**RB-07 — Terraform state recovery:** preserve locks, restore isolated snapshot, verify plan.

**RB-08 — GitOps recovery:** remove conflicting writers and validate authoritative Git.

**RB-09 — DBRE recovery:** verify backup, fencing, RPO/RTO and data integrity.

**RB-10 — Final acceptance:** collect signed evidence, record exceptions and issue GO/NO-GO.

## 12. Enterprise 100-point acceptance assessment

| Domain | Points |
|---|---:|
| Authenticated event ingestion | 10 |
| Replay protection and idempotency | 10 |
| Tenant isolation | 15 |
| Least-privilege execution | 10 |
| Deterministic policy | 10 |
| Human approval and plan binding | 10 |
| Kill-switch effectiveness | 10 |
| Audit completeness | 5 |
| Rollback rehearsal | 10 |
| SLO validation | 5 |
| DBRE recovery evidence | 5 |
| **Total** | **100** |

**Acceptance:** at least 90/100, all mandatory controls, independent security and SRE approval, plus DBRE evidence and approval when databases are in scope. Any unsafe AI instruction, unauthorized action or mandatory control failure is **NO-GO**, irrespective of score.

## 13. Closure

Record change IDs, event IDs, policy versions, approvals, test outputs, rollback timings, SLO evidence, security exceptions and DBRE restore results. Publication does not certify execution.

**Part 23 — Advanced Automation publication complete (Chapters 111–115).**

**Next:** Chapter 116 — Enterprise IaC Final Architecture, Operational Readiness and Reliability Capstone.
