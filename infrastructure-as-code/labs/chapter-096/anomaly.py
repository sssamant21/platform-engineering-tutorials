"""Synthetic spend anomaly review. Never triggers live alerts."""
from math import isfinite
def classify(current,baseline,complete=True,fresh=True,minimum_usd=10,threshold_ratio=1.5):
    if complete is not True or fresh is not True:return 'UNKNOWN'
    for v in (current,baseline,minimum_usd,threshold_ratio):
        if type(v) not in (int,float) or not isfinite(v):return 'UNKNOWN'
    if current<0 or baseline<=0 or minimum_usd<=0 or threshold_ratio<=1:return 'UNKNOWN'
    if current<minimum_usd:return 'OK'
    return 'REVIEW' if current/baseline>=threshold_ratio else 'OK'
