"""Fail-closed declared AWS stateful-data policy. Not live AWS evidence."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for key in ("allowed_environments","allowed_regions","allowed_database_engines","required_tags","allowed_resource_types"):
        if not isinstance(policy.get(key),list) or not policy[key]:errors.append("invalid policy "+key)
    for key in ("require_ticket","require_state_isolation","require_multi_az","require_database_encryption","require_deletion_protection","require_pitr","require_restorable_backups","require_s3_versioning","require_s3_encryption","deny_public_s3","require_volume_encryption","require_cross_region_dr","require_kms_recovery","require_dr_drill","require_audit","deny_destructive_actions"):
        if policy.get(key) is not True:errors.append("fail-open policy "+key)
    if errors:return errors
    env=m.get("environment")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    account=m.get("aws_account_id")
    if not isinstance(account,str) or not re.fullmatch(r"[0-9]{12}",account):errors.append("invalid AWS account ID")
    primary=m.get("primary_region");dr=m.get("dr_region")
    if primary not in policy["allowed_regions"]:errors.append("unapproved primary region")
    if dr not in policy["allowed_regions"] or dr==primary:errors.append("invalid DR region")
    for key in ("owner","change_ticket"):
        if not isinstance(m.get(key),str) or not m[key].strip():errors.append("missing "+key)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(account)+"-stateful":errors.append("state isolation mismatch")
    db=m.get("database")
    if not isinstance(db,dict):db={}
    if db.get("engine") not in policy["allowed_database_engines"]:errors.append("unapproved database engine")
    for key in ("multi_az","encrypted","deletion_protection","pitr_enabled","private_subnets","backup_restore_tested"):
        if db.get(key) is not True:errors.append("missing database control "+key)
    retention=db.get("backup_retention_days")
    if type(retention) is not int or not 7<=retention<=35:errors.append("database backup retention must be 7-35 days")
    s3=m.get("s3")
    if not isinstance(s3,dict):s3={}
    for key in ("versioning","encrypted","public_access_blocked","lifecycle_reviewed","restore_tested"):
        if s3.get(key) is not True:errors.append("missing S3 control "+key)
    volumes=m.get("volumes")
    if not isinstance(volumes,dict):volumes={}
    for key in ("ebs_encrypted","efs_encrypted","ebs_snapshot_tested","efs_restore_tested"):
        if volumes.get(key) is not True:errors.append("missing volume control "+key)
    recovery=m.get("recovery")
    if not isinstance(recovery,dict):recovery={}
    for key,low,high in (("rpo_minutes",0,1440),("rto_minutes",1,1440)):
        v=recovery.get(key)
        if type(v) is not int or not low<=v<=high:errors.append("invalid recovery objective "+key)
    for key in ("cross_region_backup","writer_fencing_tested","kms_decrypt_tested","dr_drill_passed"):
        if recovery.get(key) is not True:errors.append("missing recovery control "+key)
    audit=m.get("audit")
    if not isinstance(audit,dict):audit={}
    for key in ("cloudwatch_enabled","cloudtrail_enabled","security_reviewed","dbre_approved"):
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
    if len(argv)!=4:print("Usage: python3 stateful_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for error in errors:print("DENY:",error)
    if errors:return 1
    print("PASS: declared stateful data and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
