"""Offline self-declared capstone readiness; not native policy or cloud evidence."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"lab","aws_account":"offline","azure_subscription":"offline","gcp_project":"offline","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","source_commit":"0123456789abcdef","oidc_subject":"repo:sssamant21/platform-engineering-tutorials:ref:refs/heads/main"}
CONTROLS=["signed_source","protected_branch","codeowners_reviewed","oidc_exact_issuer","oidc_exact_audience","oidc_exact_subject","short_lived_identity","no_static_cloud_keys","aws_iam_scoped","azure_rbac_scoped","gcp_wif_scoped","cloud_org_guardrails","k8s_namespace_rbac","k8s_admission_enforced","gitops_controller_scoped","network_policy_enforced","secrets_manager_used","no_exposed_secrets","scanner_database_fresh","iac_scan_passed","dependency_scan_passed","sbom_verified","provenance_verified","artifact_digest_verified","provider_lockfile_verified","opa_policy_enforced","sentinel_policy_verified","state_encrypted","state_versioned","state_locked","state_access_scoped","kms_recovery_verified","security_approved","sre_approved","dbre_approved","backup_isolated","restore_rehearsed","slo_healthy","audit_immutable","exception_expiry_verified"]
BASELINE={"max_critical_findings":0,"max_exposed_secrets":0,"max_destroy":0,"max_replace":0,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['invalid documents']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in BASELINE.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k in ('critical_findings','exposed_secrets','destroy_count','replace_count'):
        if type(e.get(k)) is not int or e[k]!=0:errors.append(k+' prohibited')
    for k,limit in (('measured_rpo_minutes',15),('measured_rto_minutes',60)):
        if type(e.get(k)) not in (int,float) or isinstance(e.get(k),bool) or not 0<=e[k]<=limit:errors.append(k+' exceeded/invalid')
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
    for error in errors:print('REJECT',error)
    if not errors:print('PASS: offline self-declared readiness only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
