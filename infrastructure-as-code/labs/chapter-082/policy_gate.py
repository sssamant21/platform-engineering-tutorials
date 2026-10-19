"""Offline policy evidence simulator; NOT OPA/Sentinel or real cloud enforcement."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"lab","aws_account":"offline","azure_subscription":"offline","gcp_project":"offline","kube_context":"offline-kind","policy_version":"v1.0.0"}
CONTROLS=["signed_source","pinned_providers","artifact_verified","oidc_scoped","least_privilege","state_encrypted","state_versioned","state_lock","secrets_redacted","policy_bundle_verified","policy_enforced","cloud_guardrails","k8s_admission","gitops_owner_verified","dbre_approved","backup_verified","restore_rehearsed","slo_healthy","audit_immutable"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['invalid documents']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('max_destroy')!=0 or p.get('max_replace')!=0 or p.get('require_exact_controls') is not True:return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k in ('destroy_count','replace_count'):
        if type(e.get(k)) is not int or e[k]!=0:errors.append(k+' prohibited')
    c=e.get('controls')
    if not isinstance(c,dict):c={}
    if set(c)!=set(CONTROLS):errors.append('control keys mismatch')
    for k in CONTROLS:
        if c.get(k) is not True:errors.append('missing control '+k)
    from exceptions import assess
    errors+=assess(e.get('exceptions'))
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as exc:
        print('INVALID',type(exc).__name__);return 2
    errors=validate(e,p)
    for err in errors:print('REJECT',err)
    if not errors:print('PASS: offline declared policy evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
