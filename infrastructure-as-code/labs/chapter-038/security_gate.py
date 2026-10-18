"""Offline fail-closed AWS identity/KMS/secrets declared-evidence gate.

Does not parse live IAM policies, validate trust against AWS or prove attestations.
"""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):
        return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_oidc_issuers","allowed_oidc_audiences","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_short_lived_credentials","deny_static_access_keys","require_oidc_subject_scope","require_least_privilege","deny_wildcard_admin","require_kms_rotation","require_kms_key_policy_review","deny_unrestricted_decrypt","deny_secret_plaintext_in_state","require_secret_rotation","deny_public_secret_policy","require_cloudtrail","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    account=m.get("aws_account_id")
    if not isinstance(account,str) or not re.fullmatch(r"[0-9]{12}",account):errors.append("invalid AWS account ID")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(account):errors.append("state isolation mismatch")
    ident=m.get("identity")
    if not isinstance(ident,dict):ident={}
    if ident.get("short_lived_credentials") is not True:errors.append("short-lived credentials required")
    if ident.get("static_access_keys") is not False:errors.append("static access keys forbidden")
    if ident.get("oidc_issuer") not in policy["allowed_oidc_issuers"]:errors.append("unapproved OIDC issuer")
    if ident.get("oidc_audience") not in policy["allowed_oidc_audiences"]:errors.append("unapproved OIDC audience")
    subject=ident.get("oidc_subject")
    if not isinstance(subject,str) or not re.fullmatch(r"repo:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:environment:"+str(env),subject):
        errors.append("unscoped OIDC subject")
    if ident.get("least_privilege_reviewed") is not True:errors.append("least privilege review required")
    if ident.get("passrole_restricted") is not True:errors.append("PassRole restrictions required")
    if ident.get("wildcard_admin") is not False:errors.append("wildcard admin forbidden")
    kms=m.get("kms")
    if not isinstance(kms,dict):kms={}
    for key in ("customer_managed","rotation_enabled","key_policy_reviewed"):
        if kms.get(key) is not True:errors.append("missing KMS control "+key)
    days=kms.get("deletion_window_days")
    if type(days) is not int or not (14<=days<=30):errors.append("KMS deletion window must be 14-30 days")
    if kms.get("unrestricted_decrypt") is not False:errors.append("unrestricted KMS decrypt forbidden")
    secrets=m.get("secrets")
    if not isinstance(secrets,dict):secrets={}
    if secrets.get("plaintext_in_state") is not False:errors.append("plaintext secret in state forbidden")
    if secrets.get("rotation_enabled") is not True:errors.append("secret rotation required")
    if secrets.get("resource_policy_public") is not False:errors.append("public secret policy forbidden")
    if secrets.get("runtime_identity_retrieval") is not True:errors.append("runtime secret retrieval required")
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("cloudtrail_enabled","config_enabled","security_reviewed"):
        if audit.get(key) is not True:errors.append("missing audit control "+key)
    tags=m.get("tags")
    if not isinstance(tags,dict):tags={}
    for key in policy["required_tags"]:
        if not isinstance(tags.get(key),str) or not tags[key].strip():errors.append("missing tag "+key)
    if tags.get("Environment")!=env or tags.get("Owner")!=m.get("owner") or tags.get("ManagedBy")!="terraform":errors.append("tag identity mismatch")
    changes=plan.get("resource_changes")
    if not isinstance(changes,list):return errors+["plan resource_changes must be list"]
    for i,resource in enumerate(changes):
        if not isinstance(resource,dict):errors.append("invalid resource change "+str(i));continue
        if resource.get("type") not in policy["allowed_resource_types"]:errors.append("unapproved resource type "+str(i))
        if not isinstance(resource.get("address"),str) or not resource["address"]:errors.append("missing address "+str(i))
        change=resource.get("change")
        actions=change.get("actions") if isinstance(change,dict) else None
        if not isinstance(actions,list) or not actions or any(type(a) is not str or a not in ACTIONS for a in actions):
            errors.append("invalid actions "+str(i))
        elif "delete" in actions:errors.append("delete/replacement denied "+str(i))
    return errors
def main(argv):
    if len(argv)!=4:
        print("Usage: python3 security_gate.py <manifest> <plan> <policy>")
        return 1
    try:
        m,plan,policy=[json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors=validate(m,plan,policy)
    except (OSError,ValueError) as exc:
        print("DENY:",type(exc).__name__)
        return 1
    for error in errors:print("DENY:",error)
    if errors:return 1
    print("PASS: declared AWS IAM/KMS/secrets controls and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
