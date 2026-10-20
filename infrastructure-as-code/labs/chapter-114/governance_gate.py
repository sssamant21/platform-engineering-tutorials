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
