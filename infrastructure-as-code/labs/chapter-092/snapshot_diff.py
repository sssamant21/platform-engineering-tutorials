"""Strict synthetic desired/state/actual comparison. No provider semantics."""
def assess(desired,managed,actual):
    if any(not isinstance(x,dict) for x in (desired,managed,actual)):return ['snapshots invalid'],None
    errors=[]
    for label,snapshot in (('desired',desired),('managed',managed),('actual',actual)):
        if any(not isinstance(k,str) or not k or not isinstance(v,(str,int,float,bool,type(None),dict,list)) for k,v in snapshot.items()):errors.append(label+' invalid entry')
    if errors:return errors,None
    findings=[]
    for resource in sorted(set(desired)|set(managed)|set(actual)):
        d=desired.get(resource);m=managed.get(resource);a=actual.get(resource)
        present=(resource in desired,resource in managed,resource in actual)
        if present==(True,True,True) and d==m==a:continue
        if present==(False,False,True):kind='unmanaged'
        elif present==(False,True,False):kind='state_only'
        elif present==(True,False,False):kind='desired_only'
        elif present==(True,True,False):kind='missing_remote'
        elif present==(False,True,True):kind='unowned_state'
        elif present==(True,False,True):kind='unmanaged_desired'
        else:kind='three_way_mismatch'
        findings.append({'resource':resource,'kind':kind,'desired':d,'managed':m,'actual':a})
    return [],findings
