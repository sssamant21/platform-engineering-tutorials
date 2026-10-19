"""Declared DR readiness check. Not an actual failover or restore."""
def assess(e):
    if not isinstance(e,dict):return ['DR evidence invalid']
    errors=[]
    for key in ('backup_integrity','restore_drill_passed','fencing_verified','quorum_healthy','dbre_approved','encryption_key_available'):
        if e.get(key) is not True:errors.append(key+' not verified')
    for key in ('rpo_minutes','rto_minutes','replica_lag_minutes','restore_duration_minutes'):
        v=e.get(key)
        if type(v) not in (int,float) or v<0:errors.append(key+' invalid')
    if errors:return errors
    if e['replica_lag_minutes']>e['rpo_minutes']:errors.append('RPO exceeded')
    if e['restore_duration_minutes']>e['rto_minutes']:errors.append('RTO exceeded')
    return errors
