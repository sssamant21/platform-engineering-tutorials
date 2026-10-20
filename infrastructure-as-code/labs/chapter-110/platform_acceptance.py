"""Offline platform acceptance scorecard; no cloud, GitOps or database operations."""
from dataclasses import dataclass

WEIGHTS = {
    "catalog_ownership": 10,
    "golden_path_versioned": 10,
    "tenant_isolation": 15,
    "identity_least_privilege": 10,
    "policy_enforced": 10,
    "plan_hash_approved": 5,
    "state_restore_verified": 10,
    "kubernetes_slo_verified": 10,
    "database_recovery_verified": 10,
    "audit_complete": 5,
    "incident_rehearsed": 5,
}
assert sum(WEIGHTS.values()) == 100

@dataclass(frozen=True)
class PlatformAcceptance:
    platform: str
    catalog_ownership: bool
    golden_path_versioned: bool
    tenant_isolation: bool
    identity_least_privilege: bool
    policy_enforced: bool
    plan_hash_approved: bool
    state_restore_verified: bool
    kubernetes_slo_verified: bool
    database_recovery_verified: bool
    audit_complete: bool
    incident_rehearsed: bool
    security_signed: bool
    sre_signed: bool
    dbre_signed: bool
    database_in_scope: bool

MANDATORY = ("catalog_ownership", "tenant_isolation", "identity_least_privilege",
             "policy_enforced", "plan_hash_approved", "state_restore_verified",
             "kubernetes_slo_verified", "audit_complete")

def assess(e: PlatformAcceptance):
    if not e.platform.strip():
        raise ValueError("platform is required")
    checks = {name: getattr(e, name) for name in WEIGHTS}
    score = sum(points for name, points in WEIGHTS.items() if checks[name])
    failed = [name for name, ok in checks.items() if not ok]
    required = list(MANDATORY)
    if e.database_in_scope:
        required.append("database_recovery_verified")
    signatures = e.security_signed and e.sre_signed and (
        not e.database_in_scope or e.dbre_signed)
    ready = score >= 90 and signatures and all(checks[name] for name in required)
    return {"score": score, "decision": "REVIEW_READY" if ready else "NO_GO",
            "failed": failed, "signatures_complete": signatures}
