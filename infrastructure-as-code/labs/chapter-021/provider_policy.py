"""Educational provider manifest review, not Terraform HCL or cloud identity verification."""
import json
import re
import sys
from pathlib import Path

CONSTRAINT = re.compile(r"^(?:~>|>=|<=|=|>|<) ?[0-9]+(?:\.[0-9]+){0,2}(?:, ?(?:~>|>=|<=|=|>|<) ?[0-9]+(?:\.[0-9]+){0,2})*$")
ALIAS = re.compile(r"^[a-z][a-z0-9_-]*$")
FORBIDDEN = {"access_key", "secret_key", "client_secret", "password", "token", "private_key", "credentials"}

def validate(manifest, policy):
    if not isinstance(manifest, dict) or not isinstance(policy, dict):
        return ["manifest and policy must be objects"]
    errors = []
    for key in ("allowed_sources", "allowed_environments", "allowed_regions", "identity_prefixes"):
        if not isinstance(policy.get(key), list) or not policy[key] or any(not isinstance(v, str) for v in policy[key]):
            errors.append(f"invalid policy {key}")
    if policy.get("require_prod_ticket") is not True:
        errors.append("require_prod_ticket must be true")
    if errors:
        return errors
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        errors.append("invalid environment")
    if not isinstance(manifest.get("owner"), str) or not manifest["owner"].strip():
        errors.append("missing owner")
    if env == "prod" and (not isinstance(manifest.get("change_ticket"), str) or not manifest["change_ticket"].strip()):
        errors.append("production change ticket required")
    providers = manifest.get("providers")
    if not isinstance(providers, list) or not providers:
        return errors + ["providers must be a nonempty list"]
    seen = set()
    for i, item in enumerate(providers):
        if not isinstance(item, dict):
            errors.append(f"providers[{i}]: invalid entry")
            continue
        if FORBIDDEN.intersection(item):
            errors.append(f"providers[{i}]: inline credentials forbidden")
        source = item.get("source")
        alias = item.get("alias")
        if source not in policy["allowed_sources"]:
            errors.append(f"providers[{i}]: unapproved source")
        if not isinstance(alias, str) or not ALIAS.fullmatch(alias):
            errors.append(f"providers[{i}]: invalid alias")
        pair = (str(source), str(alias))
        if pair in seen:
            errors.append(f"providers[{i}]: duplicate alias")
        seen.add(pair)
        constraint = item.get("constraint")
        if not isinstance(constraint, str) or not CONSTRAINT.fullmatch(constraint):
            errors.append(f"providers[{i}]: invalid version constraint")
        if item.get("region") not in policy["allowed_regions"]:
            errors.append(f"providers[{i}]: unapproved region")
        identity = item.get("identity_ref")
        if not isinstance(identity, str) or not any(identity.startswith(prefix) and len(identity) > len(prefix) for prefix in policy["identity_prefixes"]):
            errors.append(f"providers[{i}]: invalid identity reference")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 provider_policy.py <manifest-json> <policy-json>")
        return 1
    try:
        manifest = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        errors = validate(manifest, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational provider manifest policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
