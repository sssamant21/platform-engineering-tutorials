"""Fail-closed GCP foundation declared-evidence gate; not a live cloud attestation."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_regions","required_labels","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_project_isolation","require_billing_review","require_org_policy","require_apis","require_quota_review","require_wif","deny_static_keys","require_least_privilege","require_secure_state","require_audit","require_budgets","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment");project=m.get("project_id");number=m.get("project_number")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(project,str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]",project):errors.append("invalid project ID")
    if not isinstance(number,str) or not re.fullmatch(r"[0-9]{6,15}",number):errors.append("invalid project number")
    if m.get("region") not in policy["allowed_regions"]:errors.append("unapproved region")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(project)+"-foundation":errors.append("state isolation mismatch")
    proj=m.get("project")
    if not isinstance(proj,dict):proj={}
    for key in ("billing_reviewed","org_policy_reviewed","service_apis_reviewed","quota_reviewed","api_enablement_approved","environment_isolated"):
        if proj.get(key) is not True:errors.append("missing project control "+key)
    ident=m.get("identity")
    if not isinstance(ident,dict):ident={}
    for key in ("wif_enabled","least_privilege_reviewed","service_account_impersonation_reviewed"):
        if ident.get(key) is not True:errors.append("missing identity control "+key)
    if ident.get("static_service_account_key_used") is not False:errors.append("static service account key forbidden")
    if ident.get("oidc_issuer")!="https://token.actions.githubusercontent.com":errors.append("unapproved OIDC issuer")
    if ident.get("oidc_audience")!="https://iam.googleapis.com/projects/"+str(number)+"/locations/global/workloadIdentityPools/ci/providers/github":errors.append("OIDC audience mismatch")
    if ident.get("oidc_subject")!=("repo:example-org/platform-infra:environment:"+str(env)):errors.append("OIDC subject mismatch")
    state=m.get("state")
    if not isinstance(state,dict):state={}
    for key in ("private","uniform_bucket_access","public_access_prevention","versioning","encrypted","locking","environment_isolated"):
        if state.get(key) is not True:errors.append("missing state control "+key)
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("cloud_audit_logs_enabled","monitoring_enabled","budget_alerts_enabled","security_approved","dbre_approved"):
        if audit.get(key) is not True:errors.append("missing audit control "+key)
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
    if len(argv)!=4:print("Usage: python3 gcp_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared GCP foundation and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
