"""Fail-closed educational DR manifest and synthetic Terraform state metadata validator."""
import json
import re
import sys
from pathlib import Path

SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")

def validate(manifest, state, policy):
    if not all(isinstance(x, dict) for x in (manifest, state, policy)):
        return ["manifest, state and policy must be objects"]
    errors = []
    for field in ("allowed_environments", "required_controls"):
        if not isinstance(policy.get(field), list) or not policy[field] or any(not isinstance(x, str) for x in policy[field]):
            errors.append(f"invalid policy {field}")
    for field in ("min_retention_days", "max_rpo_minutes", "max_rto_minutes"):
        if type(policy.get(field)) is not int or policy[field] <= 0:
            errors.append(f"invalid policy {field}")
    for field in ("require_prod_ticket", "require_distinct_backends"):
        if policy.get(field) is not True:
            errors.append(f"policy {field} must be true")
    if errors:
        return errors
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        errors.append("invalid environment")
    if env == "prod" and (not isinstance(manifest.get("change_ticket"), str) or not manifest["change_ticket"].strip()):
        errors.append("production change ticket required")
    source, destination = manifest.get("source_backend"), manifest.get("destination_backend")
    if not isinstance(source, str) or not source.strip() or not isinstance(destination, str) or not destination.strip() or source == destination:
        errors.append("distinct nonempty source and destination backends required")
    if not isinstance(manifest.get("snapshot_id"), str) or not manifest["snapshot_id"].strip():
        errors.append("snapshot id required")
    digest = manifest.get("snapshot_sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        errors.append("invalid SHA-256 format")
    lineage = manifest.get("snapshot_lineage")
    if not isinstance(lineage, str) or not UUID.fullmatch(lineage) or lineage != state.get("lineage"):
        errors.append("snapshot lineage mismatch")
    serial = manifest.get("snapshot_serial")
    if type(serial) is not int or type(state.get("serial")) is not int or serial < 0 or serial != state["serial"]:
        errors.append("snapshot serial mismatch")
    if type(state.get("version")) is not int or state["version"] != 4:
        errors.append("unsupported state version")
    controls = manifest.get("controls")
    if not isinstance(controls, dict):
        errors.append("controls required")
        controls = {}
    for field in policy["required_controls"]:
        if controls.get(field) is not True:
            errors.append(f"required control missing: {field}")
    for field, limit, op in (("retention_days", policy["min_retention_days"], "min"), ("rpo_minutes", policy["max_rpo_minutes"], "max"), ("rto_minutes", policy["max_rto_minutes"], "max")):
        value = manifest.get(field)
        if type(value) is not int or value <= 0 or (value < limit if op == "min" else value > limit):
            errors.append(f"invalid {field}")
    return errors

def main(argv):
    if len(argv) != 4:
        print("Usage: python3 state_dr_policy.py <manifest-json> <state-json> <policy-json>")
        return 1
    try:
        manifest, state, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors = validate(manifest, state, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: declared state DR controls and metadata")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
