"""Fail-closed GCP security declared-evidence gate, not live GCP compliance attestation."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_regions","required_labels","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_least_privilege","deny_primitive_roles","require_org_policy","require_wif","deny_static_keys","require_specific_oidc_trust","require_kms_recovery","deny_unapproved_key_destruction","require_secret_metadata_only","deny_secret_payload_in_state","require_secure_state","require_audit","require_security_approval","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment");project=m.get("project_id");number=m.get("project_number")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(project,str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]",project):errors.append("invalid project ID")
    if not isinstance(number,str) or not re.fullmatch(r"[0-9]{6,15}",number):errors.append("invalid project number")
    if m.get("region") not in policy["allowed_regions"]:errors.append("unapproved region")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(project)+"-security":errors.append("state isolation mismatch")
    checks={
      "iam":(["least_privilege","iam_deny_reviewed","org_policy_reviewed","break_glass_tested","service_agent_access_reviewed"],["primitive_roles_used"]),
      "identity":(["wif_enabled","impersonation_scoped","gke_workload_identity_reviewed"],["static_service_account_keys"]),
      "kms":(["enabled","rotation_reviewed","recovery_tested","service_agent_grants_reviewed"],["key_version_destruction_approved"]),
      "secrets":(["metadata_only","rotation_owner_assigned","secret_accessor_least_privilege","version_recovery_tested"],["payload_in_state"]),
      "state":(["private","public_access_prevention","versioned","encrypted","locking","environment_isolated"],[]),
      "audit":(["logs_enabled","security_monitoring_enabled","security_approved","dbre_approved","change_approved"],[])
    }
    for section,(true_keys,false_keys) in checks.items():
        obj=m.get(section)
        if not isinstance(obj,dict):obj={}
        for key in true_keys:
            if obj.get(key) is not True:errors.append("missing "+section+" control "+key)
        for key in false_keys:
            if obj.get(key) is not False:errors.append("forbidden "+section+" control "+key)
    ident=m.get("identity")
    if not isinstance(ident,dict):ident={}
    if ident.get("oidc_issuer")!="https://token.actions.githubusercontent.com":errors.append("unapproved OIDC issuer")
    if ident.get("oidc_audience")!="https://iam.googleapis.com/projects/"+str(number)+"/locations/global/workloadIdentityPools/ci/providers/github":errors.append("OIDC audience mismatch")
    if ident.get("oidc_subject")!="repo:example-org/platform-infra:environment:"+str(env):errors.append("OIDC subject mismatch")
    labels=m.get("labels")
    if not isinstance(labels,dict):labels={}
    for key in policy["required_labels"]:
        if not isinstance(labels.get(key),str) or not labels[key].strip():errors.append("missing label "+key)
    if labels.get("environment")!=env or labels.get("owner")!=m.get("owner") or labels.get("managed-by")!="terraform":errors.append("label identity mismatch")
    changes=plan.get("resource_changes")
    if not isinstance(changes,list):return errors+["plan resource_changes must be list"]
    for i,r in enumerate(changes):
        if not isinstance(r,dict):errors.append("invalid resource change "+str(i));continue
        if r.get("type") not in policy["allowed_resource_types"]:errors.append("unapproved resource type "+str(i))
        if not isinstance(r.get("address"),str) or not r["address"]:errors.append("missing address "+str(i))
        change=r.get("change");actions=change.get("actions") if isinstance(change,dict) else None
        if not isinstance(actions,list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):errors.append("invalid actions "+str(i))
        elif "delete" in actions:errors.append("delete/replacement denied "+str(i))
    return errors
def main(argv):
    if len(argv)!=4:print("Usage: python3 security_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared GCP security and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
