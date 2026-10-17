# Chapter 022 — Hands-on Lab: SRE Policy Factories and Higher-Order Callbacks

**Python 3.10+ | Standard library only | Read-only, offline**

## Scenario
Analyze sanitized synthetic SRE events using environment-specific closure policies. Keep policy construction separate from evaluation. Count evaluations in isolated closure state, and output a deterministic JSON report without sending alerts.

## 1. Fixture: `events.json`
```json
[
  {"environment":"prod","service":"api","latency_ms":310},
  {"environment":"staging","service":"api","latency_ms":310},
  {"environment":"prod","service":"db","latency_ms":800},
  {"environment":"staging","service":"db","latency_ms":100},
  {"environment":"prod","service":"worker","latency_ms":250}
]
```

## 2. Create `policy_factory.py`
```python
"""Pure closure policies and callback-driven SRE event evaluation."""
from collections.abc import Callable, Iterable
from functools import wraps
import math


def nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def make_latency_policy(threshold_ms: float) -> Callable[[dict], bool]:
    """Create an immutable-threshold, side-effect-free predicate."""
    threshold = nonnegative(threshold_ms, "threshold_ms")
    def is_slow(event: dict) -> bool:
        return nonnegative(event["latency_ms"], "latency_ms") >= threshold
    return is_slow


def counted(predicate: Callable[[dict], bool]):
    """Wrap predicate with an isolated call counter; not thread-safe."""
    calls = 0
    @wraps(predicate)
    def wrapper(event: dict) -> bool:
        nonlocal calls
        calls += 1
        return predicate(event)
    wrapper.call_count = lambda: calls
    return wrapper


def validate_event(event: object) -> dict:
    if not isinstance(event, dict) or set(event) != {"environment", "service", "latency_ms"}:
        raise ValueError("expected environment, service, latency_ms")
    for field in ("environment", "service"):
        if not isinstance(event[field], str) or not event[field].strip():
            raise ValueError(f"invalid {field}")
    nonnegative(event["latency_ms"], "latency_ms")
    return dict(event)


def evaluate(events: Iterable[dict], policies: dict[str, Callable[[dict], bool]]) -> dict:
    """Validate, invoke a callback per event, and summarize matches."""
    if not isinstance(policies, dict) or not policies:
        raise ValueError("policies must be a nonempty dictionary")
    counts = {}
    slow = {}
    for raw in events:
        event = validate_event(raw)
        environment = event["environment"]
        if environment not in policies:
            raise ValueError(f"missing policy for environment {environment}")
        policy = policies[environment]
        if not callable(policy):
            raise TypeError("policy must be callable")
        key = (environment, event["service"])
        counts[key] = counts.get(key, 0) + 1
        slow[key] = slow.get(key, 0) + int(policy(event))
    groups = [
        {"environment": env, "service": service,
         "events": counts[(env, service)], "slow_events": slow[(env, service)]}
        for env, service in sorted(counts)
    ]
    return {"event_count": sum(counts.values()), "groups": groups}
```

## 3. Create `evaluate_events.py`
```python
"""Offline CLI adapter. No production notifications or infrastructure access."""
import argparse
import json
from pathlib import Path
from policy_factory import counted, evaluate, make_latency_policy


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run SRE closure policy evaluator")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            records = json.load(source)
        if not isinstance(records, list):
            raise ValueError("expected JSON array")
        policies = {
            "prod": counted(make_latency_policy(250)),
            "staging": counted(make_latency_policy(500)),
        }
        report = evaluate(records, policies)
        report["policy_invocations"] = {
            env: policies[env].call_count() for env in sorted(policies)
        }
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 4. Create `test_policy_factory.py`
```python
import unittest
from policy_factory import counted, evaluate, make_latency_policy, nonnegative, validate_event


def row(env="prod", service="api", latency=300):
    return {"environment": env, "service": service, "latency_ms": latency}


