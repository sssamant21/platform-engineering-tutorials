# Chapter 050 — Integrated Files, Exceptions, Logging and Configuration SRE/DBRE Capstone Lab

**Python 3.10+ | Standard library | Offline, no infrastructure mutation**

## Layout
```text
ch050/
  capstone.py
  test_capstone.py
  config.json
  events.json
  output/
```

Create an empty `output/` directory before execution.

## 1. capstone.py

```python
"""Chapter 050 offline, read-only SRE/DBRE operations capstone. Python 3.10+."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time

MAX_BYTES=65536
POLICY={"postgresql":("replication_lag","seconds",30,120),
        "elasticsearch":("search_latency","milliseconds",200,500),
        "kafka":("consumer_lag","messages",1000,10000)}

class OpsError(Exception): pass
class InputFailure(OpsError): pass
class TransientFailure(OpsError): pass
class PermanentFailure(OpsError): pass

def pairs_unique(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise InputFailure("duplicate JSON key")
        out[key]=value
    return out

def invalid_constant(value):
    raise InputFailure("nonfinite JSON number")

def load_json(path):
    path=Path(path)
    if not path.is_file() or path.is_symlink():
        raise InputFailure("expected regular non-symlink file")
    if path.stat().st_size>MAX_BYTES:
        raise InputFailure("file exceeds size limit")
    with path.open("rb") as stream:
        raw=stream.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise InputFailure("file exceeds size limit")
    try:
        return json.loads(raw.decode("utf-8-sig"),object_pairs_hook=pairs_unique,
                          parse_constant=invalid_constant)
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise InputFailure("invalid UTF-8 or JSON") from exc

def exact(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields):
        raise InputFailure("missing or unknown schema fields")

def config_from(data):
    exact(data,("schema_version","environment","max_attempts","secret_ref"))
    if type(data["schema_version"]) is not int or data["schema_version"]!=1:
        raise InputFailure("unsupported schema")
    if data["environment"] not in ("dev","staging","prod"):
        raise InputFailure("invalid environment")
    if type(data["max_attempts"]) is not int or not 1<=data["max_attempts"]<=4:
        raise InputFailure("invalid retry count")
    ref=data["secret_ref"]
    if not isinstance(ref,str) or len(ref)>128 or (ref and not re.fullmatch(
        r"(vault|aws-sm|azure-kv):[A-Za-z0-9/_-]+",ref)):
        raise InputFailure("invalid secret reference")
    return {"schema_version":1,"environment":data["environment"],
            "max_attempts":data["max_attempts"],"secret_configured":bool(ref)}

def validate_rows(rows):
    if not isinstance(rows,list) or len(rows)>1000:
        raise InputFailure("invalid event list")
    result=[]
    for row in rows:
        exact(row,("service","engine","metric","unit","value","timestamp"))
        service=row["service"]
        if not isinstance(service,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}",service):
            raise InputFailure("invalid service")
        engine=row["engine"]
        if not isinstance(engine,str) or engine not in POLICY:
            raise InputFailure("invalid engine")
        metric,unit,warn,critical=POLICY[engine]
        if row["metric"]!=metric or row["unit"]!=unit:
            raise InputFailure("metric/unit mismatch")
        value=row["value"]
        if type(value) not in (int,float):
            raise InputFailure("invalid metric type")
        try: value=float(value)
        except (OverflowError,ValueError) as exc: raise InputFailure("invalid metric") from exc
        if not math.isfinite(value) or value<0: raise InputFailure("invalid metric")
        stamp=row["timestamp"]
        if not isinstance(stamp,str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",stamp):
            raise InputFailure("invalid timestamp")
        try: datetime.strptime(stamp,"%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc: raise InputFailure("invalid timestamp") from exc
        severity="critical" if value>=critical else "warning" if value>=warn else "healthy"
        result.append({**row,"value":value,"severity":severity})
    return sorted(result,key=lambda r:(r["timestamp"],r["engine"],r["service"]))

def retry_readonly(action,attempts,sleep=lambda _:None):
    if type(attempts) is not int or not 1<=attempts<=4:
        raise InputFailure("invalid retry count")
    for index in range(attempts):
        try: return action()
        except TransientFailure:
            if index+1==attempts: raise
            sleep(min(0.05*(2**index),0.2))
    raise AssertionError("unreachable")

def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)

def report(config,rows):
    items=validate_rows(rows)
    counts={level:sum(item["severity"]==level for item in items)
            for level in ("healthy","warning","critical")}
    return {"schema_version":1,"dry_run":True,"configuration":config,
            "counts":counts,"total":len(items),"events":items}

def safe_output_path(root,filename):
    root=Path(root)
    if not root.is_dir() or root.is_symlink():
        raise InputFailure("expected trusted non-symlink output directory")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}\.json",filename):
        raise InputFailure("invalid output filename")
    target=root/filename
    if target.is_symlink():
        raise InputFailure("symlink output refused")
    return target

def atomic_write(root,filename,payload):
    target=safe_output_path(root,filename)
    temp=None
    try:
        with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=target.parent,
                                         prefix=".tmp-",delete=False) as stream:
            temp=Path(stream.name)
            try: os.chmod(temp,0o600)
            except OSError: pass
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,target)
        temp=None
        return target
    finally:
        if temp is not None:
            try: temp.unlink()
            except FileNotFoundError: pass

class JsonFormatter(logging.Formatter):
    def format(self,record):
        return canonical({"level":record.levelname,"event":record.getMessage(),
                          "component":"ch050-capstone"})

def build_logger(log_file=None):
    logger=logging.getLogger("ch050-capstone")
    logger.handlers.clear()
    logger.propagate=False
    logger.setLevel(logging.INFO)
    handler=(RotatingFileHandler(log_file,maxBytes=32768,backupCount=2,encoding="utf-8")
             if log_file else logging.NullHandler())
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger

def execute(config_path,events_path,output_dir,logger=None):
    logger=logger or build_logger()
    try:
        config=config_from(load_json(config_path))
        rows=retry_readonly(lambda:load_json(events_path),config["max_attempts"])
        result=report(config,rows)
        fingerprint=hashlib.sha256(canonical(result).encode("utf-8")).hexdigest()
        payload=canonical({"report":result,"sha256":fingerprint})+"\n"
        target=atomic_write(output_dir,"report.json",payload)
        logger.info("report_written")
        return result,target
    except (OpsError,OSError) as exc:
        logger.error("operation_failed")
        raise OpsError("capstone execution failed; see sanitized error category") from exc

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline SRE/DBRE operational report")
    parser.add_argument("--config",required=True)
    parser.add_argument("--events",required=True)
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args(argv)
    try:
        result,target=execute(args.config,args.events,args.output_dir)
    except OpsError:
        print("operation failed: check inputs, permissions and schema",file=sys.stderr)
        return 3
    print(canonical({"path":str(target),"total":result["total"],"counts":result["counts"]}))
    return 0

if __name__=="__main__": raise SystemExit(main())
```

