"""Offline final SRE/DBRE readiness gate. No production access or certification."""
from dataclasses import dataclass
WEIGHTS={"architecture":10,"identity_and_isolation":10,"iac_state_and_drift":10,
"delivery_and_gitops":10,"policy_and_supply_chain":10,"observability_slos":10,
"incident_and_rollback":10,"disaster_recovery":10,"cost_and_capacity":10,
"dbre_integrity":10}
MANDATORY=("identity_and_isolation","iac_state_and_drift","policy_and_supply_chain",
"observability_slos","incident_and_rollback","disaster_recovery")
assert sum(WEIGHTS.values())==100

@dataclass(frozen=True)
class FinalEvidence:
    assessment_id:str
    tenant:str
    authorized_tenant:str
    environment:str
    evidence_verified:bool
    labs_executed:bool
    architecture:bool
    identity_and_isolation:bool
    iac_state_and_drift:bool
    delivery_and_gitops:bool
    policy_and_supply_chain:bool
    observability_slos:bool
    incident_and_rollback:bool
    disaster_recovery:bool
    cost_and_capacity:bool
    dbre_integrity:bool
    databases_in_scope:bool
    security_signoff:bool
    sre_signoff:bool
    dbre_signoff:bool
    critical_findings:int
    unapproved_high_findings:int

def assess(e:FinalEvidence):
    if not e.assessment_id.strip() or not e.tenant.strip():
        raise ValueError("assessment ID and tenant required")
    if e.environment not in ("dev","stage","prod"):
        raise ValueError("invalid environment")
    if e.critical_findings<0 or e.unapproved_high_findings<0:
        raise ValueError("negative finding count")
    score=sum(weight for key,weight in WEIGHTS.items() if getattr(e,key))
    failed=[key for key in MANDATORY if not getattr(e,key)]
    if e.databases_in_scope and not e.dbre_integrity: failed.append("dbre_integrity")
    if e.tenant!=e.authorized_tenant: failed.append("tenant_scope")
    if not e.evidence_verified: failed.append("evidence_unverified")
    if not e.labs_executed: failed.append("labs_not_executed")
    if not e.security_signoff: failed.append("security_signoff")
    if not e.sre_signoff: failed.append("sre_signoff")
    if e.databases_in_scope and not e.dbre_signoff: failed.append("dbre_signoff")
    if e.critical_findings: failed.append("critical_findings")
    if e.unapproved_high_findings: failed.append("unapproved_high_findings")
    return {"decision":"ELIGIBLE_FOR_INDEPENDENT_REVIEW" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
