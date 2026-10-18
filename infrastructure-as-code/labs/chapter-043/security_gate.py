"""Fail-closed declared Azure identity, RBAC and Key Vault policy gate; not live attestation."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
UUID=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_oidc_issuers","allowed_oidc_audiences","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_oidc","deny_static_secrets","require_managed_identity","require_scoped_rbac","deny_privileged_roles","require_key_vault_private","require_key_vault_rbac","require_purge_protection","require_secret_rotation","deny_plaintext_secret_state","require_cmk_recovery","require_secure_state","require_audit","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment");sub=m.get("subscription_id")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    for key in ("tenant_id","subscription_id"):
        value=m.get(key)
        if not isinstance(value,str) or not re.fullmatch(UUID,value):errors.append("invalid "+key)
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(sub)+"-security":errors.append("state isolation mismatch")
    ident=m.get("identity")
    if not isinstance(ident,dict):ident={}
    if ident.get("oidc_enabled") is not True:errors.append("OIDC required")
    if ident.get("static_client_secret_used") is not False:errors.append("static client secret forbidden")
    if ident.get("oidc_issuer") not in policy["allowed_oidc_issuers"]:errors.append("unapproved OIDC issuer")
    if ident.get("oidc_audience") not in policy["allowed_oidc_audiences"]:errors.append("unapproved OIDC audience")
    subject=ident.get("oidc_subject")
    if not isinstance(subject,str) or not re.fullmatch(r"repo:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:environment:"+str(env),subject):errors.append("unscoped OIDC subject")
    if ident.get("managed_identity_enabled") is not True:errors.append("managed identity required")
    rbac=m.get("rbac")
    if not isinstance(rbac,dict):rbac={}
    for key in ("least_privilege_reviewed","role_assignments_audited"):
        if rbac.get(key) is not True:errors.append("missing RBAC control "+key)
    for key in ("privileged_role_assignment_used","wildcard_scope_used"):
        if rbac.get(key) is not False:errors.append("forbidden RBAC "+key)
    vault=m.get("key_vault")
    if not isinstance(vault,dict):vault={}
    for key in ("rbac_enabled","private_access","purge_protection","soft_delete_enabled","secret_rotation_enabled","diagnostics_enabled","cmk_recovery_tested"):
        if vault.get(key) is not True:errors.append("missing vault control "+key)
    if vault.get("plaintext_secret_in_state") is not False:errors.append("plaintext secret in state forbidden")
    state=m.get("state")
    if not isinstance(state,dict):state={}
    for key in ("encrypted","private","azuread_auth","locking_enabled","versioning_enabled"):
        if state.get(key) is not True:errors.append("missing state control "+key)
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("activity_logs_enabled","security_reviewed","dbre_approved","rotation_drill_passed"):
        if audit.get(key) is not True:errors.append("missing audit control "+key)
    tags=m.get("tags")
    if not isinstance(tags,dict):tags={}
    for key in policy["required_tags"]:
        if not isinstance(tags.get(key),str) or not tags[key].strip():errors.append("missing tag "+key)
    if tags.get("Environment")!=env or tags.get("Owner")!=m.get("owner") or tags.get("ManagedBy")!="terraform":errors.append("tag identity mismatch")
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
    print("PASS: declared Azure identity/RBAC/Key Vault and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
