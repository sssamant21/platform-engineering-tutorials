"""Trailing-average USD forecast; deliberately not a seasonal production model."""
from decimal import Decimal,ROUND_HALF_UP,InvalidOperation
from billing_gate import validate
def project(doc,policy,remaining_days):
    errors=validate(doc,policy)
    if errors:return errors,None
    if type(remaining_days) is not int or not 0<=remaining_days<=31:return ['horizon invalid'],None
    costs=[Decimal(str(x['cost_usd'])) for x in doc['days']]
    avg=sum(costs)/Decimal(len(costs))
    projected=avg*remaining_days
    return [],{'observed_usd':str(sum(costs).quantize(Decimal('0.01'))),'daily_average_usd':str(avg.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),'remaining_forecast_usd':str(projected.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),'method':'trailing_mean_nonseasonal'}
