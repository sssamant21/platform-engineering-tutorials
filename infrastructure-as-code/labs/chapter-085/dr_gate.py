"""Declared DR rehearsal evaluator, not an actual restore."""
def assess(e):
    if not isinstance(e,dict):return ['DR evidence invalid']
    errors=[]
    for k in ('backup_isolated','restore_succeeded','kms_decrypt_verified','replication_healthy'):
        if e.get(k) is not True:errors.append(k+' missing')
    for k,limit in (('rpo_minutes',15),('rto_minutes',60)):
        v=e.get(k)
        if type(v) not in (int,float) or isinstance(v,bool) or not 0<=v<=limit:errors.append(k+' exceeded')
    return errors
