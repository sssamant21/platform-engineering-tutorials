"""Read local Terraform state metadata; never print instance attributes or output values."""
import json
import re
import sys
from pathlib import Path

UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
SECRET = re.compile(r"(password|secret|token|private_key|access_key|credentials)", re.I)

def inspect(state, policy):
    if not isinstance(state, dict) or not isinstance(policy, dict):
        return {}, ["state and policy must be objects"]
    errors = []
    for key in ("supported_state_versions", "allowed_resource_types", "allowed_modes", "required_resource_names"):
        if not isinstance(policy.get(key), list) or not policy[key]:
            errors.append(f"invalid policy {key}")
    if type(policy.get("min_serial")) is not int or policy["min_serial"] < 0:
        errors.append("invalid policy min_serial")
    if type(policy.get("min_terraform_major")) is not int or policy["min_terraform_major"] < 1:
        errors.append("invalid policy min_terraform_major")
    if errors:
        return {}, errors
    if type(state.get("version")) is not int or state["version"] not in policy["supported_state_versions"]:
        errors.append("unsupported state version")
    serial = state.get("serial")
    if type(serial) is not int or serial < policy["min_serial"]:
        errors.append("invalid state serial")
    lineage = state.get("lineage")
    if not isinstance(lineage, str) or not UUID.fullmatch(lineage):
        errors.append("invalid lineage")
    version = state.get("terraform_version")
    if not isinstance(version, str) or not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+", version) or int(version.split(".")[0]) < policy["min_terraform_major"]:
        errors.append("invalid Terraform version")
    outputs = state.get("outputs")
    if not isinstance(outputs, dict):
        errors.append("outputs must be object")
        outputs = {}
    for key in outputs:
        if SECRET.search(key):
            errors.append("secret-like output name forbidden")
    resources = state.get("resources")
    if not isinstance(resources, list):
        errors.append("resources must be list")
        resources = []
    addresses = []
    for i, resource in enumerate(resources):
        if not isinstance(resource, dict):
            errors.append(f"resource[{i}] must be object")
            continue
        if resource.get("mode") not in policy["allowed_modes"]:
            errors.append(f"resource[{i}] disallowed mode")
        if resource.get("type") not in policy["allowed_resource_types"]:
            errors.append(f"resource[{i}] disallowed type")
        name = resource.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"resource[{i}] missing name")
            continue
        module = resource.get("module", "")
        if not isinstance(module, str):
            errors.append(f"resource[{i}] invalid module path")
            continue
        address = f"{module + '.' if module else ''}{resource.get('type')}.{name}"
        if address in addresses:
            errors.append("duplicate resource address")
        addresses.append(address)
        if not isinstance(resource.get("instances"), list) or not resource["instances"]:
            errors.append(f"resource[{i}] missing instances")
    names = {r.get("name") for r in resources if isinstance(r, dict)}
    for name in policy["required_resource_names"]:
        if name not in names:
            errors.append(f"missing required resource {name}")
    # Never return attributes or output values; metadata still needs access review.
    return {"serial": serial, "lineage": lineage, "terraform_version": version, "resource_addresses": sorted(addresses), "output_names": sorted(outputs)}, errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 state_inventory.py <state-json> <policy-json>")
        return 1
    try:
        state = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        metadata, errors = inspect(state, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print(json.dumps(metadata, indent=2, sort_keys=True))
    print("PASS: limited state metadata inspection")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
