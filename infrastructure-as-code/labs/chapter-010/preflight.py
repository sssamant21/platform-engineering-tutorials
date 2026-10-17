"""Read-only IaC readiness gate, using only Python stdlib."""
import json
import re
import sys
from pathlib import Path

EXCLUDED = {".terraform", ".git", "__pycache__", ".venv"}

def validate(data):
    if not isinstance(data, dict):
        return ["manifest must be object"]
    errors = []
    if data.get("engine") not in ("terraform", "tofu"):
        errors.append("invalid engine")
    if not isinstance(data.get("cli_version"), str) or not re.fullmatch(r"\d+\.\d+\.\d+", data["cli_version"]):
        errors.append("cli_version must be exact")
    if not isinstance(data.get("ci_image"), str) or not re.fullmatch(r".+@sha256:[a-f0-9]{64}", data["ci_image"]):
        errors.append("ci_image must be immutable digest")
    stacks = data.get("stacks")
    if not isinstance(stacks, list) or not stacks:
        return errors + ["stacks must be nonempty list"]
    ids, backends = set(), set()
    for i, s in enumerate(stacks):
        p = f"stacks[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{p}: invalid stack")
            continue
        for field in ("id", "service", "owner", "cost_center", "backend_key", "ci_identity"):
            if not isinstance(s.get(field), str) or not s[field].strip():
                errors.append(f"{p}: missing {field}")
        if s.get("cloud") not in ("aws", "azure", "gcp"):
            errors.append(f"{p}: invalid cloud")
        if s.get("environment") not in ("dev", "staging", "prod"):
            errors.append(f"{p}: invalid environment")
        for field, seen in (("id", ids), ("backend_key", backends)):
            value = s.get(field)
            if isinstance(value, str):
                if value in seen:
                    errors.append(f"{p}: duplicate {field}")
                seen.add(value)
        state = s.get("state")
        if not isinstance(state, dict) or any(state.get(k) is not True for k in ("encrypted", "locking", "versioning")):
            errors.append(f"{p}: state encryption, locking and versioning required")
        if not isinstance(s.get("auto_apply"), bool):
            errors.append(f"{p}: auto_apply must be boolean")
        approvals = s.get("approvals")
        if not isinstance(approvals, list) or any(not isinstance(a, str) for a in approvals):
            errors.append(f"{p}: approvals must be string list")
            approvals = []
        if s.get("environment") == "prod":
            if s.get("auto_apply") is not False:
                errors.append(f"{p}: production auto_apply prohibited")
            if "service-owner" not in approvals:
                errors.append(f"{p}: service-owner approval required")
            if s.get("service") == "database" and "dbre" not in approvals:
                errors.append(f"{p}: production database DBRE approval required")
    return errors

def forbidden_artifacts(root):
    root = Path(root)
    errors = []
    for p in root.rglob("*"):
        if any(x in EXCLUDED for x in p.relative_to(root).parts) or not p.is_file():
            continue
        name = p.name.lower()
        if name.endswith((".tfstate", ".tfplan", ".pem", ".key")) or ".tfstate." in name:
            errors.append(f"forbidden artifact: {p.relative_to(root)}")
    return errors

def check_gitignore(root):
    p = Path(root) / ".gitignore"
    if not p.is_file():
        return [".gitignore missing"]
    lines = set(p.read_text(encoding="utf-8").splitlines())
    return [f".gitignore missing {v}" for v in (".terraform/", "*.tfstate", "*.tfplan") if v not in lines]

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 preflight.py readiness.json")
        return 1
    try:
        path = Path(argv[1])
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate(data) + forbidden_artifacts(path.parent) + check_gitignore(path.parent)
    except (OSError, json.JSONDecodeError) as exc:
        print("DENY:", exc)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: Chapter 010 sample readiness checks satisfied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
