# Chapter 112 — Enterprise IaC Event-Driven Automation, Workflow Orchestration and Closed-Loop Operations

**Part 23 — Advanced Automation · Chapter 112/120 · Enterprise SRE/DBRE**

> **Evidence boundary:** The Python lab models decisions only. It does not verify actual cryptographic signatures, authenticate principals, persist workflow state, operate a queue, execute Terraform/OpenTofu, or modify cloud, Kubernetes or database resources. Production readiness requires native validation and independent approval.

## 1. Learning objectives
Design event-driven workflows that detect, correlate, authorize, execute, verify and audit infrastructure operations. Implement event envelopes, replay protection, deduplication, idempotency, durable orchestration, bounded retries, dead-letter queues, policy gates, human approvals, state recovery, observability and SRE/DBRE runbooks.

**Prerequisites:** Chapters 106–111, Terraform/OpenTofu, Kubernetes/GitOps, OIDC/IAM, policy-as-code, SLOs, event streaming and incident management.

## 2. Enterprise architecture

```text
Cloud audit / OTel / Prometheus / GitOps / CI / DB alerts
                           |
             Authenticated event ingress
                           |
    Schema validation -> deduplication -> durable queue
                           |
     Correlation + ownership + severity classification
                           |
        Deterministic policy + scoped authorization
                           |
       Durable workflow state + human approval
                           |
      Dry run -> bounded executor -> verification
                           |
      SLO checks + audit + rollback/escalation
                           |
             Completed / failed / DLQ
```

The event bus is not an authorization system. Authenticate event producers, verify signatures where supported, reject malformed payloads, enforce tenant boundaries and use least-privilege executor identities. Do not run shell commands supplied in events, log lines or AI recommendations.

## 3. Event envelope and workflow contract

Use an immutable event identifier, correlation ID, tenant, source, schema version, timestamp, action intent, resource reference, environment, trace ID and signature verification result. Reject missing or invalid identities, unrecognized actions, stale events and duplicate requests.

**Illustrative JSON event:**

```json
{
  "schema_version": "1.0",
  "event_id": "evt-2026-0001",
  "correlation_id": "INC-1234",
  "tenant": "payments",
  "source": "iac-plan-controller",
  "environment": "stage",
  "action": "retry_readonly_plan",
  "resource": "staging-workspace",
  "idempotency_key": "INC-1234:staging-workspace:retry-readonly-plan"
}
```

This example is synthetic and contains no credentials.

## 4. Workflow state machine

```text
RECEIVED -> VALIDATED -> APPROVED -> EXECUTING -> VERIFYING -> COMPLETED
     |          |           |           |            |
     +----------+-----------+-----------+------------+--> FAILED -> DLQ/escalation
```

Persist transitions atomically and correlate every transition with a durable audit record. Use compare-and-swap or equivalent concurrency controls to prevent two workers from executing the same approved action. Never transition out of a terminal state without a separately approved new workflow.

## 5. Idempotency, retries and delivery guarantees

Event transports often provide at-least-once delivery. Treat duplicates as normal. Require durable idempotency keys, bounded exponential backoff with jitter, retry budgets, poison-message quarantine and dead-letter queues. For non-idempotent cloud operations, do not assume retry safety; inspect provider operation IDs and reconcile actual state before continuing.

A timeout does not prove an operation failed. Avoid duplicate Terraform applies, repeated database failovers or destructive cleanup triggered by uncertain outcomes.

## 6. Approval and policy model
- Allow read-only observation, approved idempotent plan retries and disposable runner recovery as low-risk candidates.
- Require scoped identities, approved tenants, policy decisions, dry-run results, rollback and audit availability.
- Bind approvals to action, tenant, environment, resource, artifact hash and expiry.
- Require human approval for production changes, Terraform apply/destroy, IAM changes, network changes and database recovery.
- Stop workflows when policy service, audit pipeline, state backend or identity provider is unavailable.
- Apply SLO-based abort conditions and explicit incident escalation.

## 7. Cloud, Kubernetes and DBRE integration

**AWS:** EventBridge, CloudTrail, Step Functions or equivalent orchestration, scoped IAM roles and CloudWatch. **Azure:** Event Grid, Activity Logs, Durable Functions/Logic Apps, managed identity and Azure Monitor. **GCP:** Eventarc, Cloud Audit Logs, Workflows/Pub/Sub, workload identity and Cloud Monitoring. These are example architectures, not executed deployments.

**Terraform/OpenTofu:** event-driven read-only drift plans, locked isolated state, immutable plan hashes, controlled apply approvals and recovery snapshots.

**Kubernetes/GitOps:** reconcile from authoritative Git, use scoped service accounts and avoid competing imperative controllers. Measure reconciliation delay, failure rates and SLO impact.

