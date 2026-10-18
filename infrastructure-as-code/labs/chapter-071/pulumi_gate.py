"""Offline Pulumi source-marker and declared evidence gate; not a Pulumi state/API parser."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FLAGS = ("require_ticket", "deny_prod_targets", "require_stack_identity", "require_preview", "require_backup", "require_dbre_approval")
STATIC = {
    "Pulumi.yaml": ("name: iac-ch071-pulumi", "name: python"),
    "__main__.py": ("import pulumi", "import pulumi_command as command", "command.local.Command(", "if environment not in", "pulumi.export("),
    "requirements.txt": ("pulumi>=", "pulumi-command>="),
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
                    errors.append("missing Pulumi contract " + path + ":" + token)
        except OSError:
            errors.append("missing Pulumi file " + path)
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
    for key, expected in (("backend", "file://local-lab"), ("project", "iac-ch071-pulumi"), ("stack", "dev"), ("account", "offline-local")):
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
    if labels.get("environment") != env or labels.get("owner") != manifest.get("owner") or labels.get("managed-by") != "pulumi":
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
        print("Usage: pulumi_gate.py evidence.json policy.json")
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
    print("PASS: offline Pulumi static contract and declared governance")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
