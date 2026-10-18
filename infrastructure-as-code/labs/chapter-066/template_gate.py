"""Offline CloudFormation template and simplified change evidence gate.
Not an AWS-native describe-change-set JSON parser.
"""
import json
import sys
from pathlib import Path

FLAGS = ("require_ticket", "deny_prod_targets", "require_iam_review", "require_dbre_backup", "require_rollback", "deny_destructive_actions")
ALLOWED_RESOURCE_TYPES = {"AWS::CloudFormation::WaitConditionHandle"}

def validate(template, manifest, policy):
    if not all(isinstance(v, dict) for v in (template, manifest, policy)):
        return ["documents must be objects"]
    errors = []
    if template.get("AWSTemplateFormatVersion") != "2010-09-09":
        errors.append("invalid template version")
    resources = template.get("Resources")
    if not isinstance(resources, dict) or not resources:
        errors.append("resources missing")
    else:
        for name, resource in resources.items():
            if not isinstance(resource, dict) or resource.get("Type") not in ALLOWED_RESOURCE_TYPES:
                errors.append("resource not allowed: " + str(name))
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
    if manifest.get("account") != "offline":
        errors.append("account denied")
    if manifest.get("region") != "us-east-1":
        errors.append("region denied")
    if manifest.get("stack") != "chapter066-offline":
        errors.append("stack denied")
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
    if len(sys.argv) != 4:
        print("Usage: template_gate.py template.json change-evidence.json policy.json")
        return 1
    try:
        template, manifest, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
        errors = validate(template, manifest, policy)
    except (OSError, ValueError) as exc:
        print("INVALID:", type(exc).__name__)
        return 1
    for error in errors:
        print("REJECT:", error)
    if errors:
        return 1
    print("PASS: offline CloudFormation template and declared change controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
