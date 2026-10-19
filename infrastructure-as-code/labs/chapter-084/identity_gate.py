"""Offline self-declared identity evidence gate, not real cloud enforcement."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"lab","aws_account":"offline","azure_subscription":"offline","gcp_project":"offline","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","oidc_issuer":"https://token.actions.githubusercontent.com","oidc_audience":"sts.amazonaws.com","oidc_subject":"repo:sssamant21/platform-engineering-tutorials:ref:refs/heads/main"}
CONTROLS=["signed_source","protected_branch","exact_oidc_issuer","exact_oidc_audience","exact_oidc_subject","short_lived_identity","no_static_cloud_keys","aws_iam_least_privilege","aws_passrole_scoped","aws_permission_boundary","aws_scp_enforced","azure_rbac_scoped","azure_federation_scoped","gcp_wif_scoped","gcp_no_service_account_keys","state_encrypted","state_access_scoped","kms_access_scoped","secrets_manager_used","kubernetes_namespace_rbac","kubernetes_no_cluster_admin","kubernetes_admission_enforced","kubernetes_network_policy","kubernetes_no_privileged_pods","gitops_controller_scoped","ansible_become_scoped","dbre_approved","backup_verified","restore_rehearsed","slo_healthy","audit_immutable","break_glass_timeboxed"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True:return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema invalid')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
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
    if not errors:print('PASS: offline declared identity evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
