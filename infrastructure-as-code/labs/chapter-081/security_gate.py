"""Offline self-declared security controls; no IAM, KMS or signature verification."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"lab","cloud_account":"offline-sandbox","repository":"sssamant21/platform-engineering-tutorials","branch":"main","oidc_issuer":"https://token.actions.githubusercontent.com","oidc_audience":"sts.amazonaws.com","oidc_subject":"repo:sssamant21/platform-engineering-tutorials:ref:refs/heads/main","state_backend":"offline-fixture"}
CONTROLS=["signed_source","protected_branch","codeowners_reviewed","oidc_exact_issuer","oidc_exact_audience","oidc_exact_subject","short_lived_credentials","least_privilege","no_static_cloud_keys","runner_isolated","toolchain_pinned","provider_lockfile","sbom_reviewed","artifact_provenance","state_encrypted","state_versioned","state_access_scoped","state_audit_enabled","kms_key_recoverable","secrets_manager_used","no_plaintext_secrets","secret_rotation_tested","kubernetes_rbac_scoped","gitops_controller_scoped","policy_enforced","security_approved","sre_approved","dbre_approved","backup_isolated","restore_rehearsed","audit_immutable"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents must be objects']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True:return ['policy baseline invalid']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for key,value in TARGET.items():
        if e.get(key)!=value:errors.append('target mismatch: '+key)
    if not isinstance(e.get('change_ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['change_ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('source_commit'),str) or not re.fullmatch(r'[0-9a-f]{16,64}',e['source_commit']):errors.append('source commit invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('artifact digest invalid')
    c=e.get('controls')
    if not isinstance(c,dict):c={}
    if set(c)!=set(CONTROLS):errors.append('control set mismatch')
    for key in CONTROLS:
        if c.get(key) is not True:errors.append('missing control: '+key)
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as exc:
        print('INVALID',type(exc).__name__);return 2
    errors=validate(e,p)
    for err in errors:print('REJECT',err)
    if not errors:print('PASS: offline declared security evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
