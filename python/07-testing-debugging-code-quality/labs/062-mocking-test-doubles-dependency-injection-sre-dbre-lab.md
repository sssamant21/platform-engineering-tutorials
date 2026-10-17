# Chapter 062 — Mocking, Test Doubles and Dependency Injection SRE/DBRE Lab

**Python 3.11+ | Standard library only | Offline, non-destructive**

## Layout
```text
ch062/
  test_doubles_ops.py
  test_test_doubles_ops.py
```

## 1. Complete application: test_doubles_ops.py
```python
"""Chapter 062 — offline dependency injection and test doubles, Python 3.11+."""
from __future__ import annotations
import argparse
import asyncio
from dataclasses import dataclass
import json
import math
import re
import sys
from typing import Protocol

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}

class ValidationError(ValueError): pass
class TransientReadError(RuntimeError): pass

@dataclass(frozen=True)
class Reading:
    service: str
    engine: str
    value: float

class Clock(Protocol):
    def monotonic(self) -> float: ...
    async def sleep(self, seconds: float) -> None: ...

class Client(Protocol):
    async def read(self, engine: str, service: str) -> dict[str, object]: ...

class SystemClock:
    def monotonic(self) -> float:
        import time
        return time.monotonic()
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

class FakeClock:
    """Deterministic simulated clock. Only suitable for controlled tests."""
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
    def monotonic(self) -> float:
        return self.now
    async def sleep(self, seconds: float) -> None:
        if seconds < 0 or not math.isfinite(seconds):
            raise ValueError("invalid delay")
        self.sleeps.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)

class FakeClient:
    """Stateful fake with scripted transient failures and call tracing."""
    def __init__(self, data: dict[tuple[str, str], dict[str, object]],
                 failures: dict[tuple[str, str], int] | None = None) -> None:
        self.data = data
        self.failures = dict(failures or {})
        self.calls: list[tuple[str, str]] = []
    async def read(self, engine: str, service: str) -> dict[str, object]:
        key = (engine, service)
        self.calls.append(key)
        remaining = self.failures.get(key, 0)
        if remaining > 0:
            self.failures[key] = remaining - 1
            raise TransientReadError("synthetic transient failure")
        if key not in self.data:
            raise ValidationError("unknown synthetic source")
        return dict(self.data[key])

def validate(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value"}:
        raise ValidationError("invalid telemetry schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise ValidationError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise ValidationError("unknown engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ValidationError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ValidationError("numeric value required")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError("invalid numeric value") from exc
    if not math.isfinite(value) or value < 0:
        raise ValidationError("invalid metric value")
    return Reading(service, engine, value)

def classify(reading: Reading) -> str:
    if reading.engine not in POLICY or not math.isfinite(reading.value) or reading.value < 0:
        raise ValidationError("invalid reading")
    _, _, warning, critical = POLICY[reading.engine]
    return "critical" if reading.value >= critical else "warning" if reading.value >= warning else "healthy"

async def fetch_with_retry(client: Client, clock: Clock, engine: str, service: str,
                           *, attempts: int = 3, base_delay: float = 0.1,
                           deadline: float = 2.0) -> Reading:
    if engine not in POLICY or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise ValidationError("invalid target")
    if type(attempts) is not int or not 1 <= attempts <= 5:
        raise ValidationError("invalid attempts")
    if type(base_delay) not in (int, float) or not math.isfinite(base_delay) or not 0 <= base_delay <= 1:
        raise ValidationError("invalid delay")
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or not 0 < deadline <= 60:
        raise ValidationError("invalid deadline")
    end = clock.monotonic() + deadline
    for attempt in range(attempts):
        if clock.monotonic() >= end:
            raise TimeoutError("synthetic operation deadline exceeded")
        try:
            result = validate(await client.read(engine, service))
            if (result.engine, result.service) != (engine, service):
                raise ValidationError("source identity mismatch")
            if clock.monotonic() > end:
                raise TimeoutError("synthetic operation deadline exceeded")
            return result
        except TransientReadError:
            if attempt + 1 >= attempts:
                raise
            delay = base_delay * (2 ** attempt)
            if clock.monotonic() + delay >= end:
                raise TimeoutError("synthetic retry deadline exceeded")
            await clock.sleep(delay)
    raise AssertionError("unreachable")

async def analyze(client: Client, clock: Clock,
                  targets: list[tuple[str, str]]) -> dict[str, object]:
    if not isinstance(targets, list) or len(targets) > 30 or len(set(targets)) != len(targets):
        raise ValidationError("too many or duplicate targets")
    results = []
    for engine, service in targets:
        reading = await fetch_with_retry(client, clock, engine, service)
        results.append({"engine": engine, "service": service,
                        "severity": classify(reading), "value": reading.value})
    results.sort(key=lambda row: (row["engine"], row["service"]))
    counts = {severity: sum(row["severity"] == severity for row in results)
              for severity in ("healthy", "warning", "critical")}
    return {"schema_version": 1, "dry_run": True, "total": len(results),
            "counts": counts, "results": results}

def fixtures() -> tuple[FakeClient, list[tuple[str, str]]]:
    rows = [
        {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
        {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
        {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000},
    ]
    data = {(row["engine"], row["service"]): row for row in rows}
    return FakeClient(data), list(data)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline SRE/DBRE test doubles lab")
    parser.add_argument("--deadline", type=float, default=2.0)
    args = parser.parse_args(argv)
    client, targets = fixtures()
    try:
        result = asyncio.run(analyze(client, FakeClock(), targets))
    except (ValidationError, TransientReadError, TimeoutError):
        print("analysis failed: sanitized operational error", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Complete automated tests: test_test_doubles_ops.py
```python
"""Chapter 062 — unittest.mock, AsyncMock, MagicMock, patch and fake clocks."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch
from test_doubles_ops import (
    ValidationError, TransientReadError, Reading, FakeClock, FakeClient,
    SystemClock, validate, classify, fetch_with_retry, analyze, fixtures, main
)
PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45}
KEY=("postgresql","pg-replica")

class UnitTests(unittest.TestCase):
    def bad(self, **updates):
        with self.assertRaises(ValidationError): validate({**PG,**updates})
    def test_valid(self): self.assertEqual(validate(PG).value,45)
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_metric(self): self.bad(metric="wrong")
    def test_bad_unit(self): self.bad(unit="ms")
    def test_bad_service(self): self.bad(service="=cmd")
    def test_bool(self): self.bad(value=True)
    def test_nan(self): self.bad(value=float("nan"))
    def test_inf(self): self.bad(value=float("inf"))
    def test_negative(self): self.bad(value=-1)
    def test_extra(self): self.bad(password="secret")
    def test_missing(self):
        d=dict(PG); del d["unit"]
        with self.assertRaises(ValidationError): validate(d)
    def test_nonobject(self):
        with self.assertRaises(ValidationError): validate([])
    def test_classify_healthy(self):
        self.assertEqual(classify(Reading("pg","postgresql",0)),"healthy")
    def test_classify_warning(self):
        self.assertEqual(classify(Reading("pg","postgresql",30)),"warning")
    def test_classify_critical(self):
        self.assertEqual(classify(Reading("pg","postgresql",120)),"critical")
    def test_classify_bad(self):
        with self.assertRaises(ValidationError): classify(Reading("pg","postgresql",-1))
    def test_magicmock_context(self):
        manager=MagicMock()
        manager.__enter__.return_value="synthetic"
        with manager as value: self.assertEqual(value,"synthetic")
        manager.__exit__.assert_called_once()
    def test_mock_spec(self):
        client=Mock(spec=["read"])
        client.read("postgresql","pg-replica")
        client.read.assert_called_once_with("postgresql","pg-replica")
    def test_patch_fixture(self):
        with patch("test_doubles_ops.fixtures") as factory:
            factory.return_value=(FakeClient({KEY:PG}),[KEY])
            client, targets=factory()
            self.assertEqual(targets,[KEY])
            factory.assert_called_once_with()
    def test_fixture(self): self.assertEqual(len(fixtures()[1]),3)
    def test_main(self): self.assertEqual(main([]),0)
    def test_main_invalid(self): self.assertEqual(main(["--deadline","-1"]),3)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_fake_clock(self):
        clock=FakeClock()
        await clock.sleep(0.25)
        self.assertEqual(clock.monotonic(),0.25)
        self.assertEqual(clock.sleeps,[0.25])
    async def test_fake_clock_negative(self):
        with self.assertRaises(ValueError): await FakeClock().sleep(-1)
    async def test_fake_clock_nan(self):
        with self.assertRaises(ValueError): await FakeClock().sleep(float("nan"))
    async def test_fake_client(self):
        c=FakeClient({KEY:PG})
        self.assertEqual((await c.read(*KEY))["value"],45)
        self.assertEqual(c.calls,[KEY])
    async def test_fake_client_missing(self):
        with self.assertRaises(ValidationError): await FakeClient({}).read(*KEY)
    async def test_fake_client_failure(self):
        c=FakeClient({KEY:PG},{KEY:1})
        with self.assertRaises(TransientReadError): await c.read(*KEY)
        self.assertEqual((await c.read(*KEY))["value"],45)
    async def test_asyncmock(self):
        client=Mock()
        client.read=AsyncMock(return_value=PG)
        reading=await fetch_with_retry(client,FakeClock(),*KEY)
        self.assertEqual(reading.value,45)
        client.read.assert_awaited_once_with(*KEY)
    async def test_asyncmock_side_effect(self):
        client=Mock()
        client.read=AsyncMock(side_effect=[TransientReadError("synthetic"),PG])
        clock=FakeClock()
        await fetch_with_retry(client,clock,*KEY)
        self.assertEqual(client.read.await_count,2)
        self.assertEqual(clock.sleeps,[0.1])
    async def test_exponential_backoff(self):
        clock=FakeClock()
        c=FakeClient({KEY:PG},{KEY:2})
        await fetch_with_retry(c,clock,*KEY)
        self.assertEqual(clock.sleeps,[0.1,0.2])
        self.assertEqual(len(c.calls),3)
    async def test_retry_exhaustion(self):
        with self.assertRaises(TransientReadError):
            await fetch_with_retry(FakeClient({KEY:PG},{KEY:3}),FakeClock(),*KEY)
    async def test_retry_deadline(self):
        with self.assertRaises(TimeoutError):
            await fetch_with_retry(FakeClient({KEY:PG},{KEY:1}),FakeClock(),*KEY,deadline=0.05)
    async def test_bad_attempts(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:PG}),FakeClock(),*KEY,attempts=0)
    async def test_bool_attempts(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:PG}),FakeClock(),*KEY,attempts=True)
    async def test_bad_delay(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:PG}),FakeClock(),*KEY,base_delay=-1)
    async def test_nan_delay(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:PG}),FakeClock(),*KEY,base_delay=float("nan"))
    async def test_bad_deadline(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:PG}),FakeClock(),*KEY,deadline=0)
    async def test_bad_target(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:PG}),FakeClock(),"mysql","pg")
    async def test_identity_mismatch(self):
        with self.assertRaises(ValidationError):
            await fetch_with_retry(FakeClient({KEY:{**PG,"service":"other"}}),FakeClock(),*KEY)
    async def test_analyze(self):
        c,targets=fixtures()
        r=await analyze(c,FakeClock(),targets)
        self.assertEqual(r["counts"],{"healthy":0,"warning":1,"critical":2})
    async def test_empty(self):
        self.assertEqual((await analyze(FakeClient({}),FakeClock(),[]))["total"],0)
    async def test_duplicates(self):
        with self.assertRaises(ValidationError):
            await analyze(FakeClient({KEY:PG}),FakeClock(),[KEY,KEY])
    async def test_many(self):
        with self.assertRaises(ValidationError):
            await analyze(FakeClient({}),FakeClock(),[("postgresql",f"pg{i}") for i in range(31)])
    async def test_not_list(self):
        with self.assertRaises(ValidationError):
            await analyze(FakeClient({}),FakeClock(),{})
    async def test_deterministic(self):
        c,targets=fixtures()
        a=await analyze(c,FakeClock(),targets)
        b=await analyze(c,FakeClock(),list(reversed(targets)))
        self.assertEqual(a,b)
    async def test_no_secrets(self):
        c,targets=fixtures()
        self.assertNotIn("password",json.dumps(await analyze(c,FakeClock(),targets)))
    async def test_no_real_io(self):
        c,targets=fixtures()
        self.assertTrue((await analyze(c,FakeClock(),targets))["dry_run"])

if __name__=="__main__":
    unittest.main()

```

## 3. Execute
```bash
python3 -m py_compile test_doubles_ops.py test_test_doubles_ops.py
python3 -m unittest -v test_test_doubles_ops.py
python3 test_doubles_ops.py --deadline 2
```
On Windows PowerShell use `py -3` instead of `python3`.

Expected synthetic result: three telemetry readings, one warning, two critical; no real service access.

## 4. Incident simulations
1. Use `Mock(spec=...)` to verify client call arguments.
2. Use `MagicMock` for context-manager entry and exit.
3. Use `AsyncMock` to verify a client coroutine was awaited.
4. Script a transient failure followed by success using `side_effect`.
5. Configure two fake-client failures and verify exponential delays of 0.1 and 0.2 seconds of simulated time.
6. Exhaust the retry budget and verify the transient error propagates.
7. Set a synthetic deadline shorter than the next retry delay.
8. Return a reading with a different service identity and verify rejection.
9. Inject NaN, Infinity, booleans, negative values and invalid units.
10. Inject duplicate targets and more than 30 sources.
11. Patch the fixture factory at the module lookup site.
12. Reverse input order and compare deterministic reports.
13. Verify the fake client records exact interactions.
14. Demonstrate that fake-clock deadlines cannot interrupt a blocked real network await; use a disposable synthetic coroutine, not a production endpoint.

## 5. Troubleshooting and runbooks
**Wrong patch target:** inspect the importing module and patch its reference.

**Unexpected await failure:** replace synchronous Mock with AsyncMock and assert await arguments.

**Flaky retry tests:** inject FakeClock and avoid real sleeps.

**Adapter contract drift:** validate fake schemas against isolated integration tests.

**Rollback:** restore known-good dependency injection and rerun unit and contract gates.

## 6. 100-point assessment
| Criterion | Points |
|---|---:|
| Syntax and automated tests | 25 |
| Mock, MagicMock and patch correctness | 20 |
| AsyncMock and side_effect | 20 |
| Fake clients, clocks and dependency injection | 15 |
| Incident simulations and negative tests | 10 |
| Troubleshooting and runbooks | 10 |

Target 90/100 with all safety tests passing. Publication does not establish a passing test suite.
