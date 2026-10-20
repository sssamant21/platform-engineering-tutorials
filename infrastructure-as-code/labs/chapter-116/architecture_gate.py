"""Offline final architecture readiness evidence gate. No infrastructure operations."""
from dataclasses import dataclass

WEIGHTS={
 "architecture_review":10,"multi_cloud_boundaries":10,
 "tenant_isolation":10,"identity_least_privilege":10,
 "state_backup_and_locking":10,"policy_and_supply_chain":10,
 "gitops_reconciliation":10,"observability_and_slos":10,
 "recovery_drill":10,"dbre_integrity":10,
}
MANDATORY=("tenant_isolation","identity_least_privilege","state_backup_and_locking",
 "policy_and_supply_chain","observability_and_slos","recovery_drill")

@dataclass(frozen=True)
class ArchitectureEvidence:
    assessment_id:str
    environment:str
    architecture_review:bool
    multi_cloud_boundaries:bool
    tenant_isolation:bool
    identity_least_privilege:bool
    state_backup_and_locking:bool
    policy_and_supply_chain:bool
    gitops_reconciliation:bool
    observability_and_slos:bool
    recovery_drill:bool
    dbre_integrity:bool
    databases_in_scope:bool
    security_signoff:bool
    sre_signoff:bool
    dbre_signoff:bool
    critical_exception_open:bool

def assess(e:ArchitectureEvidence):
    if not e.assessment_id.strip():
        raise ValueError("assessment ID required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    score=sum(weight for key,weight in WEIGHTS.items() if getattr(e,key))
    required=list(MANDATORY)
    if e.databases_in_scope:
        required.append("dbre_integrity")
    failed=[key for key in required if not getattr(e,key)]
    if not e.security_signoff: failed.append("security_signoff")
    if not e.sre_signoff: failed.append("sre_signoff")
    if e.databases_in_scope and not e.dbre_signoff: failed.append("dbre_signoff")
    if e.critical_exception_open: failed.append("critical_exception")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
