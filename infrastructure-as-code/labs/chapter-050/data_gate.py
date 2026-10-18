"""Fail-closed declared-evidence data/DR policy gate; not live GCP attestation."""
import json,re,sys
from pathlib import Path
ACTIONS={"no-op","read","create","update","delete"}
POSITIVE={
"database":["db_ha","db_pitr","db_backup_enabled","db_restore_tested","db_private_connectivity","db_connection_pool_reviewed","db_replication_reviewed"],
"storage":["storage_public_access_prevention","storage_uniform_access","storage_versioning","storage_retention_reviewed","storage_lifecycle_reviewed","storage_encrypted","storage_recovery_tested"],
"security":["kms_enabled","kms_recovery_tested","kms_service_agent_reviewed","workload_identity","private_dns_reviewed"],
"operations":["monitoring_enabled","audit_logs_enabled","dr_runbook_tested","rpo_rto_measured","dbre_approved","security_approved","change_approved"]}
NEGATIVE={"database":["db_public_ingress"],"security":["static_keys","secret_payload_in_state"]}
REQUIRED=["require_ticket","require_state_isolation","require_ha","require_pitr","require_restore_test","deny_public_db","require_private_db","require_storage_protection","require_kms_recovery","deny_static_keys","deny_secret_payload","require_dr_test","require_rpo_rto_evidence","require_approvals","deny_destructive_actions"]
def validate(m,plan,policy):
    if not all(isinstance(x,dict) for x in (m,plan,policy)):return ["manifest, plan and policy must be objects"]
    errors=[]
    for k in ("allowed_environments","allowed_regions","required_labels","allowed_resource_types"):
        if not isinstance(policy.get(k),list) or not policy[k]:errors.append("invalid policy "+k)
    for k in REQUIRED:
        if policy.get(k) is not True:errors.append("fail-open policy "+k)
    if errors:return errors
    env=m.get("environment");project=m.get("project_id")
    if env not in policy["allowed_environments"]:errors.append("invalid environment")
    if not isinstance(project,str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]",project):errors.append("invalid project ID")
    if m.get("region") not in policy["allowed_regions"]:errors.append("unapproved region")
    for k in ("owner","change_ticket"):
        if not isinstance(m.get(k),str) or not m[k].strip():errors.append("missing "+k)
    if m.get("state_namespace")!="iac-"+str(env)+"-"+str(project)+"-data":errors.append("state isolation mismatch")
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
    if len(argv)!=4:print("Usage: python3 data_gate.py <manifest> <plan> <policy>");return 1
    try:
        m,p,policy=[json.loads(Path(x).read_text(encoding="utf-8")) for x in argv[1:]]
        errors=validate(m,p,policy)
    except (OSError,ValueError) as exc:print("DENY:",type(exc).__name__);return 1
    for e in errors:print("DENY:",e)
    if errors:return 1
    print("PASS: declared GCP data protection and plan policy")
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))
