"""Read-only validator for terraform show -json state output (not raw tfstate)."""
import json
import sys
from pathlib import Path

def flatten(module):
    if not isinstance(module, dict):
        raise ValueError("module must be object")
    resources = module.get("resources", [])
    children = module.get("child_modules", [])
    if not isinstance(resources, list) or not isinstance(children, list):
        raise ValueError("resources and child_modules must be lists")
    result = list(resources)
    for child in children:
        result.extend(flatten(child))
    return result

def validate(state, policy):
    if not isinstance(state, dict) or not isinstance(policy, dict):
        return ["state and policy must be objects"]
    root = state.get("values", {}).get("root_module") if isinstance(state.get("values"), dict) else None
    if not isinstance(root, dict):
        return ["missing values.root_module (expected terraform show -json state)"]
    try:
        resources = flatten(root)
    except ValueError as exc:
        return [str(exc)]
    errors = []
    expected = policy.get("expected_addresses")
    if not isinstance(expected, list) or not expected or any(not isinstance(a, str) for a in expected):
        return ["expected_addresses must be nonempty string list"]
    if len(set(expected)) != len(expected):
        errors.append("duplicate expected address")
    if not isinstance(policy.get("environment"), str) or not policy["environment"]:
        errors.append("invalid expected environment")
    if not isinstance(policy.get("allow_unexpected"), bool) or not isinstance(policy.get("require_owner"), bool):
        errors.append("allow_unexpected and require_owner must be boolean")
    seen = set()
    for i, r in enumerate(resources):
        if not isinstance(r, dict) or not isinstance(r.get("address"), str):
            errors.append(f"invalid resource at index {i}")
            continue
        addr = r["address"]
        if addr in seen:
            errors.append(f"duplicate address {addr}")
        seen.add(addr)
        if r.get("mode") != "managed":
            continue
        values = r.get("values")
        metadata = values.get("input") if isinstance(values, dict) else None
        if not isinstance(metadata, dict):
            errors.append(f"{addr}: missing input metadata")
            continue
        if metadata.get("environment") != policy.get("environment"):
            errors.append(f"{addr}: environment mismatch")
        if policy.get("require_owner") and (not isinstance(metadata.get("owner"), str) or not metadata["owner"].strip()):
            errors.append(f"{addr}: missing owner")
    for addr in expected:
        if addr not in seen:
            errors.append(f"missing expected address {addr}")
    if policy.get("allow_unexpected") is False:
        for addr in seen:
            if addr not in expected:
                errors.append(f"unexpected address {addr}")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 state_policy.py <show-json> <policy-json>")
        return 1
    try:
        state = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        errors = validate(state, policy)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational state address inventory")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
