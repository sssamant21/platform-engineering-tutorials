"""Offline actual/forecast budget classification; no alerts sent."""
from decimal import Decimal,InvalidOperation
def classify(actual,forecast,budget,thresholds=(50,80,100)):
    try:
        if any(type(x) not in (int,float,str,Decimal) for x in (actual,forecast,budget)):return 'UNKNOWN'
        a,f,b=[Decimal(str(x)) for x in (actual,forecast,budget)]
        if not all(x.is_finite() for x in (a,f,b)) or a<0 or f<0 or b<=0:return 'UNKNOWN'
        if list(thresholds)!=[50,80,100]:return 'UNKNOWN'
    except (InvalidOperation,ValueError,TypeError):return 'UNKNOWN'
    percent=max(a,f)/b*100
    return 'BREACH' if percent>=100 else 'WATCH' if percent>=80 else 'OK'
