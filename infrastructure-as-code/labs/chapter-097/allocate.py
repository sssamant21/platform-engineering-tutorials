"""Deterministic integer-cent allocation, including explicit unallocated bucket."""
from ledger_gate import validate
def distribute(cents,weights):
    if type(cents) is not int or cents<0 or not isinstance(weights,dict) or not weights or any(not isinstance(k,str) or not k or type(v) is not int or v<=0 for k,v in weights.items()):raise ValueError('invalid allocation')
    total=sum(weights.values())
    base={k:(cents*v)//total for k,v in weights.items()}
    remainder=cents-sum(base.values())
    order=sorted(weights,key=lambda k:(-((cents*weights[k])%total),k))
    for k in order[:remainder]:base[k]+=1
    return dict(sorted(base.items()))
def allocate(doc,policy):
    errors=validate(doc,policy)
    if errors:return errors,None
    ledger={};source=0
    for r in doc['records']:
        amount=r['cents'];source+=amount
        if r['kind']=='shared':alloc=distribute(amount,r['weights'])
        elif r['kind']=='unallocated':alloc={'__unallocated__':amount}
        else:alloc={r['tags']['cost_center'].strip().lower():amount}
        for owner,cents in alloc.items():ledger[owner]=ledger.get(owner,0)+cents
    return [],{'source_cents':source,'ledger_cents':dict(sorted(ledger.items())),'allocated_cents':sum(v for k,v in ledger.items() if k!='__unallocated__'),'unallocated_cents':ledger.get('__unallocated__',0)}
