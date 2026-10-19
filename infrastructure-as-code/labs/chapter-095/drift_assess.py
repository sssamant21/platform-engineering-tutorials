"""Three-way synthetic drift; missing inventory cannot certify health."""
def assess(desired,managed,actual,complete=True):
    if complete is not True or any(not isinstance(x,dict) for x in (desired,managed,actual)):return ['inventory incomplete or snapshots invalid'],None
    findings=[]
    for name in sorted(set(desired)|set(managed)|set(actual)):
        d=name in desired;m=name in managed;a=name in actual
        if d and m and a and desired[name]==managed[name]==actual[name]:continue
        if a and not d and not m:kind='unmanaged'
        elif d and m and not a:kind='missing_remote'
        elif m and not d and not a:kind='state_only'
        elif d and not m and not a:kind='desired_only'
        else:kind='mismatch'
        findings.append({'resource':name,'kind':kind})
    return [],findings
