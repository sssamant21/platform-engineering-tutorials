# Chapter 032 — SRE/DBRE Probe Factories and Lifecycle Lab

**Python 3.10+ | Standard library | Offline/read-only**

## Goal

Implement a validated configuration value object, polymorphic classmethod factories, static validation, stateful instance methods, and an idempotent context-managed session over synthetic latency data.

## Project

```text
ch032/
  probe.py
  cli.py
  sample.json
  test_probe.py
```

### 1. `probe.py`

```python
"""Offline lifecycle-safe SRE probe. No network or destructive actions."""
from dataclasses import dataclass
import math


class SessionClosed(RuntimeError):
    pass


class SourceExhausted(RuntimeError):
    pass


@dataclass(frozen=True)
class ProbeConfig:
    service: str
    environment: str = "staging"
    warning_ms: float = 200.0
    critical_ms: float = 500.0

    @staticmethod
    def valid_service(value):
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 64

    def __post_init__(self):
        if not self.valid_service(self.service):
            raise ValueError("invalid service")
        if self.environment not in ("dev", "staging", "prod"):
            raise ValueError("invalid environment")
        for value in (self.warning_ms, self.critical_ms):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("thresholds must be finite numeric values")
        if not 0 < self.warning_ms < self.critical_ms:
            raise ValueError("thresholds must be ordered")

    @classmethod
    def from_mapping(cls, data):
        if not isinstance(data, dict) or not {"service"} <= set(data) or set(data) - {
            "service", "environment", "warning_ms", "critical_ms"
        }:
            raise ValueError("invalid config schema")
        return cls(**data)

    @classmethod
    def for_staging(cls, service):
        return cls(service=service, environment="staging")


class ProbeSession:
    """Explicit single-use session. Owns an immutable synthetic data source."""

    active_sessions = 0

    def __init__(self, config, samples):
        if not isinstance(config, ProbeConfig):
            raise TypeError("expected ProbeConfig")
        if not isinstance(samples, (list, tuple)):
            raise TypeError("samples must be a list or tuple")
        validated = []
        for value in samples:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("samples must be finite nonnegative numbers")
            validated.append(float(value))
        self._config = config
        self._samples = tuple(validated)
        self._index = 0
        self._state = "new"

    @property
    def state(self):
        return self._state

    @property
    def remaining(self):
        return len(self._samples) - self._index

    @classmethod
    def from_mapping(cls, config_mapping, samples):
        return cls(ProbeConfig.from_mapping(config_mapping), samples)

    @staticmethod
    def classify(latency, config):
        if not isinstance(config, ProbeConfig):
            raise TypeError("expected ProbeConfig")
        if isinstance(latency, bool) or not isinstance(latency, (int, float)) or not math.isfinite(latency) or latency < 0:
            raise ValueError("invalid latency")
        if latency >= config.critical_ms:
            return "critical"
        if latency >= config.warning_ms:
            return "warning"
        return "healthy"

    def open(self):
        if self._state != "new":
            raise RuntimeError("session cannot be reopened")
        self._state = "open"
        type(self).active_sessions += 1
        return self

    def sample(self):
        if self._state != "open":
            raise SessionClosed("session is not open")
        if self._index >= len(self._samples):
            raise SourceExhausted("no more synthetic samples")
        latency = self._samples[self._index]
        self._index += 1
        return {
            "service": self._config.service,
            "environment": self._config.environment,
            "latency_ms": latency,
            "status": self.classify(latency, self._config),
        }

    def close(self):
        if self._state == "open":
            type(self).active_sessions -= 1
        self._state = "closed"

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
```

The `active_sessions` counter is an educational diagnostic, **not thread-safe production telemetry**. The lab creates base-class sessions; subclasses overriding lifecycle logic would need their own counter policy.

### 2. `cli.py`