## 2. config.json

```json
{"schema_version":1,"environment":"staging","max_attempts":3,"secret_ref":"vault:synthetic/read-only"}
```

## 3. events.json

```json
[
 {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45,"timestamp":"2026-10-17T12:00:00Z"},
 {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650,"timestamp":"2026-10-17T12:01:00Z"},
 {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000,"timestamp":"2026-10-17T12:02:00Z"}
]
```

## 4. test_capstone.py — automated tests

```python
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from capstone import (InputFailure,TransientFailure,PermanentFailure,OpsError,
    pairs_unique,load_json,config_from,validate_rows,retry_readonly,canonical,report,
    safe_output_path,atomic_write,JsonFormatter,build_logger,execute,main,MAX_BYTES)

CONFIG={"schema_version":1,"environment":"staging","max_attempts":3,
        "secret_ref":"vault:synthetic/read-only"}
EVENT={"service":"pg-replica","engine":"postgresql","metric":"replication_lag",
       "unit":"seconds","value":45,"timestamp":"2026-10-17T12:00:00Z"}

class CapstoneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.config=self.root/"config.json"
        self.events=self.root/"events.json"
        self.config.write_text(json.dumps(CONFIG))
        self.events.write_text(json.dumps([EVENT]))
    def bad_config(self,**changes):
        d={**CONFIG,**changes}
        with self.assertRaises(InputFailure): config_from(d)
    def bad_event(self,**changes):
        d={**EVENT,**changes}
        with self.assertRaises(InputFailure): validate_rows([d])
    def test_pairs(self): self.assertEqual(pairs_unique([("a",1)]),{"a":1})
    def test_duplicate(self):
        with self.assertRaises(InputFailure): pairs_unique([("a",1),("a",2)])
    def test_json(self): self.assertEqual(load_json(self.config),CONFIG)
    def test_bad_json(self):
        self.config.write_text("{bad")
        with self.assertRaises(InputFailure): load_json(self.config)
    def test_json_nan(self):
        self.config.write_text('{"a":NaN}')
        with self.assertRaises(InputFailure): load_json(self.config)
    def test_json_duplicate(self):
        self.config.write_text('{"a":1,"a":2}')
        with self.assertRaises(InputFailure): load_json(self.config)
    def test_json_utf8(self):
        self.config.write_bytes(b"\xff")
        with self.assertRaises(InputFailure): load_json(self.config)
    def test_json_large(self):
        self.config.write_bytes(b" "*(MAX_BYTES+1))
        with self.assertRaises(InputFailure): load_json(self.config)
    def test_json_missing(self):
        with self.assertRaises(InputFailure): load_json(self.root/"missing")
    def test_json_symlink(self):
        link=self.root/"link"
        try: link.symlink_to(self.config)
        except OSError: self.skipTest("symlink unsupported")
        with self.assertRaises(InputFailure): load_json(link)
    def test_config(self): self.assertEqual(config_from(CONFIG)["environment"],"staging")
    def test_config_redaction(self): self.assertNotIn("vault:",canonical(config_from(CONFIG)))
    def test_config_schema(self): self.bad_config(schema_version=2)
    def test_config_schema_bool(self): self.bad_config(schema_version=True)
    def test_config_env(self): self.bad_config(environment="production")
    def test_config_attempt_zero(self): self.bad_config(max_attempts=0)
    def test_config_attempt_high(self): self.bad_config(max_attempts=5)
    def test_config_attempt_bool(self): self.bad_config(max_attempts=True)
    def test_config_secret(self): self.bad_config(secret_ref="plaintext:secret")
    def test_config_extra(self): self.bad_config(password="unsafe")
    def test_config_missing(self):
        d=dict(CONFIG);d.pop("environment")
        with self.assertRaises(InputFailure): config_from(d)
    def test_event(self): self.assertEqual(validate_rows([EVENT])[0]["severity"],"warning")
    def test_event_healthy(self): self.assertEqual(validate_rows([{**EVENT,"value":5}])[0]["severity"],"healthy")
    def test_event_critical(self): self.assertEqual(validate_rows([{**EVENT,"value":120}])[0]["severity"],"critical")
    def test_event_engine(self): self.bad_event(engine="mysql")
    def test_event_metric(self): self.bad_event(metric="wrong")
    def test_event_unit(self): self.bad_event(unit="milliseconds")
    def test_event_service(self): self.bad_event(service="=1+1")
    def test_event_negative(self): self.bad_event(value=-1)
    def test_event_bool(self): self.bad_event(value=True)
    def test_event_nan(self): self.bad_event(value=float("nan"))
    def test_event_inf(self): self.bad_event(value=float("inf"))
    def test_event_string(self): self.bad_event(value="45")
    def test_event_date(self): self.bad_event(timestamp="2026-02-30T12:00:00Z")
    def test_event_naive(self): self.bad_event(timestamp="2026-10-17T12:00:00")
    def test_event_extra(self): self.bad_event(secret="x")
    def test_event_root(self):
        with self.assertRaises(InputFailure): validate_rows({})
    def test_event_es(self):
        e={**EVENT,"engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":500}
        self.assertEqual(validate_rows([e])[0]["severity"],"critical")
    def test_event_kafka(self):
        e={**EVENT,"engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000}
        self.assertEqual(validate_rows([e])[0]["severity"],"critical")
    def test_retry_success(self): self.assertEqual(retry_readonly(lambda:42,3),42)
    def test_retry_transient(self):
        action=Mock(side_effect=[TransientFailure(),42])
        self.assertEqual(retry_readonly(action,3),42)
        self.assertEqual(action.call_count,2)
    def test_retry_exhausted(self):
        with self.assertRaises(TransientFailure): retry_readonly(Mock(side_effect=TransientFailure()),2)
    def test_retry_permanent(self):
        action=Mock(side_effect=PermanentFailure())
        with self.assertRaises(PermanentFailure): retry_readonly(action,3)
        self.assertEqual(action.call_count,1)
    def test_retry_invalid(self):
        with self.assertRaises(InputFailure): retry_readonly(lambda:42,0)
    def test_retry_backoff(self):
        sleep=Mock()
        retry_readonly(Mock(side_effect=[TransientFailure(),TransientFailure(),1]),3,sleep)
        self.assertEqual(sleep.call_count,2)
    def test_report(self): self.assertEqual(report(config_from(CONFIG),[EVENT])["total"],1)
    def test_report_counts(self): self.assertEqual(report(config_from(CONFIG),[EVENT])["counts"]["warning"],1)
    def test_report_dry_run(self): self.assertTrue(report(config_from(CONFIG),[])["dry_run"])
    def test_canonical(self): self.assertEqual(canonical({"b":2,"a":1}),'{"a":1,"b":2}')
    def test_output_path(self): self.assertEqual(safe_output_path(self.root,"report.json"),self.root/"report.json")
    def test_output_traversal(self):
        with self.assertRaises(InputFailure): safe_output_path(self.root,"../bad.json")
    def test_output_extension(self):
        with self.assertRaises(InputFailure): safe_output_path(self.root,"bad.txt")
    def test_output_missing_dir(self):
        with self.assertRaises(InputFailure): safe_output_path(self.root/"missing","report.json")
    def test_output_symlink(self):
        link=self.root/"report.json"
        try: link.symlink_to(self.config)
        except OSError: self.skipTest("symlink unsupported")
        with self.assertRaises(InputFailure): safe_output_path(self.root,"report.json")
    def test_atomic(self):
        path=atomic_write(self.root,"report.json",'{"ok":true}\n')
        self.assertEqual(path.read_text(),'{"ok":true}\n')
    def test_atomic_overwrite(self):
        atomic_write(self.root,"report.json","old")
        atomic_write(self.root,"report.json","new")
        self.assertEqual((self.root/"report.json").read_text(),"new")
    def test_formatter(self):
        record=logging.LogRecord("x",logging.INFO,"x",1,"report_written",(),None)
        self.assertEqual(json.loads(JsonFormatter().format(record))["event"],"report_written")
    def test_logger(self): self.assertFalse(build_logger().propagate)
    def test_execute(self):
        result,path=execute(self.config,self.events,self.root)
        self.assertEqual(result["total"],1)
        self.assertTrue(path.is_file())
    def test_execute_digest(self):
        execute(self.config,self.events,self.root)
        self.assertEqual(len(json.loads((self.root/"report.json").read_text())["sha256"]),64)
    def test_execute_secret(self):
        execute(self.config,self.events,self.root)
        self.assertNotIn("vault:",(self.root/"report.json").read_text())
    def test_execute_input_unchanged(self):
        before=self.config.read_bytes(),self.events.read_bytes()
        execute(self.config,self.events,self.root)
        self.assertEqual(before,(self.config.read_bytes(),self.events.read_bytes()))
    def test_execute_error_chain(self):
        self.events.write_text("{bad")
        with self.assertRaises(OpsError) as ctx: execute(self.config,self.events,self.root)
        self.assertIsNotNone(ctx.exception.__cause__)
    def test_cli(self): self.assertEqual(main(["--config",str(self.config),"--events",str(self.events),"--output-dir",str(self.root)]),0)
    def test_cli_error(self):
        self.events.write_text("{bad")
        self.assertEqual(main(["--config",str(self.config),"--events",str(self.events),"--output-dir",str(self.root)]),3)

if __name__=="__main__": unittest.main()
```

