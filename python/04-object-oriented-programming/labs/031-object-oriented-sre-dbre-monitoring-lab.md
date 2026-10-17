# Chapter 031 — Object-Oriented SRE/DBRE Monitoring Lab

**Python 3.10+ | Standard library only | Offline/read-only**

## Architecture and files

```text
ch031/
  monitor.py
  cli.py
  sample.json
  test_monitor.py
```

Objects: immutable `MetricSnapshot`, validated `ThresholdPolicy`, encapsulated `ServiceMonitor`, and composed `MonitoringFleet`. All input is synthetic; no service connections are made.

## 1. `monitor.py`

```python
"""Validated, bounded, offline SRE monitoring domain model."""
from dataclasses import dataclass
import math


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return float(value)


@dataclass(frozen=True)
class MetricSnapshot:
    latency_ms: float
    errors: int
    requests: int

    def __post_init__(self):
        number(self.latency_ms, "latency_ms")
        if (isinstance(self.errors, bool) or isinstance(self.requests, bool)
                or not isinstance(self.errors, int)
                or not isinstance(self.requests, int)
                or self.requests < 1 or not 0 <= self.errors <= self.requests):
            raise ValueError("invalid request/error counts")

    @property
    def error_rate(self):
        return self.errors / self.requests


class ThresholdPolicy:
    def __init__(self, warning_ms=200, critical_ms=500, warning_rate=0.02, critical_rate=0.10):
        values = [number(v, "threshold") for v in (
            warning_ms, critical_ms, warning_rate, critical_rate
        )]
        w_ms, c_ms, w_rate, c_rate = values
        if not 0 < w_ms < c_ms or not 0 < w_rate < c_rate <= 1:
            raise ValueError("thresholds must be ordered and positive")
        self._warning_ms, self._critical_ms = w_ms, c_ms
        self._warning_rate, self._critical_rate = w_rate, c_rate

    @property
    def warning_ms(self):
        return self._warning_ms

    @property
    def critical_ms(self):
        return self._critical_ms

    def classify(self, snapshot):
        if not isinstance(snapshot, MetricSnapshot):
            raise TypeError("expected MetricSnapshot")
        if snapshot.latency_ms >= self._critical_ms or snapshot.error_rate >= self._critical_rate:
            return "critical"
        if snapshot.latency_ms >= self._warning_ms or snapshot.error_rate >= self._warning_rate:
            return "warning"
        return "healthy"


class ServiceMonitor:
    def __init__(self, service, policy=None, history_limit=10):
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError("invalid service name")
        if policy is not None and not isinstance(policy, ThresholdPolicy):
            raise TypeError("invalid policy")
        if isinstance(history_limit, bool) or not isinstance(history_limit, int) or not 1 <= history_limit <= 1000:
            raise ValueError("history_limit must be in 1..1000")
        self._service = service
        self._policy = policy if policy is not None else ThresholdPolicy()
        self._limit = history_limit
        self._history = []

    @property
    def service(self):
        return self._service

    @property
    def history(self):
        return tuple(self._history)

    def record(self, snapshot):
        if not isinstance(snapshot, MetricSnapshot):
            raise TypeError("expected MetricSnapshot")
        # Validate policy before mutating state.
        status = self._policy.classify(snapshot)
        self._history.append(snapshot)
        if len(self._history) > self._limit:
            del self._history[:-self._limit]
        return status

    def summary(self):
        if not self._history:
            return {"service": self._service, "samples": 0, "status": "unknown"}
        latest = self._history[-1]
        return {
            "service": self._service,
            "samples": len(self._history),
            "latency_ms": latest.latency_ms,
            "error_rate": round(latest.error_rate, 6),
            "status": self._policy.classify(latest),
        }


class MonitoringFleet:
    def __init__(self):
        self._monitors = {}

    def add(self, monitor):
        if not isinstance(monitor, ServiceMonitor):
            raise TypeError("expected ServiceMonitor")
        if monitor.service in self._monitors:
            raise ValueError("duplicate service")
        self._monitors[monitor.service] = monitor

    def report(self):
        results = [self._monitors[name].summary() for name in sorted(self._monitors)]
        return {"schema_version": 1, "service_count": len(results), "services": results}
```

## 2. `cli.py`

