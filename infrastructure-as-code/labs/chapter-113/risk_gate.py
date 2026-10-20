"""Offline IaC change-risk assessment. No model inference or infrastructure changes."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ChangeEvidence:
    change_id:str
    tenant:str
    authorized_tenant:str
    environment:str
    drift_resources:int
    destructive_changes:int
    privileged_changes:int
    estimated_capacity_utilization_pct:float
    projected_capacity_utilization_pct:float
    telemetry_fresh:bool
    drift_plan_reviewed:bool
    policy_passed:bool
    plan_hash_approved:bool
    audit_available:bool
    rollback_tested:bool
    security_approved:bool
    sre_approved:bool
    dbre_approved:bool
    database_affected:bool

def assess(e:ChangeEvidence):
    if not e.change_id.strip() or not e.tenant.strip():
        raise ValueError("change and tenant required")
    if any(v<0 for v in (e.drift_resources,e.destructive_changes,e.privileged_changes)):
        raise ValueError("change counts cannot be negative")
    if not all(0<=v<=100 for v in (e.estimated_capacity_utilization_pct,
                                  e.projected_capacity_utilization_pct)):
        raise ValueError("capacity percentage outside 0..100")
    score=min(100, e.drift_resources*3+e.destructive_changes*25+
              e.privileged_changes*20+
              max(0,e.projected_capacity_utilization_pct-75)*2)
    checks={
        "tenant_scope":e.tenant==e.authorized_tenant,
        "environment":e.environment in {"dev","stage","prod"},
        "telemetry":e.telemetry_fresh,
        "plan_review":e.drift_plan_reviewed,
        "policy":e.policy_passed,
        "plan_binding":e.plan_hash_approved,
        "audit":e.audit_available,
        "rollback":e.rollback_tested,
        "capacity":e.projected_capacity_utilization_pct<=85,
        "destructive_change":e.destructive_changes==0,
        "privileged_change":e.privileged_changes==0,
        "security_signoff":e.environment!="prod" or e.security_approved,
        "sre_signoff":e.environment!="prod" or e.sre_approved,
        "dbre_signoff":not e.database_affected or e.dbre_approved,
        "risk_threshold":score<=25,
    }
    failed=[name for name,ok in checks.items() if not ok]
    return {"decision":"REVIEW_READY" if not failed else "NO_GO",
            "risk_score":score,"failed_controls":failed}