**DBRE:** PostgreSQL, MongoDB, Redis, Kafka and Elasticsearch incidents require database-specific quorum, fencing, backup/PITR, consistency and recovery runbooks. An event-driven alert must not directly initiate unapproved database failover.

## 8. Lab A — Offline workflow gate

Create `infrastructure-as-code/labs/chapter-112/workflow_gate.py`:

```python
"""Offline event-driven workflow decision gate; never executes infrastructure changes."""
from dataclasses import dataclass

ACTIONS={"observe","retry_readonly_plan","restart_disposable_runner","reconcile_catalog"}
STATES={"received","validated","approved","executing","verifying","completed","failed"}
@dataclass(frozen=True)
class WorkflowEvent:
    event_id:str
    correlation_id:str
    tenant:str
    authorized_tenant:str
    source:str
    action:str
    environment:str
    current_state:str
    next_state:str
    signature_verified:bool
    replay_protected:bool
    idempotency_key_present:bool
    policy_passed:bool
    audit_available:bool
    approval_present:bool
    dry_run_passed:bool
    rollback_ready:bool
    max_retries:int
    attempted_retries:int
    database_affected:bool
    dbre_approved:bool
    security_affected:bool
    security_approved:bool

TRANSITIONS={
    "received":{"validated","failed"},
    "validated":{"approved","failed"},
    "approved":{"executing","failed"},
    "executing":{"verifying","failed"},
    "verifying":{"completed","failed"},
    "completed":set(),
    "failed":set(),
}

def evaluate(e:WorkflowEvent):
    if not all((e.event_id.strip(),e.correlation_id.strip(),e.tenant.strip(),e.source.strip())):
        raise ValueError("event identity, correlation, tenant and source required")
    if e.max_retries<0 or e.attempted_retries<0:
        raise ValueError("retry counts cannot be negative")
    checks={
        "event_signature":e.signature_verified,
        "replay_protection":e.replay_protected,
        "idempotency":e.idempotency_key_present,
        "tenant_isolation":e.tenant==e.authorized_tenant,
        "action_allowlist":e.action in ACTIONS,
        "environment":e.environment in {"dev","stage","prod"},
        "state_transition":e.current_state in STATES and e.next_state in TRANSITIONS.get(e.current_state,set()),
        "retry_budget":e.attempted_retries<=e.max_retries,
        "policy":e.policy_passed,
        "audit":e.audit_available,
        "approval":e.approval_present,
        "dry_run":e.dry_run_passed,
        "rollback":e.rollback_ready,
        "database_approval":not e.database_affected or e.dbre_approved,
        "security_approval":not e.security_affected or e.security_approved,
    }
    failed=[key for key,ok in checks.items() if not ok]
    return {"decision":"REVIEW_READY" if not failed else "NO_GO","failed_controls":failed}
```

A `REVIEW_READY` result represents only modeled eligibility. It is not a live workflow authorization.

## 9. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-112/test_workflow_gate.py`:

```python
import unittest
from dataclasses import replace
from workflow_gate import WorkflowEvent,evaluate

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.e=WorkflowEvent("evt-1","INC-1","team-a","team-a","otel",
            "retry_readonly_plan","stage","approved","executing",
            True,True,True,True,True,True,True,True,3,1,False,False,False,False)
    def test_valid(self):
        self.assertEqual(evaluate(self.e)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_isolation",evaluate(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_disallowed_apply(self):
        self.assertIn("action_allowlist",evaluate(replace(self.e,action="terraform_apply"))["failed_controls"])
    def test_replay(self):
        self.assertIn("replay_protection",evaluate(replace(self.e,replay_protected=False))["failed_controls"])
    def test_terminal_state(self):
        self.assertIn("state_transition",evaluate(replace(self.e,current_state="completed"))["failed_controls"])
    def test_retry_exhaustion(self):
        self.assertIn("retry_budget",evaluate(replace(self.e,attempted_retries=4))["failed_controls"])
    def test_controls(self):
        for field in ("signature_verified","idempotency_key_present","policy_passed",
                      "audit_available","approval_present","dry_run_passed","rollback_ready"):
            with self.subTest(field=field):
                self.assertEqual(evaluate(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_dbre(self):
        self.assertIn("database_approval",evaluate(replace(self.e,database_affected=True))["failed_controls"])
    def test_security(self):
        self.assertIn("security_approval",evaluate(replace(self.e,security_affected=True))["failed_controls"])
    def test_invalid_retries(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.e,max_retries=-1))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-112 -p 'test_*.py' -v
```

Tests cover replay, cross-tenant denial, forbidden Terraform apply, terminal-state protection, retry exhaustion, audit/policy failure and DBRE/security approvals.

