"""Synthetic anomaly classification with freshness and absolute spend floor."""
from decimal import Decimal,InvalidOperation
def classify(current,baseline,complete=True,fresh=True,ratio='1.5',absolute_usd='20'):
    if complete is not True or fresh is not True:return 'UNKNOWN'
    try:
        if any(type(x) not in (str,int,float,Decimal) for x in (current,baseline,ratio,absolute_usd)):return 'UNKNOWN'
        c,b,r,m=[Decimal(str(x)) for x in (current,baseline,ratio,absolute_usd)]
        if not all(x.is_finite() for x in (c,b,r,m)) or c<0 or b<=0 or r<=1 or m<=0:return 'UNKNOWN'
    except (InvalidOperation,ValueError):return 'UNKNOWN'
    return 'REVIEW' if c-b>=m and c/b>=r else 'OK'
