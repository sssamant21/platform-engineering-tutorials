"""Fail-closed change gate; outputs advice only and never mutates infra."""
def decide(change):
    if not isinstance(change,dict):return 'QUARANTINE'
    if change.get('environment') not in ('dev','staging','production') or change.get('risk') not in ('low','medium','high','critical'):return 'QUARANTINE'
    for k in ('destructive','database','telemetry_fresh','approved','slo_healthy','critical_incident','state_preserved'):
        if type(change.get(k)) is not bool:return 'QUARANTINE'
    if change['destructive'] or change['database'] or change['risk'] in ('high','critical') or not change['telemetry_fresh'] or not change['state_preserved']:return 'QUARANTINE'
    if change['critical_incident'] or not change['slo_healthy'] or not change['approved'] or change['environment']=='production' or change['risk']=='medium':return 'HOLD'
    return 'PROCEED'
