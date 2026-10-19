"""Offline declared security evidence only; no scanners or signatures verified."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"lab","repository":"sssamant21/platform-engineering-tutorials","branch":"main","cloud_account":"offline","kube_context":"offline-kind","scanner_policy_version":"v1"}
CONTROLS=["source_signed","protected_branch","scanner_version_pinned","scanner_database_fresh","iac_scan_passed","secrets_scan_passed","dependency_scan_passed","container_scan_passed","sbom_generated","sbom_reviewed","provenance_verified","builder_identity_trusted","artifact_digest_verified","provider_lockfile_verified","no_critical_vulnerabilities","no_exposed_secrets","exceptions_reviewed","exceptions_not_expired","state_encrypted","state_access_scoped","cloud_runtime_inventory","drift_detection_enabled","gitops_integrity","oidc_scoped","security_approved","sre_approved","dbre_approved","backup_verified","restore_rehearsed","slo_healthy","audit_retained"]
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or p.get('max_critical_findings')!=0 or p.get('max_exposed_secrets')!=0:return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema invalid')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k in ('critical_findings','exposed_secrets'):
        if type(e.get(k)) is not int or e[k]!=0:errors.append(k+' unresolved')
    c=e.get('controls')
    if not isinstance(c,dict):c={}
    if set(c)!=set(CONTROLS):errors.append('control keys mismatch')
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
    if not errors:print('PASS: offline declared security evidence')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
