"""Financial chargeback advice only. No payment or provider API calls."""
def decide(c):
    if not isinstance(c,dict) or c.get('environment') not in ('dev','staging','production') or c.get('risk') not in ('low','medium','high','critical'):return 'QUARANTINE'
    for k in ('approved','finance_approved','source_complete','ledger_reconciled','tenant_isolated','slo_healthy','rpo_healthy','rto_healthy','destructive','database'):
        if type(c.get(k)) is not bool:return 'QUARANTINE'
    if c['destructive'] or c['database'] or c['risk'] in ('high','critical') or not c['source_complete'] or not c['ledger_reconciled'] or not c['tenant_isolated'] or not c['rpo_healthy'] or not c['rto_healthy']:return 'QUARANTINE'
    if c['environment']=='production' or c['risk']=='medium' or not c['approved'] or not c['finance_approved'] or not c['slo_healthy']:return 'HOLD'
    return 'READY_FOR_REVIEW'
