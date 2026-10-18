"""Fail-closed declared-evidence Terragrunt DAG and CI policy; not a native plan adapter."""
import json
import sys
from pathlib import Path

CONTROLS = {
    "graph": ["graph_acyclic", "output_contracts_reviewed", "upstream_state_verified", "mock_outputs_disabled_prod", "failure_domains_separated", "bounded_parallelism", "graph_reviewed"],
    "state": ["backend_keys_unique", "backend_encrypted", "backend_lock_verified", "state_backup_verified", "restore_tested", "account_region_isolated"],
    "cicd": ["toolchain_pinned", "module_revisions_pinned", "oidc_short_lived", "plan_artifact_reviewed", "native_plan_adapter_reviewed", "environment_approval_required"],
    "operations": ["policy_gate_enabled", "drift_reviewed", "slo_monitored", "dbre_approved", "security_approved", "change_approved"],
}
FORBIDDEN = {"state": ["concurrent_writers"], "cicd": ["untrusted_pr_prod_access"], "operations": ["unapproved_destroy"]}
REQUIRED_POLICY = ["require_ticket", "require_state_isolation", "require_backend_encryption", "require_backend_key_uniqueness", "require_locking", "require_state_backup", "require_restore_test", "require_exclusive_writer", "require_toolchain_pins", "require_module_pinning", "require_acyclic_graph", "require_dependency_outputs", "require_bounded_parallelism", "deny_prod_mock_outputs", "require_oidc", "require_plan_approval", "require_dbre_security_approval", "deny_destructive_actions"]

def validate(manifest, plan, policy):
    if not all(isinstance(v, dict) for v in (manifest, plan, policy)):
        return ["documents must be objects"]
    issues = []
    for key in REQUIRED_POLICY:
        if policy.get(key) is not True:
            issues.append("policy missing " + key)
    for key in ("allowed_environments", "required_labels", "allowed_resource_types"):
        if not isinstance(policy.get(key), list) or not policy[key]:
            issues.append("policy list missing " + key)
    if issues:
        return issues
    env = manifest.get("environment")
    if env not in policy["allowed_environments"]:
        issues.append("invalid environment")
    for key in ("root_name", "backend_key", "owner", "change_ticket"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            issues.append("missing " + key)
    if manifest.get("state_namespace") != "iac-" + str(env) + "-" + str(manifest.get("root_name")):
        issues.append("state isolation")
    backend = manifest.get("backend_key")
    if not isinstance(backend, str) or not backend.startswith("iac/" + str(env) + "/") or ".." in backend:
        issues.append("backend key")
    labels = manifest.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    for key in policy["required_labels"]:
        if not isinstance(labels.get(key), str) or not labels[key].strip():
            issues.append("missing label " + key)
    if labels.get("environment") != env or labels.get("owner") != manifest.get("owner") or labels.get("managed-by") != "terragrunt":
        issues.append("label identity")
    for section, keys in CONTROLS.items():
        evidence = manifest.get(section)
        if not isinstance(evidence, dict):
            evidence = {}
        for key in keys:
            if evidence.get(key) is not True:
                issues.append("missing " + section + "." + key)
        for key in FORBIDDEN.get(section, []):
            if evidence.get(key) is not False:
                issues.append("forbidden " + section + "." + key)
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return issues + ["missing resource_changes"]
    for i, item in enumerate(changes):
        if not isinstance(item, dict):
            issues.append("invalid change " + str(i))
            continue
        if item.get("type") not in policy["allowed_resource_types"]:
            issues.append("resource type " + str(i))
        if not isinstance(item.get("address"), str) or not item["address"]:
            issues.append("resource address " + str(i))
        change = item.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(actions, list) or not actions or any(type(a) is not str or a not in ("no-op", "read", "create", "update", "delete") for a in actions):
            issues.append("invalid actions " + str(i))
        elif "delete" in actions:
            issues.append("destructive action " + str(i))
    return issues

def main():
    if len(sys.argv) != 4:
        print("Usage: orchestration_gate.py manifest plan policy")
        return 1
    try:
        manifest, plan, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
        issues = validate(manifest, plan, policy)
    except (OSError, ValueError) as exc:
        print("INVALID:", type(exc).__name__)
        return 1
    for issue in issues:
        print("REJECT:", issue)
    if issues:
        return 1
    print("PASS: declared DAG/state/CI orchestration controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
