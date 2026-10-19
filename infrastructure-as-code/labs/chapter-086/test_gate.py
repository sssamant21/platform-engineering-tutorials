"""Offline self-declared IaC testing evidence gate, NOT native tool execution."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"lab","repository":"sssamant21/platform-engineering-tutorials","cloud_account":"offline","kube_context":"offline-kind","source_commit":"0123456789abcdef","policy_version":"v1"}
CONTROLS=["source_signed","protected_branch","toolchain_pinned","provider_lockfile_verified","format_passed","syntax_passed","static_scan_passed","secrets_scan_passed","unit_tests_passed","negative_tests_passed","policy_tests_passed","policy_enforced","plan_reviewed","no_destructive_actions","target_verified","artifact_digest_verified","identity_scoped","state_locked","state_encrypted","integration_tests_passed","ephemeral_isolation","cleanup_verified","kubernetes_rbac_tested","admission_tested","gitops_reconciliation_tested","dbre_approved","backup_verified","restore_rehearsed","slo_healthy","audit_retained"]
BASELINE={"min_unit_tests":20,"min_negative_tests":10,"max_skipped_critical":0,"max_destroy":0,"max_replace":0,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['invalid documents']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in BASELINE.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k,minimum in (('unit_tests',20),('negative_tests',10)):
        if type(e.get(k)) is not int or e[k]<minimum:errors.append(k+' below minimum')
    for k in ('skipped_critical','destroy_count','replace_count'):
        if type(e.get(k)) is not int or e[k]!=0:errors.append(k+' prohibited')
    for k,limit in (('measured_rpo_minutes',15),('measured_rto_minutes',60)):
        v=e.get(k)
        if type(v) not in (int,float) or isinstance(v,bool) or not 0<=v<=limit:errors.append(k+' exceeded/invalid')
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
    if not errors:print('PASS: synthetic test evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
