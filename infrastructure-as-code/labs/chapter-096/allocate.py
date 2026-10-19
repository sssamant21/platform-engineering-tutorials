"""Decimal USD allocation for validated synthetic billing exports."""
from decimal import Decimal,InvalidOperation
from billing_gate import validate
def allocate(doc,policy):
    errors=validate(doc,policy)
    if errors:return errors,None
    ledger={};total=Decimal('0')
    for row in doc['records']:
        amount=Decimal(str(row['cost_usd']))
        center=row['tags']['cost_center'].strip().lower()
        ledger[center]=ledger.get(center,Decimal('0'))+amount
        total+=amount
    return [],{'total_usd':str(total.quantize(Decimal('0.01'))),'by_cost_center':{k:str(v.quantize(Decimal('0.01'))) for k,v in sorted(ledger.items())},'unallocated_usd':'0.00'}
