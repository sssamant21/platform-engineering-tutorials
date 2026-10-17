"""Educational provider manifest and Terraform plan action gate. Not cloud identity proof."""
import json
import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(r"(access_key|secret_key|client_secret|password|private_key|api_token|credentials)", re.I)
ALIASES = re.compile(r"^[a-z][a-z0-9_-]*$")
VALID_ACTIONS = {"no-op", "read", "create", "update", "delete"}

def validate(manifest, plan, policy):
    if not all(isinstance(v, dict) for v in (manifest, plan, policy)):
        return ["manifest, plan and policy must be objects"]
    errors = []
    for field in ("allowed_provider_sources", "allowed_regions", "allowed_identity_prefixes", "allowed_resource_types"):
        if not isinstance(policy.get(field), list) or not policy[field] or any(not isinstance(x, str) for x in policy[field]):
            errors.append(f"invalid policy {field}")
    for field in ("require_prod_ticket", "deny_deletes", "deny_replacements"):
        if policy.get(field) is not True:
            errors.append(f"policy {field} must be true")
    if errors:
        return errors
    if manifest.get("environment") not in ("dev", "staging", "prod"):
        errors.append("invalid environment")
    for field in ("owner",):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"missing {field}")
    if manifest.get("environment") == "prod" and (not isinstance(manifest.get("change_ticket"), str) or not manifest["change_ticket"].strip()):
        errors.append("production change ticket required")
    providers = manifest.get("providers")
    if not isinstance(providers, list) or not providers:
        errors.append("providers must be nonempty list")
        providers = []
    seen = set()
    for i, item in enumerate(providers):
        if not isinstance(item, dict):
            errors.append(f"provider[{i}] invalid entry")
            continue
        if any(FORBIDDEN.search(str(k)) for k in item):
            errors.append(f"provider[{i}] inline secret-like key")
        if item.get("source") not in policy["allowed_provider_sources"]:
            errors.append(f"provider[{i}] unapproved source")
        alias = item.get("alias")
        if not isinstance(alias, str) or not ALIASES.fullmatch(alias):
            errors.append(f"provider[{i}] invalid alias")
        pair = (str(item.get("source")), str(alias))
        if pair in seen:
            errors.append(f"provider[{i}] duplicate alias")
        seen.add(pair)
        if item.get("region") not in policy["allowed_regions"]:
            errors.append(f"provider[{i}] unapproved region")
        identity = item.get("identity_ref")
        if not isinstance(identity, str) or not any(identity.startswith(prefix) and len(identity) > len(prefix) for prefix in policy["allowed_identity_prefixes"]):
            errors.append(f"provider[{i}] invalid identity reference")
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return errors + ["resource_changes must be list"]
    for i, item in enumerate(changes):
        if not isinstance(item, dict):
            errors.append(f"change[{i}] invalid item")
            continue
        if not isinstance(item.get("address"), str) or not item["address"]:
            errors.append(f"change[{i}] missing address")
        if item.get("type") not in policy["allowed_resource_types"]:
            errors.append(f"change[{i}] unapproved resource type")
        change = item.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(actions, list) or not actions or any(type(x) is not str or x not in VALID_ACTIONS for x in actions):
            errors.append(f"change[{i}] invalid actions")
            continue
        if "delete" in actions:
            errors.append(f"change[{i}] delete or replacement denied")
    return errors

def main(argv):
    if len(argv) != 4:
        print("Usage: python3 capstone_policy.py <manifest-json> <plan-json> <policy-json>")
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
    print("PASS: educational provider manifest and plan policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
