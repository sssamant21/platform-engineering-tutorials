"""Validate fictional IaC stack boundaries. Not a cloud authorization control."""
import json
import sys
from pathlib import Path

REQUIRED = ("id", "cloud", "environment", "owner", "service", "cost_center", "backend_key", "state", "auto_apply", "approvals")
ENVIRONMENTS = {"dev", "staging", "prod"}
CLOUDS = {"aws", "azure", "gcp"}

def validate(document):
    if not isinstance(document, dict) or not isinstance(document.get("stacks"), list) or not document["stacks"]:
        return ["stacks must be a nonempty list"]
    errors, ids, keys = [], set(), set()
    for index, item in enumerate(document["stacks"]):
        prefix = f"stacks[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be object")
            continue
        for field in REQUIRED:
            if field not in item:
                errors.append(f"{prefix}: missing {field}")
        for field in ("id", "owner", "service", "cost_center", "backend_key"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{prefix}: invalid {field}")
        if item.get("cloud") not in CLOUDS:
            errors.append(f"{prefix}: invalid cloud")
        if item.get("environment") not in ENVIRONMENTS:
            errors.append(f"{prefix}: invalid environment")
        for field, seen in (("id", ids), ("backend_key", keys)):
            value = item.get(field)
            if isinstance(value, str):
                if value in seen:
                    errors.append(f"{prefix}: duplicate {field}")
                seen.add(value)
        state = item.get("state")
        if not isinstance(state, dict) or any(state.get(k) is not True for k in ("encrypted", "locking", "versioning")):
            errors.append(f"{prefix}: state encryption, locking and versioning required")
        if not isinstance(item.get("auto_apply"), bool):
            errors.append(f"{prefix}: auto_apply must be boolean")
        approvals = item.get("approvals")
        if not isinstance(approvals, list) or any(not isinstance(a, str) for a in approvals):
            errors.append(f"{prefix}: approvals must be a list of strings")
            approvals = []
        if item.get("environment") == "prod":
            if item.get("auto_apply") is not False:
                errors.append(f"{prefix}: production auto_apply prohibited")
            if "service-owner" not in approvals:
                errors.append(f"{prefix}: production service-owner approval required")
            if item.get("service") == "database" and "dbre" not in approvals:
                errors.append(f"{prefix}: DBRE approval required for production database")
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 validate_stacks.py stacks.json")
        return 1
    try:
        document = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DENY: {exc}")
        return 1
    errors = validate(document)
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: stack isolation and governance checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
