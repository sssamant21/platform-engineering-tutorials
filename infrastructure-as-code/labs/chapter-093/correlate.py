"""Rank hypotheses; no causal inference or native event collection."""
from datetime import datetime,timezone
def parse(value):
    if not isinstance(value,str):raise ValueError('invalid time')
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None or t.utcoffset().total_seconds()!=0:raise ValueError('UTC required')
    return t
def rank(incident,changes,window_minutes=60):
    if not isinstance(incident,dict) or not isinstance(changes,list) or type(window_minutes) not in (int,float) or not 0<window_minutes<=1440:return ['invalid input'],None
    try:onset=parse(incident['onset'])
    except (KeyError,ValueError,TypeError,OverflowError):return ['invalid onset'],None
    if not isinstance(incident.get('service'),str) or not isinstance(incident.get('environment'),str):return ['invalid scope'],None
    out=[]
    for c in changes:
        if not isinstance(c,dict):return ['invalid change'],None
        try:timestamp=parse(c['timestamp'])
        except (KeyError,ValueError,TypeError,OverflowError):return ['invalid timestamp'],None
        if not isinstance(c.get('change_id'),str) or not c['change_id'] or type(c.get('evidence_complete')) is not bool:return ['invalid change evidence'],None
        delta=(onset-timestamp).total_seconds()/60
        if not 0<=delta<=window_minutes:continue
        score=1
        if c.get('service')==incident['service']:score+=3
        if c.get('environment')==incident['environment']:score+=2
        if c.get('dependency')==incident.get('dependency'):score+=2
        if c['evidence_complete']:score+=1
        out.append({'change_id':c['change_id'],'score':score,'minutes_before_onset':delta,'causal_proof':False})
    out.sort(key=lambda x:(-x['score'],x['minutes_before_onset'],x['change_id']))
    return [],out
