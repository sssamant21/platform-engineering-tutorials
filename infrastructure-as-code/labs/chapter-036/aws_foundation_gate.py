"""Fail-closed offline AWS foundation manifest and Terraform plan validator."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for k in ("allowed_environments","allowed_regions","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(k),list) or not policy[k]:errors.append("invalid policy "+k)
    for k in ("require_ticket","require_short_lived_identity","require_oidc","require_least_privilege","require_encrypted_versioned_locked_state","require_state_isolation","deny_destructive_actions"):
        if policy.get(k) is not True:errors.append("fail-open policy "+k)
    if errors:return errors
    env=m.get("environment")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    account=m.get("aws_account_id")
    if not isinstance(account,str) or not re.fullmatch(r"[0-9]{12}",account):errors.append("invalid AWS account ID")
    primary=m.get("primary_region");dr=m.get("dr_region")
    if primary not in policy["allowed_regions"]:errors.append("unapproved primary region")
    if dr not in policy["allowed_regions"] or dr==primary:errors.append("unapproved or identical DR region")
    for k in ("owner","cost_center","change_ticket"):
        if not isinstance(m.get(k),str) or not m[k].strip():errors.append("missing "+k)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(account):errors.append("state namespace mismatch")
    tags=m.get("tags")
    if not isinstance(tags,dict):tags={}
    for k in policy["required_tags"]:
        if not isinstance(tags.get(k),str) or not tags[k].strip():errors.append("missing tag "+k)
    if tags.get("Environment")!=env or tags.get("Owner")!=m.get("owner") or tags.get("CostCenter")!=m.get("cost_center") or tags.get("ManagedBy")!="terraform":errors.append("tag/identity mismatch")
    identity=m.get("identity")
    if not isinstance(identity,dict):identity={}
    for k in ("short_lived_credentials","oidc_federation","least_privilege_reviewed"):
        if identity.get(k) is not True:errors.append("missing identity control "+k)
    backend=m.get("backend")
    if not isinstance(backend,dict):backend={}
    if backend.get("type")!="s3":errors.append("unapproved backend")
    for k in ("encrypted","versioning","lockfile","public_access_blocked"):
        if backend.get(k) is not True:errors.append("missing backend control "+k)
    db=m.get("database")
    if not isinstance(db,dict):errors.append("database controls missing")
    elif env=="prod":
        if type(db.get("replicas")) is not int or db["replicas"]<3:errors.append("production replicas below three")
        for k in ("backup_enabled","encryption_enabled","multi_az_enabled"):
            if db.get(k) is not True:errors.append("missing production database control "+k)
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
    if len(argv)!=4:print("Usage: python3 aws_foundation_gate.py <foundation> <plan> <policy>");return 1
    try:
        m,plan,policy=[json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors=validate(m,plan,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared AWS foundation and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
