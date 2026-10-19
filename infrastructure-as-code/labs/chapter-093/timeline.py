"""Validate ordered synthetic UTC events; no source clock authentication."""
from datetime import datetime
def assess(events):
    if not isinstance(events,list) or not events:return ['events invalid']
    errors=[];seen=set();previous=None
    for i,event in enumerate(events):
        if not isinstance(event,dict):errors.append(f'event {i} invalid');continue
        eid=event.get('event_id');change=event.get('change_id')
        if not isinstance(eid,str) or not eid or eid in seen:errors.append(f'event {i} ID invalid')
        else:seen.add(eid)
        if not isinstance(change,str) or not change:errors.append(f'event {i} change missing')
        try:
            raw=event['timestamp']
            if not isinstance(raw,str):raise ValueError('time invalid')
            dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if dt.tzinfo is None or dt.utcoffset().total_seconds()!=0:raise ValueError('not UTC')
            if previous is not None and dt<previous:errors.append(f'event {i} out of order')
            previous=dt
        except (KeyError,ValueError,TypeError,OverflowError):errors.append(f'event {i} time invalid')
    return errors
