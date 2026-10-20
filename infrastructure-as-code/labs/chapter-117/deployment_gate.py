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
