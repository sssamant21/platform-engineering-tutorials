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
