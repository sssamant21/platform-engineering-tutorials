"""Offline enterprise IaC audit gate. Synthetic evidence; no cloud access."""
from dataclasses import dataclass

WEIGHTS={
    "identity_and_tenant_isolation":15,
    "state_and_secrets_protection":10,
    "supply_chain_and_policy":10,
    "audit_and_compliance_evidence":15,
    "cost_allocation_and_budget":10,
    "capacity_and_slo":10,
    "recovery_drill":10,
    "change_governance":10,
    "dbre_integrity":10,
}
assert sum(WEIGHTS.values()) == 100
MANDATORY=(
    "identity_and_tenant_isolation","state_and_secrets_protection",
    "supply_chain_and_policy","audit_and_compliance_evidence",
    "recovery_drill","change_governance",
)

@dataclass(frozen=True)
class AuditEvidence:
    audit_id: str
    environment: str
    tenant: str
    authorized_tenant: str
    evidence_current: bool
    evidence_provenance_verified: bool
    identity_and_tenant_isolation: bool
    state_and_secrets_protection: bool
    supply_chain_and_policy: bool
    audit_and_compliance_evidence: bool
    cost_allocation_and_budget: bool
    capacity_and_slo: bool
    recovery_drill: bool
    change_governance: bool
    dbre_integrity: bool
    databases_in_scope: bool
    dbre_signoff: bool
    security_signoff: bool
    sre_signoff: bool
    critical_findings_open: int
    high_findings_open: int
    approved_high_exceptions: int

def assess(e: AuditEvidence):
    if not e.audit_id.strip() or not e.tenant.strip():
        raise ValueError("audit ID and tenant required")
    if e.environment not in ("dev", "stage", "prod"):
        raise ValueError("invalid environment")
    if min(e.critical_findings_open,e.high_findings_open,e.approved_high_exceptions)<0:
        raise ValueError("negative finding count")
    if e.approved_high_exceptions>e.high_findings_open:
        raise ValueError("exceptions exceed high findings")
    score=sum(weight for key,weight in WEIGHTS.items() if getattr(e,key))
    failed=[key for key in MANDATORY if not getattr(e,key)]
    if e.databases_in_scope and not e.dbre_integrity: failed.append("dbre_integrity")
    if e.tenant!=e.authorized_tenant: failed.append("tenant_scope")
    if not e.evidence_current: failed.append("evidence_freshness")
    if not e.evidence_provenance_verified: failed.append("evidence_provenance")
    if not e.security_signoff: failed.append("security_signoff")
    if not e.sre_signoff: failed.append("sre_signoff")
    if e.databases_in_scope and not e.dbre_signoff: failed.append("dbre_signoff")
    if e.critical_findings_open: failed.append("critical_findings")
    if e.high_findings_open>e.approved_high_exceptions:
        failed.append("unapproved_high_findings")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
