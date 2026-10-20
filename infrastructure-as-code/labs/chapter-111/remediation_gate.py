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
