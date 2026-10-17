"""Educational fail-closed Terraform plan JSON policy. Never log sensitive plan content."""
import json
import sys
from pathlib import Path

VALID_ACTIONS = {"no-op", "create", "read", "update", "delete"}

def validate(plan, policy):
    errors = []
    if not isinstance(plan, dict) or not isinstance(policy, dict):
        return ["plan and policy must be objects"]
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return ["resource_changes must be a list"]
    if policy.get("environment") not in {"lab", "dev", "staging", "prod"}:
        errors.append("invalid policy environment")
    if policy.get("allow_deletes") is not False:
        errors.append("deletes must be explicitly disabled in this lab policy")
    if not isinstance(policy.get("require_no_changes"), bool):
        errors.append("require_no_changes must be boolean")
    if not isinstance(policy.get("production_approved"), bool):
        errors.append("production_approved must be boolean")
    any_change = False
    for i, resource in enumerate(changes):
        if not isinstance(resource, dict):
            errors.append(f"resource_changes[{i}] invalid")
            continue
        change = resource.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(actions, list) or not actions or any(a not in VALID_ACTIONS for a in actions):
            errors.append(f"resource_changes[{i}] missing or invalid actions")
            continue
        if "delete" in actions:
            errors.append(f"resource_changes[{i}] destructive action prohibited")
        if actions != ["no-op"] and actions != ["read"]:
            any_change = True
    if policy.get("require_no_changes") is True and any_change:
        errors.append("no-change mode prohibits changes")
    if policy.get("environment") == "prod" and any_change and policy.get("production_approved") is not True:
        errors.append("production change requires approval")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 plan_policy.py <plan-json> <policy-json>")
        return 1
    try:
        plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    errors = validate(plan, policy)
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational Terraform plan policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
