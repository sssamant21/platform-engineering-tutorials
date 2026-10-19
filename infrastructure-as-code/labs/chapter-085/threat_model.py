"""Synthetic STRIDE risk register validation."""
CATEGORIES={'spoofing','tampering','repudiation','information_disclosure','denial_of_service','elevation_of_privilege'}
def assess(items):
    if not isinstance(items,list):return ['risk register invalid']
    errors=[]
    for i,t in enumerate(items):
        if not isinstance(t,dict):errors.append(f'threat {i} invalid');continue
        if t.get('category') not in CATEGORIES:errors.append(f'threat {i} category invalid')
        for k in ('asset','owner','mitigation'):
            if not isinstance(t.get(k),str) or not t[k].strip():errors.append(f'threat {i} missing {k}')
        for k in ('likelihood','impact'):
            if type(t.get(k)) is not int or not 1<=t[k]<=5:errors.append(f'threat {i} {k} invalid')
        if t.get('status') not in ('mitigated','open'):errors.append(f'threat {i} status invalid')
        if type(t.get('likelihood')) is int and type(t.get('impact')) is int and t['likelihood']*t['impact']>=12 and t.get('status')!='mitigated':errors.append(f'threat {i} high risk open')
    return errors
