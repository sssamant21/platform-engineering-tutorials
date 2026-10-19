"""Offline synthetic cloud billing contract. No provider billing API calls."""
import json,re,sys
from decimal import Decimal,InvalidOperation
from pathlib import Path
TARGET={"environment":"offline-finops-lab","account":"offline-096","repository":"sssamant21/platform-engineering-tutorials","owner":"sre-dbre-lab","usage_date":"2026-10-18"}
TAGS=["owner","environment","cost_center","application","managed_by"]
PROVIDERS=('aws','azure','gcp')
def validate(doc,policy):
    if not isinstance(doc,dict) or not isinstance(policy,dict):return ['invalid document']
    if policy.get('schema_version')!=1 or policy.get('target')!=TARGET or policy.get('required_tags')!=TAGS or policy.get('accepted_providers')!=list(PROVIDERS) or policy.get('currency')!='USD' or policy.get('cost_basis')!='amortized' or policy.get('max_export_age_hours')!=48 or policy.get('max_unallocated_percent')!=0 or policy.get('require_unique_lines') is not True:return ['policy baseline mismatch']
    errors=[]
    if doc.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if doc.get(k)!=v:errors.append('target mismatch '+k)
    age=doc.get('export_age_hours')
    if type(age) not in (int,float) or not 0<=age<=48:errors.append('export stale')
    rows=doc.get('records')
    if not isinstance(rows,list) or not rows:return errors+['records invalid']
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,dict):errors.append('row invalid '+str(i));continue
        lid=row.get('line_id')
        if not isinstance(lid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{2,64}',lid) or lid in seen:errors.append('line duplicate/invalid '+str(i))
        else:seen.add(lid)
        if row.get('provider') not in PROVIDERS or row.get('account')!=TARGET['account'] or row.get('usage_date')!=TARGET['usage_date']:errors.append('scope invalid '+str(i))
        if row.get('currency')!='USD' or row.get('cost_basis')!='amortized':errors.append('basis invalid '+str(i))
        for k in ('service','resource_id','export_id'):
            if not isinstance(row.get(k),str) or not row[k].strip():errors.append('metadata invalid '+k)
        digest=row.get('source_digest')
        if not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',digest):errors.append('digest invalid')
        raw=row.get('cost_usd')
        try:
            if type(raw) not in (int,float,str) or not Decimal(str(raw)).is_finite() or Decimal(str(raw))<0:raise InvalidOperation()
        except (InvalidOperation,ValueError):errors.append('cost invalid')
        tags=row.get('tags')
        if not isinstance(tags,dict) or set(tags)!=set(TAGS) or any(not isinstance(tags.get(k),str) or not tags[k].strip() for k in TAGS):errors.append('tags invalid')
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:doc,policy=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as e:print('INVALID',type(e).__name__);return 2
    errors=validate(doc,policy)
    for e in errors:print('REJECT',e)
    if not errors:print('PASS synthetic billing contract only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
