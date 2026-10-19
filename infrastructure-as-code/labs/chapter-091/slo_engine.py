"""Request-based SLO arithmetic; no real metric ingestion."""
from math import isfinite
def assess(total,errors,objective=0.999,window_total=None,window_errors=None):
    if type(total) is not int or total<=0 or type(errors) is not int or not 0<=errors<=total:return ['invalid request counts'],None
    if type(objective) not in (int,float) or not isfinite(objective) or not 0<objective<1:return ['invalid objective'],None
    allowed=total*(1-objective)
    result={'availability':(total-errors)/total,'allowed_errors':allowed,'remaining_errors':allowed-errors,'budget_consumed':errors/allowed}
    if window_total is not None or window_errors is not None:
        if type(window_total) is not int or window_total<=0 or type(window_errors) is not int or not 0<=window_errors<=window_total:return ['invalid short window'],None
        result['burn_rate']=(window_errors/window_total)/(1-objective)
    return [],result
