"""Offline self-declared drift assurance; no native cloud access."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-drift-lab","repository":"sssamant21/platform-engineering-tutorials","cloud_account":"offline","kube_context":"offline-kind","source_commit":"0123456789abcdef","policy_version":"v1"}
CONTROLS=["source_approved","protected_branch","artifact_digest_verified","exact_cloud_target","least_privilege_readonly","observation_fresh","inventory_complete","terraform_refresh_reviewed","opentofu_plan_reviewed","pulumi_drift_checked","cloudformation_drift_checked","bicep_whatif_checked","aws_config_enabled","azure_policy_enabled","gcp_org_policy_enabled","kubernetes_admission_enforced","gitops_revision_verified","opa_enforced","sentinel_enforced","audit_logs_enabled","evidence_hash_verified","exceptions_unexpired","exception_approver_independent","no_auto_destroy","dbre_approved","backup_verified","restore_rehearsed","rpo_accepted","rto_accepted","slo_healthy"]
LIMITS={"max_critical_findings":0,"max_observation_age_minutes":15,"max_exception_age_days":30,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in LIMITS.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema invalid')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k,limit in LIMITS.items():
        key=k[4:];v=e.get(key)
        if type(v) not in (int,float) or not 0<=v<=limit:errors.append(key+' exceeded/invalid')
    c=e.get('controls')
    if not isinstance(c,dict):c={}
    if set(c)!=set(CONTROLS):errors.append('control set mismatch')
    for k in CONTROLS:
        if c.get(k) is not True:errors.append('missing control '+k)
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as exc:
        print('INVALID',type(exc).__name__);return 2
    errors=validate(e,p)
    for err in errors:print('REJECT',err)
    if not errors:print('PASS: synthetic drift evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
