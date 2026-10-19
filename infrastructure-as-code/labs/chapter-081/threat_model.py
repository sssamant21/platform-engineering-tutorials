"""Offline STRIDE threat risk register and mitigation validation."""
STRIDE=('spoofing','tampering','repudiation','information_disclosure','denial_of_service','elevation_of_privilege')
def assess(threats):
    if not isinstance(threats,list):return ['threat register invalid']
    errors=[]
    for i,t in enumerate(threats):
        if not isinstance(t,dict):errors.append(f'threat {i}: invalid');continue
        if t.get('category') not in STRIDE:errors.append(f'threat {i}: category')
        for k in ('likelihood','impact'):
            if type(t.get(k)) is not int or not 1<=t[k]<=5:errors.append(f'threat {i}: {k}')
        if not isinstance(t.get('owner'),str) or not t['owner'].strip():errors.append(f'threat {i}: owner')
        if not isinstance(t.get('mitigation'),str) or not t['mitigation'].strip():errors.append(f'threat {i}: mitigation')
        if type(t.get('likelihood')) is int and type(t.get('impact')) is int and t['likelihood']*t['impact']>=15 and t.get('status')!='mitigated':
            errors.append(f'threat {i}: high risk unmitigated')
    return errors
