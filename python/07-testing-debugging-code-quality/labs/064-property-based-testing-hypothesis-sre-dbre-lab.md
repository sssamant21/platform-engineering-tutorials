# Chapter 064 — Property-Based Testing and Hypothesis SRE/DBRE Lab

**Python 3.11+ | pytest + Hypothesis | Offline, non-destructive**

Save each fenced block in the named file.

## telemetry_properties.py
```python
from dataclasses import dataclass
import json, math, re

POLICY = {"postgresql": ("replication_lag","seconds",30,120),
          "elasticsearch": ("search_latency","milliseconds",200,500),
          "kafka": ("consumer_lag","messages",1000,10000)}
class InvalidTelemetry(ValueError): pass

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

def parse(record):
    if not isinstance(record,dict) or set(record) != {"engine","service","metric","unit","value"}:
        raise InvalidTelemetry("invalid schema")
    engine, service, value = record["engine"],record["service"],record["value"]
    if not isinstance(engine,str) or engine not in POLICY:
        raise InvalidTelemetry("invalid engine")
    if not isinstance(service,str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}",service) is None:
        raise InvalidTelemetry("invalid service")
    metric,unit,_,_ = POLICY[engine]
    if record["metric"] != metric or record["unit"] != unit:
        raise InvalidTelemetry("metric mismatch")
    if type(value) not in (int,float):
        raise InvalidTelemetry("invalid type")
    try: value=float(value)
    except (OverflowError,ValueError) as exc: raise InvalidTelemetry("invalid number") from exc
    if not math.isfinite(value) or value < 0:
        raise InvalidTelemetry("invalid value")
    return Reading(engine,service,value)

def classify(reading):
    if reading.engine not in POLICY or not math.isfinite(reading.value) or reading.value < 0:
        raise InvalidTelemetry("invalid reading")
    _,_,warning,critical=POLICY[reading.engine]
    return "critical" if reading.value>=critical else "warning" if reading.value>=warning else "healthy"

def summarize(records):
    if not isinstance(records,list) or len(records)>100:
        raise InvalidTelemetry("invalid batch")
    parsed=[parse(r) for r in records]
    if len({(r.engine,r.service) for r in parsed}) != len(parsed):
        raise InvalidTelemetry("duplicate source")
    counts={"healthy":0,"warning":0,"critical":0}
    rows=[]
    for reading in sorted(parsed,key=lambda r:(r.engine,r.service)):
        severity=classify(reading)
        counts[severity]+=1
        rows.append({"engine":reading.engine,"service":reading.service,
                     "severity":severity,"value":reading.value})
    return {"dry_run":True,"total":len(rows),"counts":counts,"results":rows}

def fixtures():
    return [{"engine":e,"service":f"node{i}","metric":p[0],"unit":p[1],"value":p[2]}
            for i,(e,p) in enumerate(POLICY.items())]

if __name__=="__main__":
    print(json.dumps(summarize(fixtures()),sort_keys=True,allow_nan=False))
```

