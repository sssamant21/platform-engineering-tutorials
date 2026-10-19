"""Synthetic observability claims only; no Prometheus, OTLP, cloud or DB calls."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-observability-lab","cloud_account":"offline","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","source_commit":"0123456789abcdef","owner":"sre-dbre-lab"}
CONTROLS=["source_approved","target_verified","otel_collector_healthy","prometheus_scrape_healthy","logs_redacted","traces_redacted","audit_logs_enabled","collector_tls_enforced","exporter_authenticated","metrics_cardinality_bounded","metrics_fresh","logs_fresh","traces_fresh","alert_routes_verified","runbooks_linked","slo_calculated","burn_rate_reviewed","error_budget_reviewed","gitops_observed","drift_observed","policy_decisions_observed","state_lock_observed","provider_throttling_observed","dbre_replication_observed","dbre_backup_observed","dbre_restore_rehearsed","rpo_accepted","rto_accepted","slo_healthy","retention_verified"]
METRICS=["iac_pipeline_runs_total","iac_pipeline_duration_seconds","iac_plan_destructive_changes_total","iac_state_lock_wait_seconds","iac_policy_denials_total","iac_drift_findings","iac_drift_detection_age_seconds","iac_gitops_reconcile_duration_seconds","iac_resource_orphans","iac_observability_export_failures_total","iac_dbre_restore_duration_seconds","iac_change_slo_breaches_total"]
LIMITS={"max_critical_findings":0,"max_telemetry_age_minutes":5,"max_drift_age_minutes":15,"max_export_failures":0,"max_error_rate_percent":1,"max_rpo_minutes":15,"max_rto_minutes":60}
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['documents invalid']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('required_controls')!=CONTROLS or p.get('required_metrics')!=METRICS or p.get('require_exact_controls') is not True or any(p.get(k)!=v for k,v in LIMITS.items()):return ['policy baseline mismatch']
    errors=[]
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if e.get(k)!=v:errors.append('target mismatch '+k)
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('artifact_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['artifact_digest']):errors.append('digest invalid')
    if e.get('metrics')!=METRICS:errors.append('metrics incomplete or reordered')
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
    if not errors:print('PASS: synthetic observability claims only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
