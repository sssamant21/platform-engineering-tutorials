"""Fail-closed Ansible lab declared-evidence gate; not an Ansible playbook parser."""
import json
import sys
from pathlib import Path

REQUIRED_POLICY = ("require_ticket", "require_local_scope", "deny_prod_targets", "require_idempotence", "require_approval", "require_dbre_backup", "deny_plaintext_secrets")

def validate(manifest, policy):
    if not isinstance(manifest, dict) or not isinstance(policy, dict):
        return ["documents must be objects"]
    issues = []
    for key in REQUIRED_POLICY:
        if policy.get(key) is not True:
            issues.append("policy missing " + key)
    for key in ("allowed_environments", "allowed_connections", "required_labels"):
        if not isinstance(policy.get(key), list) or not policy[key]:
            issues.append("policy list missing " + key)
    controls = policy.get("required_controls")
    forbidden = policy.get("forbidden_controls")
    if not isinstance(controls, dict) or not controls or not isinstance(forbidden, dict):
        issues.append("policy controls missing")
    if issues:
        return issues
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        issues.append("invalid environment")
    if manifest.get("connection") not in policy["allowed_connections"]:
        issues.append("invalid connection")
    if manifest.get("inventory") != "inventory.ini":
        issues.append("inventory not approved")
    if manifest.get("target_hosts") != ["localhost"]:
        issues.append("target hosts not localhost only")
    for key in ("owner", "change_ticket"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            issues.append("missing " + key)
    labels = manifest.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    for key in policy["required_labels"]:
        if not isinstance(labels.get(key), str) or not labels[key].strip():
            issues.append("missing label " + key)
    if labels.get("environment") != env or labels.get("owner") != manifest.get("owner") or labels.get("managed-by") != "ansible":
        issues.append("label identity")
    for section, keys in controls.items():
        if not isinstance(keys, list) or not keys:
            issues.append("invalid control policy " + section)
            continue
        evidence = manifest.get(section)
        if not isinstance(evidence, dict):
            evidence = {}
        for key in keys:
            if key in forbidden.get(section, []):
                if evidence.get(key) is not False:
                    issues.append("forbidden " + section + "." + key)
            elif evidence.get(key) is not True:
                issues.append("missing " + section + "." + key)
    return issues

def main():
    if len(sys.argv) != 3:
        print("Usage: ansible_gate.py manifest policy")
        return 1
    try:
        manifest, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
        issues = validate(manifest, policy)
    except (OSError, ValueError) as exc:
        print("INVALID:", type(exc).__name__)
        return 1
    for issue in issues:
        print("REJECT:", issue)
    if issues:
        return 1
    print("PASS: declared Ansible inventory/configuration/security/operations controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
