"""Offline synthetic billing daily series validator; no cloud access."""
import json,re,sys
from pathlib import Path
from decimal import Decimal,InvalidOperation
from datetime import date
TARGET={"environment":"offline-finops-forecast","billing_account":"offline-098","currency":"USD","cost_basis":"amortized","owner":"platform-sre","repository":"sssamant21/platform-engineering-tutorials"}
def validate(d,p):
    if not isinstance(d,dict) or not isinstance(p,dict):return ['invalid documents']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('max_export_age_hours')!=48 or p.get('min_days')!=7 or p.get('max_days')!=31 or p.get('thresholds')!=[50,80,100]:return ['policy mismatch']
    errors=[]
    if d.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if d.get(k)!=v:errors.append('target '+k)
    age=d.get('export_age_hours')
    if type(age) not in (int,float) or not 0<=age<=48:errors.append('export stale')
    rows=d.get('days')
    if not isinstance(rows,list) or not 7<=len(rows)<=31:return errors+['day count']
    seen=set();previous=None
    for i,r in enumerate(rows):
        if not isinstance(r,dict):errors.append('row invalid');continue
        raw=r.get('day')
        try:
            if not isinstance(raw,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):raise ValueError()
            day=date.fromisoformat(raw)
            if day in seen:errors.append('duplicate day')
            if previous is not None and (day-previous).days!=1:errors.append('gap or unordered')
            previous=day;seen.add(day)
        except ValueError:errors.append('date invalid')
        if not isinstance(r.get('source_id'),str) or not re.fullmatch(r'CUR-098-[0-9]+',r['source_id']):errors.append('source invalid')
        if r.get('owner')!=TARGET['owner']:errors.append('owner invalid')
        v=r.get('cost_usd')
        try:
            if type(v) not in (str,int,float) or not Decimal(str(v)).is_finite() or Decimal(str(v))<0:raise InvalidOperation()
        except (InvalidOperation,ValueError):errors.append('cost invalid')
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:d,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as e:print('INVALID',type(e).__name__);return 2
    errors=validate(d,p)
    for e in errors:print('REJECT',e)
    if not errors:print('PASS synthetic billing only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
