"""Offline nested-stack contract and declared StackSet policy; not an AWS API response parser."""
import json
import sys
from pathlib import Path

FLAGS = ("require_ticket", "deny_prod_targets", "require_account_region_allowlist", "require_iam_review", "require_dbre_backup", "require_rollback")

def validate(parent, child, manifest, policy):
    if not all(isinstance(x, dict) for x in (parent, child, manifest, policy)):
        return ["documents must be objects"]
    errors = []
    for name, template in (("parent", parent), ("child", child)):
        if template.get("AWSTemplateFormatVersion") != "2010-09-09":
            errors.append("invalid " + name + " version")
        if not isinstance(template.get("Resources"), dict) or not template["Resources"]:
            errors.append("missing " + name + " resources")
        if not isinstance(template.get("Parameters"), dict) or "Environment" not in template["Parameters"]:
            errors.append("missing " + name + " environment contract")
    resources = parent.get("Resources", {})
    if isinstance(resources, dict):
        if len(resources) != 1 or resources.get("NestedDemo", {}).get("Type") != "AWS::CloudFormation::Stack":
            errors.append("parent nested stack contract denied")
        else:
            props = resources["NestedDemo"].get("Properties", {})
            if props.get("TemplateURL") != "https://example.invalid/chapter067/child-template.json":
                errors.append("unapproved child artifact")
            if props.get("Parameters", {}).get("Environment") != {"Ref": "Environment"}:
                errors.append("child parameter mapping denied")
    if child.get("Outputs", {}).get("Environment", {}).get("Value") != {"Ref": "Environment"}:
        errors.append("child output contract denied")
    for key in FLAGS:
        if policy.get(key) is not True:
            errors.append("policy missing " + key)
    for key in ("allowed_environments", "required_labels"):
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
    for key, expected in (("account", "offline-sandbox"), ("region", "us-east-1"), ("ou", "sandbox"), ("stackset", "chapter067-offline")):
        if manifest.get(key) != expected:
            errors.append(key + " denied")
    for key in ("owner", "change_ticket"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            errors.append("missing " + key)
    labels = manifest.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    for key in policy["required_labels"]:
        if not isinstance(labels.get(key), str) or not labels[key].strip():
            errors.append("missing label " + key)
    if labels.get("environment") != env or labels.get("owner") != manifest.get("owner") or labels.get("managed-by") != "cloudformation":
        errors.append("label identity mismatch")
    for section, keys in controls.items():
        if not isinstance(keys, list) or not keys:
            errors.append("invalid policy section " + section)
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
    if len(sys.argv) != 5:
        print("Usage: stackset_gate.py parent child evidence policy")
        return 1
    try:
        parent, child, evidence, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
        errors = validate(parent, child, evidence, policy)
    except (OSError, ValueError) as exc:
        print("INVALID:", type(exc).__name__)
        return 1
    for error in errors:
        print("REJECT:", error)
    if errors:
        return 1
    print("PASS: offline nested-stack and declared StackSet governance")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
