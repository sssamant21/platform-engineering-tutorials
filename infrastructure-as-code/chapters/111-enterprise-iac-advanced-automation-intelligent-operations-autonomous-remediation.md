# Chapter 111 — Enterprise IaC Advanced Automation, Intelligent Operations and Autonomous Remediation

**Part 23 — Advanced Automation · Chapter 111/120 · Enterprise SRE/DBRE**

> **Safety boundary:** This chapter's offline gate models eligibility only. It does not authenticate users, call an LLM, execute Terraform/OpenTofu, remediate Kubernetes, or modify databases. A `REVIEW_READY` decision is not deployment authorization.

## 1. Objectives
Build a bounded automation operating model for IaC drift, failed plans, GitOps reconciliation, CI runner recovery and SRE/DBRE incident response. Learn event correlation, deterministic policy, AI-assisted triage, human approvals, blast-radius limits, rollback, observability and evidence retention.

**Prerequisites:** Chapters 106–110, cloud IAM/OIDC, Terraform/OpenTofu state, Kubernetes/GitOps, policy-as-code, incident response, SLOs, DBRE backup and restore.

## 2. Reference architecture

```text
Prometheus / OpenTelemetry / cloud audit / GitOps events
                         |
            Normalize + deduplicate + correlate
                         |
           Incident classification and evidence
                         |
      Optional AI recommendation (untrusted advice)
                         |
        Deterministic allowlist + policy engine
                         |
    Tenant scope + identity + approval + blast radius
                         |
          Dry run + change window + rollback
                         |
   Human approval where required + scoped executor
                         |
       Post-action validation + audit + SLO checks
                         |
             Stop / rollback / escalation
```

AI-generated remediation is advisory and must never directly authorize execution. Treat model output and incident log content as untrusted inputs. Avoid feeding secrets, customer data or unrestricted credentials to an AI system.

## 3. Automation maturity levels

| Level | Capability | Execution policy |
|---|---|---|
| L0 | Detect and alert | No changes |
| L1 | Correlate and recommend | Human executes |
| L2 | Dry-run and prepare approved plan | No privileged apply |
| L3 | Bounded low-risk self-healing | Preapproved allowlist, audit, rollback |
| L4 | High-impact production remediation | Explicit human and domain-owner approval |

Do not treat maturity level as permission to skip cloud IAM, Kubernetes RBAC, provider-native policy or change controls.

## 4. Safe remediation catalog
**Potentially automatable after validation:** restart an isolated disposable CI runner; retry a verified idempotent failed plan without apply; reconcile nonproduction service catalog metadata from an authoritative source.

**Human-controlled:** Terraform/OpenTofu apply or destroy; state force-unlock; cloud IAM changes; Kubernetes cluster-wide changes; database failover; backup deletion; schema changes; secret rotation with production impact; network policy modifications.

Every action must define owner, preconditions, timeout, idempotency key, scope, rate limit, blast-radius ceiling, evidence, success criteria and abort procedure.

## 5. Cloud and platform integration
- **AWS:** EventBridge/CloudWatch and CloudTrail for event evidence; assume scoped roles through STS/OIDC, never broad permanent credentials.
- **Azure:** Azure Monitor and Activity Logs, managed identity, Azure Policy and scoped RBAC.
- **GCP:** Cloud Monitoring and Audit Logs, workload identity federation and organization policies.
- **Terraform/OpenTofu:** read-only drift assessment, protected state backends, plan hashes, locking and reviewed apply.
- **Kubernetes:** namespace-scoped service accounts, admission policy, controller health, GitOps reconciliation and SLO gates.
- **DBRE:** PostgreSQL, MongoDB, Redis, Kafka and Elasticsearch have different failover/consistency semantics; require domain runbooks and DBRE authorization before changing data-plane state.

## 6. Reliability and security invariants
1. Fail closed if policy, identity, audit, rollback evidence or state-lock status is unavailable.
2. Never let an LLM-generated command execute without deterministic validation.
3. Bind approval to the exact tenant, resource, action, environment and artifact hash.
4. Enforce least-privilege short-lived executor credentials.
5. Limit concurrency and action rate to avoid remediation loops.
6. Prevent cross-tenant actions and privileged escalation.
7. Require human authorization for production changes and DBRE/security-impacting operations.
8. Capture pre/post metrics, logs, trace IDs, decision rationale and approver identity.
9. Stop and escalate when validation fails, SLO worsens or state is ambiguous.
10. Periodically test rollback and incident containment in isolated staging.

