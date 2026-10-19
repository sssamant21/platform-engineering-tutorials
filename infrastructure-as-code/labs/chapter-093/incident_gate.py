"""Synthetic incident assurance only; no real cloud or observability calls."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-incident-lab","cloud_account":"offline","kube_context":"offline-kind","repository":"sssamant21/platform-engineering-tutorials","source_commit":"0123456789abcdef","owner":"sre-dbre-lab"}
CONTROLS=["source_approved","protected_branch","immutable_artifact","exact_target","change_ticket_verified","actor_identity_verified","plan_digest_verified","provider_audit_enabled","cloud_inventory_complete","otel_traces_present","prometheus_metrics_fresh","gitops_health_observed","policy_enforced","state_snapshot_preserved","event_time_utc","clock_skew_bounded","trace_context_propagated","slo_burn_rate_checked","error_budget_reviewed","incident_commander_assigned","blast_radius_documented","alternative_hypotheses_reviewed","no_automatic_causal_claim","no_auto_destroy","rollback_approved","dbre_backup_verified","dbre_restore_rehearsed","rpo_accepted","rto_accepted","slo_healthy","evidence_retained","postmortem_owner_assigned"]
LIMITS={"max_critical_findings":0,"max_destructive_actions":0,"max_missing_evidence":0,"max_event_age_minutes":15,"max_clock_skew_seconds":30,"max_change_failure_rate_percent":10,"max_rpo_minutes":15,"max_rto_minutes":60}
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
        if type(v) not in (int,float) or not 0<=v<=limit:errors.append(field+' invalid or above limit')
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
    if not errors:print('PASS: synthetic incident claims only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
