"""Synthetic test matrix quality checks; not a real coverage collector."""
REQUIRED={'format','static','unit','policy','plan','integration','restore','canary'}
def assess(e):
    if not isinstance(e,dict):return ['matrix invalid']
    errors=[]
    layers=e.get('layers')
    if not isinstance(layers,list) or set(layers)!=REQUIRED or len(layers)!=len(REQUIRED):errors.append('layers incomplete')
    n=e.get('negative_cases')
    if type(n) is not int or n<10:errors.append('negative cases insufficient')
    n=e.get('skipped_critical')
    if type(n) is not int or n!=0:errors.append('critical tests skipped')
    n=e.get('max_age_hours')
    if type(n) is not int or not 0<=n<=24:errors.append('evidence stale')
    return errors
