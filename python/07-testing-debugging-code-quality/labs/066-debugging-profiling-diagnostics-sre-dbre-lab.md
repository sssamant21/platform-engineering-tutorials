# Chapter 066 — Python Debugging, Profiling and Diagnostics SRE/DBRE Lab

**Python 3.11+ | Standard library | Offline and non-destructive**

## Layout
```text
ch066/
  diagnostics_ops.py
  test_diagnostics_ops.py
```

## 1. Complete application: diagnostics_ops.py
```python
"""Chapter 066 — safe offline SRE/DBRE diagnostics (Python 3.11+)."""
from __future__ import annotations
import argparse
import cProfile
from dataclasses import dataclass
import io
import json
import math
import pstats
import re
import sys
import tracemalloc
import traceback
from typing import Callable

POLICIES = {
    "postgresql": ("replication_lag", "seconds", 30.0, 120.0),
    "elasticsearch": ("search_latency", "milliseconds", 200.0, 500.0),
    "kafka": ("consumer_lag", "messages", 1000.0, 10000.0),
}

class DiagnosticError(ValueError): pass

@dataclass(frozen=True)
class Reading:
    service: str
    engine: str
    value: float

def validate(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"service","engine","metric","unit","value"}:
        raise DiagnosticError("invalid schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise DiagnosticError("invalid service")
    if not isinstance(engine, str) or engine not in POLICIES:
        raise DiagnosticError("unknown engine")
    metric, unit, _, _ = POLICIES[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise DiagnosticError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise DiagnosticError("numeric value required")
    try: number = float(value)
    except (OverflowError, ValueError) as exc: raise DiagnosticError("invalid value") from exc
    if not math.isfinite(number) or number < 0:
        raise DiagnosticError("invalid value")
    return Reading(service, engine, number)

def classify(reading: Reading) -> str:
    if reading.engine not in POLICIES or not math.isfinite(reading.value) or reading.value < 0:
        raise DiagnosticError("invalid reading")
    _, _, warn, critical = POLICIES[reading.engine]
    return "critical" if reading.value >= critical else "warning" if reading.value >= warn else "healthy"

def analyze(raw: object) -> dict[str, object]:
    if not isinstance(raw, list) or len(raw) > 100:
        raise DiagnosticError("expected list of at most 100 readings")
    readings = [validate(row) for row in raw]
    if len({(r.engine, r.service) for r in readings}) != len(readings):
        raise DiagnosticError("duplicate source")
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    rows = []
    for reading in sorted(readings, key=lambda r: (r.engine, r.service)):
        level = classify(reading)
        counts[level] += 1
        rows.append({"service":reading.service,"engine":reading.engine,
                     "value":reading.value,"severity":level})
    return {"dry_run":True,"total":len(rows),"counts":counts,"results":rows}

def fixtures() -> list[dict[str, object]]:
    return [
        {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
        {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
        {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000},
    ]

def profile_function(func: Callable[[], object], *, limit: int = 8) -> dict[str, object]:
    if type(limit) is not int or not 1 <= limit <= 20:
        raise DiagnosticError("invalid profile limit")
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        result = func()
    finally:
        profiler.disable()
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(limit)
    # This text is intended for local synthetic training only: profile paths/names
    # may be sensitive in production. Never expose unreviewed profile output.
    return {"result":result, "profile_text":stream.getvalue()}

def memory_snapshot(func: Callable[[], object]) -> dict[str, object]:
    already_tracing = tracemalloc.is_tracing()
    if not already_tracing:
        tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        result = func()
        after, peak = tracemalloc.get_traced_memory()
        return {"result":result, "before_bytes":before, "after_bytes":after,
                "peak_bytes":peak, "delta_bytes":after-before}
    finally:
        if not already_tracing:
            tracemalloc.stop()

def safe_exception_summary(exc: Exception) -> dict[str, str]:
    # Do not expose exception message, traceback frames or local variables.
    return {"error_type":type(exc).__name__, "error":"sanitized diagnostic failure"}

def local_traceback(exc: Exception) -> str:
    """For disposable local debugging only; may include sensitive source paths."""
    return "".join(traceback.format_exception(type(exc),exc,exc.__traceback__))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline SRE/DBRE diagnostics")
    parser.add_argument("--mode", choices=("normal","profile","memory"), default="normal")
    args = parser.parse_args(argv)
    try:
        if args.mode == "profile":
            result = profile_function(lambda: analyze(fixtures()))
            # Do not serialize profile_text to stdout; report a bounded marker.
            payload = {"dry_run":True,"mode":"profile","total":result["result"]["total"],
                       "profile_generated":bool(result["profile_text"])}
        elif args.mode == "memory":
            result = memory_snapshot(lambda: analyze(fixtures()))
            payload = {"dry_run":True,"mode":"memory","total":result["result"]["total"],
                       "peak_bytes":result["peak_bytes"],"delta_bytes":result["delta_bytes"]}
        else:
            payload = analyze(fixtures())
    except DiagnosticError as exc:
        print(json.dumps(safe_exception_summary(exc)), file=sys.stderr)
        return 3
    print(json.dumps(payload,sort_keys=True,allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Complete automated tests: test_diagnostics_ops.py
```python
"""Chapter 066 standard-library tests; no external services."""
import contextlib
import io
import json
import math
import tracemalloc
import unittest
from unittest.mock import patch
from diagnostics_ops import (
    DiagnosticError, Reading, validate, classify, analyze, fixtures,
    profile_function, memory_snapshot, safe_exception_summary, local_traceback, main
)
PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45}

