"""Offline declared-evidence Ansible/Kubernetes/GitOps gate, not native verification."""
import json,re,sys
from pathlib import Path
TARGETS={"environment":"lab","inventory":"localhost","kube_context":"offline-kind","namespace":"iac-lab","gitops_controller":"argocd","promotion_branch":"release/lab"}
CONTROLS=["signed_source","pinned_collections","immutable_image_digest","oidc_scoped","least_privilege","inventory_verified","kube_context_verified","namespace_verified","gitops_owner_verified","no_direct_patch","ansible_check_reviewed","k8s_diff_reviewed","policy_approved","approval_signed","backup_verified","restore_rehearsed","dbre_approved","serial_rollout_bounded","pdb_reviewed","no_destructive_prune","canary_healthy","slo_healthy","audit_recorded"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents must be objects']
    if p.get('schema_version')!=1 or p.get('targets')!=TARGETS or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True:
        return ['policy baseline invalid']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGETS.items():
        if e.get(k)!=v:errors.append('target mismatch: '+k)
    for k in ('owner','change_ticket'):
        if not isinstance(e.get(k),str) or not e[k].strip():errors.append('missing '+k)
    if not isinstance(e.get('change_ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['change_ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('image_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['image_digest']):errors.append('image digest invalid')
    c=e.get('controls')
    if not isinstance(c,dict):c={}
    if set(c)!=set(CONTROLS):errors.append('control keys mismatch')
    for k in CONTROLS:
        if c.get(k) is not True:errors.append('missing control: '+k)
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError):return 2
    errors=validate(e,p)
    for err in errors:print('REJECT:',err)
    if not errors:print('PASS: offline declared GitOps governance')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