class PolicyFactoryTests(unittest.TestCase):
    def test_threshold_below(self):
        self.assertFalse(make_latency_policy(250)(row(latency=249)))
    def test_threshold_inclusive(self):
        self.assertTrue(make_latency_policy(250)(row(latency=250)))
    def test_separate_thresholds(self):
        self.assertNotEqual(make_latency_policy(250)(row()), make_latency_policy(500)(row()))
    def test_negative_threshold(self):
        with self.assertRaises(ValueError):
            make_latency_policy(-1)
    def test_boolean_threshold(self):
        with self.assertRaises(TypeError):
            make_latency_policy(True)
    def test_nan_threshold(self):
        with self.assertRaises(ValueError):
            make_latency_policy(float("nan"))
    def test_counter_zero(self):
        policy = counted(make_latency_policy(250))
        self.assertEqual(policy.call_count(), 0)
    def test_counter_increment(self):
        policy = counted(make_latency_policy(250))
        policy(row())
        self.assertEqual(policy.call_count(), 1)
    def test_counter_isolation(self):
        first = counted(make_latency_policy(250))
        second = counted(make_latency_policy(250))
        first(row())
        self.assertEqual(second.call_count(), 0)
    def test_wraps_metadata(self):
        policy = counted(make_latency_policy(250))
        self.assertEqual(policy.__name__, "is_slow")
    def test_valid_event(self):
        self.assertEqual(validate_event(row())["service"], "api")
    def test_missing_field(self):
        with self.assertRaises(ValueError):
            validate_event({"service": "api"})
    def test_invalid_service(self):
        with self.assertRaises(ValueError):
            validate_event(row(service=""))
    def test_boolean_latency(self):
        with self.assertRaises(TypeError):
            validate_event(row(latency=True))
    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            validate_event(row(latency=-1))
    def test_nonfinite_latency(self):
        with self.assertRaises(ValueError):
            nonnegative(float("inf"), "latency")
    def test_empty_policy_map(self):
        with self.assertRaises(ValueError):
            evaluate([], {})
    def test_missing_environment_policy(self):
        with self.assertRaises(ValueError):
            evaluate([row(env="dev")], {"prod": make_latency_policy(250)})
    def test_noncallable_policy(self):
        with self.assertRaises(TypeError):
            evaluate([row()], {"prod": 250})
    def test_evaluation(self):
        report = evaluate([row(latency=300), row(latency=100)], {"prod": make_latency_policy(250)})
        self.assertEqual(report["groups"][0]["slow_events"], 1)
    def test_group_sort(self):
        report = evaluate([row(service="z"), row(service="a")], {"prod": make_latency_policy(250)})
        self.assertEqual(report["groups"][0]["service"], "a")
    def test_event_count(self):
        report = evaluate([row(), row()], {"prod": make_latency_policy(250)})
        self.assertEqual(report["event_count"], 2)
    def test_empty_events(self):
        self.assertEqual(evaluate([], {"prod": make_latency_policy(250)})["event_count"], 0)
    def test_no_input_mutation(self):
        event = row()
        evaluate([event], {"prod": make_latency_policy(250)})
        self.assertEqual(event["latency_ms"], 300)
    def test_callback_invocations(self):
        policy = counted(make_latency_policy(250))
        evaluate([row(), row()], {"prod": policy})
        self.assertEqual(policy.call_count(), 2)
    def test_policy_failure_propagates(self):
        def broken(_event):
            raise RuntimeError("simulated policy failure")
        with self.assertRaises(RuntimeError):
            evaluate([row()], {"prod": broken})


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute
```bash
python evaluate_events.py --input events.json
python -m unittest -v test_policy_factory.py
python -m py_compile policy_factory.py evaluate_events.py
```

Expected: five events, three prod policy invocations, two staging policy invocations. Slow matches: `prod/api` 1, `prod/db` 1, `prod/worker` 1; staging groups 0. The lab includes **26 unit tests**.

## 6. Failure injection
1. Add an unknown environment: fail with missing-policy error.
2. Replace a latency with `true` or `-1`: fail validation.
3. Remove `service`: reject the record.
4. Use malformed JSON: nonzero exit, no success report.
5. Replace a policy with a noncallable: reject.
6. Inject a callback that raises: verify the exception is not silently swallowed.

## 7. Production considerations
A closure counter is local to one Python process and is not thread-safe. It is not a distributed incident counter. Avoid retaining sensitive event objects in closures, and do not use unreviewed callbacks from arbitrary plugins. For production, use approved metrics backends, immutable policy configuration, rate-limited alert delivery, explicit error handling and audit logs.

## 8. Acceptance
- [ ] Closures retain independent immutable thresholds.
- [ ] Counter wrappers isolate state.
- [ ] Higher-order evaluator accepts injectable callbacks.
- [ ] Inputs remain unchanged.
- [ ] Deterministic report and fail-closed validation.
- [ ] All 26 tests pass locally.
- [ ] No infrastructure mutations or alert delivery.
