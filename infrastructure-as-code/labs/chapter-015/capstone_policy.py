"""Educational fail-closed change ticket + Terraform plan JSON gate."""
import json
import sys
from pathlib import Path

ACTIONS = {"no-op", "create", "read", "update", "delete"}

def validate(plan, policy):
    if not isinstance(plan, dict) or not isinstance(policy, dict):
        return ["plan and policy must be objects"]
    errors = []
    for field in ("change_ticket", "owner"):
        if not isinstance(policy.get(field), str) or not policy[field].strip():
            errors.append(f"missing {field}")
    if policy.get("environment") not in ("dev", "staging", "prod"):
        errors.append("invalid environment")
    if policy.get("allow_deletes") is not False:
        errors.append("deletes must be disabled in this capstone")
    for field in ("production_approved", "dbre_approved"):
        if not isinstance(policy.get(field), bool):
            errors.append(f"{field} must be boolean")
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return errors + ["resource_changes must be a list"]
    any_change = False
    for i, item in enumerate(changes):
        change = item.get("change") if isinstance(item, dict) else None
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(actions, list) or not actions or any(a not in ACTIONS for a in actions):
            errors.append(f"resource_changes[{i}]: invalid actions")
            continue
        if "delete" in actions:
            errors.append(f"resource_changes[{i}]: destructive action prohibited")
        if actions not in (["no-op"], ["read"]):
            any_change = True
    if policy.get("environment") == "prod" and any_change:
        if policy.get("production_approved") is not True:
            errors.append("production approval required")
        if policy.get("service_kind") == "database" and policy.get("dbre_approved") is not True:
            errors.append("production database DBRE approval required")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 capstone_policy.py <plan-json> <change-policy-json>")
        return 1
    try:
        plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        errors = validate(plan, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational capstone change-control policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
