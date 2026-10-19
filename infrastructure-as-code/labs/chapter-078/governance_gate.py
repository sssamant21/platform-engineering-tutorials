"""Offline self-declared governance checks; NOT native cloud attestations."""
import json,re,sys
from pathlib import Path
TOOLS=('pulumi','cloudformation','bicep')
TARGETS={'pulumi':'offline-dev-stack','cloudformation':'offline-aws-stack','bicep':'offline-azure-subscription'}
CONTROLS=["signed_source","pinned_toolchain","oidc_scoped","least_privilege","preview_reviewed","policy_enforced","approval_signed","preview_digest_verified","commit_binding_verified","target_binding_verified","no_destroy","no_stateful_replacement","state_backup_verified","db_backup_verified","restore_rehearsed","dbre_approved","canary_approved","slo_healthy","audit_enabled","gitops_ownership_reviewed"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents must be objects']
    if p.get('schema_version')!=1 or p.get('allowed_environment')!='lab' or p.get('required_tools')!=list(TOOLS) or p.get('targets')!=TARGETS or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True:
        return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema invalid')
    if e.get('environment')!='lab':errors.append('environment denied')
    if e.get('tools')!=list(TOOLS):errors.append('tool list mismatch')
    if e.get('targets')!=TARGETS:errors.append('tool target mismatch')
    for key in ('commit','owner','ticket'):
        if not isinstance(e.get(key),str) or not e[key].strip():errors.append(key+' missing')
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('preview_digest'),str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',e['preview_digest']):errors.append('preview digest invalid')
    actual=e.get('controls')
    if not isinstance(actual,dict):actual={}
    if set(actual)!=set(CONTROLS):errors.append('control keys mismatch')
    for key in CONTROLS:
        if actual.get(key) is not True:errors.append('missing control '+key)
    return errors
def main():
    if len(sys.argv)!=3:
        print('usage: governance_gate.py evidence.json policy.json');return 2
    try:e,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as exc:
        print('ERROR',type(exc).__name__);return 2
    errors=validate(e,p)
    for err in errors:print('REJECT',err)
    if not errors:print('PASS: offline declared multi-tool CI/CD evidence')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