```python
"""Offline JSON-file adapter for the object model."""
import argparse
import json
from pathlib import Path
from monitor import MetricSnapshot, MonitoringFleet, ServiceMonitor


def run(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        rows = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("input file could not be read or parsed") from exc
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    fleet = MonitoringFleet()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"service", "latency_ms", "errors", "requests"}:
            raise ValueError("invalid row schema")
        monitor = ServiceMonitor(row["service"])
        snapshot = MetricSnapshot(row["latency_ms"], row["errors"], row["requests"])
        monitor.record(snapshot)
        fleet.add(monitor)
    return fleet.report()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only SRE object-model lab")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.input)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. `sample.json`

```json
[
  {"service":"api","latency_ms":120,"errors":1,"requests":100},
  {"service":"postgresql","latency_ms":650,"errors":12,"requests":100},
  {"service":"elasticsearch","latency_ms":250,"errors":1,"requests":100}
]
```

## 4. `test_monitor.py` — 30 tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from monitor import MetricSnapshot, ThresholdPolicy, ServiceMonitor, MonitoringFleet
from cli import run


class MonitorTests(unittest.TestCase):
    def snap(self, latency=100, errors=1, requests=100):
        return MetricSnapshot(latency, errors, requests)

    def test_snapshot(self): self.assertEqual(self.snap().latency_ms, 100)
    def test_frozen(self):
        with self.assertRaises(FrozenInstanceError): self.snap().errors = 4
    def test_error_rate(self): self.assertEqual(self.snap(errors=5).error_rate, 0.05)
    def test_negative_latency(self):
        with self.assertRaises(ValueError): self.snap(latency=-1)
    def test_nan(self):
        with self.assertRaises(ValueError): self.snap(latency=float("nan"))
    def test_infinity(self):
        with self.assertRaises(ValueError): self.snap(latency=float("inf"))
    def test_boolean_latency(self):
        with self.assertRaises(ValueError): self.snap(latency=True)
    def test_boolean_count(self):
        with self.assertRaises(ValueError): self.snap(errors=True)
    def test_zero_requests(self):
        with self.assertRaises(ValueError): self.snap(requests=0)
    def test_too_many_errors(self):
        with self.assertRaises(ValueError): self.snap(errors=101)
    def test_policy_healthy(self): self.assertEqual(ThresholdPolicy().classify(self.snap()), "healthy")
    def test_policy_warning_latency(self): self.assertEqual(ThresholdPolicy().classify(self.snap(latency=200)), "warning")
    def test_policy_critical_latency(self): self.assertEqual(ThresholdPolicy().classify(self.snap(latency=500)), "critical")
    def test_policy_warning_errors(self): self.assertEqual(ThresholdPolicy().classify(self.snap(errors=2)), "warning")
    def test_policy_critical_errors(self): self.assertEqual(ThresholdPolicy().classify(self.snap(errors=10)), "critical")
    def test_custom_policy(self): self.assertEqual(ThresholdPolicy(50, 100).classify(self.snap(latency=75)), "warning")
    def test_invalid_policy(self):
        with self.assertRaises(ValueError): ThresholdPolicy(500, 200)
    def test_policy_property(self): self.assertEqual(ThresholdPolicy().warning_ms, 200)
    def test_empty_service(self):
        with self.assertRaises(ValueError): ServiceMonitor("")
    def test_empty_monitor(self): self.assertEqual(ServiceMonitor("api").summary()["status"], "unknown")
    def test_record(self):
        monitor = ServiceMonitor("api")
        self.assertEqual(monitor.record(self.snap()), "healthy")
    def test_history_tuple(self):
        monitor = ServiceMonitor("api")
        monitor.record(self.snap())
        self.assertIsInstance(monitor.history, tuple)
    def test_bounded_history(self):
        monitor = ServiceMonitor("api", history_limit=2)
        for latency in (10, 20, 30): monitor.record(self.snap(latency=latency))
        self.assertEqual([s.latency_ms for s in monitor.history], [20, 30])
    def test_instance_isolation(self):
        a, b = ServiceMonitor("a"), ServiceMonitor("b")
        a.record(self.snap())
        self.assertEqual(len(b.history), 0)
    def test_invalid_record_no_mutation(self):
        monitor = ServiceMonitor("api")
        with self.assertRaises(TypeError): monitor.record({})
        self.assertEqual(len(monitor.history), 0)
    def test_invalid_history_limit(self):
        with self.assertRaises(ValueError): ServiceMonitor("api", history_limit=0)
    def test_fleet_sort(self):
        fleet = MonitoringFleet()
        fleet.add(ServiceMonitor("z"))
        fleet.add(ServiceMonitor("a"))
        self.assertEqual(fleet.report()["services"][0]["service"], "a")
    def test_fleet_duplicate(self):
        fleet = MonitoringFleet()
        fleet.add(ServiceMonitor("api"))
        with self.assertRaises(ValueError): fleet.add(ServiceMonitor("api"))
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.json"
            path.write_text(json.dumps([{"service":"api","latency_ms":120,"errors":1,"requests":100}]), encoding="utf-8")
            self.assertEqual(run(path)["service_count"], 1)
    def test_cli_invalid_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps([{"service":"api"}]), encoding="utf-8")
            with self.assertRaises(ValueError): run(path)


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute

Linux / macOS / WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_monitor.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile monitor.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_monitor.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile monitor.py cli.py
```

Expected: **30 tests** and deterministic report with three services: api healthy, elasticsearch warning, postgresql critical. These are synthetic classifications, not live health checks.

## 6. Failure injection and troubleshooting

1. Change latency to `-1`, `NaN` or `Infinity`: reject invalid/nonfinite data.
2. Set `errors > requests`: reject invalid count relationship.
3. Duplicate a service: reject duplicate fleet membership.
4. Attempt to modify a frozen snapshot: raise `FrozenInstanceError`.
5. Add three samples to a monitor with `history_limit=2`: retain only the latest two.
6. Replace the JSON array with an object: reject schema.
7. Use an unknown field: reject the row before reporting.

If a test fails, inspect the class invariant, constructor input and method boundary. Do not weaken validation to make a synthetic fixture pass. The CLI uses no credentials or network calls.

## 7. Production runbooks

**Policy drift:** review thresholds and change approvals; create new `ThresholdPolicy` objects rather than mutating private fields.

**Unexpected shared state:** inspect class attributes versus `self` attributes and reproduce with two instances.

**Memory pressure:** verify `history_limit` and number of monitor objects; bound retention.

**Concurrency:** do not share mutable `ServiceMonitor` instances across threads without synchronization.

**Audit:** preserve sanitized fixture, Python version, test output and expected policy.

## 8. Acceptance

- [ ] All 30 tests pass locally.
- [ ] Snapshots are immutable and strictly validated.
- [ ] Thresholds are ordered and encapsulated.
- [ ] Monitors have independent bounded histories.
- [ ] Fleet rejects duplicate services.
- [ ] CLI output is deterministic and contains no secrets.
- [ ] No live service access or destructive operations occur.

**Execution status:** Source and tests are published; learner-side test execution remains pending.