```python
"""Read synthetic fixture and print a deterministic report."""
import argparse
import json
from pathlib import Path
from probe import ProbeSession


def run(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("input file could not be read or parsed") from exc
    if not isinstance(data, dict) or set(data) != {"config", "samples"}:
        raise ValueError("invalid fixture schema")
    session = ProbeSession.from_mapping(data["config"], data["samples"])
    results = []
    with session:
        while session.remaining:
            results.append(session.sample())
    return {"schema_version": 1, "results": results, "session_state": session.state}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline SRE lifecycle probe")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.input)
    except (ValueError, TypeError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 3. `sample.json`

```json
{
  "config": {"service":"postgresql","environment":"staging","warning_ms":200,"critical_ms":500},
  "samples": [100, 250, 650]
}
```

### 4. `test_probe.py` — 32 tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from probe import ProbeConfig, ProbeSession, SessionClosed, SourceExhausted
from cli import run


class ConfigTests(unittest.TestCase):
    def test_defaults(self): self.assertEqual(ProbeConfig("api").environment, "staging")
    def test_staging_factory(self): self.assertEqual(ProbeConfig.for_staging("db").service, "db")
    def test_mapping_factory(self): self.assertEqual(ProbeConfig.from_mapping({"service":"db"}).service, "db")
    def test_static_validation(self): self.assertTrue(ProbeConfig.valid_service("db"))
    def test_invalid_service(self):
        with self.assertRaises(ValueError): ProbeConfig("")
    def test_invalid_environment(self):
        with self.assertRaises(ValueError): ProbeConfig("api", "invalid")
    def test_bad_threshold_order(self):
        with self.assertRaises(ValueError): ProbeConfig("api", warning_ms=500, critical_ms=200)
    def test_nan_threshold(self):
        with self.assertRaises(ValueError): ProbeConfig("api", warning_ms=float("nan"))
    def test_bool_threshold(self):
        with self.assertRaises(ValueError): ProbeConfig("api", warning_ms=True)
    def test_unknown_config_key(self):
        with self.assertRaises(ValueError): ProbeConfig.from_mapping({"service":"api","token":"secret"})
    def test_missing_service(self):
        with self.assertRaises(ValueError): ProbeConfig.from_mapping({"environment":"staging"})
    def test_frozen(self):
        with self.assertRaises(FrozenInstanceError): ProbeConfig("api").service = "changed"
    def test_subclass_factory(self):
        class Child(ProbeConfig):
            pass
        self.assertIsInstance(Child.for_staging("api"), Child)
    def test_classmethod_session(self):
        self.assertEqual(ProbeSession.from_mapping({"service":"api"}, [1]).remaining, 1)
    def test_config_type(self):
        with self.assertRaises(TypeError): ProbeSession({}, [1])
    def test_samples_type(self):
        with self.assertRaises(TypeError): ProbeSession(ProbeConfig("api"), "bad")


class LifecycleTests(unittest.TestCase):
    def make(self, values=(100, 250, 650)):
        return ProbeSession(ProbeConfig("api"), values)
    def tearDown(self):
        self.assertEqual(ProbeSession.active_sessions, 0)
    def test_new(self): self.assertEqual(self.make().state, "new")
    def test_open(self):
        s = self.make()
        s.open()
        self.assertEqual(s.state, "open")
        s.close()
    def test_close_idempotent(self):
        s = self.make()
        s.open()
        s.close()
        s.close()
        self.assertEqual(s.state, "closed")
    def test_context_cleanup(self):
        s = self.make()
        with s:
            self.assertEqual(s.state, "open")
        self.assertEqual(s.state, "closed")
    def test_context_exception(self):
        s = self.make()
        with self.assertRaisesRegex(RuntimeError, "injected"):
            with s:
                raise RuntimeError("injected")
        self.assertEqual(s.state, "closed")
    def test_cannot_reopen(self):
        s = self.make()
        with s:
            pass
        with self.assertRaises(RuntimeError): s.open()
    def test_sample_before_open(self):
        with self.assertRaises(SessionClosed): self.make().sample()
    def test_sample_after_close(self):
        s = self.make()
        with s: pass
        with self.assertRaises(SessionClosed): s.sample()
    def test_exhaustion(self):
        with self.make([1]) as s:
            s.sample()
            with self.assertRaises(SourceExhausted): s.sample()
    def test_classification(self):
        with self.make() as s:
            self.assertEqual([s.sample()["status"] for _ in range(3)], ["healthy","warning","critical"])
    def test_bad_sample(self):
        with self.assertRaises(ValueError): self.make([float("inf")])
    def test_bool_sample(self):
        with self.assertRaises(ValueError): self.make([True])
    def test_invalid_static_latency(self):
        with self.assertRaises(ValueError): ProbeSession.classify(-1, ProbeConfig("api"))
    def test_remaining(self):
        with self.make([1,2]) as s:
            self.assertEqual(s.remaining, 2)
            s.sample()
            self.assertEqual(s.remaining, 1)
    def test_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            path.write_text(json.dumps({"config":{"service":"api"},"samples":[1,300]}), encoding="utf-8")
            self.assertEqual(run(path)["session_state"], "closed")
    def test_cli_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"unexpected":true}', encoding="utf-8")
            with self.assertRaises(ValueError): run(path)


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_probe.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile probe.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_probe.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile probe.py cli.py
```

Expected output: three synthetic PostgreSQL latency classifications (healthy, warning, critical), with `"session_state":"closed"`. **32 unit tests** are included; execute locally to confirm.

## 6. Failure injection

1. Set `warning_ms >= critical_ms` and verify constructor rejection.
2. Add an unexpected `token` key to config and verify schema rejection without echoing its value.
3. Call `sample()` before `open()` and after `close()`.
4. Call `open()` twice; verify the lifecycle error.
5. Raise an exception inside `with session:` and verify `close()` runs.
6. Pass `NaN`, `Infinity`, a boolean or negative sample and verify validation.
7. Exhaust all samples and verify `SourceExhausted`.
8. Confirm `active_sessions` returns to zero after context exit.

## 7. Troubleshooting and runbooks

**Leak investigation:** compare open and close transitions; ensure each acquired session is used in a `with` block. If acquisition fails, do not increment active resource counts.

**Unexpected closure:** verify that callers do not use a session after leaving its context; create a new session for a new operation.

**Factory failure:** check the reviewed configuration schema and thresholds. Do not log raw input that might contain credentials.

**Concurrency warning:** the class counter and session state are not synchronized. Use one session per worker and a thread-safe telemetry backend for real workloads.

## 8. Acceptance

- [ ] 32 tests pass locally.
- [ ] Factory methods validate configuration and preserve subclass type.
- [ ] Static methods do not depend on instance state.
- [ ] Lifecycle transitions are explicit and cleanup is idempotent.
- [ ] Exceptions propagate while cleanup runs.
- [ ] CLI emits deterministic sanitized JSON.
- [ ] No network calls, credentials or mutations.
