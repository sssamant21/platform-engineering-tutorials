"""Fail-closed Azure stateful-data declared-evidence gate, not live Azure attestation."""
import json,re,sys
from pathlib import Path
UUID=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_locations","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_private_data","require_tls","require_ha","require_backup","require_pitr","require_storage_security","require_key_recovery","require_restore_drill","require_monitoring","require_dbre_approval","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    for key in ("max_rpo_minutes","max_rto_minutes"):
        value=policy.get(key)
        if type(value) not in (int,float) or value<=0:errors.append("invalid policy "+key)
    if errors:return errors
    env=m.get("environment");sub=m.get("subscription_id")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(sub,str) or not re.fullmatch(UUID,sub):errors.append("invalid subscription ID")
    if m.get("location") not in policy["allowed_locations"]:errors.append("unapproved location")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(sub)+"-data":errors.append("state isolation mismatch")
    checks={
      "database":(["postgresql_private","postgresql_tls","postgresql_ha","postgresql_pitr","postgresql_backup_retention_reviewed","sql_private","sql_backup_enabled","sql_restore_tested","connection_pool_reviewed"],[]),
      "storage":(["private","versioning","soft_delete","encrypted","shared_keys_disabled","replication_reviewed","restore_tested"],[]),
      "security":(["key_vault_private","purge_protection","cmk_access_reviewed","cmk_recovery_tested","managed_identity_enabled"],["plaintext_secret_in_state"]),
      "recovery":(["backup_enabled","restore_drill_tested","geo_recovery_reviewed","integrity_verified"],[]),
      "audit":(["diagnostics_enabled","alerts_enabled","dbre_approved","security_approved","change_approved"],[])
    }
    for section,(true_keys,false_keys) in checks.items():
        obj=m.get(section)
        if not isinstance(obj,dict):obj={}
        for key in true_keys:
            if obj.get(key) is not True:errors.append("missing "+section+" control "+key)
        for key in false_keys:
            if obj.get(key) is not False:errors.append("forbidden "+section+" control "+key)
    recovery=m.get("recovery")
    if not isinstance(recovery,dict):recovery={}
    for key,limit in (("rpo_minutes",policy["max_rpo_minutes"]),("rto_minutes",policy["max_rto_minutes"])):
        val=recovery.get(key)
        if type(val) not in (int,float) or val<0 or (key=="rto_minutes" and val==0) or val>limit:errors.append("invalid recovery objective "+key)
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
    if len(argv)!=4:print("Usage: python3 data_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared Azure stateful-data and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
