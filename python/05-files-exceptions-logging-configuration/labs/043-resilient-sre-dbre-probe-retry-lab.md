# Chapter 043 — Resilient SRE/DBRE Probe and Retry Lab

**Python 3.10+ · standard library · offline synthetic simulation**

## Objective

Implement explicit transient/permanent/timeout errors, immutable retry policy, bounded exponential backoff, deterministic virtual time, a JSON CLI and automated tests. No infrastructure connections or mutations.

## Layout

```text
ch043/
  resilience.py
  cli.py
  sample.json
  test_resilience.py
```

## resilience.py

```python
from dataclasses import dataclass
from enum import Enum
import math

class FailureKind(str, Enum):
    TRANSIENT="transient"
    PERMANENT="permanent"
    TIMEOUT="timeout"
    EXHAUSTED="exhausted"

class OperationalError(Exception):
    kind=FailureKind.PERMANENT
    def __init__(self, message, *, service="unknown"):
        super().__init__(message)
        self.service=service

class TransientError(OperationalError): kind=FailureKind.TRANSIENT
class PermanentError(OperationalError): kind=FailureKind.PERMANENT
class DeadlineExceeded(OperationalError): kind=FailureKind.TIMEOUT

class RetryExhausted(OperationalError):
    kind=FailureKind.EXHAUSTED
    def __init__(self, message, *, service="unknown", attempts=0):
        super().__init__(message,service=service)
        self.attempts=attempts

@dataclass(frozen=True,slots=True)
class RetryPolicy:
    max_attempts:int=3
    base_delay:float=0.1
    max_delay:float=1.0
    deadline:float=5.0

    def __post_init__(self):
        if isinstance(self.max_attempts,bool) or not isinstance(self.max_attempts,int) or not 1<=self.max_attempts<=10:
            raise ValueError("max_attempts must be 1..10")
        for name in ("base_delay","max_delay","deadline"):
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError(f"invalid {name}")
        if self.base_delay>self.max_delay or self.deadline<=0:
            raise ValueError("invalid retry budget")

    def delay_for(self,n):
        if isinstance(n,bool) or not isinstance(n,int) or n<1:
            raise ValueError("invalid failure number")
        return min(self.max_delay,self.base_delay*2**(n-1))

@dataclass(frozen=True,slots=True)
class Outcome:
    service:str
    status:str
    attempts:int
    value:str|None
    failure_kind:str|None

class VirtualClock:
    def __init__(self):
        self.now=0.0
        self.sleeps=[]
    def sleep(self,seconds):
        if seconds<0: raise ValueError("negative sleep")
        self.sleeps.append(seconds)
        self.now+=seconds

class SyntheticProbe:
    def __init__(self,service,actions):
        if not isinstance(service,str) or not service or len(service)>64:
            raise ValueError("invalid service")
        if not isinstance(actions,(list,tuple)) or not actions or any(a not in ("ok","transient","permanent","timeout") for a in actions):
            raise ValueError("invalid actions")
        self.service=service
        self.actions=tuple(actions)
        self.calls=0

    def check(self):
        action=self.actions[min(self.calls,len(self.actions)-1)]
        self.calls+=1
        if action=="transient": raise TransientError("synthetic transient",service=self.service)
        if action=="permanent": raise PermanentError("synthetic permanent",service=self.service)
        if action=="timeout": raise DeadlineExceeded("synthetic timeout",service=self.service)
        return "healthy"

def run_probe(probe,policy,clock):
    if not isinstance(probe,SyntheticProbe) or not isinstance(policy,RetryPolicy) or not isinstance(clock,VirtualClock):
        raise TypeError("invalid runner arguments")
    start=clock.now
    for attempt in range(1,policy.max_attempts+1):
        try:
            return Outcome(probe.service,"ok",attempt,probe.check(),None)
        except PermanentError as exc:
            return Outcome(probe.service,"failed",attempt,None,exc.kind.value)
        except (TransientError,DeadlineExceeded) as exc:
            if attempt==policy.max_attempts:
                exhausted=RetryExhausted("attempts exhausted",service=probe.service,attempts=attempt)
                exhausted.__cause__=exc
                return Outcome(probe.service,"failed",attempt,None,exhausted.kind.value)
            delay=policy.delay_for(attempt)
            if clock.now-start+delay>=policy.deadline:
                return Outcome(probe.service,"failed",attempt,None,FailureKind.TIMEOUT.value)
            clock.sleep(delay)
    raise AssertionError("unreachable")

def batch_report(rows,policy=None):
    if not isinstance(rows,list) or len(rows)>100: raise ValueError("invalid batch")
    policy=RetryPolicy() if policy is None else policy
    if not isinstance(policy,RetryPolicy): raise TypeError("invalid policy")
    seen=set()
    results=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"service","actions"}: raise ValueError("invalid row")
        probe=SyntheticProbe(row["service"],row["actions"])
        if probe.service in seen: raise ValueError("duplicate service")
        seen.add(probe.service)
        outcome=run_probe(probe,policy,VirtualClock())
        results.append({"service":outcome.service,"status":outcome.status,"attempts":outcome.attempts,
                        "value":outcome.value,"failure_kind":outcome.failure_kind})
    return {"schema_version":1,"dry_run":True,"results":sorted(results,key=lambda x:x["service"])}
```

