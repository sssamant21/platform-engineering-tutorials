"""Advice-only cost control; never executes IaC, billing, or database actions."""
def decide(c):
    if not isinstance(c,dict) or c.get('environment') not in ('dev','staging','production') or c.get('risk') not in ('low','medium','high','critical'):return 'QUARANTINE'
    for k in ('destructive','database','approved','finance_approved','source_complete','alert_delivered','slo_healthy','rpo_healthy','rto_healthy','capacity_verified'):
        if type(c.get(k)) is not bool:return 'QUARANTINE'
    if c['destructive'] or c['database'] or c['risk'] in ('high','critical') or not c['source_complete'] or not c['alert_delivered'] or not c['rpo_healthy'] or not c['rto_healthy'] or not c['capacity_verified']:return 'QUARANTINE'
    if c['environment']=='production' or c['risk']=='medium' or not c['approved'] or not c['finance_approved'] or not c['slo_healthy']:return 'HOLD'
    return 'PROPOSAL_ONLY'
