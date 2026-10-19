"""Request SLO and burn rate arithmetic, not live Prometheus."""
from math import isfinite
def assess(total,bad,objective=0.999,windows=None):
    if type(total) is not int or total<=0 or type(bad) is not int or not 0<=bad<=total:return ['counts invalid'],None
    if type(objective) not in (int,float) or not isfinite(objective) or not 0<objective<1:return ['objective invalid'],None
    allowed=total*(1-objective)
    result={'availability':1-bad/total,'allowed_bad':allowed,'remaining_bad':allowed-bad,'budget_consumed':bad/allowed}
    if windows is not None:
        if not isinstance(windows,dict) or not windows:return ['windows invalid'],None
        result['burn_rates']={}
        for name,pair in windows.items():
            if not isinstance(name,str) or not name or not isinstance(pair,(tuple,list)) or len(pair)!=2:return ['window invalid'],None
            n,e=pair
            if type(n) is not int or n<=0 or type(e) is not int or not 0<=e<=n:return ['window counts invalid'],None
            result['burn_rates'][name]=(e/n)/(1-objective)
    return [],result
