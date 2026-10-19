"""Offline failover authorization model; never controls production routing."""
from dataclasses import dataclass

@dataclass(frozen=True)
class FailoverEvidence:
    primary_fenced: bool
    quorum_verified: bool
    replica_lag_seconds: int
    max_lag_seconds: int
    backup_restorable: bool
    recovery_keys_ready: bool
    target_capacity_ready: bool
    dns_ready: bool
    incident_commander_approved: bool
    dbre_approved: bool
    rollback_plan_ready: bool

def decide(e: FailoverEvidence):
    if e.replica_lag_seconds < 0 or e.max_lag_seconds < 0:
        raise ValueError("negative lag is invalid")
    checks = {
        "fencing": e.primary_fenced,
        "quorum": e.quorum_verified,
        "lag": e.replica_lag_seconds <= e.max_lag_seconds,
        "backup": e.backup_restorable,
        "keys": e.recovery_keys_ready,
        "capacity": e.target_capacity_ready,
        "dns": e.dns_ready,
        "incident_approval": e.incident_commander_approved,
        "dbre_approval": e.dbre_approved,
        "rollback": e.rollback_plan_ready,
    }
    return {"decision": "REHEARSAL_READY" if all(checks.values()) else "BLOCK",
            "failed": [k for k, v in checks.items() if not v]}
