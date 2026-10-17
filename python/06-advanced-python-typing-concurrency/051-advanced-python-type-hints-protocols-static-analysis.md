# Chapter 051 — Advanced Python Type Hints, Protocols and Static Analysis

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.10+ | 5–7 hours**

## Learning objectives

Use function and variable annotations, `Literal`, `TypedDict`, generics, `TypeVar`, structural `Protocol`, frozen dataclasses, runtime schema validation and static analyzers to build maintainable SRE/DBRE tools.

## 1. Static types are contracts, not runtime enforcement

```python
def lag_seconds(service: str, value: float) -> float:
    return value

lag_seconds("replica", "not a number")  # Python permits this at runtime!
```

Python annotations are normally not enforced by the interpreter. Static analyzers such as mypy and pyright can flag invalid calls, but untrusted JSON, environment variables and network responses **still require runtime validation**.

## 2. Fundamental annotation vocabulary

| Feature | Purpose | Example |
|---|---|---|
| `str`, `int`, `float`, `bool` | Primitive contracts | `timeout: float` |
| `list[T]`, `dict[K,V]` | Typed collections | `list[str]` |
| `T | None` | Optional value | `str | None` |
| `Literal` | Restricted string values | `Literal["dev","prod"]` |
| `TypedDict` | JSON-like record shape | `class Event(TypedDict)` |
| `Protocol` | Structural interface | `read_events()` |
| `TypeVar`, `Generic` | Reusable generic containers | `Batch[T]` |
| `@dataclass(frozen=True)` | Immutable records | `Event` |

Avoid `Any` when the value's shape can be represented accurately. Prefer `object` for unknown inputs and validate before narrowing. Use `Mapping` for read-only inputs and `Iterable` when iteration is sufficient.

## 3. TypedDict for external payloads

```python
from typing import Literal, TypedDict
Engine = Literal["postgresql", "elasticsearch", "kafka"]
class RawEvent(TypedDict):
    service: str
    engine: Engine
    value: float
```

A `TypedDict` provides static shape information; it does **not** validate a JSON object at runtime. Use explicit key checks, numeric validation and allowlisted engine names at the I/O boundary.

## 4. Protocols and dependency inversion

```python
from typing import Iterable, Protocol
class EventSource(Protocol):
    def read_events(self) -> Iterable["Event"]: ...
```

A concrete object with a compatible `read_events` method satisfies the interface without inheritance. This is useful for replacing a production telemetry adapter with an offline fixture. `@runtime_checkable` can check that a method exists but does not deeply verify its annotations or semantics.

## 5. Generics and immutable operational data

```python
from dataclasses import dataclass
from typing import Generic, TypeVar
T = TypeVar("T")
@dataclass(frozen=True)
class Batch(Generic[T]):
    items: tuple[T, ...]
    def count(self) -> int:
        return len(self.items)
```

`Batch[Event]` preserves item-type information for static analysis. The frozen dataclass prevents attribute reassignment, but it does not recursively freeze arbitrary nested mutable objects.

## 6. Static analysis workflows

For Python 3.10+:

```bash
python -m pip install mypy pyright
python -m mypy --strict typed_ops.py
python -m pyright typed_ops.py
```

Use a pinned virtual environment and CI dependency lockfile for repeatable production builds. An example `mypy.ini`:

```ini
[mypy]
python_version = 3.10
strict = True
warn_unused_ignores = True
```

A minimal `pyrightconfig.json`:

```json
{"pythonVersion":"3.10","typeCheckingMode":"strict","include":["typed_ops.py"]}
```

These tools have different inference rules and may require different refinements. **Do not treat a green unit test run as proof that both static analyzers pass.** Avoid suppressing type errors with `# type: ignore` without documented justification.

## 7. Architecture for SRE/DBRE

```text
untrusted JSON
   -> size / syntax / schema validation
   -> typed immutable Event
   -> Protocol-based EventSource
   -> generic Batch[Event]
   -> deterministic severity report
   -> CI: unittest + mypy + pyright
```

Synthetic metric thresholds:

| System | Warning | Critical | Unit |
|---|---:|---:|---|
| PostgreSQL replica lag | 30 | 120 | seconds |
| Elasticsearch search latency | 200 | 500 | milliseconds |
| Kafka consumer lag | 1,000 | 10,000 | messages |

These thresholds are illustrative only.

## 8. Common mistakes and troubleshooting

- **Runtime TypeError despite annotations:** add runtime validation at ingress.
- **`TypedDict` rejects a value in mypy:** ensure all required keys exist and use appropriate narrowing.
- **`Protocol` implementation fails:** compare signatures, return types and variance.
- **Generic container becomes `Any`:** explicitly annotate public boundaries.
- **`bool` accepted as `int`:** use `type(value) is int` when booleans are forbidden.
- **`float('nan')` passes a numeric check:** require `math.isfinite`.
- **mypy/pyright disagree:** inspect configuration and inferred types; test both in CI.
- **Suppression masks a regression:** remove unnecessary `type: ignore` and document unavoidable exceptions.

## 9. Production runbooks

**Type regression during deployment:** stop rollout, identify changed public API, run strict analysis and contract tests, roll back incompatible adapter.

**Malformed telemetry payload:** quarantine input, log only sanitized error categories, correct producer schema and replay safe fixtures.

**Static analyzer upgrade:** pin tool version, inspect new diagnostics, stage remediation and compare CI results before rollout.

**Protocol adapter outage:** switch to a tested read-only adapter, verify equivalent output, restore the production adapter after remediation.

## 10. Hands-on lab and acceptance

[Chapter 051 — Typed SRE/DBRE Telemetry Analyzer Lab](labs/051-typed-sre-dbre-telemetry-analyzer-lab.md) contains a complete offline project, 40 unit tests, negative cases, static-analysis configuration, incident simulations, troubleshooting and a 100-point rubric.

**Next:** Chapter 052 — Python Iterators, Generators and Streaming Data Pipelines (provisional).
