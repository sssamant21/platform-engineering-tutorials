"""Offline multi-cloud static contract and declared evidence gate; NOT cloud API validation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FLAGS = ("require_ticket", "deny_prod_targets", "require_aws_review", "require_azure_review", "require_backup", "require_dbre_approval", "require_slo_gate")
STATIC = {
    "azure/main.bicep": ("targetScope = 'subscription'", "existing = {", "scope: targetRg", "module storage './modules/private-storage.bicep'", "output storageResourceId"),
    "azure/modules/private-storage.bicep": ("targetScope = 'resourceGroup'", "supportsHttpsTrafficOnly: true", "minimumTlsVersion: 'TLS1_2'", "allowBlobPublicAccess: false", "publicNetworkAccess: 'Disabled'"),
    "azure/parameters/lab.bicepparam": ("using '../main.bicep'", "param environment = 'lab'"),
}

def validate(manifest, policy, root=ROOT):
    if not isinstance(manifest, dict) or not isinstance(policy, dict):
        return ["documents must be objects"]
    errors = []
    for path, tokens in STATIC.items():
        try:
            content = (root / path).read_text(encoding="utf-8")
            for token in tokens:
                if token not in content:
                    errors.append("missing Bicep contract " + path + ":" + token)
        except OSError:
            errors.append("missing Bicep file " + path)
    try:
        parent = json.loads((root / "aws/parent-template.json").read_text(encoding="utf-8"))
        child = json.loads((root / "aws/child-template.json").read_text(encoding="utf-8"))
        if parent.get("AWSTemplateFormatVersion") != "2010-09-09" or child.get("AWSTemplateFormatVersion") != "2010-09-09":
            errors.append("CloudFormation template version denied")
        nested = parent.get("Resources", {}).get("NestedDemo", {})
        if nested.get("Type") != "AWS::CloudFormation::Stack":
            errors.append("nested-stack resource missing")
        props = nested.get("Properties", {})
        if props.get("TemplateURL") != "https://example.invalid/chapter070/child-template.json":
            errors.append("unapproved child template URL")
        if props.get("Parameters", {}).get("Environment") != {"Ref": "Environment"}:
            errors.append("nested parameter contract denied")
        if child.get("Outputs", {}).get("Environment", {}).get("Value") != {"Ref": "Environment"}:
            errors.append("child output contract denied")
    except (OSError, ValueError, TypeError, AttributeError):
        errors.append("invalid CloudFormation contract")
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
    for key, expected in (("aws_account", "offline-sandbox"), ("aws_region", "us-east-1"), ("azure_tenant", "offline-sandbox"), ("azure_subscription", "offline-sandbox"), ("azure_resource_group", "rg-ch070-lab")):
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
    if labels.get("environment") != env or labels.get("owner") != manifest.get("owner") or labels.get("managed-by") != "native-iac":
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
    if len(sys.argv) != 3:
        print("Usage: multicloud_gate.py evidence.json policy.json")
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
    print("PASS: offline multi-cloud native-IaC contract and declared controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
