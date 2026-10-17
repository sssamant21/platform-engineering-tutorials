"""Educational parser for flat example tfvars; not a general HCL parser."""
import json
import re
import sys
from pathlib import Path

KEY = re.compile(r'^([a-z][a-z0-9_]*)\s*=\s*(?:"([^"]*)"|(-?\d+)|true|false)\s*$')
ALLOWED = {"environment", "service", "owner", "replicas", "change_ticket", "db_replicas", "db_encrypted", "db_backup_enabled"}

def parse(text):
    values = {}
    errors = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = KEY.fullmatch(line)
        if not m:
            errors.append(f"line {lineno}: unsupported syntax")
            continue
        key = m.group(1)
        if key not in ALLOWED:
            errors.append(f"line {lineno}: unsupported key {key}")
            continue
        if key in values:
            errors.append(f"line {lineno}: duplicate key {key}")
            continue
        if m.group(2) is not None:
            value = m.group(2)
        elif m.group(3) is not None:
            value = int(m.group(3))
        else:
            value = line.split("=", 1)[1].strip() == "true"
        values[key] = value
    return values, errors

def validate(values, policy):
    errors = []
    if values.get("environment") not in policy.get("environments", []):
        errors.append("invalid environment")
    for key in ("service", "owner", "change_ticket"):
        if not isinstance(values.get(key), str) or not values[key].strip():
            errors.append(f"missing {key}")
    for key in ("replicas", "db_replicas"):
        if type(values.get(key)) is not int or values[key] < 0:
            errors.append(f"invalid {key}")
    for key in ("db_encrypted", "db_backup_enabled"):
        if type(values.get(key)) is not bool:
            errors.append(f"invalid {key}")
    if values.get("environment") == "prod":
        if type(values.get("db_replicas")) is not int or values["db_replicas"] < policy.get("production_min_db_replicas", 2):
            errors.append("production database replica minimum not met")
        if values.get("db_encrypted") is not True:
            errors.append("production database encryption required")
        if values.get("db_backup_enabled") is not True:
            errors.append("production database backup required")
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 validate_inputs.py <tfvars> <policy-json>")
        return 1
    try:
        values, errors = parse(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        errors += validate(values, policy)
    except (OSError, ValueError, TypeError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational input policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
