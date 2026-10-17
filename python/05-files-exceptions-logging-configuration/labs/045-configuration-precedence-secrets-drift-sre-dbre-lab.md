# Chapter 045 — Configuration Precedence, Secrets and Drift SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline, synthetic, read-only**

Create `config_lab.py`, `cli.py`, `sample.json`, `baseline.json`, and `test_config_lab.py` as below. The CLI never retrieves secret values or accesses infrastructure.

## 1. config_lab.py

```python
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import re

ALLOWED = frozenset({'environment','service','timeout_seconds','retry_attempts','log_level','secret_ref'})
DEFAULTS = {'environment':'staging','service':'postgresql','timeout_seconds':5,'retry_attempts':2,'log_level':'INFO','secret_ref':''}
ENV_MAP = {'SRE_ENVIRONMENT':'environment','SRE_SERVICE':'service','SRE_TIMEOUT_SECONDS':'timeout_seconds','SRE_RETRY_ATTEMPTS':'retry_attempts','SRE_LOG_LEVEL':'log_level','SRE_SECRET_REF':'secret_ref'}
MAX_FILE = 65536

class ConfigurationError(ValueError):
    pass

def unique_pairs(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:
            raise ConfigurationError('duplicate configuration key')
        obj[key]=value
    return obj

def strict_json(text):
    try:
        return json.loads(text,object_pairs_hook=unique_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ConfigurationError('nonfinite JSON value')))
    except json.JSONDecodeError as exc:
        raise ConfigurationError('invalid configuration JSON') from exc

def file_layer(path):
    if path is None:
        return {}
    path=Path(path)
    if path.stat().st_size>MAX_FILE:
        raise ConfigurationError('configuration file too large')
    with path.open('r',encoding='utf-8') as handle:
        text=handle.read(MAX_FILE+1)
    if len(text.encode('utf-8'))>MAX_FILE:
        raise ConfigurationError('configuration file too large')
    data=strict_json(text)
    if not isinstance(data,dict):
        raise ConfigurationError('configuration must be an object')
    return data

def environment_layer(environ):
    if environ is None:
        environ=os.environ
    return {field:environ[name] for name,field in ENV_MAP.items() if name in environ}

def _int(value,low,high,field):
    if isinstance(value,bool):
        raise ConfigurationError('invalid '+field)
    if isinstance(value,str):
        if not re.fullmatch(r'[0-9]+',value):
            raise ConfigurationError('invalid '+field)
        value=int(value)
    if not isinstance(value,int) or not low<=value<=high:
        raise ConfigurationError('invalid '+field)
    return value

@dataclass(frozen=True,slots=True)
class Config:
    environment:str
    service:str
    timeout_seconds:int
    retry_attempts:int
    log_level:str
    secret_ref:str

    def safe_dict(self):
        return {'environment':self.environment,'service':self.service,'timeout_seconds':self.timeout_seconds,'retry_attempts':self.retry_attempts,'log_level':self.log_level,'secret_configured':bool(self.secret_ref)}

    def fingerprint(self):
        data=self.safe_dict()
        return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(data):
    if not isinstance(data,dict) or set(data)!=ALLOWED:
        raise ConfigurationError('missing or unknown configuration keys')
    environment=data['environment']
    service=data['service']
    level=data['log_level']
    ref=data['secret_ref']
    if environment not in ('dev','staging','prod'):
        raise ConfigurationError('invalid environment')
    if service not in ('postgresql','elasticsearch','kafka','redis'):
        raise ConfigurationError('invalid service')
    if level not in ('DEBUG','INFO','WARNING','ERROR'):
        raise ConfigurationError('invalid log level')
    if not isinstance(ref,str) or len(ref)>128 or (ref and not re.fullmatch(r'(vault|aws-sm|azure-kv):[A-Za-z0-9/_-]+',ref)):
        raise ConfigurationError('invalid secret reference')
    return Config(environment,service,_int(data['timeout_seconds'],1,120,'timeout'),_int(data['retry_attempts'],0,5,'retries'),level,ref)

def resolve(file_data=None,environ=None,overrides=None):
    layers=(DEFAULTS,file_data or {},environment_layer(environ),overrides or {})
    merged={}
    sources={}
    for source,layer in zip(('default','file','environment','override'),layers):
        if not isinstance(layer,dict) or not set(layer).issubset(ALLOWED):
            raise ConfigurationError('unknown configuration key')
        for key,value in layer.items():
            merged[key]=value
            sources[key]=source
    config=validate(merged)
    return config,{key:sources[key] for key in sorted(sources)}

def drift(expected,actual):
    if not isinstance(expected,Config) or not isinstance(actual,Config):
        raise TypeError('expected validated Config instances')
    old=expected.safe_dict()
    new=actual.safe_dict()
    return [{'field':field,'expected':old[field],'actual':new[field]} for field in sorted(old) if old[field]!=new[field]]

def report(config,sources,baseline=None):
    if not isinstance(config,Config):
        raise TypeError('invalid configuration')
    return {'schema_version':1,'dry_run':True,'effective':config.safe_dict(),'sources':sources,'fingerprint':config.fingerprint(),'drift':[] if baseline is None else drift(baseline,config)}
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from config_lab import ConfigurationError,file_layer,resolve,report

def main(argv=None):
    parser=argparse.ArgumentParser(description='Synthetic SRE configuration validation')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--environment',choices=['dev','staging','prod'])
    parser.add_argument('--service',choices=['postgresql','elasticsearch','kafka','redis'])
    args=parser.parse_args(argv)
    overrides={key:value for key,value in (('environment',args.environment),('service',args.service)) if value is not None}
    try:
        current,sources=resolve(file_layer(args.config),overrides=overrides)
        baseline=resolve(file_layer(args.baseline),environ={})[0] if args.baseline else None
        result=report(current,sources,baseline)
    except (OSError,UnicodeError,ConfigurationError) as exc:
        parser.error(str(exc))
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
```

