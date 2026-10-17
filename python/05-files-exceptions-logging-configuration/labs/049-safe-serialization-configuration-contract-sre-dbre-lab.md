# Chapter 049 — Safe Serialization and Configuration Contract SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline, read-only**

This is a complete executable lab for versioned JSON contracts, safe parsing, deterministic serialization, sanitized configuration, PostgreSQL/Elasticsearch/Kafka synthetic telemetry, and SHA-256 content fingerprints. No cloud, Kubernetes or database operations are performed.

## Layout
```text
ch049/
  contract_lab.py
  test_contract_lab.py
  config.json
  events.json
```

## 1. contract_lab.py

```python
"""Offline JSON contract validation for SRE/DBRE telemetry."""
import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys

MAX_BYTES=65536
POLICY={"postgresql":("replication_lag","seconds",120),
        "elasticsearch":("search_latency","milliseconds",500),
        "kafka":("consumer_lag","messages",10000)}

class ContractError(ValueError): pass

def unique_pairs(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ContractError("duplicate JSON key")
        out[key]=value
    return out

def reject_constant(value):
    raise ContractError("nonfinite JSON value")

def parse_json(raw):
    if not isinstance(raw,(bytes,str)): raise ContractError("expected JSON")
    if isinstance(raw,bytes):
        if len(raw)>MAX_BYTES: raise ContractError("file too large")
        try: raw=raw.decode("utf-8-sig")
        except UnicodeError as exc: raise ContractError("invalid UTF-8") from exc
    if len(raw.encode("utf-8"))>MAX_BYTES: raise ContractError("file too large")
    try:
        return json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=reject_constant)
    except json.JSONDecodeError as exc: raise ContractError("invalid JSON") from exc

def read_json(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink(): raise ContractError("expected regular file")
    if p.stat().st_size>MAX_BYTES: raise ContractError("file too large")
    with p.open("rb") as stream: return parse_json(stream.read(MAX_BYTES+1))

def exact(data,fields):
    if not isinstance(data,dict) or set(data)!=set(fields):
        raise ContractError("unknown or missing fields")

@dataclass(frozen=True)
class Config:
    schema_version:int
    environment:str
    max_events:int
    secret_ref:str
    def public(self):
        return {"schema_version":self.schema_version,"environment":self.environment,
                "max_events":self.max_events,"secret_configured":bool(self.secret_ref)}

def validate_config(data):
    exact(data,("schema_version","environment","max_events","secret_ref"))
    if type(data["schema_version"]) is not int or data["schema_version"]!=1:
        raise ContractError("unsupported schema version")
    if data["environment"] not in ("dev","staging","prod"):
        raise ContractError("invalid environment")
    if type(data["max_events"]) is not int or not 1<=data["max_events"]<=1000:
        raise ContractError("invalid event limit")
    ref=data["secret_ref"]
    if not isinstance(ref,str) or len(ref)>128 or (ref and not re.fullmatch(r"(vault|aws-sm|azure-kv):[A-Za-z0-9/_-]+",ref)):
        raise ContractError("invalid secret reference")
    return Config(**data)

def validate_event(data):
    exact(data,("service","engine","metric","value","unit","timestamp"))
    if not isinstance(data["service"],str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}",data["service"]):
        raise ContractError("invalid service")
    engine=data["engine"]
    if not isinstance(engine,str) or engine not in POLICY:
        raise ContractError("unknown engine")
    metric,unit,threshold=POLICY[engine]
    if data["metric"]!=metric or data["unit"]!=unit:
        raise ContractError("metric/unit mismatch")
    value=data["value"]
    if type(value) not in (int,float):
        raise ContractError("invalid numeric type")
    try: value=float(value)
    except (ValueError,OverflowError) as exc: raise ContractError("invalid number") from exc
    if not math.isfinite(value) or value<0: raise ContractError("invalid numeric value")
    stamp=data["timestamp"]
    if not isinstance(stamp,str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",stamp):
        raise ContractError("invalid timestamp format")
    try: datetime.strptime(stamp,"%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc: raise ContractError("invalid calendar date") from exc
    return {**data,"value":value,"severity":"critical" if value>=threshold else "normal"}

def canonical(data):
    try: return json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)
    except (TypeError,ValueError) as exc: raise ContractError("not serializable") from exc

def report(config_data,events_data):
    config=validate_config(config_data)
    if not isinstance(events_data,list) or len(events_data)>config.max_events:
        raise ContractError("invalid event array or count")
    events=[validate_event(e) for e in events_data]
    events.sort(key=lambda e:(e["timestamp"],e["engine"],e["service"]))
    return {"schema_version":1,"dry_run":True,"configuration":config.public(),
            "total":len(events),"critical":sum(e["severity"]=="critical" for e in events),
            "events":events}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline SRE/DBRE JSON contract lab")
    parser.add_argument("--config",required=True)
    parser.add_argument("--events",required=True)
    args=parser.parse_args(argv)
    try:
        result=report(read_json(args.config),read_json(args.events))
        fingerprint=hashlib.sha256(canonical(result).encode()).hexdigest()
    except (ContractError,OSError) as exc:
        print("input error: "+str(exc),file=sys.stderr)
        return 3
    print(canonical({"report":result,"sha256":fingerprint}))
    return 0

if __name__=="__main__": raise SystemExit(main())
```

