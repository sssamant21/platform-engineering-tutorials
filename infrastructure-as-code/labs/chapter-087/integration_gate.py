"""Offline declared integration evidence. No cloud, Terratest, Molecule or DB execution."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"ephemeral-lab","cloud_account":"offline-test-account","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","region":"us-east-1","run_id":"iac087-run-0001","owner":"sre-lab"}
CONTROLS=["source_signed","protected_branch","test_only_oidc","exact_cloud_target","unique_run_id","owner_assigned","lease_active","ttl_bounded","cost_budget_set","resources_tagged","state_isolated","state_encrypted","terraform_plan_reviewed","terratest_passed","molecule_converge_passed","molecule_idempotence_passed","native_resource_assertions","negative_tests_passed","kubernetes_admission_tested","kubernetes_rbac_tested","gitops_reconciliation_tested","database_isolated","backup_verified","restore_rehearsed","kms_access_verified","rpo_accepted","rto_accepted","slo_healthy","cleanup_executed","cleanup_inventory_zero","credentials_revoked","audit_retained"]
LIMITS={"min_native_assertions":5,"min_negative_tests":10,"max_skipped_critical":0,"max_orphaned_resources":0,"max_cost_usd":25,"max_lease_minutes":120,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in LIMITS.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema invalid')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k,minv in (('native_assertions',5),('negative_tests',10)):
        if type(e.get(k)) is not int or e[k]<minv:errors.append(k+' insufficient')
    for k in ('skipped_critical','orphaned_resources'):
        if type(e.get(k)) is not int or e[k]!=0:errors.append(k+' prohibited')
    for k,maxv in (('cost_usd',25),('lease_minutes',120),('rpo_minutes',15),('rto_minutes',60)):
        v=e.get(k)
        if type(v) not in (int,float) or not 0<=v<=maxv:errors.append(k+' exceeded or invalid')
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
    if not errors:print('PASS: synthetic integration evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
