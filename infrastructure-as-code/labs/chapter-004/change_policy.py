"""Local educational change gate; not a production Terraform plan parser."""
import json
import re
import sys
from pathlib import Path

ALLOWED_ACTIONS = {"create", "update", "delete", "replace", "no-op"}
ALLOWED_ENVIRONMENTS = {"lab", "staging", "prod"}

def validate_change(change):
    errors = []
    if not isinstance(change, dict):
        return ["Change request must be an object"]
    for field in ("ticket", "environment", "commit_sha", "owner", "rollback_plan", "verification"):
        if not isinstance(change.get(field), str) or not change[field].strip():
            errors.append(f"Missing or invalid {field}")
    env = change.get("environment")
    if env not in ALLOWED_ENVIRONMENTS:
        errors.append("Unsupported environment")
    sha = change.get("commit_sha", "")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        errors.append("commit_sha must be a 7-40 character hexadecimal Git SHA")
    actions = change.get("actions")
    if not isinstance(actions, list) or not actions or any(a not in ALLOWED_ACTIONS for a in actions):
        errors.append("actions must be a nonempty list of known actions")
        actions = []
    approvals = change.get("approvals")
    if not isinstance(approvals, list) or any(not isinstance(a, str) for a in approvals):
        errors.append("approvals must be a list of strings")
        approvals = []
    if env == "prod" and "production-owner" not in approvals:
        errors.append("Production owner approval required")
    if env == "prod" and any(a in {"delete", "replace"} for a in actions):
        if "destructive-change" not in approvals:
            errors.append("Destructive production change approval required")
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 change_policy.py change_request.json")
        return 1
    try:
        request = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DENIED: cannot read request: {exc}")
        return 1
    errors = validate_change(request)
    if errors:
        for error in errors:
            print(f"DENIED: {error}")
        return 1
    print("APPROVED: sample change policy checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
