"""Advice-only FinOps rightsizing gate. Never modifies infrastructure."""
def decide(c):
    if not isinstance(c,dict) or c.get('environment') not in ('dev','staging','production') or c.get('risk') not in ('low','medium','high','critical'):return 'QUARANTINE'
    for k in ('destructive','database','slo_healthy','rpo_healthy','rto_healthy','approved','billing_fresh','capacity_verified','state_preserved'):
        if type(c.get(k)) is not bool:return 'QUARANTINE'
    if c['destructive'] or c['database'] or c['risk'] in ('high','critical') or not c['billing_fresh'] or not c['capacity_verified'] or not c['state_preserved'] or not c['rpo_healthy'] or not c['rto_healthy']:return 'QUARANTINE'
    if c['environment']=='production' or c['risk']=='medium' or not c['approved'] or not c['slo_healthy']:return 'HOLD'
    return 'REVIEW_ONLY'
