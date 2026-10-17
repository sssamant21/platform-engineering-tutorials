"""Educational JSON input + Terraform plan JSON gate. No external approvals checked."""
import json
import re
import sys
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9-]*$")
ACTIONS = {"no-op", "read", "create", "update", "delete"}

def validate(inputs, plan, policy):
    if not all(isinstance(v, dict) for v in (inputs, plan, policy)):
        return ["inputs, plan and policy must be objects"]
    errors = []
    allowed = policy.get("allowed_environments")
    zones_allowed = policy.get("allowed_zones")
    minimum = policy.get("min_production_replicas")
    maximum = policy.get("max_workloads")
    if not isinstance(allowed, list) or not allowed or not all(isinstance(v, str) for v in allowed):
        errors.append("invalid allowed_environments policy")
    if not isinstance(zones_allowed, list) or not zones_allowed or not all(isinstance(v, str) for v in zones_allowed):
        errors.append("invalid allowed_zones policy")
    if type(minimum) is not int or minimum < 2:
        errors.append("invalid min_production_replicas policy")
    if type(maximum) is not int or maximum < 1:
        errors.append("invalid max_workloads policy")
    if policy.get("deny_deletes") is not True:
        errors.append("deny_deletes must be true")
    if errors:
        return errors
    env = inputs.get("environment")
    if env not in allowed:
        errors.append("invalid environment")
    for field in ("owner", "change_ticket"):
        if not isinstance(inputs.get(field), str) or not inputs[field].strip():
            errors.append(f"missing {field}")
    zones = inputs.get("zones")
    if not isinstance(zones, list) or not zones:
        errors.append("zones must be a nonempty list")
        zones = []
    if any(not isinstance(z, str) or z not in zones_allowed for z in zones):
        errors.append("invalid zone")
    if len(zones) != len(set(str(z) for z in zones)):
        errors.append("duplicate zones")
    services = inputs.get("services")
    if not isinstance(services, dict) or not services:
        errors.append("services must be a nonempty map")
        services = {}
    active = 0
    for name, spec in services.items():
        if not isinstance(name, str) or not NAME.fullmatch(name):
            errors.append(f"invalid service name {name}")
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
            if env == "prod" and (type(replicas) is not int or replicas < minimum):
                errors.append(f"{name}: production replica minimum not met")
    if active == 0:
        errors.append("no enabled services")
    if active * len(zones) > maximum:
        errors.append("workload matrix exceeds cap")
    database = inputs.get("database")
    if not isinstance(database, dict):
        errors.append("database must be an object")
        database = {}
    db_replicas = database.get("replicas")
    if type(db_replicas) is not int or db_replicas < 0:
        errors.append("invalid database replicas")
    for field in ("backup_enabled", "encrypted", "deletion_protection"):
        if type(database.get(field)) is not bool:
            errors.append(f"invalid database {field}")
    if env == "prod":
        if type(db_replicas) is not int or db_replicas < minimum:
            errors.append("production database replica minimum not met")
        for field in ("backup_enabled", "encrypted", "deletion_protection"):
            if database.get(field) is not True:
                errors.append(f"production database requires {field}")
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        errors.append("resource_changes must be a list")
    else:
        for i, item in enumerate(changes):
            change = item.get("change") if isinstance(item, dict) else None
            actions = change.get("actions") if isinstance(change, dict) else None
            if not isinstance(actions, list) or not actions or any(a not in ACTIONS for a in actions):
                errors.append(f"resource_changes[{i}]: invalid actions")
            elif "delete" in actions:
                errors.append(f"resource_changes[{i}]: destructive action denied")
    return errors

def main(argv):
    if len(argv) != 4:
        print("Usage: python3 capstone_policy.py <inputs-json> <plan-json> <policy-json>")
        return 1
    try:
        inputs = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        plan = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
        errors = validate(inputs, plan, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational IaC Part 04 capstone policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