## 7. Lab A — Offline remediation eligibility engine

Create `infrastructure-as-code/labs/chapter-111/remediation_gate.py`:

```python
"""Fail-closed offline remediation eligibility gate. No infrastructure actions."""
from dataclasses import dataclass

ALLOWED={"restart_disposable_runner","retry_idempotent_plan","reconcile_nonprod_catalog"}
@dataclass(frozen=True)
class Remediation:
    incident_id:str
    action:str
    environment:str
    tenant:str
    approved_tenant:str
    idempotent:bool
    preapproved:bool
    policy_passed:bool
    dry_run_passed:bool
    change_window_open:bool
    rollback_available:bool
    audit_sink_healthy:bool
    state_lock_clear:bool
    blast_radius_resources:int
    confidence_percent:int
    database_affected:bool
    security_affected:bool
    human_approved:bool
    dbre_approved:bool
    security_approved:bool

def evaluate(r:Remediation):
    if not r.incident_id.strip() or not r.tenant.strip():
        raise ValueError("incident and tenant required")
    if not 0<=r.confidence_percent<=100 or r.blast_radius_resources<0:
        raise ValueError("invalid confidence or blast radius")
    checks={
        "action_allowlist":r.action in ALLOWED,
        "environment":r.environment in {"dev","stage","prod"},
        "tenant_scope":r.tenant==r.approved_tenant,
        "idempotency":r.idempotent,
        "preapproval":r.preapproved,
        "policy":r.policy_passed,
        "dry_run":r.dry_run_passed,
        "change_window":r.change_window_open,
        "rollback":r.rollback_available,
        "audit":r.audit_sink_healthy,
        "state_lock":r.state_lock_clear,
        "blast_radius":r.blast_radius_resources<=3,
        "confidence":r.confidence_percent>=95,
        "production_human":r.environment!="prod" or r.human_approved,
        "database_human":not r.database_affected or (r.human_approved and r.dbre_approved),
        "security_human":not r.security_affected or (r.human_approved and r.security_approved),
    }
    failed=[k for k,v in checks.items() if not v]
    return {"decision":"REVIEW_READY" if not failed else "NO_GO","failed_controls":failed}
```

The allowlist intentionally excludes Terraform apply/destroy and database mutations.

## 8. Lab B — Negative unit tests

Create `infrastructure-as-code/labs/chapter-111/test_remediation_gate.py`:

```python
import unittest
from dataclasses import replace
from remediation_gate import Remediation,evaluate

class GateTests(unittest.TestCase):
    def setUp(self):
        self.r=Remediation("INC-123","retry_idempotent_plan","stage","team-a",
            "team-a",True,True,True,True,True,True,True,True,
            1,99,False,False,False,False,False)
    def test_allowed(self):
        self.assertEqual(evaluate(self.r)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_scope",evaluate(replace(self.r,tenant="team-b"))["failed_controls"])
    def test_disallowed_action(self):
        self.assertIn("action_allowlist",evaluate(replace(self.r,action="terraform_apply"))["failed_controls"])
    def test_all_guards_fail_closed(self):
        for f in ("idempotent","preapproved","policy_passed","dry_run_passed",
                  "change_window_open","rollback_available","audit_sink_healthy",
                  "state_lock_clear"):
            with self.subTest(f=f):
                self.assertEqual(evaluate(replace(self.r,**{f:False}))["decision"],"NO_GO")
    def test_production_needs_human(self):
        self.assertIn("production_human",evaluate(replace(self.r,environment="prod"))["failed_controls"])
    def test_database_needs_dbre(self):
        self.assertIn("database_human",evaluate(replace(self.r,database_affected=True,human_approved=True))["failed_controls"])
    def test_security_needs_review(self):
        self.assertIn("security_human",evaluate(replace(self.r,security_affected=True,human_approved=True))["failed_controls"])
    def test_invalid_confidence(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.r,confidence_percent=101))
    def test_blast_radius(self):
        self.assertIn("blast_radius",evaluate(replace(self.r,blast_radius_resources=4))["failed_controls"])
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-111 -p 'test_*.py' -v
```

