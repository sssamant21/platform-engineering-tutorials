"""Illustrative realized savings reconciliation; no real invoice integration."""
from decimal import Decimal,InvalidOperation
def classify(predicted_savings,realized_savings,complete=True,tolerance_usd='10'):
    if complete is not True:return 'UNKNOWN'
    try:
        vals=(predicted_savings,realized_savings,tolerance_usd)
        if any(type(v) not in (int,float,str,Decimal) for v in vals):return 'UNKNOWN'
        p,r,t=[Decimal(str(v)) for v in vals]
        if not all(x.is_finite() for x in (p,r,t)) or t<0:return 'UNKNOWN'
        return 'RECONCILED' if abs(p-r)<=t else 'REVIEW'
    except (InvalidOperation,ValueError):return 'UNKNOWN'
