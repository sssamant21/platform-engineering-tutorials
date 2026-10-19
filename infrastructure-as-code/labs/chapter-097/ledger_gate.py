"""Synthetic cost ledger validation; no native cloud or financial settlement."""
import json,re,sys
from pathlib import Path
TARGET={"environment":"offline-chargeback-lab","billing_account":"offline-097","usage_month":"2026-09","currency":"USD","cost_basis":"amortized","repository":"sssamant21/platform-engineering-tutorials"}
KINDS=('direct','shared','unallocated')
TAGS=('owner','cost_center','application')
def validate(doc,policy):
    if not isinstance(doc,dict) or not isinstance(policy,dict):return ['document invalid']
    if policy.get('schema_version')!=1 or policy.get('target')!=TARGET or policy.get('accepted_kinds')!=list(KINDS) or policy.get('required_tags')!=list(TAGS) or policy.get('max_export_age_hours')!=72 or policy.get('require_unique_lines') is not True:return ['policy mismatch']
    errors=[]
    if doc.get('schema_version')!=1:errors.append('schema')
    for k,v in TARGET.items():
        if doc.get(k)!=v:errors.append('scope '+k)
    age=doc.get('export_age_hours')
    if type(age) not in (int,float) or not 0<=age<=72:errors.append('stale')
    rows=doc.get('records')
    if not isinstance(rows,list) or not rows:return errors+['rows']
    seen=set()
    for i,r in enumerate(rows):
        if not isinstance(r,dict):errors.append('row '+str(i));continue
        lid=r.get('line_id')
        if not isinstance(lid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{2,64}',lid) or lid in seen:errors.append('duplicate/id '+str(i))
        else:seen.add(lid)
        if r.get('kind') not in KINDS:errors.append('kind')
        if type(r.get('cents')) is not int or r['cents']<0:errors.append('cents')
        for k in ('billing_account','usage_month','currency','cost_basis'):
            if r.get(k)!=TARGET[k]:errors.append('row scope '+k)
        if r.get('provider') not in ('aws','azure','gcp'):errors.append('provider')
        if not isinstance(r.get('export_id'),str) or not r['export_id'].strip():errors.append('export')
        digest=r.get('source_digest')
        if not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',digest):errors.append('digest')
        tags=r.get('tags')
        if not isinstance(tags,dict) or set(tags)!=set(TAGS) or any(not isinstance(tags.get(k),str) or not tags[k].strip() for k in TAGS):errors.append('tags')
        weights=r.get('weights')
        if not isinstance(weights,dict):errors.append('weights');continue
        if r.get('kind')=='shared':
            if not weights or any(not isinstance(k,str) or not k.strip() or type(v) is not int or v<=0 for k,v in weights.items()):errors.append('shared weights')
        elif weights:errors.append('nonshared weights')
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:d,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as e:print('INVALID',type(e).__name__);return 2
    errors=validate(d,p)
    for e in errors:print('REJECT',e)
    if not errors:print('PASS synthetic ledger only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
