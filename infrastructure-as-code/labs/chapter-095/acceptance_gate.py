"""Synthetic capstone evidence gate. NOT production acceptance."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-capstone-lab","cloud_account":"offline","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","source_commit":"0123456789abcdef","owner":"sre-dbre-lab"}
CONTROLS=["source_approved","protected_branch","immutable_plan","target_verified","state_version_preserved","read_only_inventory","inventory_complete","inventory_fresh","aws_audit_healthy","azure_audit_healthy","gcp_audit_healthy","otel_collector_healthy","prometheus_scrape_fresh","metrics_cardinality_bounded","logs_redacted","traces_redacted","gitops_revision_verified","drift_three_way_reviewed","change_ticket_verified","incident_timeline_utc","alternative_causes_reviewed","sli_denominator_valid","error_budget_verified","multi_window_alerts_verified","paging_delivery_verified","incident_commander_assigned","no_auto_destroy","rollback_approved","dbre_backup_verified","dbre_restore_rehearsed","rpo_accepted","rto_accepted","application_slo_healthy","data_integrity_verified","audit_evidence_retained","cleanup_zero_orphans"]
LIMITS={"max_critical_findings":0,"max_destructive_actions":0,"max_missing_evidence":0,"max_inventory_age_minutes":15,"max_telemetry_age_minutes":5,"max_error_budget_consumed_percent":100,"max_rpo_minutes":15,"max_rto_minutes":60,"max_orphan_resources":0}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in LIMITS.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    for k,limit in LIMITS.items():
        field=k[4:];v=e.get(field)
        if type(v) not in (int,float) or not 0<=v<=limit:errors.append(field+' invalid or exceeds limit')
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
    if not errors:print('PASS: synthetic capstone claims only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