## 5. Execute

Linux/macOS/WSL:
```bash
mkdir -p output
python3 -m py_compile capstone.py test_capstone.py
python3 -m unittest -v test_capstone.py
python3 capstone.py --config config.json --events events.json --output-dir output
python3 -m json.tool output/report.json
```

Windows PowerShell:
```powershell
New-Item -ItemType Directory -Force output
py -3 -m unittest -v test_capstone.py
py -3 capstone.py --config config.json --events events.json --output-dir output
Get-Content output/report.json
```

Expected synthetic results: 3 records, 0 healthy, 1 warning, 2 critical; exit code 0 indicates a successfully written report, **not healthy infrastructure**.

## 6. Incident simulations
1. Inject malformed JSON, duplicate keys, NaN and invalid UTF-8.
2. Supply an unknown schema field, invalid version or plaintext secret value.
3. Inject a negative or boolean metric, wrong unit or invalid timestamp.
4. Point to a symlink input or output path.
5. Point to an output directory without permissions.
6. Verify permanent failures are never retried.
7. Simulate two transient failures followed by a successful read-only call.
8. Exhaust retry attempts and inspect exception chaining.
9. Compare canonical SHA-256 fingerprints for unchanged and modified data.
10. Verify secret references never appear in report JSON or structured logs.
11. Verify atomic replacement does not leave a temporary file on success.
12. Confirm the input files remain byte-for-byte unchanged.

## 7. Production runbooks
**Input contract incident:** stop ingestion, identify sanitized schema category, fix producer and rerun tests.

**Retry storm:** suspend retries, inspect rate limits, use deadlines and jitter for real transports.

**Report corruption:** restore known-good source snapshot, rerun deterministic generation and verify the output.

**Credential exposure:** contain logs/artifacts, rotate secrets and review redaction policy.

**Rollback:** disable scheduled execution, restore previous CLI version, replay fixtures and verify dashboards.

## 8. Final 100-point assessment

| Area | Points |
|---|---:|
| Automated tests and syntax validation | 25 |
| Safe filesystem and atomic output | 15 |
| Strict JSON/configuration/metric validation | 15 |
| Exception taxonomy and retry safety | 15 |
| JSON logs, redaction and report fingerprint | 10 |
| Incident simulations and troubleshooting | 10 |
| Production runbooks and rollback demonstration | 10 |

**Passing target:** 90/100, with all safety controls passing. The tests are supplied for independent execution; no authoring-environment test result is claimed here.
