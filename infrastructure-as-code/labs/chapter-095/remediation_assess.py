"""Advice-only remediation circuit breaker; never calls cloud APIs."""
def decide(c):
    if not isinstance(c,dict) or c.get('environment') not in ('dev','staging','production') or c.get('risk') not in ('low','medium','high','critical'):return 'QUARANTINE'
    for k in ('destructive','database','telemetry_fresh','inventory_complete','approved','slo_healthy','active_incident','state_preserved'):
        if type(c.get(k)) is not bool:return 'QUARANTINE'
    if c['destructive'] or c['database'] or c['risk'] in ('high','critical') or not c['telemetry_fresh'] or not c['inventory_complete'] or not c['state_preserved']:return 'QUARANTINE'
    if c['environment']=='production' or c['risk']=='medium' or c['active_incident'] or not c['approved'] or not c['slo_healthy']:return 'HOLD'
    return 'PROPOSAL_ONLY'
