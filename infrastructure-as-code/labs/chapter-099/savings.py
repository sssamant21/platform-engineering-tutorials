"""Decimal projected savings, not realized provider billing savings."""
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
def estimate(baseline,target):
    try:
        if any(type(v) not in (int,float,str,Decimal) for v in (baseline,target)):return None
        b,t=Decimal(str(baseline)),Decimal(str(target))
        if not b.is_finite() or not t.is_finite() or b<=0 or t<0:return None
        delta=b-t
        return {'baseline_usd':str(b.quantize(Decimal('0.01'))),'target_usd':str(t.quantize(Decimal('0.01'))),'projected_savings_usd':str(delta.quantize(Decimal('0.01'))),'projected_savings_pct':str((delta/b*100).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))}
    except (InvalidOperation,ValueError):return None
