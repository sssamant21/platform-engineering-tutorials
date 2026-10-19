"""UTC timeline and candidate ranking. Correlation is not causation."""
from datetime import datetime
def utc(value):
    if not isinstance(value,str):raise ValueError('timestamp invalid')
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset().total_seconds()!=0:raise ValueError('UTC required')
    return dt
def assess(events):
    if not isinstance(events,list) or not events:return ['events invalid']
    seen=set();previous=None;errors=[]
    for i,e in enumerate(events):
        if not isinstance(e,dict):errors.append('event invalid');continue
        if not isinstance(e.get('event_id'),str) or not e['event_id'] or e['event_id'] in seen:errors.append('duplicate or missing ID')
        else:seen.add(e['event_id'])
        if not isinstance(e.get('change_id'),str) or not e['change_id']:errors.append('change ID missing')
        try:
            dt=utc(e['timestamp'])
            if previous is not None and dt<previous:errors.append('out of order')
            previous=dt
        except (ValueError,TypeError,KeyError,OverflowError):errors.append('time invalid')
    return errors
def candidates(incident,changes,window=60):
    if not isinstance(incident,dict) or not isinstance(changes,list) or type(window) not in (int,float) or not 0<window<=1440:return ['input invalid'],None
    try:onset=utc(incident['onset'])
    except (KeyError,ValueError,TypeError,OverflowError):return ['onset invalid'],None
    out=[]
    for c in changes:
        if not isinstance(c,dict):return ['change invalid'],None
        try:delta=(onset-utc(c['timestamp'])).total_seconds()/60
        except (KeyError,ValueError,TypeError,OverflowError):return ['timestamp invalid'],None
        if not isinstance(c.get('change_id'),str) or not c['change_id'] or type(c.get('evidence_complete')) is not bool:return ['evidence invalid'],None
        if 0<=delta<=window:
            score=1+3*int(c.get('service')==incident.get('service'))+2*int(c.get('environment')==incident.get('environment'))+int(c['evidence_complete'])
            out.append({'change_id':c['change_id'],'score':score,'causal_proof':False})
    out.sort(key=lambda x:(-x['score'],x['change_id']))
    return [],out
