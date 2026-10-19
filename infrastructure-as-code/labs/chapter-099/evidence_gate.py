"""Synthetic FinOps optimization evidence contract; no provider APIs."""
import json,re,sys
from decimal import Decimal,InvalidOperation
from pathlib import Path
TARGET={"environment":"offline-finops-optimization","billing_account":"offline-099","currency":"USD","cost_basis":"amortized","owner":"platform-sre","repository":"sssamant21/platform-engineering-tutorials"}
BOOL=('forecast_complete','backup_verified','slo_healthy','rpo_healthy','rto_healthy','rollback_tested')
def validate(d,p):
    if not isinstance(d,dict) or not isinstance(p,dict):return ['invalid documents']
    if p.get('schema_version')!=1 or p.get('target')!=TARGET or p.get('max_age_hours')!=48 or p.get('minimum_headroom_pct')!=20:return ['policy mismatch']
    errors=[]
    if d.get('schema_version')!=1:errors.append('schema mismatch')
    for k,v in TARGET.items():
        if d.get(k)!=v:errors.append('target '+k)
    age=d.get('export_age_hours')
    if type(age) not in (int,float) or not 0<=age<=48:errors.append('stale')
    for k in ('baseline_monthly_usd','target_monthly_usd'):
        v=d.get(k)
        try:
            if type(v) not in (str,int,float) or not Decimal(str(v)).is_finite() or Decimal(str(v))<0 or (k=='baseline_monthly_usd' and Decimal(str(v))==0):raise InvalidOperation()
        except (InvalidOperation,ValueError):errors.append('invalid '+k)
    for k in ('cpu_p99_pct','memory_p99_pct','headroom_pct'):
        v=d.get(k)
        if type(v) not in (int,float) or not 0<=v<=100:errors.append('invalid '+k)
    if type(d.get('headroom_pct')) in (int,float) and d['headroom_pct']<20:errors.append('headroom below policy')
    for k in BOOL:
        if d.get(k) is not True:errors.append('missing/failed '+k)
    if not isinstance(d.get('resource_id'),str) or not re.fullmatch(r'offline-099-[a-z0-9-]+',d['resource_id']):errors.append('resource scope')
    if not isinstance(d.get('source_digest'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',d['source_digest']):errors.append('digest invalid')
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:d,p=[json.loads(Path(x).read_text(encoding='utf-8')) for x in sys.argv[1:]]
    except (OSError,ValueError) as e:print('INVALID',type(e).__name__);return 2
    errors=validate(d,p)
    for e in errors:print('REJECT',e)
    if not errors:print('PASS synthetic optimization evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
