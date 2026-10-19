"""Synthetic backup inventory and restore-readiness gate. No cloud API calls."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

@dataclass(frozen=True)
class RecoveryPoint:
    id: str
    workload: str
    created_utc: str
    checksum_sha256: str
    source_region: str
    replica_region: str
    isolated_account: bool
    immutable_until_utc: str
    restore_verified: bool
    encryption_key_accessible: bool
    state_manifest_present: bool

def utc(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset() != timezone.utc.utcoffset(d):
        raise ValueError("explicit UTC required")
    return d

def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()

def validate(point, now_utc, max_age_minutes):
    if max_age_minutes < 0 or not point.id or not point.workload:
        raise ValueError("invalid backup contract")
    now, created, until = utc(now_utc), utc(point.created_utc), utc(point.immutable_until_utc)
    if created > now or until < created:
        raise ValueError("invalid backup timeline")
    age = (now-created).total_seconds()/60
    checks = {
        "freshness": age <= max_age_minutes,
        "checksum_format": len(point.checksum_sha256)==64 and all(c in "0123456789abcdef" for c in point.checksum_sha256),
        "regional_separation": point.source_region != point.replica_region,
        "account_isolation": point.isolated_account,
        "immutability": until > now,
        "restore": point.restore_verified,
        "key_access": point.encryption_key_accessible,
        "state_manifest": point.state_manifest_present,
    }
    return {"decision":"REVIEW_READY" if all(checks.values()) else "NO_GO",
            "age_minutes":age,
            "failed":[k for k,v in checks.items() if not v]}
