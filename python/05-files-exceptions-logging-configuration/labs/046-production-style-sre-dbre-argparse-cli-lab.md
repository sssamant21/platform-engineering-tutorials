# Chapter 046 — Production-Style SRE/DBRE argparse CLI Lab

**Python 3.10+ | Standard library | Offline, read-only**

## Objectives
Implement a validated datastore inventory CLI with `validate`, `check`, `plan`, strict JSON input, deterministic JSON/CSV output, documented exit codes and automated tests. No real database or cloud calls.

## Project layout
```text
ch046/
  sre_cli.py
  test_sre_cli.py
  inventory.json
```

## 1. sre_cli.py

```python
"""Offline, read-only SRE/DBRE inventory CLI."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import sys

LIMITS = {"postgresql": (30,120,"seconds"), "elasticsearch": (200,500,"milliseconds"), "kafka": (1000,10000,"messages")}
MAX_BYTES = 1048576

class InputError(ValueError):
    pass

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate JSON key")
        result[key] = value
    return result

def parse_json(text):
    try:
        return json.loads(text, object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(InputError("nonfinite JSON")))
    except json.JSONDecodeError as exc:
        raise InputError("malformed JSON") from exc

def load_inventory(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise InputError("expected regular non-symlink file")
    if path.stat().st_size > MAX_BYTES:
        raise InputError("inventory too large")
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        raise InputError("inventory too large")
    try:
        rows = parse_json(raw.decode("utf-8-sig"))
    except UnicodeError as exc:
        raise InputError("expected UTF-8") from exc
    if not isinstance(rows,list) or len(rows)>1000:
        raise InputError("expected array of <=1000 records")
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"service","engine","value"}:
            raise InputError("invalid record schema")
        service,engine,value=row["service"],row["engine"],row["value"]
        if not isinstance(service,str) or not 1<=len(service)<=64 or not all(c.isalnum() or c in "-_" for c in service):
            raise InputError("invalid service")
        if engine not in LIMITS:
            raise InputError("unknown engine")
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            raise InputError("invalid metric")
        if (engine,service) in seen:
            raise InputError("duplicate service")
        seen.add((engine,service))
    return rows

def classify(row):
    warning,critical,unit=LIMITS[row["engine"]]
    value=row["value"]
    status="critical" if value>=critical else "warning" if value>=warning else "healthy"
    return {**row,"unit":unit,"status":status}

def summarize(rows,engine=None):
    selected=sorted((classify(r) for r in rows if engine is None or r["engine"]==engine),
                    key=lambda r:(r["engine"],r["service"]))
    counts={status:sum(r["status"]==status for r in selected) for status in ("healthy","warning","critical")}
    return {"schema_version":1,"dry_run":True,"total":len(selected),"counts":counts,"results":selected}

def render(report,fmt):
    if fmt=="json":
        return json.dumps(report,sort_keys=True,allow_nan=False)+"\n"
    output=io.StringIO()
    writer=csv.writer(output,lineterminator="\n")
    writer.writerow(["service","engine","value","unit","status"])
    for r in report["results"]:
        writer.writerow([r[k] for k in ("service","engine","value","unit","status")])
    return output.getvalue()

def build_parser():
    parser=argparse.ArgumentParser(prog="sre-cli",description="Offline datastore inventory checks")
    parser.add_argument("--inventory",required=True,type=Path)
    parser.add_argument("--format",choices=("json","csv"),default="json")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("validate")
    for command in ("check","plan"):
        sub.add_parser(command).add_argument("--engine",choices=tuple(LIMITS))
    return parser

def run(argv=None,out=None,err=None):
    out=sys.stdout if out is None else out
    err=sys.stderr if err is None else err
    args=build_parser().parse_args(argv)
    try:
        rows=load_inventory(args.inventory)
        if args.command=="validate":
            out.write(json.dumps({"schema_version":1,"dry_run":True,"valid":True,"records":len(rows)},sort_keys=True)+"\n")
            return 0
        report=summarize(rows,args.engine)
        if args.command=="plan":
            report["advisory"]=[{"engine":r["engine"],"service":r["service"],
                "recommendation":"investigate; no automatic changes"} for r in report["results"] if r["status"]!="healthy"]
        out.write(render(report,args.format))
        return 2 if report["counts"]["critical"] else 1 if report["counts"]["warning"] else 0
    except (InputError,OSError,UnicodeError) as exc:
        err.write("input error: "+str(exc)+"\n")
        return 3

if __name__=="__main__":
    raise SystemExit(run())
```