## test_properties.py
```python
import json, math
import pytest
from hypothesis import given, settings, strategies as st, example
from telemetry_properties import POLICY, InvalidTelemetry, Reading, parse, classify, summarize, fixtures

ENGINES=tuple(POLICY)
VALUES=st.floats(min_value=0,max_value=1000000,allow_nan=False,allow_infinity=False)

@st.composite
def record(draw):
    engine=draw(st.sampled_from(ENGINES))
    metric,unit,_,_=POLICY[engine]
    return {"engine":engine,"service":draw(st.from_regex(r"[A-Za-z][A-Za-z0-9_-]{0,10}",fullmatch=True)),
            "metric":metric,"unit":unit,"value":draw(VALUES)}

@st.composite
def batch(draw):
    count=draw(st.integers(0,20))
    engines=draw(st.lists(st.sampled_from(ENGINES),min_size=count,max_size=count))
    values=draw(st.lists(VALUES,min_size=count,max_size=count))
    return [{"engine":engine,"service":f"node{i}","metric":POLICY[engine][0],
             "unit":POLICY[engine][1],"value":value}
            for i,(engine,value) in enumerate(zip(engines,values))]

@settings(max_examples=100,deadline=None)
@given(record())
def test_roundtrip(r):
    reading=parse(r)
    assert (reading.engine,reading.service,reading.value)==(r["engine"],r["service"],r["value"])

@settings(max_examples=100,deadline=None)
@given(batch())
def test_conservation(rows):
    result=summarize(rows)
    assert result["total"]==len(rows)==sum(result["counts"].values())

@settings(max_examples=100,deadline=None)
@given(batch())
def test_permutation(rows):
    assert summarize(rows)==summarize(list(reversed(rows)))

@settings(max_examples=100,deadline=None)
@given(batch())
def test_json(rows):
    json.dumps(summarize(rows),allow_nan=False)

@settings(max_examples=100,deadline=None)
@given(st.sampled_from(ENGINES),VALUES,VALUES)
def test_monotonic(engine,a,b):
    low,high=sorted((a,b))
    ranks={"healthy":0,"warning":1,"critical":2}
    assert ranks[classify(Reading(engine,"node",low))] <= ranks[classify(Reading(engine,"node",high))]

@pytest.mark.parametrize("engine",ENGINES)
def test_boundaries(engine):
    _,_,warning,critical=POLICY[engine]
    assert classify(Reading(engine,"node",math.nextafter(warning,-math.inf)))=="healthy"
    assert classify(Reading(engine,"node",warning))=="warning"
    assert classify(Reading(engine,"node",math.nextafter(critical,-math.inf)))=="warning"
    assert classify(Reading(engine,"node",critical))=="critical"

@settings(max_examples=100,deadline=None)
@given(st.one_of(st.none(),st.booleans(),st.text(max_size=20),st.lists(st.integers(),max_size=5)))
def test_bad_schema(value):
    with pytest.raises(InvalidTelemetry): parse(value)

@settings(max_examples=100,deadline=None)
@given(st.one_of(st.booleans(),st.text(max_size=20),st.none(),
                 st.sampled_from([-1,float("nan"),float("inf"),float("-inf")])))
def test_bad_value(value):
    r=fixtures()[0];r["value"]=value
    with pytest.raises(InvalidTelemetry):parse(r)

@settings(max_examples=50,deadline=None)
@given(record())
def test_duplicate(r):
    with pytest.raises(InvalidTelemetry): summarize([r,dict(r)])

@settings(max_examples=50,deadline=None)
@given(record())
def test_oversize(r):
    with pytest.raises(InvalidTelemetry): summarize([r]*101)

def test_bad_unit():
    r=fixtures()[0];r["unit"]="wrong"
    with pytest.raises(InvalidTelemetry):parse(r)

def test_no_secrets():
    assert "password" not in json.dumps(summarize(fixtures()))
```

## test_stateful.py
```python
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule, invariant
from telemetry_properties import POLICY,summarize

class BatchMachine(RuleBasedStateMachine):
    @initialize()
    def initialize_batch(self):
        self.rows={}
    @rule(engine=st.sampled_from(tuple(POLICY)),index=st.integers(0,20),
          value=st.integers(0,20000))
    def upsert(self,engine,index,value):
        metric,unit,_,_=POLICY[engine]
        self.rows[(engine,index)]={"engine":engine,"service":f"node{index}",
                                   "metric":metric,"unit":unit,"value":value}
    @rule(engine=st.sampled_from(tuple(POLICY)),index=st.integers(0,20))
    def remove(self,engine,index):
        self.rows.pop((engine,index),None)
    @invariant()
    def consistent(self):
        result=summarize(list(self.rows.values()))
        assert result["total"]==len(self.rows)
        assert sum(result["counts"].values())==len(self.rows)
        assert result["results"]==sorted(result["results"],key=lambda r:(r["engine"],r["service"]))

TestBatch=BatchMachine.TestCase
TestBatch.settings=settings(max_examples=40,stateful_step_count=30,deadline=None)
```

## Execute
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install 'pytest>=8,<10' 'hypothesis>=6,<7'
python -m py_compile telemetry_properties.py test_properties.py test_stateful.py
python -m pytest -v
python telemetry_properties.py
```
On Windows use `py -3 -m venv .venv` and `.venv\Scripts\Activate.ps1`. Use pinned, reviewed dependencies for production CI. Actual pass counts require execution.

## Incident simulations
1. Change `>=` to `>` and inspect boundary counterexamples.
2. Remove sorting and observe permutation invariant failures.
3. Remove a count increment and observe conservation failures.
4. Accept NaN and observe serialization rejection.
5. Run stateful upsert/remove sequences and replay minimized failures.
6. Introduce duplicate sources, invalid units and oversized batches.
7. Save minimized cases with `@example` for permanent regression coverage.
8. Verify no production connections or writes.

## Production runbooks
**Property failure:** preserve shrunk input, block promotion, fix code, add regression, rerun.

**Flaky test:** pin versions, isolate state and remove nondeterministic timing.

**Unsafe fuzz target:** disconnect live adapters and run only synthetic fixtures.

**Rollback:** restore last accepted version and replay regression cases.

## 100-point assessment
| Area | Points |
|---|---:|
| Strategies and generators | 20 |
| Invariants and metamorphic properties | 25 |
| Shrinking and regression | 15 |
| Stateful model | 15 |
| Boundary and malformed-input fuzzing | 15 |
| Runbooks and CI safety | 10 |

Target 90/100, all safety tests passing. Test execution remains to be verified.
