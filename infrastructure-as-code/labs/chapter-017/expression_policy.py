"""Educational JSON input policy; not a Terraform HCL or plan parser."""
import ipaddress
import json
import re
import sys
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9-]*$")

def validate(data, policy):
    if not isinstance(data, dict) or not isinstance(policy, dict):
        return ["inputs and policy must be objects"]
    errors = []
    env = data.get("environment")
    if env not in policy.get("allowed_environments", []):
        errors.append("invalid environment")
    service = data.get("service")
    if not isinstance(service, str) or not NAME.fullmatch(service):
        errors.append("invalid service name")
    owner = data.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        errors.append("missing owner")
    services = data.get("services")
    if not isinstance(services, dict) or not services:
        return errors + ["services must be a nonempty map"]
    seen = set()
    for key, spec in services.items():
        if not isinstance(key, str) or not NAME.fullmatch(key):
            errors.append(f"invalid service key {key}")
        normalized = key.lower() if isinstance(key, str) else str(key)
        if normalized in seen:
            errors.append(f"duplicate canonical service name {normalized}")
        seen.add(normalized)
        if not isinstance(spec, dict):
            errors.append(f"{key}: invalid service definition")
            continue
        count = spec.get("replicas")
        if type(count) is not int or count < 1 or count > 12:
            errors.append(f"{key}: invalid replicas")
        if type(spec.get("enabled")) is not bool:
            errors.append(f"{key}: enabled must be boolean")
        if env == "prod" and spec.get("enabled") is True and (type(count) is not int or count < policy.get("min_production_replicas", 3)):
            errors.append(f"{key}: production replica minimum not met")
    try:
        network = ipaddress.ip_network(data.get("network_cidr", ""), strict=True)
        if network.version != 4 or (policy.get("require_private_ipv4") and not network.is_private):
            errors.append("network must be private IPv4")
    except (ValueError, TypeError):
        errors.append("invalid network CIDR")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 expression_policy.py <inputs-json> <policy-json>")
        return 1
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        errors = validate(data, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational expression policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
