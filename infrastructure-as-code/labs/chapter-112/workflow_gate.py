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
