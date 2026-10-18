"""Fail-closed declared-evidence policy for Chapter 063; not an Ansible AST parser."""
import json
import sys
from pathlib import Path

REQUIRED_FLAGS = ("require_ticket", "deny_prod_targets", "require_serial_one", "require_failure_gate", "require_dbre_approval", "deny_plaintext_secrets")

def validate(manifest, policy):
    if not isinstance(manifest, dict) or not isinstance(policy, dict):
        return ["documents must be objects"]
    errors = []
    for key in REQUIRED_FLAGS:
        if policy.get(key) is not True:
            errors.append("policy missing " + key)
    for key in ("allowed_environments", "allowed_connections", "required_labels"):
        if not isinstance(policy.get(key), list) or not policy[key]:
            errors.append("policy list missing " + key)
    controls = policy.get("required_controls")
    forbidden = policy.get("forbidden_controls")
    if not isinstance(controls, dict) or not controls or not isinstance(forbidden, dict):
        errors.append("control policy missing")
    if errors:
        return errors
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        errors.append("environment denied")
    if manifest.get("connection") not in policy["allowed_connections"]:
        errors.append("connection denied")
    if manifest.get("inventory") != "inventory.ini":
        errors.append("inventory denied")
    if manifest.get("target_hosts") != ["canary_a", "canary_b"]:
        errors.append("targets denied")
    for key in ("owner", "change_ticket"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            errors.append("missing " + key)
    labels = manifest.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    for key in policy["required_labels"]:
        if not isinstance(labels.get(key), str) or not labels[key].strip():
            errors.append("missing label " + key)
    if labels.get("environment") != env or labels.get("owner") != manifest.get("owner") or labels.get("managed-by") != "ansible":
        errors.append("label identity mismatch")
    for section, keys in controls.items():
        if not isinstance(keys, list) or not keys:
            errors.append("invalid control policy " + section)
            continue
        evidence = manifest.get(section)
        if not isinstance(evidence, dict):
            evidence = {}
        for key in keys:
            if key in forbidden.get(section, []):
                if evidence.get(key) is not False:
                    errors.append("forbidden " + section + "." + key)
            elif evidence.get(key) is not True:
                errors.append("missing " + section + "." + key)
    return errors

def main():
    if len(sys.argv) != 3:
        print("Usage: execution_gate.py manifest policy")
        return 1
    try:
        manifest, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
        errors = validate(manifest, policy)
    except (OSError, ValueError) as exc:
        print("INVALID:", type(exc).__name__)
        return 1
    for error in errors:
        print("REJECT:", error)
    if errors:
        return 1
    print("PASS: declared Ansible rolling execution controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
