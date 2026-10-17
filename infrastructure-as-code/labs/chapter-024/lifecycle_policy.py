"""Fail-closed educational Terraform plan action policy; not a backup/approval verifier."""
import json
import sys
from pathlib import Path

VALID = {"no-op", "read", "create", "update", "delete"}

def validate(plan, policy):
    if not isinstance(plan, dict) or not isinstance(policy, dict):
        return ["plan and policy must be objects"]
    errors = []
    types = policy.get("allowed_resource_types")
    if not isinstance(types, list) or not types or not all(isinstance(x, str) for x in types):
        errors.append("invalid allowed_resource_types policy")
    if policy.get("deny_deletes") is not True or policy.get("deny_replacements") is not True:
        errors.append("destructive actions must be denied by policy")
    if type(policy.get("allow_updates")) is not bool:
        errors.append("allow_updates must be boolean")
    if errors:
        return errors
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return ["resource_changes must be a list"]
    for i, item in enumerate(changes):
        if not isinstance(item, dict):
            errors.append(f"resource_changes[{i}]: invalid item")
            continue
        if item.get("type") not in types:
            errors.append(f"resource_changes[{i}]: unapproved type")
        if not isinstance(item.get("address"), str) or not item["address"]:
            errors.append(f"resource_changes[{i}]: missing address")
        change = item.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(actions, list) or not actions or any(type(a) is not str or a not in VALID for a in actions):
            errors.append(f"resource_changes[{i}]: invalid actions")
            continue
        if "delete" in actions:
            errors.append(f"resource_changes[{i}]: delete or replacement denied")
        if "update" in actions and not policy["allow_updates"]:
            errors.append(f"resource_changes[{i}]: updates denied")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 lifecycle_policy.py <plan-json> <policy-json>")
        return 1
    try:
        plan, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors = validate(plan, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational lifecycle plan policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
