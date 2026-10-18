"""Fail-closed declared-evidence Kubernetes tenant policy; not live cluster attestation."""
import json,re,sys
from pathlib import Path
POSITIVE={
"namespace":["namespace_owner_verified","quota_enabled","limitrange_enabled","psa_restricted","namespace_deletion_protected"],
"rbac":["dedicated_service_accounts","rbac_least_privilege","rbac_scoped_rolebindings","effective_permissions_tested","token_automount_disabled"],
"network":["default_deny_ingress","default_deny_egress","dns_egress_explicit","database_egress_scoped","cni_enforcement_tested"],
"operations":["audit_logs_enabled","monitoring_enabled","tenant_cost_labels","backup_reviewed","dbre_approved","security_approved","change_approved"]}
NEGATIVE={"rbac":["wildcard_cluster_admin","default_service_account_used"],"network":["broad_egress"],"operations":["unapproved_destroy"]}
REQUIRED=["require_ticket","require_state_isolation","require_namespace_governance","require_quota","require_psa","require_rbac","deny_cluster_admin","deny_default_sa","require_default_deny","require_dns_egress","deny_broad_egress","require_db_review","require_audit","require_approvals","deny_destructive_actions"]
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for k in ("allowed_environments","required_labels","allowed_resource_types"):
        if not isinstance(policy.get(k),list) or not policy[k]:errors.append("invalid policy "+k)
    for k in REQUIRED:
        if policy.get(k) is not True:errors.append("fail-open policy "+k)
    if errors:return errors
    env=m.get("environment");cluster=m.get("cluster_name");ns=m.get("namespace")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    for k in ("cluster_name","namespace","owner","change_ticket"):
        if not isinstance(m.get(k),str) or not m[k].strip():errors.append("missing "+k)
    for k,val in (("cluster_name",cluster),("namespace",ns)):
        if not isinstance(val,str) or not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?",val):errors.append("invalid "+k)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(cluster)+"-"+str(ns):errors.append("state isolation mismatch")
    for section,keys in POSITIVE.items():
        obj=m.get(section)
        if not isinstance(obj,dict):obj={}
        for k in keys:
            if obj.get(k) is not True:errors.append("missing "+section+" control "+k)
        for k in NEGATIVE.get(section,[]):
            if obj.get(k) is not False:errors.append("forbidden "+section+" control "+k)
    labels=m.get("labels")
    if not isinstance(labels,dict):labels={}
    for k in policy["required_labels"]:
        if not isinstance(labels.get(k),str) or not labels[k].strip():errors.append("missing label "+k)
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
    if len(argv)!=4:print("Usage: python3 tenant_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared Kubernetes tenancy and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
