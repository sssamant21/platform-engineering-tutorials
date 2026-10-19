"""Synthetic control catalog completeness; framework references are illustrative."""
REQUIRED=["IAC-001","IAC-002","IAC-003","IAC-004","IAC-005","IAC-006","IAC-007","IAC-008"]
def assess(items):
    if not isinstance(items,list):return ['catalog invalid']
    errors=[]
    seen=set()
    for i,r in enumerate(items):
        if not isinstance(r,dict):errors.append(f'row {i} invalid');continue
        cid=r.get('id')
        if not isinstance(cid,str) or cid in seen:errors.append(f'row {i} duplicate/invalid ID')
        if isinstance(cid,str):seen.add(cid)
        for k in ('owner','objective','framework','implementation','evidence','frequency'):
            if not isinstance(r.get(k),str) or not r[k].strip():errors.append(f'row {i} missing {k}')
    if seen!=set(REQUIRED) or len(items)!=len(REQUIRED):errors.append('required catalog IDs missing/extra')
    return errors
