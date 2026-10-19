"""Offline self-declared compliance claims; NOT external audit certification."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-compliance-lab","repository":"sssamant21/platform-engineering-tutorials","cloud_account":"offline","kube_context":"offline-kind","source_commit":"0123456789abcdef","audit_period":"2026-Q4"}
IDS=["IAC-001","IAC-002","IAC-003","IAC-004","IAC-005","IAC-006","IAC-007","IAC-008"]
CONTROLS=["source_approved","protected_branch","artifact_digest_verified","oidc_scoped","cloud_iam_least_privilege","state_encrypted","state_versioned","secrets_scanned","opa_enforced","sentinel_enforced","cloud_org_policy_enforced","kubernetes_admission_enforced","gitops_scoped","audit_logs_enabled","audit_retention_verified","evidence_immutable","evidence_hashes_verified","sbom_verified","provenance_verified","scanner_fresh","policy_bundle_pinned","exception_owner_verified","exception_approver_independent","exception_expiry_verified","backup_encrypted","restore_rehearsed","kms_decrypt_verified","rpo_accepted","rto_accepted","slo_healthy","dbre_approved","security_approved"]
LIMITS={"max_critical_findings":0,"max_exception_age_days":30,"max_evidence_age_hours":24,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['invalid documents']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_control_ids')!=IDS or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in LIMITS.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('artifact digest invalid')
    if e.get('control_ids')!=IDS:errors.append('control IDs mismatch')
    if type(e.get('critical_findings')) is not int or e['critical_findings']!=0:errors.append('critical findings')
    for k,limit in (('exception_age_days',30),('evidence_age_hours',24),('rpo_minutes',15),('rto_minutes',60)):
        v=e.get(k)
        if type(v) not in (int,float) or not 0<=v<=limit:errors.append(k+' exceeded or invalid')
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
    if not errors:print('PASS: synthetic compliance claims only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
