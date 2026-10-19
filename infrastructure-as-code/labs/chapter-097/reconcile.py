"""Fail-closed reconciliation: integer cents, no missing pools or double charges."""
def reconcile(result):
    if not isinstance(result,dict) or type(result.get('source_cents')) is not int or result['source_cents']<0:return ['source invalid']
    ledger=result.get('ledger_cents')
    if not isinstance(ledger,dict) or not ledger or any(not isinstance(k,str) or not k or type(v) is not int or v<0 for k,v in ledger.items()):return ['ledger invalid']
    if type(result.get('allocated_cents')) is not int or type(result.get('unallocated_cents')) is not int:return ['totals invalid']
    allocated=sum(v for k,v in ledger.items() if k!='__unallocated__')
    unallocated=ledger.get('__unallocated__',0)
    errors=[]
    if allocated!=result['allocated_cents'] or unallocated!=result['unallocated_cents']:errors.append('subtotals mismatch')
    if allocated+unallocated!=result['source_cents']:errors.append('reconciliation residual')
    return errors
