"""Request-based SLO calculations; no live telemetry."""
from math import isfinite
def calculate(total,bad,objective=0.999,windows=None):
    if type(total) is not int or total<=0 or type(bad) is not int or not 0<=bad<=total:return ['invalid counts'],None
    if type(objective) not in (int,float) or not isfinite(objective) or not 0<objective<1:return ['invalid objective'],None
    allowed=total*(1-objective)
    out={'availability':1-bad/total,'allowed_bad':allowed,'remaining_bad':allowed-bad,'budget_consumed':bad/allowed}
    if windows is not None:
        if not isinstance(windows,dict) or not windows:return ['invalid windows'],None
        burns={}
        for name,pair in windows.items():
            if not isinstance(name,str) or not name or not isinstance(pair,(list,tuple)) or len(pair)!=2:return ['invalid window '+str(name)],None
            n,e=pair
            if type(n) is not int or n<=0 or type(e) is not int or not 0<=e<=n:return ['invalid window counts '+name],None
            burns[name]=(e/n)/(1-objective)
        out['burn_rates']=burns
    return [],out