## 2. config.json

```json
{"schema_version":1,"environment":"staging","max_events":10,"secret_ref":"vault:synthetic/reader"}
```

## 3. events.json

```json
[
  {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","value":45,"unit":"seconds","timestamp":"2026-10-17T12:00:00Z"},
  {"service":"es-search","engine":"elasticsearch","metric":"search_latency","value":650,"unit":"milliseconds","timestamp":"2026-10-17T12:01:00Z"},
  {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","value":10000,"unit":"messages","timestamp":"2026-10-17T12:02:00Z"}
]
```

## 4. test_contract_lab.py — automated tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from contract_lab import ContractError,parse_json,read_json,validate_config,validate_event,canonical,report,main,MAX_BYTES

CONFIG={"schema_version":1,"environment":"staging","max_events":10,"secret_ref":"vault:synthetic/reader"}
EVENT={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","value":45,"unit":"seconds","timestamp":"2026-10-17T12:00:00Z"}

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config=Path(self.tmp.name)/"config.json"
        self.events=Path(self.tmp.name)/"events.json"
        self.config.write_text(json.dumps(CONFIG))
        self.events.write_text(json.dumps([EVENT]))
    def bad_config(self,**changes):
        obj=dict(CONFIG);obj.update(changes)
        with self.assertRaises(ContractError): validate_config(obj)
    def bad_event(self,**changes):
        obj=dict(EVENT);obj.update(changes)
        with self.assertRaises(ContractError): validate_event(obj)
    def test_json_object(self): self.assertEqual(parse_json('{"a":1}'),{"a":1})
    def test_json_array(self): self.assertEqual(parse_json("[]"),[])
    def test_json_bytes(self): self.assertEqual(parse_json(b'{}'),{})
    def test_json_bom(self): self.assertEqual(parse_json(b'\xef\xbb\xbf{}'),{})
    def test_duplicate(self):
        with self.assertRaises(ContractError): parse_json('{"x":1,"x":2}')
    def test_nan(self):
        with self.assertRaises(ContractError): parse_json("[NaN]")
    def test_infinity(self):
        with self.assertRaises(ContractError): parse_json("[Infinity]")
    def test_bad_json(self):
        with self.assertRaises(ContractError): parse_json("{bad")
    def test_bad_type(self):
        with self.assertRaises(ContractError): parse_json(1)
    def test_bad_utf8(self):
        with self.assertRaises(ContractError): parse_json(b'\xff')
    def test_large(self):
        with self.assertRaises(ContractError): parse_json(b' '*(MAX_BYTES+1))
    def test_file(self): self.assertEqual(read_json(self.config),CONFIG)
    def test_missing_file(self):
        with self.assertRaises(ContractError): read_json(self.config.parent/"missing")
    def test_symlink(self):
        link=self.config.parent/"link"
        try: link.symlink_to(self.config)
        except OSError: self.skipTest("symlink unsupported")
        with self.assertRaises(ContractError): read_json(link)
    def test_config(self): self.assertEqual(validate_config(CONFIG).environment,"staging")
    def test_config_immutable(self):
        c=validate_config(CONFIG)
        with self.assertRaises(FrozenInstanceError): c.environment="prod"
    def test_config_safe(self): self.assertNotIn("vault:",canonical(validate_config(CONFIG).public()))
    def test_config_version(self): self.bad_config(schema_version=2)
    def test_config_version_bool(self): self.bad_config(schema_version=True)
    def test_config_environment(self): self.bad_config(environment="production")
    def test_config_limit_zero(self): self.bad_config(max_events=0)
    def test_config_limit_high(self): self.bad_config(max_events=1001)
    def test_config_limit_bool(self): self.bad_config(max_events=True)
    def test_config_secret(self): self.bad_config(secret_ref="plaintext:password")
    def test_config_secret_long(self): self.bad_config(secret_ref="vault:"+"x"*130)
    def test_config_unknown(self): self.bad_config(password="x")
    def test_config_missing(self):
        d=dict(CONFIG);d.pop("environment")
        with self.assertRaises(ContractError): validate_config(d)
    def test_event(self): self.assertEqual(validate_event(EVENT)["severity"],"normal")
    def test_event_critical(self): self.assertEqual(validate_event({**EVENT,"value":120})["severity"],"critical")
    def test_event_service(self): self.bad_event(service="=1+1")
    def test_event_engine(self): self.bad_event(engine="mysql")
    def test_event_metric(self): self.bad_event(metric="latency")
    def test_event_unit(self): self.bad_event(unit="milliseconds")
    def test_event_negative(self): self.bad_event(value=-1)
    def test_event_boolean(self): self.bad_event(value=True)
    def test_event_string(self): self.bad_event(value="45")
    def test_event_nan(self): self.bad_event(value=float("nan"))
    def test_event_infinite(self): self.bad_event(value=float("inf"))
    def test_event_timestamp(self): self.bad_event(timestamp="2026-02-30T12:00:00Z")
    def test_event_naive(self): self.bad_event(timestamp="2026-10-17T12:00:00")
    def test_event_unknown(self): self.bad_event(password="x")
    def test_es(self):
        e={**EVENT,"engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":500}
        self.assertEqual(validate_event(e)["severity"],"critical")
    def test_kafka(self):
        e={**EVENT,"engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000}
        self.assertEqual(validate_event(e)["severity"],"critical")
    def test_canonical(self): self.assertEqual(canonical({"b":2,"a":1}),'{"a":1,"b":2}')
    def test_canonical_nan(self):
        with self.assertRaises(ContractError): canonical({"x":float("nan")})
    def test_report(self): self.assertEqual(report(CONFIG,[EVENT])["total"],1)
    def test_report_empty(self): self.assertEqual(report(CONFIG,[])["total"],0)
    def test_report_limit(self):
        with self.assertRaises(ContractError): report({**CONFIG,"max_events":1},[EVENT,EVENT])
    def test_report_type(self):
        with self.assertRaises(ContractError): report(CONFIG,{})
    def test_report_safe(self): self.assertNotIn("vault:",canonical(report(CONFIG,[EVENT])))
    def test_report_deterministic(self): self.assertEqual(canonical(report(CONFIG,[EVENT])),canonical(report(CONFIG,[EVENT])))
    def test_cli(self): self.assertEqual(main(["--config",str(self.config),"--events",str(self.events)]),0)
    def test_cli_error(self):
        self.events.write_text("{bad")
        self.assertEqual(main(["--config",str(self.config),"--events",str(self.events)]),3)
    def test_no_mutation(self):
        before=self.config.read_bytes(),self.events.read_bytes()
        main(["--config",str(self.config),"--events",str(self.events)])
        self.assertEqual(before,(self.config.read_bytes(),self.events.read_bytes()))

if __name__=="__main__": unittest.main()
```

## 5. Execute

Linux/macOS/WSL:
```bash
python3 -m py_compile contract_lab.py test_contract_lab.py
python3 -m unittest -v test_contract_lab.py
python3 contract_lab.py --config config.json --events events.json
```

Windows PowerShell:
```powershell
py -3 -m unittest -v test_contract_lab.py
py -3 contract_lab.py --config config.json --events events.json
```

Expected: three validated events, two critical classifications, deterministic JSON and digest, and no secret reference in the report. Exit code 0 indicates successful validation—not healthy datastore status.

## 6. Failure injection

1. Duplicate a JSON object key; verify rejection.
2. Inject NaN, Infinity or invalid UTF-8.
3. Add an unknown schema field or unsupported version.
4. Supply a negative, boolean or string metric value.
5. Swap metric units across engines.
6. Replace a UTC timestamp with a naive timestamp or invalid date.
7. Exceed the configured event count or file size.
8. Verify output redaction and input immutability.
9. Compare digests after a permitted public metric change.
10. Confirm a secret reference never appears in the serialized report.

## 7. Troubleshooting and runbooks

**Schema mismatch:** stop ingestion, review producer and consumer schema versions, restore compatible export, replay test fixtures.

**Corrupt payload:** quarantine the file, regenerate a clean UTF-8 export, verify bounded size and schema.

**Secret exposure:** contain artifacts, rotate credentials if needed, fix unsafe serialization and audit access.

**Rollback:** pin the last known-good parser and schema, execute contract tests and verify downstream telemetry.

**Fingerprint drift:** compare canonicalized public report contents; SHA-256 is a checksum, not a signature.

## 8. Acceptance rubric

| Area | Points |
|---|---:|
| Automated tests | 30 |
| Safe JSON and schema validation | 25 |
| Secret-safe deterministic output | 20 |
| Failure injection | 15 |
| Runbooks and rollback | 10 |

Target 90/100 with safety checks passing. **Execution of the published tests has not been verified in this turn.**