## 9. Lab C — Staging drift and incident correlation (manual)
1. Provision a disposable staging IaC workspace with encrypted, locked state.
2. Instrument runner, policy service, backend and GitOps controller with metrics, logs and trace IDs.
3. Introduce a controlled nonproduction configuration drift; generate a read-only plan.
4. Correlate cloud audit events, Git commit, pipeline ID and observed resource diff.
5. Feed sanitized event metadata to an optional AI assistant for explanation only.
6. Compare the recommendation against deterministic policy and allowlisted actions.
7. Test a rejected Terraform apply recommendation and verify no privileged execution.
8. Exercise a safe staging runner restart with documented approvals and rollback.
9. Measure detection and recovery time, capture SLO impact and audit evidence.
10. Remove only approved disposable resources.

## 10. Lab D — DBRE incident automation boundaries (manual)
1. Generate a synthetic staging database incident with replication lag or backup freshness warning.
2. Verify the event correlation pipeline produces evidence and routes to the DBRE owner.
3. Attempt a proposed automatic failover; confirm it is rejected by the low-risk allowlist.
4. Review RPO/RTO, quorum/fencing, PITR coverage and application transaction integrity.
5. Obtain human DBRE/SRE approval before any separately controlled recovery exercise.
6. Record data integrity, post-recovery health and audit evidence.
7. Repeat threat modeling for MongoDB, Redis, Kafka and Elasticsearch-specific recovery behavior.

## 11. Troubleshooting scenarios

| Scenario | Evidence | Safe response |
|---|---|---|
| Duplicate alert storm | event rate | deduplicate |
| False incident correlation | mismatched IDs | verify sources |
| Missing trace context | broken span links | repair instrumentation |
| Stale drift snapshot | old plan | regenerate read-only plan |
| Prompt injection in logs | suspicious instructions | ignore untrusted content |
| Hallucinated remediation command | unsupported action | deny |
| Wrong tenant | tenant mismatch | deny and investigate |
| Overprivileged executor | IAM audit | revoke scope |
| Policy service outage | no decision | fail closed |
| Audit sink outage | missing receipt | halt automation |
| State lock active | backend lock | investigate owner |
| Plan hash changed | artifact mismatch | reapprove |
| Retry not idempotent | duplicate effect | block |
| Remediation loop | repeated action | rate-limit and disable |
| Blast radius too large | resource count | escalate |
| SLO regression | burn alert | abort and roll back |
| GitOps fights automation | reconciliation loop | use source of truth |
| Database failover suggested | data-plane risk | DBRE review |
| Backup freshness unknown | missing archive evidence | block recovery |
| Emergency action expired | approval TTL | revoke access |

## 12. Production runbooks
**RB-01 Automation incident:** disable executor, preserve decisions, identify affected tenants.

**RB-02 Drift triage:** capture read-only plan, compare desired/live state and route ownership.

**RB-03 Policy outage:** stop all privileged automation and restore policy decision service.

**RB-04 Credential exposure:** revoke workload identity, rotate affected secrets and audit actions.

**RB-05 Remediation loop:** disable trigger, preserve state and investigate idempotency.

**RB-06 Terraform state incident:** preserve locks/snapshots, restore isolated state and review plans.

**RB-07 GitOps conflict:** halt competing writes and reconcile authoritative Git state.

**RB-08 DBRE event:** preserve consistency, backup and fencing evidence; obtain DBRE approval.

**RB-09 Failed rollback:** freeze changes, invoke incident command and validate service transactions.

**RB-10 Automation governance review:** review false positives, policy exceptions, SLOs, audit and change approvals.

## 13. Enterprise acceptance (100 points)

| Domain | Points |
|---|---:|
| Event ingestion and correlation | 10 |
| Deterministic policy and allowlist | 15 |
| Tenant identity and least privilege | 15 |
| Idempotency, rate and blast-radius controls | 10 |
| Dry run, change approval and plan binding | 10 |
| Audit, observability and SLO safeguards | 10 |
| Rollback and failure containment | 10 |
| DBRE data integrity and human approval | 10 |
| Negative tests and incident rehearsal | 10 |
| **Total** | **100** |

**Production acceptance:** at least 90/100 and mandatory native evidence of tenant isolation, policy fail-closed, scoped credentials, audit, rollback, no unauthorized production apply and DBRE review for database-impacting actions. Any mandatory control failure is **NO-GO**.

## 14. Cleanup and next chapter
Retain sanitized incidents, policy decisions, dry-run plans, negative tests and approval evidence. Do not use production data or credentials in AI prompts.

**Next:** Chapter 112 — Enterprise IaC Event-Driven Automation, Workflow Orchestration and Closed-Loop Operations.