class ValidationTests(unittest.TestCase):
    def bad(self, **updates):
        with self.assertRaises(DiagnosticError): validate({**PG,**updates})
    def test_valid(self): self.assertEqual(validate(PG).value,45)
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_metric(self): self.bad(metric="bad")
    def test_bad_unit(self): self.bad(unit="ms")
    def test_bad_service(self): self.bad(service="=cmd")
    def test_bad_bool(self): self.bad(value=True)
    def test_bad_nan(self): self.bad(value=float("nan"))
    def test_bad_inf(self): self.bad(value=float("inf"))
    def test_bad_negative(self): self.bad(value=-1)
    def test_extra(self): self.bad(password="secret")
    def test_missing(self):
        raw=dict(PG); del raw["unit"]
        with self.assertRaises(DiagnosticError): validate(raw)
    def test_not_dict(self):
        with self.assertRaises(DiagnosticError): validate([])
    def test_healthy(self):
        self.assertEqual(classify(Reading("pg","postgresql",0)),"healthy")
    def test_warning_boundary(self):
        self.assertEqual(classify(Reading("pg","postgresql",30)),"warning")
    def test_critical_boundary(self):
        self.assertEqual(classify(Reading("pg","postgresql",120)),"critical")
    def test_classify_invalid(self):
        with self.assertRaises(DiagnosticError): classify(Reading("pg","postgresql",-1))
    def test_classify_engine(self):
        with self.assertRaises(DiagnosticError): classify(Reading("pg","mysql",1))
    def test_counts(self):
        self.assertEqual(analyze(fixtures())["counts"],{"healthy":0,"warning":1,"critical":2})
    def test_empty(self): self.assertEqual(analyze([])["total"],0)
    def test_duplicate(self):
        with self.assertRaises(DiagnosticError): analyze([PG,PG])
    def test_oversized(self):
        with self.assertRaises(DiagnosticError): analyze([PG]*101)
    def test_nonlist(self):
        with self.assertRaises(DiagnosticError): analyze({})
    def test_determinism(self):
        self.assertEqual(analyze(fixtures()),analyze(list(reversed(fixtures()))))
    def test_no_secrets(self):
        self.assertNotIn("password",json.dumps(analyze(fixtures())))

