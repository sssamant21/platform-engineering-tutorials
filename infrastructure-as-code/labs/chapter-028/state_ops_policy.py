"""Educational operation-manifest and plan gate; not a live Terraform state parser."""
import json
import sys
from pathlib import Path

ACTIONS = {"no-op", "read", "create", "update", "delete"}

def validate(manifest, plan, policy):
    if not all(isinstance(x, dict) for x in (manifest, plan, policy)):
        return ["manifest, plan and policy must be objects"]
    errors = []
    for key in ("allowed_operations", "allowed_environments", "allowed_resource_types"):
        if not isinstance(policy.get(key), list) or not policy[key] or any(not isinstance(x, str) for x in policy[key]):
            errors.append(f"invalid policy {key}")
    for key in ("require_backup", "require_lock", "require_prod_ticket", "deny_plan_deletes", "deny_plan_replacements"):
        if policy.get(key) is not True:
            errors.append(f"policy {key} must be true")
    if errors:
        return errors
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        errors.append("invalid environment")
    if env == "prod" and (not isinstance(manifest.get("change_ticket"), str) or not manifest["change_ticket"].strip()):
        errors.append("production change ticket required")
    if manifest.get("state_backup_verified") is not True:
        errors.append("verified state backup required")
    if manifest.get("exclusive_lock_verified") is not True:
        errors.append("verified exclusive lock required")
    operations = manifest.get("operations")
    if not isinstance(operations, list) or not operations:
        errors.append("operations must be nonempty list")
        operations = []
    targets = set()
    for i, op in enumerate(operations):
        if not isinstance(op, dict):
            errors.append(f"operation[{i}] invalid entry")
            continue
        kind = op.get("operation")
        if kind not in policy["allowed_operations"]:
            errors.append(f"operation[{i}] unapproved operation")
            continue
        if kind == "move":
            source, target = op.get("from"), op.get("to")
            if not isinstance(source, str) or not source or not isinstance(target, str) or not target or source == target:
                errors.append(f"operation[{i}] invalid move mapping")
            if not isinstance(op.get("owner"), str) or not op["owner"].strip():
                errors.append(f"operation[{i}] missing owner")
        elif kind == "import":
            target = op.get("to")
            if not isinstance(op.get("object_id"), str) or not op["object_id"].strip() or op.get("ownership_verified") is not True:
                errors.append(f"operation[{i}] import identity/ownership unverified")
            if not isinstance(op.get("owner"), str) or not op["owner"].strip():
                errors.append(f"operation[{i}] missing owner")
        elif kind == "forget":
            target = None
            if not isinstance(op.get("from"), str) or not op["from"] or op.get("destroy") is not False:
                errors.append(f"operation[{i}] unsafe forget")
            if not isinstance(op.get("handoff_owner"), str) or not op["handoff_owner"].strip():
                errors.append(f"operation[{i}] missing handoff owner")
        else:
            target = None
            if not isinstance(op.get("address"), str) or not op["address"]:
                errors.append(f"operation[{i}] missing refresh address")
        if target is not None:
            if not isinstance(target, str) or not target:
                errors.append(f"operation[{i}] missing target")
            elif target in targets:
                errors.append(f"operation[{i}] duplicate target")
            else:
                targets.add(target)
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return errors + ["resource_changes must be list"]
    for i, item in enumerate(changes):
        if not isinstance(item, dict):
            errors.append(f"change[{i}] invalid entry")
            continue
        if item.get("type") not in policy["allowed_resource_types"]:
            errors.append(f"change[{i}] disallowed resource type")
        if not isinstance(item.get("address"), str) or not item["address"]:
            errors.append(f"change[{i}] missing address")
        change = item.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(actions, list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):
            errors.append(f"change[{i}] invalid actions")
            continue
        if "delete" in actions:
            errors.append(f"change[{i}] destructive delete/replacement denied")
    return errors

def main(argv):
    if len(argv) != 4:
        print("Usage: python3 state_ops_policy.py <operations-json> <plan-json> <policy-json>")
        return 1
    try:
        manifest, plan, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors = validate(manifest, plan, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational state operation manifest and plan")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
