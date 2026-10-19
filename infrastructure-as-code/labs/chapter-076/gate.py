"""Offline declared-evidence gate; no cloud API or real approval verification."""
import json,sys
from pathlib import Path
STAGES=('lint','unit','security','plan','approval','backup','canary','slo','audit')
REQUIRED=('source_signed','runner_pinned','oidc_scoped','least_privilege','plan_fresh','policy_passed','state_locked','backup_verified','restore_tested','dbre_approved','slo_healthy','audit_recorded','no_destructive_changes')
TARGETS={'environment':'lab','stack':'dev','cloud_account':'offline-sandbox','backend':'local-fixture'}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['evidence and policy must be objects']
    if p.get('required_controls')!=list(REQUIRED) or p.get('stages')!=list(STAGES) or p.get('targets')!=TARGETS:return ['policy baseline mismatch']
    errors=[]
    for k,v in TARGETS.items():
        if e.get(k)!=v:errors.append(k+': incorrect target')
    for k in ('owner','change_ticket','commit_sha','plan_digest'):
        if not isinstance(e.get(k),str) or not e[k].strip():errors.append(k+': missing')
    controls=e.get('controls')
    if not isinstance(controls,dict):controls={}
    for k in REQUIRED:
        if controls.get(k) is not True:errors.append('control '+k+': not verified')
    if e.get('stages')!=list(STAGES):errors.append('stage order or completeness invalid')
    if e.get('change_ticket')=='APPROVED' or e.get('plan_digest')=='unverified':errors.append('placeholder evidence denied')
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(x).read_text()) for x in sys.argv[1:]]
    except (OSError,ValueError):return 2
    errors=validate(e,p)
    for error in errors:print('REJECT:',error)
    if not errors:print('PASS: offline declared IaC delivery evidence')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
