"""Offline declared-evidence policy, not cloud/provider or signature verification."""
import json,re,sys
from pathlib import Path
TARGETS={"environment":"lab","aws_account":"offline-sandbox","azure_subscription":"offline-sandbox","gcp_project":"offline-sandbox","kube_context":"offline-kind","ansible_inventory":"localhost","pulumi_stack":"dev","terraform_workspace":"lab","gitops_branch":"release/lab"}
CONTROLS=["source_signed","codeowners_reviewed","toolchain_pinned","sbom_reviewed","oidc_scoped","least_privilege","targets_verified","backend_encrypted","backend_versioned","state_lock_verified","preview_reviewed","artifact_digest_verified","policy_enforced","no_destroy","no_stateful_replacement","security_approved","sre_approved","dbre_approved","backup_verified","restore_rehearsed","rpo_rto_defined","quorum_reviewed","fencing_reviewed","gitops_ownership_verified","canary_approved","slo_healthy","audit_immutable","finops_reviewed"]
TOOLS=["terraform","opentofu","pulumi","cloudformation","bicep","ansible","kubernetes","argocd","flux"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents must be objects']
    if p.get('schema_version')!=1 or p.get('targets')!=TARGETS or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or p.get('allowed_tools')!=TOOLS:
        return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema invalid')
    for key,value in TARGETS.items():
        if e.get(key)!=value:errors.append('target mismatch: '+key)
    if e.get('tools')!=TOOLS:errors.append('tool scope mismatch')
    for key in ('owner','source_commit'):
        if not isinstance(e.get(key),str) or not e[key].strip():errors.append(key+' missing')
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('artifact digest invalid')
    controls=e.get('controls')
    if not isinstance(controls,dict):controls={}
    if set(controls)!=set(CONTROLS):errors.append('control set mismatch')
    for key in CONTROLS:
        if controls.get(key) is not True:errors.append('missing control: '+key)
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as exc:
        print('INVALID',type(exc).__name__);return 2
    errors=validate(e,p)
    for error in errors:print('REJECT',error)
    if not errors:print('PASS: offline declared enterprise CI/CD evidence')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
