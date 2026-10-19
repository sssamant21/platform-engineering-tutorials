"""Synthetic commitment model; never purchases or recommends binding contracts."""
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
def model(eligible_ondemand_usd,commitment_cost_usd,utilization_pct):
    try:
        vals=(eligible_ondemand_usd,commitment_cost_usd,utilization_pct)
        if any(type(v) not in (int,float,str,Decimal) for v in vals):return None
        eligible,cost,util=[Decimal(str(v)) for v in vals]
        if not all(x.is_finite() for x in (eligible,cost,util)) or eligible<=0 or cost<0 or not 0<=util<=100:return None
        utilized=eligible*util/100
        return {'eligible_ondemand_usd':str(eligible.quantize(Decimal('0.01'))),'commitment_cost_usd':str(cost.quantize(Decimal('0.01'))),'utilized_equivalent_usd':str(utilized.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),'illustrative_net_usd':str((utilized-cost).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),'break_even':utilized>=cost}
    except (InvalidOperation,ValueError):return None
