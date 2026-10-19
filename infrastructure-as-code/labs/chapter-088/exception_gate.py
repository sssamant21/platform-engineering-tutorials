"""Deterministic exception governance, no external approval validation."""
def assess(e,now_day=100):
    if not isinstance(e,dict) or type(now_day) is not int:return ['exception invalid']
    errors=[]
    for k in ('control_id','resource','owner','approver','reason','compensating_control'):
        if not isinstance(e.get(k),str) or not e[k].strip():errors.append(k+' missing')
    if e.get('resource') in ('*','all','production/*'):errors.append('wildcard resource')
    if e.get('owner')==e.get('approver'):errors.append('self approval')
    expiry=e.get('expiry_day')
    if type(expiry) is not int or not now_day<expiry<=now_day+30:errors.append('expired or excessive expiry')
    if e.get('approved') is not True:errors.append('approval missing')
    return errors
