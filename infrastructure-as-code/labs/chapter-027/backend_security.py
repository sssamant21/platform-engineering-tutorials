"""Educational backend inventory policy. Does not query cloud APIs or verify actual IAM."""
import json
import re
import sys
from pathlib import Path

SECRET = re.compile(r"(access_key|secret_key|password|client_secret|private_key|api_token|credentials)", re.I)

def validate(inventory, policy):
    if not isinstance(inventory, dict) or not isinstance(policy, dict):
        return ["inventory and policy must be objects"]
    errors = []
    for field in ("allowed_backend_types", "allowed_identity_prefixes", "required_controls"):
        if not isinstance(policy.get(field), list) or not policy[field] or not all(isinstance(v, str) for v in policy[field]):
            errors.append(f"invalid policy {field}")
    for field in ("require_private", "require_prod_remote", "forbid_wildcard_permissions"):
        if policy.get(field) is not True:
            errors.append(f"policy {field} must be true")
    if errors:
        return errors
    backends = inventory.get("backends")
    if not isinstance(backends, list) or not backends:
        return ["backends must be nonempty list"]
    seen = set()
    for i, backend in enumerate(backends):
        if not isinstance(backend, dict):
            errors.append(f"backend[{i}] invalid entry")
            continue
        for key in backend:
            if SECRET.search(str(key)):
                errors.append(f"backend[{i}] secret-like key forbidden")
        env = backend.get("environment")
        if env not in ("dev", "staging", "prod"):
            errors.append(f"backend[{i}] invalid environment")
        kind = backend.get("backend_type")
        if kind not in policy["allowed_backend_types"]:
            errors.append(f"backend[{i}] unsupported or local backend")
        key = backend.get("state_key")
        if not isinstance(key, str) or not key.strip() or not isinstance(env, str) or f"/{env}/" not in f"/{key}":
            errors.append(f"backend[{i}] state key lacks environment isolation")
        if isinstance(key, str):
            if key in seen:
                errors.append(f"backend[{i}] duplicate state key")
            seen.add(key)
        identity = backend.get("identity_ref")
        if not isinstance(identity, str) or not any(identity.startswith(p) and len(identity) > len(p) for p in policy["allowed_identity_prefixes"]):
            errors.append(f"backend[{i}] invalid identity reference")
        if backend.get("public_access") is not False:
            errors.append(f"backend[{i}] public access not explicitly disabled")
        permissions = backend.get("permissions")
        if not isinstance(permissions, list) or not permissions or any(not isinstance(p, str) or not p.strip() or "*" in p for p in permissions):
            errors.append(f"backend[{i}] invalid or wildcard permissions")
        controls = backend.get("controls")
        if not isinstance(controls, dict):
            errors.append(f"backend[{i}] missing controls")
            continue
        for control in policy["required_controls"]:
            if controls.get(control) is not True:
                errors.append(f"backend[{i}] required control missing: {control}")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 backend_security.py <inventory-json> <policy-json>")
        return 1
    try:
        inventory, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors = validate(inventory, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: declared backend inventory controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
