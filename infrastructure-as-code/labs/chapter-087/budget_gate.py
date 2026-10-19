"""Synthetic cost/lease checks; not billing or cloud inventory."""
def assess(e):
    if not isinstance(e,dict):return ['budget evidence invalid']
    errors=[]
    for k,expected in (('environment','ephemeral-lab'),('owner','sre-lab'),('run_id','iac087-run-0001')):
        if e.get(k)!=expected:errors.append(k+' mismatch')
    for k,limit in (('cost_usd',25),('lease_minutes',120)):
        v=e.get(k)
        if type(v) not in (int,float) or not 0<=v<=limit:errors.append(k+' over limit')
    if type(e.get('orphaned_resources')) is not int or e['orphaned_resources']!=0:errors.append('orphans')
    if e.get('cleanup_verified') is not True:errors.append('cleanup not verified')
    return errors
