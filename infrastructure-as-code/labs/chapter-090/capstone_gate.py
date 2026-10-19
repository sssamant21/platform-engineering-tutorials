"""Synthetic claims only; no native IaC, cloud, Kubernetes or DBRE execution."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-capstone-lab","cloud_account":"offline","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","source_commit":"0123456789abcdef","run_id":"iac090-run-0001","owner":"sre-dbre-lab"}
CONTROLS=["source_approved","protected_branch","immutable_artifact","exact_target","oidc_scoped","state_encrypted","state_isolated","secrets_scanned","sbom_verified","provenance_verified","terraform_validated","opentofu_validated","terratest_passed","molecule_converge_passed","molecule_idempotence_passed","pulumi_preview_reviewed","cloudformation_changeset_reviewed","bicep_whatif_reviewed","opa_enforced","sentinel_enforced","negative_tests_passed","aws_policy_checked","azure_policy_checked","gcp_policy_checked","kubernetes_admission_enforced","kubernetes_rbac_checked","gitops_revision_verified","drift_observation_fresh","drift_remediation_approved","no_auto_destroy","exception_independently_approved","audit_logs_enabled","evidence_chain_verified","retention_verified","backup_encrypted","restore_rehearsed","kms_decrypt_verified","rpo_accepted","rto_accepted","slo_healthy"]
LIMITS={"min_native_assertions":5,"min_negative_tests":10,"max_skipped_critical":0,"max_critical_findings":0,"max_orphaned_resources":0,"max_evidence_age_hours":24,"max_cost_usd":25,"max_lease_minutes":120,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in LIMITS.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k,limit in LIMITS.items():
        if not k.startswith('max_'):continue
        field=k[4:];v=e.get(field)
        if type(v) not in (int,float) or not 0<=v<=limit:errors.append(field+' invalid or exceeds limit')
    for k,limit in (('native_assertions',5),('negative_tests',10)):
        v=e.get(k)
        if type(v) is not int or v<limit:errors.append(k+' insufficient')
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
    if not errors:print('PASS: synthetic capstone claims only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
