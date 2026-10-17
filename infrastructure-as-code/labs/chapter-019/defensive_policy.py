"""Fail-closed educational JSON policy; not a Terraform HCL/plan parser."""
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
    allowed = policy.get("allowed_environments")
    minimum = policy.get("min_production_replicas")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(x, str) for x in allowed):
        return ["invalid allowed_environments policy"]
    if type(minimum) is not int or minimum < 2:
        return ["invalid min_production_replicas policy"]
    if type(policy.get("require_private_ipv4")) is not bool:
        return ["invalid require_private_ipv4 policy"]
    if env not in allowed:
        errors.append("invalid environment")
    name = data.get("service")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        errors.append("invalid service")
    for key in ("owner", "change_ticket"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"missing {key}")
    count = data.get("replicas")
    if type(count) is not int or count < 1 or count > 12:
        errors.append("invalid replicas")
    for key in ("backup_enabled", "encryption_enabled", "deletion_protection"):
        if type(data.get(key)) is not bool:
            errors.append(f"invalid {key}: must be boolean")
    if env == "prod":
        if type(count) is not int or count < minimum:
            errors.append("production replica minimum not met")
        for key in ("backup_enabled", "encryption_enabled", "deletion_protection"):
            if data.get(key) is not True:
                errors.append(f"production requires {key}")
    try:
        network = ipaddress.ip_network(data.get("network_cidr", ""), strict=True)
        if network.version != 4 or (policy["require_private_ipv4"] and not network.is_private):
            errors.append("network must be private IPv4")
    except (ValueError, TypeError):
        errors.append("invalid network CIDR")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 defensive_policy.py <inputs-json> <policy-json>")
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
    print("PASS: educational defensive configuration policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
