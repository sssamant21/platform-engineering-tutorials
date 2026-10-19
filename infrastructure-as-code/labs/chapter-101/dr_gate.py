"""Offline DR policy evaluator. No provider APIs or destructive actions."""
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class RecoveryEvidence:
    service: str
    tier: str
    rpo_target_minutes: int
    rto_target_minutes: int
    latest_recoverable_point: str
    outage_started: str
    service_restored: str
    backup_immutable: bool
    restore_test_passed: bool
    state_recoverable: bool
    secrets_recoverable: bool
    region_independent: bool
    owner_approved: bool

def parse_utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamps must be explicitly UTC")
    return parsed

def evaluate(e):
    if not e.service or e.rpo_target_minutes < 0 or e.rto_target_minutes < 0:
        raise ValueError("invalid recovery contract")
    backup = parse_utc(e.latest_recoverable_point)
    outage = parse_utc(e.outage_started)
    restored = parse_utc(e.service_restored)
    if backup > outage or restored < outage:
        raise ValueError("inconsistent recovery timeline")
    observed_rpo = (outage - backup).total_seconds() / 60
    observed_rto = (restored - outage).total_seconds() / 60
    checks = {
        "rpo": observed_rpo <= e.rpo_target_minutes,
        "rto": observed_rto <= e.rto_target_minutes,
        "immutable_backup": e.backup_immutable,
        "restore_test": e.restore_test_passed,
        "iac_state": e.state_recoverable,
        "secrets": e.secrets_recoverable,
        "failure_domain": e.region_independent,
        "approval": e.owner_approved,
    }
    return {
        "decision": "REVIEW_READY" if all(checks.values()) else "NO_GO",
        "observed_rpo_minutes": observed_rpo,
        "observed_rto_minutes": observed_rto,
        "failed_controls": [k for k, ok in checks.items() if not ok],
    }