## cli.py

```python
import argparse
import json
from pathlib import Path
from resilience import batch_report

MAX_INPUT=1024*1024

def run(path):
    path=Path(path)
    if path.stat().st_size>MAX_INPUT: raise ValueError("input too large")
    with path.open(encoding="utf-8") as handle:
        content=handle.read(MAX_INPUT+1)
    if len(content.encode("utf-8"))>MAX_INPUT: raise ValueError("input too large")
    rows=json.loads(content,parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    return batch_report(rows)

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline SRE retry simulation")
    parser.add_argument("--input",type=Path,required=True)
    args=parser.parse_args(argv)
    try: result=run(args.input)
    except (OSError,ValueError,TypeError,UnicodeError) as exc: parser.error(str(exc))
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
```

## sample.json

```json
[
 {"service":"postgresql-replica","actions":["transient","ok"]},
 {"service":"elasticsearch-search","actions":["timeout","transient","ok"]},
 {"service":"kafka-consumer","actions":["permanent"]},
 {"service":"redis-cache","actions":["transient","transient","transient"]}
]
```

## test_resilience.py

```python
import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import FrozenInstanceError
from resilience import *
from cli import run,main

class ResilienceTests(unittest.TestCase):
    def p(self,**kw): return RetryPolicy(**kw)
    def q(self,actions=("ok",)): return SyntheticProbe("pg",actions)
    def test_enum(self): self.assertEqual(FailureKind.TRANSIENT.value,"transient")
    def test_hierarchy(self): self.assertIsInstance(TransientError("x"),OperationalError)
    def test_service(self): self.assertEqual(PermanentError("x",service="es").service,"es")
    def test_exhaustion_metadata(self): self.assertEqual(RetryExhausted("x",attempts=3).attempts,3)
    def test_policy(self): self.assertEqual(self.p().max_attempts,3)
    def test_frozen(self):
        with self.assertRaises(FrozenInstanceError): self.p().max_attempts=5
    def test_attempts_zero(self):
        with self.assertRaises(ValueError): self.p(max_attempts=0)
    def test_attempts_bool(self):
        with self.assertRaises(ValueError): self.p(max_attempts=True)
    def test_attempts_high(self):
        with self.assertRaises(ValueError): self.p(max_attempts=11)
    def test_negative_delay(self):
        with self.assertRaises(ValueError): self.p(base_delay=-1)
    def test_nan(self):
        with self.assertRaises(ValueError): self.p(deadline=float("nan"))
    def test_zero_deadline(self):
        with self.assertRaises(ValueError): self.p(deadline=0)
    def test_delay_order(self):
        with self.assertRaises(ValueError): self.p(base_delay=2,max_delay=1)
    def test_delay_first(self): self.assertEqual(self.p().delay_for(1),0.1)
    def test_delay_second(self): self.assertEqual(self.p().delay_for(2),0.2)
    def test_delay_cap(self): self.assertEqual(self.p().delay_for(10),1.0)
    def test_bad_failure_number(self):
        with self.assertRaises(ValueError): self.p().delay_for(0)
    def test_clock(self):
        c=VirtualClock(); c.sleep(0.5); self.assertEqual(c.now,0.5)
    def test_clock_negative(self):
        with self.assertRaises(ValueError): VirtualClock().sleep(-1)
    def test_probe_ok(self): self.assertEqual(self.q().check(),"healthy")
    def test_probe_transient(self):
        with self.assertRaises(TransientError): self.q(["transient"]).check()
    def test_probe_permanent(self):
        with self.assertRaises(PermanentError): self.q(["permanent"]).check()
    def test_probe_timeout(self):
        with self.assertRaises(DeadlineExceeded): self.q(["timeout"]).check()
    def test_bad_service(self):
        with self.assertRaises(ValueError): SyntheticProbe("",["ok"])
    def test_empty_actions(self):
        with self.assertRaises(ValueError): SyntheticProbe("pg",[])
    def test_unknown_action(self):
        with self.assertRaises(ValueError): SyntheticProbe("pg",["delete"])
    def test_success(self): self.assertEqual(run_probe(self.q(),self.p(),VirtualClock()).attempts,1)
    def test_retry_success(self): self.assertEqual(run_probe(self.q(["transient","ok"]),self.p(),VirtualClock()).attempts,2)
    def test_timeout_recovery(self): self.assertEqual(run_probe(self.q(["timeout","ok"]),self.p(),VirtualClock()).status,"ok")
    def test_permanent_no_retry(self): self.assertEqual(run_probe(self.q(["permanent","ok"]),self.p(),VirtualClock()).attempts,1)
    def test_exhausted(self): self.assertEqual(run_probe(self.q(["transient"]),self.p(),VirtualClock()).failure_kind,"exhausted")
    def test_deadline(self): self.assertEqual(run_probe(self.q(["transient"]),self.p(deadline=0.1),VirtualClock()).failure_kind,"timeout")
    def test_attempt_cap(self): self.assertEqual(run_probe(self.q(["transient"]),self.p(max_attempts=2),VirtualClock()).attempts,2)
    def test_sleep(self):
        c=VirtualClock(); run_probe(self.q(["transient","ok"]),self.p(),c)
        self.assertEqual(c.sleeps,[0.1])
    def test_bad_runner(self):
        with self.assertRaises(TypeError): run_probe(None,self.p(),VirtualClock())
    def test_batch(self): self.assertEqual(batch_report([{"service":"pg","actions":["ok"]}])["results"][0]["status"],"ok")
    def test_batch_empty(self): self.assertEqual(batch_report([])["results"],[])
    def test_batch_schema(self):
        with self.assertRaises(ValueError): batch_report([{"service":"pg"}])
    def test_batch_duplicate(self):
        with self.assertRaises(ValueError): batch_report([{"service":"pg","actions":["ok"]}]*2)
    def test_batch_sorted(self):
        rows=[{"service":"z","actions":["ok"]},{"service":"a","actions":["ok"]}]
        self.assertEqual([r["service"] for r in batch_report(rows)["results"]],["a","z"])
    def test_batch_limit(self):
        with self.assertRaises(ValueError): batch_report([{"service":str(i),"actions":["ok"]} for i in range(101)])
    def test_batch_policy(self):
        with self.assertRaises(TypeError): batch_report([],policy="bad")
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"; p.write_text(json.dumps([{"service":"pg","actions":["ok"]}]))
            self.assertTrue(run(p)["dry_run"])
    def test_cli_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"; p.write_text("{bad")
            with self.assertRaises(ValueError): run(p)
    def test_cli_large(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json"; p.write_text(" "*(1024*1024+1))
            with self.assertRaises(ValueError): run(p)
    def test_cli_missing(self):
        with self.assertRaises(SystemExit): main(["--input","does-not-exist.json"])

if __name__=="__main__": unittest.main()
```

## Run

```bash
python3 -m unittest -v test_resilience.py
python3 cli.py --input sample.json
python3 -m py_compile resilience.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m unittest -v test_resilience.py
py -3 cli.py --input sample.json
```

## Failure injection and runbooks

- **Transient then success:** exactly two attempts; check backoff.
- **Permanent failure:** stop after one attempt; do not retry authorization or schema errors.
- **Timeout:** use remaining deadline; do not assume a remote write was rolled back.
- **Exhaustion:** report failure, escalate and avoid retry storms.
- **Invalid input:** reject malformed, duplicate or oversized scenarios.
- **Recovery:** adjust policy in a synthetic fixture, run regression tests, and roll back aggressive retry settings when they amplify load.

## Acceptance

- [ ] All 46 published tests pass on the learner's machine.
- [ ] Retry budgets, exception hierarchy, and deterministic output validated.
- [ ] Four failure scenarios documented.
- [ ] No live infrastructure accessed or mutated.

**Authoring verification:** An equivalent 46-test implementation was executed successfully in the Linux sandbox; rerun this published version locally before treating it as validated. The virtual clock does not implement real wall-clock timeouts.
