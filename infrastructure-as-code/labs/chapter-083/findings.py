"""Synthetic finding triage, no real secrets."""
from datetime import datetime,timezone
def assess(items,now=None):
    if not isinstance(items,list):return ['findings must be list']
    now=now or datetime.now(timezone.utc)
    errors=[]
    for i,f in enumerate(items):
        if not isinstance(f,dict):errors.append(f'finding {i} invalid');continue
        for k in ('id','severity','owner','fingerprint','status'):
            if not isinstance(f.get(k),str) or not f[k].strip():errors.append(f'finding {i} missing {k}')
        if f.get('severity') not in ('low','medium','high','critical'):errors.append(f'finding {i} severity invalid')
        if f.get('status') not in ('resolved','open','suppressed'):errors.append(f'finding {i} status invalid')
        if f.get('severity')=='critical' and f.get('status')!='resolved':errors.append(f'finding {i} critical unresolved')
        if f.get('status')=='suppressed':
            if not isinstance(f.get('approver'),str) or not f['approver'].strip() or f.get('approver')==f.get('owner'):errors.append(f'finding {i} suppression approval')
            if not isinstance(f.get('reason'),str) or not f['reason'].strip():errors.append(f'finding {i} suppression reason')
            try:
                expiry=datetime.fromisoformat(f['expires_at'].replace('Z','+00:00'))
                if expiry.tzinfo is None or expiry<=now:errors.append(f'finding {i} suppression expired')
            except (KeyError,ValueError,TypeError,AttributeError):errors.append(f'finding {i} suppression expiry invalid')
    return errors
