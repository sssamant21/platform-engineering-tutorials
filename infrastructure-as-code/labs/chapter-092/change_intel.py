"""Synthetic change correlation; no cryptographic or audit verification."""
import re
def assess(change):
    if not isinstance(change,dict):return ['change invalid']
    errors=[]
    if not isinstance(change.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',change['ticket']):errors.append('ticket invalid')
    for k in ('commit','approved_commit'):
        v=change.get(k)
        if not isinstance(v,str) or not re.fullmatch(r'[0-9a-f]{16,64}',v):errors.append(k+' invalid')
    if change.get('commit')!=change.get('approved_commit'):errors.append('commit mismatch')
    if change.get('actor')!=change.get('approved_actor') or not isinstance(change.get('actor'),str) or not change['actor']:errors.append('actor mismatch')
    if change.get('policy_version')!=change.get('approved_policy_version') or not isinstance(change.get('policy_version'),str) or not change['policy_version']:errors.append('policy mismatch')
    skew=change.get('time_skew_minutes')
    if type(skew) not in (int,float) or not 0<=skew<=15:errors.append('time skew invalid')
    if change.get('exception_valid') is not True:errors.append('exception invalid')
    return errors
