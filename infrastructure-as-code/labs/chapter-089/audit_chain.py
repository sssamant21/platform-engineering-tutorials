"""Canonical JSON hash chain; cannot authenticate a signer or timestamp."""
import hashlib,json
def digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def assess(entries):
    if not isinstance(entries,list) or not entries:return ['chain invalid']
    errors=[];previous='GENESIS'
    for i,entry in enumerate(entries):
        if not isinstance(entry,dict):errors.append(f'entry {i} invalid');continue
        payload=entry.get('payload')
        if not isinstance(payload,dict):errors.append(f'entry {i} payload invalid');continue
        actual=digest(payload)
        if entry.get('digest')!=actual:errors.append(f'entry {i} hash mismatch')
        if entry.get('previous_digest')!=previous:errors.append(f'entry {i} link mismatch')
        previous=actual
    return errors
