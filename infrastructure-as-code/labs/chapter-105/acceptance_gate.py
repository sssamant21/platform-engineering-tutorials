"""Offline enterprise DR capstone evidence gate. Never initiates failover."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Acceptance:
    service: str
    rpo_target_minutes: int
    rpo_observed_minutes: int
    rto_target_minutes: int
    rto_observed_minutes: int
    immutable_copy_verified: bool
    independent_keys_verified: bool
    state_restore_verified: bool
    kubernetes_restore_verified: bool
    database_integrity_verified: bool
    old_primary_fenced: bool
    quorum_verified: bool
    business_transaction_verified: bool
    rollback_verified: bool
    evidence_complete: bool
    sre_signed: bool
    dbre_signed: bool

WEIGHTS = {
    "rpo":10, "rto":10, "immutable_copy":10, "independent_keys":5,
    "state_restore":10, "kubernetes_restore":10, "database_integrity":15,
    "fencing":10, "quorum":5, "business_transaction":5,
    "rollback":5, "evidence":3, "sre_signoff":1, "dbre_signoff":1,
}
assert sum(WEIGHTS.values()) == 100

def assess(e: Acceptance):
    if not e.service or any(v < 0 for v in (
        e.rpo_target_minutes,e.rpo_observed_minutes,
        e.rto_target_minutes,e.rto_observed_minutes)):
        raise ValueError("invalid service or recovery objective")
    checks = {
        "rpo": e.rpo_observed_minutes <= e.rpo_target_minutes,
        "rto": e.rto_observed_minutes <= e.rto_target_minutes,
        "immutable_copy": e.immutable_copy_verified,
        "independent_keys": e.independent_keys_verified,
        "state_restore": e.state_restore_verified,
        "kubernetes_restore": e.kubernetes_restore_verified,
        "database_integrity": e.database_integrity_verified,
        "fencing": e.old_primary_fenced,
        "quorum": e.quorum_verified,
        "business_transaction": e.business_transaction_verified,
        "rollback": e.rollback_verified,
        "evidence": e.evidence_complete,
        "sre_signoff": e.sre_signed,
        "dbre_signoff": e.dbre_signed,
    }
    score = sum(WEIGHTS[k] for k, ok in checks.items() if ok)
    mandatory = ("rpo","rto","immutable_copy","independent_keys","state_restore",
                 "database_integrity","fencing","quorum","business_transaction",
                 "evidence","sre_signoff","dbre_signoff")
    failed = [k for k,v in checks.items() if not v]
    return {"score":score,
            "decision":"REVIEW_READY" if score >= 90 and all(checks[k] for k in mandatory) else "NO_GO",
            "failed":failed}
