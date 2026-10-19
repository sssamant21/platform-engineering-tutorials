"""Offline chaos drill acceptance gate. Does not inject faults or call APIs."""
from dataclasses import dataclass

@dataclass(frozen=True)
class DrillEvidence:
    service: str
    blast_radius: str
    authorized: bool
    staging_only: bool
    stop_switch_verified: bool
    baseline_slo_ok: bool
    fault_observed: bool
    recovery_verified: bool
    data_integrity_verified: bool
    rollback_verified: bool
    rpo_observed_seconds: int
    rpo_target_seconds: int
    rto_observed_seconds: int
    rto_target_seconds: int
    dbre_approved: bool
    sre_approved: bool

def assess(d: DrillEvidence):
    if not d.service or not d.blast_radius:
        raise ValueError("service and blast radius required")
    metrics=(d.rpo_observed_seconds,d.rpo_target_seconds,
             d.rto_observed_seconds,d.rto_target_seconds)
    if any(x < 0 for x in metrics):
        raise ValueError("negative recovery times are invalid")
    checks={
        "authorization":d.authorized,
        "staging_boundary":d.staging_only,
        "stop_switch":d.stop_switch_verified,
        "baseline_slo":d.baseline_slo_ok,
        "fault_observed":d.fault_observed,
        "recovery":d.recovery_verified,
        "data_integrity":d.data_integrity_verified,
        "rollback":d.rollback_verified,
        "rpo":d.rpo_observed_seconds<=d.rpo_target_seconds,
        "rto":d.rto_observed_seconds<=d.rto_target_seconds,
        "dbre_approval":d.dbre_approved,
        "sre_approval":d.sre_approved,
    }
    return {"decision":"REVIEW_READY" if all(checks.values()) else "NO_GO",
            "failed":[key for key,ok in checks.items() if not ok]}
