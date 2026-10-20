"""Offline chaos and disaster recovery acceptance gate. Never injects failures."""
from dataclasses import dataclass

WEIGHTS={"blast_radius":10,"abort_controls":10,"baseline_slos":10,
 "failure_observability":10,"state_restore":10,"gitops_recovery":10,
 "identity_and_policy":10,"rto_met":10,"rpo_met":10,"data_integrity":10}
assert sum(WEIGHTS.values())==100
MANDATORY=("blast_radius","abort_controls","baseline_slos","failure_observability",
 "state_restore","identity_and_policy","rto_met","rpo_met")

@dataclass(frozen=True)
class DrillEvidence:
    drill_id:str
    environment:str
    tenant:str
    authorized_tenant:str
    approved_fault:str
    proposed_fault:str
    measured_rto_seconds:int
    target_rto_seconds:int
    measured_rpo_seconds:int
    target_rpo_seconds:int
    blast_radius:bool
    abort_controls:bool
    baseline_slos:bool
    failure_observability:bool
    state_restore:bool
    gitops_recovery:bool
    identity_and_policy:bool
    data_integrity:bool
    database_in_scope:bool
    dbre_approved:bool
    security_approved:bool
    sre_approved:bool
    kill_switch_active:bool
    critical_exception_open:bool

def assess(e:DrillEvidence):
    if not e.drill_id.strip() or not e.tenant.strip():
        raise ValueError("drill and tenant required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    if any(v<0 for v in (e.measured_rto_seconds,e.target_rto_seconds,
                         e.measured_rpo_seconds,e.target_rpo_seconds)):
        raise ValueError("negative recovery time")
    if e.target_rto_seconds==0 or e.target_rpo_seconds==0:
        raise ValueError("RTO/RPO targets must be positive")
    rto=e.measured_rto_seconds<=e.target_rto_seconds
    rpo=e.measured_rpo_seconds<=e.target_rpo_seconds
    checks={key:getattr(e,key) for key in WEIGHTS if key not in ("rto_met","rpo_met")}
    checks.update(rto_met=rto,rpo_met=rpo)
    score=sum(points for key,points in WEIGHTS.items() if checks[key])
    failed=[key for key in MANDATORY if not checks[key]]
    if e.database_in_scope and not e.data_integrity: failed.append("data_integrity")
    if e.tenant!=e.authorized_tenant: failed.append("tenant_scope")
    if not e.approved_fault or e.proposed_fault!=e.approved_fault:
        failed.append("fault_binding")
    if e.environment=="prod": failed.append("production_drill_requires_separate_process")
    if not e.sre_approved: failed.append("sre_approval")
    if not e.security_approved: failed.append("security_approval")
    if e.database_in_scope and not e.dbre_approved: failed.append("dbre_approval")
    if e.kill_switch_active: failed.append("kill_switch")
    if e.critical_exception_open: failed.append("critical_exception")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
