"""Fail-closed declared-evidence Ansible security governance gate; not an AST or IAM validator."""
import json
import sys
from pathlib import Path

FLAGS = ("require_ticket", "deny_prod_targets", "require_tenant_isolation", "require_vault_policy", "require_provenance", "require_approval", "require_dbre_backup")

def validate(manifest, policy):
    if not isinstance(manifest, dict) or not isinstance(policy, dict):
        return ["documents must be objects"]
    issues = []
    for key in FLAGS:
        if policy.get(key) is not True:
            issues.append("policy missing " + key)
    for key in ("allowed_environments", "required_labels"):
        if not isinstance(policy.get(key), list) or not policy[key]:
            issues.append("policy list missing " + key)
    controls = policy.get("required_controls")
    forbidden = policy.get("forbidden_controls")
    if not isinstance(controls, dict) or not controls or not isinstance(forbidden, dict):
        issues.append("control policy missing")
    if issues:
        return issues
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        issues.append("environment denied")
    if manifest.get("inventory") != "inventory/dynamic_inventory.py":
        issues.append("inventory denied")
    if manifest.get("target_hosts") != ["lab_a", "lab_b"]:
        issues.append("targets denied")
    if manifest.get("tenant") != "sandbox":
        issues.append("tenant denied")
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
        issues.append("label identity mismatch")
    for section, keys in controls.items():
        if not isinstance(keys, list) or not keys:
            issues.append("invalid policy section " + section)
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
        print("Usage: governance_gate.py manifest policy")
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
    print("PASS: declared inventory/Vault/identity/governance/DBRE controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
