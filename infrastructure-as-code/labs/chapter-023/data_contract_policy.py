"""Educational JSON contract validator; does not inspect HCL, providers or remote state."""
import json
import re
import sys
from pathlib import Path

SECRET_KEYS = re.compile(r"(password|secret|token|private_key|access_key|credentials)", re.I)

def validate(contract, policy):
    if not isinstance(contract, dict) or not isinstance(policy, dict):
        return ["contract and policy must be objects"]
    errors = []
    for key in ("allowed_environments", "allowed_source_types", "supported_schema_versions", "required_subnet_keys"):
        if not isinstance(policy.get(key), list) or not policy[key]:
            errors.append(f"invalid policy {key}")
    if policy.get("require_prod_backup") is not True or policy.get("require_prod_encryption") is not True:
        errors.append("production safeguards must be enabled in policy")
    if errors:
        return errors
    if type(contract.get("schema_version")) is not int or contract["schema_version"] not in policy["supported_schema_versions"]:
        errors.append("unsupported schema version")
    if contract.get("source_type") not in policy["allowed_source_types"]:
        errors.append("unapproved source type")
    env = contract.get("environment")
    if env not in policy["allowed_environments"]:
        errors.append("invalid environment")
    for field in ("owner", "change_ticket", "source_identity"):
        if not isinstance(contract.get(field), str) or not contract[field].strip():
            errors.append(f"missing {field}")
    subnets = contract.get("subnets")
    if not isinstance(subnets, dict):
        errors.append("subnets must be an object")
        subnets = {}
    ids = []
    for key in policy["required_subnet_keys"]:
        value = subnets.get(key)
        if not isinstance(value, str) or not value.startswith("subnet-") or len(value) <= 7:
            errors.append(f"invalid subnet {key}")
        else:
            ids.append(value)
    if len(ids) != len(set(ids)):
        errors.append("duplicate subnet IDs")
    database = contract.get("database")
    if not isinstance(database, dict):
        errors.append("database must be an object")
        database = {}
    if not isinstance(database.get("name"), str) or not database["name"].strip():
        errors.append("missing database name")
    for field in ("backup_enabled", "encrypted"):
        if type(database.get(field)) is not bool:
            errors.append(f"invalid database {field}")
        if env == "prod" and database.get(field) is not True:
            errors.append(f"production requires {field}")
    def scan(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if SECRET_KEYS.search(str(key)):
                    errors.append(f"secret-like field forbidden: {prefix}{key}")
                scan(value, f"{prefix}{key}.")
        elif isinstance(obj, list):
            for value in obj:
                scan(value, prefix)
    scan(contract)
    return errors

def main(argv):
    if len(argv) != 3:
        print("Usage: python3 data_contract_policy.py <contract-json> <policy-json>")
        return 1
    try:
        contract = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        policy = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        errors = validate(contract, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational cross-module data contract")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