## 2. inventory.json — synthetic fixture

```json
[
  {"service":"pg1","engine":"postgresql","value":5},
  {"service":"pg2","engine":"postgresql","value":35},
  {"service":"es1","engine":"elasticsearch","value":650},
  {"service":"kafka1","engine":"kafka","value":10000}
]
```

## 3. test_sre_cli.py — 50 automated tests

```python
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from sre_cli import InputError,unique_pairs,parse_json,load_inventory,classify,summarize,render,build_parser,run,MAX_BYTES

ROWS=[{"service":"pg1","engine":"postgresql","value":5},
      {"service":"pg2","engine":"postgresql","value":35},
      {"service":"es1","engine":"elasticsearch","value":650},
      {"service":"kafka1","engine":"kafka","value":10000}]

class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"inventory.json"
        self.write(ROWS)
    def write(self,rows): self.path.write_text(json.dumps(rows),encoding="utf-8")
    def invoke(self,*args):
        out,err=io.StringIO(),io.StringIO()
        code=run(["--inventory",str(self.path),*args],out,err)
        return code,out.getvalue(),err.getvalue()
    def test_parse_object(self): self.assertEqual(parse_json('{"a":1}'),{"a":1})
    def test_parse_array(self): self.assertEqual(parse_json("[]"),[])
    def test_duplicate(self):
        with self.assertRaises(InputError): parse_json('{"a":1,"a":2}')
    def test_nan(self):
        with self.assertRaises(InputError): parse_json("[NaN]")
    def test_infinity(self):
        with self.assertRaises(InputError): parse_json("[Infinity]")
    def test_bad_json(self):
        with self.assertRaises(InputError): parse_json("{bad")
    def test_inventory(self): self.assertEqual(len(load_inventory(self.path)),4)
    def test_empty(self):
        self.write([])
        self.assertEqual(load_inventory(self.path),[])
    def test_object_root(self):
        self.write({})
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_missing_field(self):
        self.write([{"service":"pg","engine":"postgresql"}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_extra_field(self):
        self.write([{**ROWS[0],"password":"x"}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_engine(self):
        self.write([{"service":"pg","engine":"mysql","value":1}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_negative(self):
        self.write([{**ROWS[0],"value":-1}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_boolean(self):
        self.write([{**ROWS[0],"value":True}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_string_value(self):
        self.write([{**ROWS[0],"value":"5"}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_empty_name(self):
        self.write([{**ROWS[0],"service":""}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_formula_name(self):
        self.write([{**ROWS[0],"service":"=1+1"}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_long_name(self):
        self.write([{**ROWS[0],"service":"x"*65}])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_duplicate_service(self):
        self.write([ROWS[0],ROWS[0]])
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_different_engine_same_service(self):
        self.write([ROWS[0],{"service":"pg1","engine":"kafka","value":1}])
        self.assertEqual(len(load_inventory(self.path)),2)
    def test_large(self):
        self.path.write_bytes(b" "*(MAX_BYTES+1))
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_invalid_utf8(self):
        self.path.write_bytes(b"\xff")
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_missing_file(self):
        self.path.unlink()
        with self.assertRaises(InputError): load_inventory(self.path)
    def test_symlink(self):
        link=self.path.parent/"link.json"
        try: link.symlink_to(self.path)
        except OSError: self.skipTest("symlink not supported")
        with self.assertRaises(InputError): load_inventory(link)
    def test_healthy(self): self.assertEqual(classify(ROWS[0])["status"],"healthy")
    def test_warning(self): self.assertEqual(classify(ROWS[1])["status"],"warning")
    def test_critical_es(self): self.assertEqual(classify(ROWS[2])["status"],"critical")
    def test_critical_kafka(self): self.assertEqual(classify(ROWS[3])["status"],"critical")
    def test_unit(self): self.assertEqual(classify(ROWS[0])["unit"],"seconds")
    def test_total(self): self.assertEqual(summarize(ROWS)["total"],4)
    def test_counts(self): self.assertEqual(summarize(ROWS)["counts"],{"healthy":1,"warning":1,"critical":2})
    def test_filter(self): self.assertEqual(summarize(ROWS,"postgresql")["total"],2)
    def test_empty_filter(self): self.assertEqual(summarize(ROWS,"redis")["total"],0)
    def test_sort(self): self.assertEqual(summarize(ROWS)["results"][0]["engine"],"elasticsearch")
    def test_json_output(self): self.assertTrue(json.loads(render(summarize(ROWS),"json"))["dry_run"])
    def test_csv_output(self): self.assertEqual(len(list(csv.reader(io.StringIO(render(summarize(ROWS),"csv"))))),5)
    def test_validate(self):
        code,text,_=self.invoke("validate")
        self.assertEqual(code,0)
        self.assertEqual(json.loads(text)["records"],4)
    def test_check_critical(self): self.assertEqual(self.invoke("check")[0],2)
    def test_check_warning(self): self.assertEqual(self.invoke("check","--engine","postgresql")[0],1)
    def test_check_healthy(self):
        self.write([ROWS[0]])
        self.assertEqual(self.invoke("check")[0],0)
    def test_plan(self): self.assertEqual(len(json.loads(self.invoke("plan")[1])["advisory"]),3)
    def test_plan_no_mutation(self):
        before=self.path.read_bytes()
        self.invoke("plan")
        self.assertEqual(self.path.read_bytes(),before)
    def test_plan_filter(self): self.assertEqual(len(json.loads(self.invoke("plan","--engine","postgresql")[1])["advisory"]),1)
    def test_csv_cli(self): self.assertIn("service,engine,value,unit,status",self.invoke("--format","csv","check")[1])
    def test_error_exit(self):
        self.path.write_text("{bad")
        self.assertEqual(self.invoke("validate")[0],3)
    def test_missing_subcommand(self):
        with self.assertRaises(SystemExit): build_parser().parse_args(["--inventory",str(self.path)])
    def test_invalid_engine_arg(self):
        with self.assertRaises(SystemExit): build_parser().parse_args(["--inventory",str(self.path),"check","--engine","unknown"])
    def test_no_password(self): self.assertNotIn("password",render(summarize(ROWS),"json"))
    def test_exit_codes(self): self.assertEqual((self.invoke("validate")[0],self.invoke("check")[0]),(0,2))

if __name__=="__main__": unittest.main()
```