class DiagnosticTests(unittest.TestCase):
    def test_profile(self):
        result=profile_function(lambda: analyze(fixtures()))
        self.assertEqual(result["result"]["total"],3)
        self.assertIn("function calls",result["profile_text"])
    def test_profile_limit(self):
        with self.assertRaises(DiagnosticError): profile_function(lambda:None,limit=0)
    def test_profile_exception(self):
        def boom(): raise RuntimeError("synthetic")
        with self.assertRaises(RuntimeError): profile_function(boom)
    def test_memory(self):
        result=memory_snapshot(lambda: analyze(fixtures()))
        self.assertGreaterEqual(result["peak_bytes"],result["after_bytes"])
        self.assertEqual(result["result"]["total"],3)
    def test_memory_tracer_restored(self):
        before=tracemalloc.is_tracing()
        memory_snapshot(lambda: 1)
        self.assertEqual(tracemalloc.is_tracing(),before)
    def test_memory_exception_cleanup(self):
        before=tracemalloc.is_tracing()
        def boom(): raise RuntimeError("synthetic")
        with self.assertRaises(RuntimeError): memory_snapshot(boom)
        self.assertEqual(tracemalloc.is_tracing(),before)
    def test_safe_error(self):
        error=safe_exception_summary(ValueError("password=secret"))
        self.assertNotIn("secret",json.dumps(error))
        self.assertEqual(error["error_type"],"ValueError")
    def test_local_traceback(self):
        try: raise RuntimeError("synthetic local")
        except RuntimeError as exc:
            self.assertIn("RuntimeError",local_traceback(exc))
    def test_main_normal(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main([]),0)
        self.assertEqual(json.loads(out.getvalue())["total"],3)
    def test_main_profile(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--mode","profile"]),0)
        self.assertTrue(json.loads(out.getvalue())["profile_generated"])
    def test_main_memory(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--mode","memory"]),0)
        self.assertGreaterEqual(json.loads(out.getvalue())["peak_bytes"],0)
    def test_main_sanitized(self):
        with patch("diagnostics_ops.fixtures",side_effect=DiagnosticError("password=secret")):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(main([]),3)
        self.assertNotIn("secret",err.getvalue())

if __name__=="__main__": unittest.main()

```

## 3. Execute
Linux/macOS/WSL:
```bash
python3 -m py_compile diagnostics_ops.py test_diagnostics_ops.py
python3 -m unittest -v test_diagnostics_ops.py
python3 diagnostics_ops.py
python3 diagnostics_ops.py --mode profile
python3 diagnostics_ops.py --mode memory
python3 -m cProfile -s cumulative diagnostics_ops.py
```

Windows PowerShell: replace `python3` with `py -3`.

Expected offline telemetry summary: 3 synthetic readings, 1 warning and 2 critical. Memory allocation counts and profiling timings vary by interpreter and host.

## 4. Interactive debugging (disposable lab only)
```bash
python3 -m pdb diagnostics_ops.py
```
In pdb: `b analyze`, `c`, `n`, `p raw`, `bt`, `q`. Alternatively add `breakpoint()` temporarily to `analyze` and remove it before committing. Never enable interactive debugging in a live SRE/DBRE automation worker.

## 5. Local faulthandler exercise
Create `hang_probe.py`:
```python
import faulthandler
import sys
import time

faulthandler.enable(file=sys.stderr)
faulthandler.dump_traceback_later(0.2, repeat=False, file=sys.stderr)
try:
    time.sleep(0.3)  # Synthetic bounded delay, no external I/O.
finally:
    faulthandler.cancel_dump_traceback_later()
```
Run `python3 hang_probe.py` and inspect the synthetic stack dump. The output may include local file paths; do not publish unredacted dumps from production.

## 6. Incident simulations
1. Reject NaN, Infinity, negative and boolean telemetry.
2. Inject duplicate sources and oversized batches.
3. Capture a sanitized exception and confirm secrets do not appear.
4. Inspect a raw traceback **locally only** and compare with sanitized output.
5. Run `pdb` and inspect `analyze` call arguments.
6. Run cProfile and compare cumulative vs self time.
7. Run tracemalloc and inspect current/peak traced allocations.
8. Verify tracemalloc is restored when the diagnostic function raises.
9. Run faulthandler's bounded synthetic hang probe.
10. Compare Python allocation metrics with OS RSS metrics.
11. Introduce a CPU-heavy pure-Python loop in a disposable copy and profile it.
12. Remove all debugging instrumentation and rerun regression tests.

## 7. Production runbooks
**CPU incident:** capture bounded profile, identify hot function, test optimization and roll back safely.

**Memory incident:** compare tracemalloc and RSS, isolate retained allocations, apply capacity limits and restore stable version.

**Hung worker:** capture protected thread stacks, inspect deadlocks and I/O timeouts, restart using change-controlled procedures.

**Sensitive logs:** restrict access, remove exposed artifacts and rotate credentials when applicable.

**Rollback:** restore code, rerun unit tests and verify resource baselines.

## 8. 100-point acceptance assessment
| Criterion | Points |
|---|---:|
| Input validation and automated tests | 20 |
| pdb and breakpoint debugging | 15 |
| traceback and faulthandler diagnostics | 20 |
| cProfile and pstats analysis | 15 |
| tracemalloc and memory diagnostics | 15 |
| Incident simulations, runbooks and rollback | 15 |

**Pass:** 90/100, all safety tests passing, and independently verified lab execution. Publication does not imply the tests or profiling were executed.
