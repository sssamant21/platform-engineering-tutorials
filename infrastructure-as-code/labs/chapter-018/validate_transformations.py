"""Validate a simplified JSON input contract; NOT an HCL parser."""
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
    owner = data.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        errors.append("missing owner")
    zones = data.get("zones")
    if not isinstance(zones, list) or not zones:
        return errors + ["zones must be a nonempty list"]
    if any(not isinstance(z, str) or z not in policy.get("allowed_zones", []) for z in zones):
        errors.append("invalid zone")
    if len(set(str(z) for z in zones)) != len(zones):
        errors.append("duplicate zones")
    services = data.get("services")
    if not isinstance(services, dict) or not services:
        return errors + ["services must be a nonempty map"]
    seen = set()
    active = 0
    for name, spec in services.items():
        if not isinstance(name, str) or not NAME.fullmatch(name):
            errors.append(f"invalid service name {name}")
        canonical = str(name).lower()
        if canonical in seen:
            errors.append(f"duplicate canonical key {canonical}")
        seen.add(canonical)
        if not isinstance(spec, dict):
            errors.append(f"{name}: invalid specification")
            continue
        replicas = spec.get("replicas")
        if type(replicas) is not int or not 1 <= replicas <= 12:
            errors.append(f"{name}: invalid replicas")
        if type(spec.get("enabled")) is not bool:
            errors.append(f"{name}: enabled must be boolean")
        if not isinstance(spec.get("tier"), str) or not spec["tier"].strip():
            errors.append(f"{name}: missing tier")
        if spec.get("enabled") is True:
            active += 1
            if env == "prod" and (type(replicas) is not int or replicas < policy.get("min_production_replicas", 3)):
                errors.append(f"{name}: production replica minimum not met")
    if active == 0:
        errors.append("no enabled services")
    if active * len(zones) > policy.get("max_workloads", 30):
        errors.append("workload matrix exceeds policy cap")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 validate_transformations.py <inputs-json> <policy-json>")
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
    print("PASS: educational transformation policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