## 4. Execute

Linux/macOS/WSL:
```bash
python3 -m unittest -v test_sre_cli.py
python3 -m py_compile sre_cli.py test_sre_cli.py
python3 sre_cli.py --inventory inventory.json validate
python3 sre_cli.py --inventory inventory.json check
python3 sre_cli.py --inventory inventory.json check --engine postgresql
python3 sre_cli.py --inventory inventory.json --format csv check
python3 sre_cli.py --inventory inventory.json plan
```

Windows PowerShell:
```powershell
py -3 -m unittest -v test_sre_cli.py
py -3 sre_cli.py --inventory inventory.json validate
py -3 sre_cli.py --inventory inventory.json check
py -3 sre_cli.py --inventory inventory.json plan
```

Expected: **healthy 1, warning 1, critical 2**. `validate` returns 0; `check` returns 2 on the fixture. A command-line usage error also returns 2 under default argparse; inspect stderr and fix the ambiguity before production use.

## 5. Failure injection
1. Omit the inventory flag or command.
2. Pass an unsupported engine.
3. Supply duplicate JSON object keys, NaN or Infinity.
4. Add extra schema fields or duplicate engine/service.
5. Supply negative, boolean or string metric values.
6. Supply invalid UTF-8 or a file exceeding 1 MiB.
7. Point to a symlink inventory file.
8. Compare JSON and CSV classification results.
9. Confirm warning-only versus critical exit codes.
10. Confirm `plan` leaves the input file byte-for-byte unchanged.

## 6. Production runbooks
**Input failure:** stop scheduled automation, inspect sanitized metadata, fix the exporter and rerun known-good fixtures.

**Critical classification:** corroborate with authoritative telemetry and SLO context; never auto-remediate based on this synthetic lab.

**Exit-code conflict:** distinguish argparse usage errors from health status using stderr and report schema; adopt unique codes before CI integration.

**Rollback:** pin previous script/schema, run regression fixtures and compare machine-readable results.

**Security:** avoid secret-bearing flags and CSV formula injection; retain strict field allowlists.

## 7. Acceptance assessment (100 points)
| Criterion | Points |
|---|---:|
| All 50 automated tests pass | 30 |
| Correct subcommands and help | 15 |
| Strict JSON/schema validation | 15 |
| Deterministic JSON and CSV output | 10 |
| Exit-code and stderr contract | 10 |
| Dry-run/no-mutation evidence | 10 |
| Runbook and rollback demonstration | 10 |

Pass target: **90/100**, with all safety checks passed. The authoring implementation passed 50 tests in Linux; independently rerun the published version on your OS.
