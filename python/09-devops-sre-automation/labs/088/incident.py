"""Sandbox-only incident automation with explicit approval, idempotency and audit.

No network calls, shell execution, service restarts or production mutations.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
INCIDENT = re.compile(r"^INC-[0-9]{4,12}$")
ALLOWED_ACTION = "create-lab-marker"
MAX_EVIDENCE = 20

class PolicyError(ValueError):
    pass

@dataclass(frozen=True)
class Signal:
    kind: str
    value: float
    observed_at: float

@dataclass(frozen=True)
class Plan:
    incident_id: str
    service: str
    action: str
    rationale: str

    def validate(self):
        if not INCIDENT.fullmatch(self.incident_id):
            raise PolicyError("invalid incident ID")
        if not IDENTIFIER.fullmatch(self.service):
            raise PolicyError("invalid service")
        if self.action != ALLOWED_ACTION:
            raise PolicyError("action not allowlisted")
        if self.rationale not in ("disk-pressure", "high-error-rate", "manual-exercise"):
            raise PolicyError("invalid rationale")

    def digest(self):
        self.validate()
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

def correlate(signals: list[Signal], now: float, max_age: float = 300) -> str:
    if len(signals) > MAX_EVIDENCE or max_age <= 0:
        raise PolicyError("invalid evidence budget")
    fresh = {}
    for signal in signals:
        if signal.kind not in ("disk_percent", "error_rate", "cpu_percent"):
            raise PolicyError("unexpected diagnostic kind")
        if not (0 <= signal.value <= 100):
            raise PolicyError("diagnostic out of range")
        if not (now - max_age <= signal.observed_at <= now):
            raise PolicyError("stale or future diagnostic")
        fresh[signal.kind] = signal.value
    if fresh.get("disk_percent", 0) >= 90:
        return "disk-pressure"
    if fresh.get("error_rate", 0) >= 5:
        return "high-error-rate"
    return "manual-exercise"

def synthetic_diagnostics(now: float) -> list[Signal]:
    return [
        Signal("disk_percent", 94, now - 10),
        Signal("error_rate", 1, now - 10),
        Signal("cpu_percent", 38, now - 10),
    ]

def _safe_root(root: Path) -> Path:
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise PolicyError("invalid sandbox directory")
    return root

def audit(root: Path, event: dict):
    """Teaching JSONL audit; not a tamper-evident production ledger."""
    target = root / "audit.jsonl"
    if target.is_symlink():
        raise PolicyError("audit symlink forbidden")
    payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    # A single append write is sufficient for local sequential exercises,
    # not a durable multi-process transaction.
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

def execute(plan: Plan, root: Path, *, apply: bool = False,
            approval_digest: str | None = None, approver: str | None = None,
            approval_expires: float | None = None, now: float | None = None) -> dict:
    plan.validate()
    digest = plan.digest()
    if not apply:
        return {"status": "dry-run", "action": plan.action, "plan_digest": digest,
                "incident_id": plan.incident_id, "service": plan.service,
                "network_calls": 0, "mutations": 0}
    current = time.time() if now is None else now
    if (approval_digest != digest or not approver or not IDENTIFIER.fullmatch(approver)
            or approval_expires is None or not current <= approval_expires <= current + 3600):
        raise PolicyError("missing, invalid or expired simulated approval")
    root = _safe_root(root)
    marker = root / (plan.incident_id + "-" + plan.service + ".marker")
    if marker.is_symlink():
        raise PolicyError("marker symlink forbidden")
    # Simulated approval is NOT an authentication/authorization system.
    # Atomic O_EXCL protects a single local marker against duplicate creation.
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        try:
            existing = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PolicyError("unverifiable prior action") from exc
        if existing.get("plan_digest") != digest:
            raise PolicyError("idempotency conflict")
        audit(root, {"incident_id": plan.incident_id, "event": "duplicate",
                     "plan_digest": digest, "actor": approver})
        return {"status": "already-applied", "plan_digest": digest}
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"plan_digest": digest, "incident_id": plan.incident_id,
                       "service": plan.service}, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # In an ambiguous outcome do not automatically remove marker/retry.
        raise
    audit(root, {"incident_id": plan.incident_id, "event": "applied",
                 "plan_digest": digest, "actor": approver, "action": plan.action})
    return {"status": "applied", "plan_digest": digest, "marker": marker.name}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Sandbox-only incident response")
    parser.add_argument("--incident", default="INC-1001")
    parser.add_argument("--service", default="postgres-health")
    parser.add_argument("--sandbox", type=Path, default=Path("."))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--approval-digest")
    parser.add_argument("--approver")
    parser.add_argument("--approval-expires", type=float)
    args = parser.parse_args(argv)
    now = time.time()
    try:
        rationale = correlate(synthetic_diagnostics(now), now)
        plan = Plan(args.incident, args.service, ALLOWED_ACTION, rationale)
        result = execute(plan, args.sandbox, apply=args.apply,
                         approval_digest=args.approval_digest,
                         approver=args.approver,
                         approval_expires=args.approval_expires, now=now)
    except (PolicyError, OSError):
        print(json.dumps({"status": "rejected"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
