"""Advice-only SRE/DBRE optimization gate. No cloud actions."""
def decide(c):
    if not isinstance(c,dict) or c.get('environment') not in ('dev','staging','production') or c.get('risk') not in ('low','medium','high','critical'):return 'QUARANTINE'
    for k in ('destructive','database','approved','finance_approved','evidence_fresh','forecast_complete','capacity_verified','slo_healthy','rpo_healthy','rto_healthy','backup_verified','rollback_tested'):
        if type(c.get(k)) is not bool:return 'QUARANTINE'
    if c['destructive'] or c['database'] or c['risk'] in ('high','critical') or not c['evidence_fresh'] or not c['forecast_complete'] or not c['capacity_verified'] or not c['rpo_healthy'] or not c['rto_healthy'] or not c['backup_verified'] or not c['rollback_tested']:return 'QUARANTINE'
    if c['environment']=='production' or c['risk']=='medium' or not c['approved'] or not c['finance_approved'] or not c['slo_healthy']:return 'HOLD'
    return 'REVIEW_ONLY'