## 10. Lab C — Event-driven staging workflow (manual)

1. Provision a disposable staging queue, dead-letter queue and durable workflow store.
2. Create scoped test producer and consumer identities; validate event source authentication.
3. Publish a synthetic drift alert with schema version, tenant, correlation ID and idempotency key.
4. Verify schema validation, ownership routing and policy decision.
5. Route an approved read-only plan retry to a least-privilege staging runner.
6. Publish the same event twice; confirm exactly one effect through durable deduplication.
7. Inject worker timeout and restart; verify state recovery without duplicate execution.
8. Exhaust retry budget and confirm DLQ delivery and alert routing.
9. Simulate policy engine outage; verify fail-closed behavior.
10. Capture traces, logs, queue metrics, workflow history and audit evidence; remove disposable resources.

## 11. Lab D — Closed-loop Kubernetes and DBRE incident exercise (manual)

1. Generate a synthetic staging GitOps reconciliation failure and a separate database backup freshness alert.
2. Correlate events with trace IDs and service ownership.
3. Run only read-only Kubernetes/GitOps diagnostics through scoped identities.
4. Verify a proposed direct database failover is denied by automation policy.
5. Obtain DBRE/SRE approval for any separate staging restore rehearsal.
6. Verify backup integrity, database transactions, RPO/RTO and post-recovery SLOs.
7. Document whether the workflow completed, failed, rolled back or escalated.
8. Preserve sanitized evidence for independent acceptance.

## 12. Troubleshooting scenarios

| Failure | Evidence | Safe response |
|---|---|---|
| Duplicate event | same event ID | deduplicate |
| Event replay | stale timestamp/nonce | reject |
| Invalid signature | verification failure | quarantine |
| Schema mismatch | validation error | reject |
| Wrong tenant | scope mismatch | deny |
| Missing correlation ID | trace gap | reject |
| Queue backlog | age/depth | scale safely |
| Consumer crash | lease timeout | recover state |
| Concurrent workers | duplicate claim | atomic lock |
| Retry storm | attempt count | enforce budget |
| DLQ growth | poison messages | investigate |
| Policy unavailable | missing decision | fail closed |
| Audit unavailable | missing receipt | halt |
| Expired approval | approval metadata | reapprove |
| Plan hash changed | artifact mismatch | stop |
| State backend locked | lock record | inspect owner |
| GitOps conflict | repeated drift | fix Git source |
| Kubernetes RBAC denial | audit event | review scope |
| Database failover suggested | unsafe action | DBRE escalation |
| Post-action SLO breach | burn alert | abort/rollback |

## 13. Production runbooks

**RB-01 Event ingress incident:** validate producer identity, schema, replay controls and ingress health.

**RB-02 Queue saturation:** inspect backlog, age, retries and consumer capacity; protect high-priority recovery traffic.

**RB-03 Duplicate execution:** suspend executor, reconcile actual effects and repair idempotency.

**RB-04 Workflow state corruption:** preserve logs, restore durable state and verify transition integrity.

**RB-05 Policy outage:** fail closed, queue requests and restore policy service.

**RB-06 Executor credential compromise:** revoke identity, audit changes and rotate secrets.

**RB-07 Terraform state incident:** preserve locks, inspect plans and restore isolated snapshots.

**RB-08 GitOps reconciliation incident:** validate controller scope and source-of-truth conflicts.

**RB-09 DBRE workflow incident:** preserve data consistency, backup evidence and fencing; obtain DBRE approval.

**RB-10 Operational acceptance:** verify event metrics, DLQ, audit, rollback, SLOs and sign-offs.

## 14. Enterprise acceptance (100 points)

| Domain | Points |
|---|---:|
| Event identity, schema and replay protection | 15 |
| Durable workflow state and idempotency | 15 |
| Tenant isolation and least privilege | 15 |
| Policy, approval and plan binding | 15 |
| Retry, DLQ and failure containment | 10 |
| Observability, audit and SLO verification | 10 |
| Terraform/OpenTofu and GitOps safety | 10 |
| DBRE recovery boundaries and runbooks | 10 |
| **Total** | **100** |

**Production acceptance:** at least 90/100 plus live proof of replay rejection, duplicate-effect prevention, tenant isolation, policy fail-closed, scoped executor identity, auditable approvals, bounded retries, rollback/escalation and DBRE approval for database-impacting actions. Any mandatory failure means **NO-GO**.

## 15. Cleanup and next chapter

Preserve sanitized event envelopes, workflow transition logs, policy decisions, traces, queue metrics, incident reports and approvals. Do not execute destructive operations to complete a tutorial lab.

**Next:** Chapter 113 — Enterprise IaC Predictive Operations, Drift Intelligence and AI-Assisted Change Risk Analysis.
