"""Educational IaC inventory governance validator (stdlib only)."""
import json
import sys
from pathlib import Path

REQUIRED = ("name", "cloud", "environment", "owner", "cost_center", "backend_key", "state", "auto_apply", "approvals")
ENVIRONMENTS = {"lab", "dev", "staging", "prod"}
CLOUDS = {"aws", "azure", "gcp"}

def validate_inventory(document):
    errors = []
    if not isinstance(document, dict) or not isinstance(document.get("stacks"), list) or not document["stacks"]:
        return ["stacks must be a nonempty list"]
    keys = set()
    names = set()
    for i, stack in enumerate(document["stacks"]):
        prefix = f"stacks[{i}]"
        if not isinstance(stack, dict):
            errors.append(f"{prefix}: must be object")
            continue
        for key in REQUIRED:
            if key not in stack:
                errors.append(f"{prefix}: missing {key}")
        for key in ("name", "owner", "cost_center", "backend_key"):
            if not isinstance(stack.get(key), str) or not stack[key].strip():
                errors.append(f"{prefix}: invalid {key}")
        if stack.get("cloud") not in CLOUDS:
            errors.append(f"{prefix}: unsupported cloud")
        if stack.get("environment") not in ENVIRONMENTS:
            errors.append(f"{prefix}: unsupported environment")
        name = stack.get("name")
        if isinstance(name, str):
            if name in names:
                errors.append(f"{prefix}: duplicate stack name")
            names.add(name)
        key = stack.get("backend_key")
        if isinstance(key, str):
            if key in keys:
                errors.append(f"{prefix}: duplicate backend key")
            keys.add(key)
        state = stack.get("state")
        if not isinstance(state, dict) or any(state.get(control) is not True for control in ("encrypted", "locking", "versioning")):
            errors.append(f"{prefix}: state must enable encryption, locking and versioning")
        if not isinstance(stack.get("auto_apply"), bool):
            errors.append(f"{prefix}: auto_apply must be boolean")
        approvals = stack.get("approvals")
        if not isinstance(approvals, list) or any(not isinstance(a, str) for a in approvals):
            errors.append(f"{prefix}: approvals must be list of strings")
            approvals = []
        if stack.get("environment") == "prod":
            if stack.get("auto_apply") is not False:
                errors.append(f"{prefix}: production auto_apply prohibited")
            if "service-owner" not in approvals:
                errors.append(f"{prefix}: production service-owner approval required")
            if stack.get("name", "").endswith("database") and "dbre" not in approvals:
                errors.append(f"{prefix}: database DBRE approval required")
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 governance.py environments.json")
        return 1
    try:
        document = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DENY: cannot read inventory: {exc}")
        return 1
    errors = validate_inventory(document)
    if errors:
        for error in errors:
            print("DENY:", error)
        return 1
    print("PASS: inventory governance checks satisfied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
