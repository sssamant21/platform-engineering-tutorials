"""Fail-closed exception registry validation with explicit UTC reference time."""
from datetime import datetime,timezone
def assess(items,now=None):
    if not isinstance(items,list):return ['exceptions must be a list']
    now=now or datetime.now(timezone.utc)
    errors=[]
    for i,x in enumerate(items):
        if not isinstance(x,dict):errors.append(f'exception {i} invalid');continue
        for k in ('control_id','resource','ticket','reason','approver','requester','compensating_control','scope','environment'):
            if not isinstance(x.get(k),str) or not x[k].strip():errors.append(f'exception {i} missing {k}')
        if x.get('approver')==x.get('requester'):errors.append(f'exception {i} self approved')
        if x.get('environment')=='production' and x.get('scope')=='*':errors.append(f'exception {i} blanket production scope')
        try:
            expiry=datetime.fromisoformat(x['expires_at'].replace('Z','+00:00'))
            if expiry.tzinfo is None or expiry<=now:errors.append(f'exception {i} expired/naive')
        except (ValueError,KeyError,TypeError,AttributeError):errors.append(f'exception {i} invalid expiry')
    return errors
