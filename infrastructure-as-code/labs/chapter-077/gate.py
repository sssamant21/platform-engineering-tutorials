"""Fail-closed declared-evidence gate; not a Terraform/OpenTofu plan parser."""
import json,re,sys
from pathlib import Path
def validate(e,p):
    if not isinstance(e,dict) or not isinstance(p,dict):return ['invalid documents']
    errors=[]
    if p.get('schema_version')!=1 or p.get('require_exact_controls') is not True:errors.append('policy baseline invalid')
    expected=p.get('expected'); required=p.get('required_controls')
    if not isinstance(expected,dict) or not isinstance(required,list) or len(required)!=len(set(required)) or not required:errors.append('policy shape invalid')
    if errors:return errors
    for key,value in expected.items():
        if e.get(key)!=value:errors.append('target mismatch: '+key)
    if e.get('schema_version')!=1:errors.append('schema mismatch')
    if not isinstance(e.get('ticket'),str) or not re.fullmatch(r'CHG-[0-9]{3,}-[A-Z0-9-]+',e['ticket']):errors.append('ticket invalid')
    if not isinstance(e.get('plan_sha256'),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e['plan_sha256']):errors.append('plan digest invalid')
    controls=e.get('controls')
    if not isinstance(controls,dict):controls={}
    if set(controls)!=set(required):errors.append('control set mismatch')
    for key in required:
        if controls.get(key) is not True:errors.append('missing verified control: '+key)
    return errors
def main():
    if len(sys.argv)!=3:return 2
    try:e,p=[json.loads(Path(path).read_text()) for path in sys.argv[1:]]
    except (OSError,ValueError) as exc:
        print('ERROR:',type(exc).__name__);return 2
    errors=validate(e,p)
    for err in errors:print('REJECT:',err)
    if not errors:print('PASS: offline declared plan/apply evidence only')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