## 3. Synthetic fixtures

`sample.json`:

```json
{"environment":"staging","service":"postgresql","timeout_seconds":10,"retry_attempts":3,"log_level":"INFO","secret_ref":"vault:synthetic/pg-reader"}
```

`baseline.json`:

```json
{"environment":"staging","service":"postgresql","timeout_seconds":5,"retry_attempts":2,"log_level":"INFO","secret_ref":"vault:synthetic/pg-reader"}
```

## 4. test_config_lab.py — 50 automated tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch
from config_lab import (ALLOWED,DEFAULTS,ENV_MAP,MAX_FILE,Config,ConfigurationError,strict_json,file_layer,environment_layer,validate,resolve,drift,report)
from cli import main

class ConfigurationTests(unittest.TestCase):
    def config(self,**updates):
        data=dict(DEFAULTS)
        data.update(updates)
        return validate(data)
    def test_defaults(self): self.assertEqual(resolve(environ={})[0].environment,'staging')
    def test_immutable(self):
        with self.assertRaises(FrozenInstanceError): self.config().environment='prod'
    def test_safe_dict(self): self.assertFalse(self.config().safe_dict()['secret_configured'])
    def test_secret_reference_not_exposed(self):
        cfg=self.config(secret_ref='vault:synthetic/path')
        self.assertNotIn('vault:',json.dumps(cfg.safe_dict()))
    def test_fingerprint_stable(self): self.assertEqual(self.config().fingerprint(),self.config().fingerprint())
    def test_fingerprint_changes(self): self.assertNotEqual(self.config().fingerprint(),self.config(timeout_seconds=7).fingerprint())
    def test_file_precedence(self): self.assertEqual(resolve({'timeout_seconds':7},environ={})[0].timeout_seconds,7)
    def test_environment_precedence(self): self.assertEqual(resolve({'timeout_seconds':7},{'SRE_TIMEOUT_SECONDS':'8'})[0].timeout_seconds,8)
    def test_override_precedence(self): self.assertEqual(resolve({'timeout_seconds':7},{'SRE_TIMEOUT_SECONDS':'8'},{'timeout_seconds':9})[0].timeout_seconds,9)
    def test_source_provenance(self): self.assertEqual(resolve({'timeout_seconds':7},environ={})[1]['timeout_seconds'],'file')
    def test_environment_provenance(self): self.assertEqual(resolve(environ={'SRE_TIMEOUT_SECONDS':'8'})[1]['timeout_seconds'],'environment')
    def test_override_provenance(self): self.assertEqual(resolve(environ={},overrides={'timeout_seconds':9})[1]['timeout_seconds'],'override')
    def test_unknown_key(self):
        with self.assertRaises(ConfigurationError): resolve({'password':'secret'},environ={})
    def test_bad_environment(self):
        with self.assertRaises(ConfigurationError): self.config(environment='production')
    def test_bad_service(self):
        with self.assertRaises(ConfigurationError): self.config(service='mysql')
    def test_bad_level(self):
        with self.assertRaises(ConfigurationError): self.config(log_level='TRACE')
    def test_timeout_zero(self):
        with self.assertRaises(ConfigurationError): self.config(timeout_seconds=0)
    def test_timeout_high(self):
        with self.assertRaises(ConfigurationError): self.config(timeout_seconds=121)
    def test_timeout_bool(self):
        with self.assertRaises(ConfigurationError): self.config(timeout_seconds=True)
    def test_timeout_fraction(self):
        with self.assertRaises(ConfigurationError): self.config(timeout_seconds=1.5)
    def test_retry_negative(self):
        with self.assertRaises(ConfigurationError): self.config(retry_attempts=-1)
    def test_retry_high(self):
        with self.assertRaises(ConfigurationError): self.config(retry_attempts=6)
    def test_retry_string(self): self.assertEqual(self.config(retry_attempts='3').retry_attempts,3)
    def test_retry_bad_string(self):
        with self.assertRaises(ConfigurationError): self.config(retry_attempts='three')
    def test_secret_ref_allowed(self): self.assertEqual(self.config(secret_ref='aws-sm:ops/pg').secret_ref,'aws-sm:ops/pg')
    def test_secret_ref_bad(self):
        with self.assertRaises(ConfigurationError): self.config(secret_ref='plaintext:password')
    def test_secret_ref_long(self):
        with self.assertRaises(ConfigurationError): self.config(secret_ref='vault:'+'x'*130)
    def test_duplicate_json(self):
        with self.assertRaises(ConfigurationError): strict_json('{"x":1,"x":2}')
    def test_json_nan(self):
        with self.assertRaises(ConfigurationError): strict_json('{"x":NaN}')
    def test_json_malformed(self):
        with self.assertRaises(ConfigurationError): strict_json('{bad')
    def test_json_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_text('{"service":"kafka"}')
            self.assertEqual(file_layer(p),{'service':'kafka'})
    def test_json_file_array(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_text('[]')
            with self.assertRaises(ConfigurationError): file_layer(p)
    def test_json_file_size(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_text(' '* (MAX_FILE+1))
            with self.assertRaises(ConfigurationError): file_layer(p)
    def test_none_file(self): self.assertEqual(file_layer(None),{})
    def test_environment_mapping(self): self.assertEqual(environment_layer({'SRE_SERVICE':'redis'}),{'service':'redis'})
    def test_ignore_other_environment(self): self.assertEqual(environment_layer({'SECRET_PASSWORD':'oops'}),{})
    def test_drift_none(self): self.assertEqual(drift(self.config(),self.config()),[])
    def test_drift_detected(self): self.assertEqual(drift(self.config(),self.config(timeout_seconds=8))[0]['field'],'timeout_seconds')
    def test_drift_no_secret_values(self):
        result=drift(self.config(secret_ref='vault:old'),self.config(secret_ref='vault:new'))
        self.assertEqual(result,[])
    def test_drift_secret_presence(self):
        result=drift(self.config(),self.config(secret_ref='vault:synthetic'))
        self.assertEqual(result[0]['field'],'secret_configured')
    def test_drift_wrong_type(self):
        with self.assertRaises(TypeError): drift('bad',self.config())
    def test_report(self): self.assertTrue(report(self.config(),{})['dry_run'])
    def test_report_schema(self): self.assertEqual(report(self.config(),{})['schema_version'],1)
    def test_report_baseline(self): self.assertEqual(len(report(self.config(timeout_seconds=8),{},self.config())['drift']),1)
    def test_cli(self):
        with patch.dict('os.environ',{},clear=True): self.assertEqual(main([]),0)
    def test_cli_bad_file(self):
        with self.assertRaises(SystemExit): main(['--config','missing-configuration-file.json'])
    def test_cli_override(self):
        with patch.dict('os.environ',{},clear=True): self.assertEqual(main(['--service','kafka']),0)
    def test_cli_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_text('{"timeout_seconds":8}')
            with patch.dict('os.environ',{},clear=True): self.assertEqual(main(['--baseline',str(p)]),0)
    def test_unknown_override(self):
        with self.assertRaises(ConfigurationError): resolve(environ={},overrides={'unknown':1})
    def test_missing_schema(self):
        with self.assertRaises(ConfigurationError): validate({'service':'kafka'})

if __name__=='__main__': unittest.main()
```

## 5. Execute

```bash
python3 -m unittest -v test_config_lab.py
python3 -m py_compile config_lab.py cli.py
python3 cli.py --config sample.json --baseline baseline.json
python3 cli.py --config sample.json --service kafka
```

Windows PowerShell:

```powershell
py -3 -m unittest -v test_config_lab.py
py -3 cli.py --config sample.json --baseline baseline.json
```

**Expected:** `sample.json` versus `baseline.json` reports drift for `timeout_seconds` and `retry_attempts`. The secret reference is never emitted.

## 6. Failure injection

1. Set `SRE_TIMEOUT_SECONDS=0`: validation rejects it.
2. Supply unknown key `password`: reject.
3. Set `secret_ref` to a plaintext value: reject.
4. Duplicate a JSON key: reject.
5. Add NaN/Infinity: reject.
6. Change environment from staging to prod via CLI: verify precedence.
7. Change a public timeout: verify fingerprint and drift.
8. Change one secret reference to another: observe intentionally limited secret-version drift detection.

## 7. Production runbooks

**Misconfiguration:** halt rollout, compare safe effective settings with approved baseline, restore through change control.

**Secret exposure:** contain log artifacts, rotate compromised credentials and use managed identity/secret manager access.

**Drift:** inspect provenance, deployment revision and authorized change record; do not auto-overwrite production.

**Rollback:** pin known-good configuration, test staging, verify SLOs after gradual rollout.

## 8. Acceptance

- [x] 50 automated tests passed in Linux authoring sandbox.
- [x] Strict precedence, validation, drift and secret minimization covered.
- [ ] Re-run on learner's OS.
- [ ] Review configuration governance and production secret handling before live use.

**Safety:** This lab never retrieves real secrets, connects to services, or modifies infrastructure.
