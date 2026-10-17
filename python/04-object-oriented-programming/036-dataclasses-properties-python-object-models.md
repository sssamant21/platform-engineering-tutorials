# Chapter 036 — Dataclasses, Properties and Python Object Models

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Learning outcomes

Use `@dataclass`, `field()`, `__post_init__`, `frozen=True`, `slots=True` (Python 3.10+), `default_factory`, computed properties, explicit serialization, equality, representation and defensive validation. Distinguish shallow immutability from deep immutability and model reliable SRE/DBRE telemetry and configuration.

## 1. Why object models matter

Production diagnostics pass structured data across ingestion, policy, reporting and alerting boundaries. Mutable dictionaries make it easy to change units, thresholds or labels inadvertently. Dataclasses provide concise constructors, readable representations, value equality and optional immutability while keeping validation explicit.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Lag:
    service: str
    seconds: float

assert Lag("pg", 2.0) == Lag("pg", 2.0)
```

Dataclasses do not automatically validate types at runtime. `Lag("pg", "slow")` can still be constructed unless you add checks.

## 2. Generated methods and field design

By default, `@dataclass` generates `__init__`, `__repr__`, and `__eq__`. Options include `order=True`, `frozen=True`, `slots=True`, `kw_only=True` and `repr=False` on sensitive fields. Generated representations must never be treated as a security boundary: explicitly exclude secrets and avoid logging raw objects.

```python
from dataclasses import dataclass, field

@dataclass(slots=True)
class ProbeState:
    observations: list[float] = field(default_factory=list)
```

Avoid `observations=[]` or other shared mutable defaults. `default_factory` creates a new list for each instance.

## 3. `__post_init__` and frozen validation

```python
from dataclasses import dataclass
import math

@dataclass(frozen=True, slots=True)
class Thresholds:
    warning: float
    critical: float

    def __post_init__(self):
        for value in (self.warning, self.critical):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("invalid threshold")
        if not 0 < self.warning < self.critical:
            raise ValueError("thresholds must be ordered")
```

With frozen dataclasses, use `object.__setattr__` only when essential for normalized derived fields during `__post_init__`; do not use it to bypass invariants later.

## 4. Shallow versus deep immutability

A frozen dataclass prevents ordinary attribute reassignment, but does not recursively freeze nested lists and dictionaries.

```python
@dataclass(frozen=True)
class UnsafeSnapshot:
    labels: dict[str, str]  # mutable even though outer instance is frozen
```

Use tuples of immutable pairs or defensive copies. Avoid claiming that `frozen=True` protects secrets, thread safety or authorization.

## 5. Properties and derived data

`@property` exposes computed information through an attribute-like interface. Prefer computed properties when derivation is cheap and deterministic.

```python
@dataclass(frozen=True)
class ErrorStats:
    errors: int
    requests: int

    @property
    def error_rate(self):
        return self.errors / self.requests
```

Validate `requests > 0` and `0 <= errors <= requests` before constructing a production-quality model. Properties with setters can enforce controlled mutation on non-frozen classes; choose immutability when a telemetry snapshot should never change.

## 6. Architecture

```text
synthetic JSON fixture
       |
       v
validated immutable MetricSnapshot
       |
       v
validated immutable ThresholdPolicy
       |
       v
HealthEvaluation (derived status property)
       |
       v
explicit allowlisted serializer
       |
       v
deterministic JSON report
```

The lab uses immutable value objects for configuration and measurements and a mutable, bounded `SnapshotBuffer` with defensive tuple exposure. No live service connections are made.

## 7. Object representation, equality and serialization

`repr` is useful for debugging but must be sanitized. `dataclasses.asdict` recursively copies dataclass fields, which can unintentionally include credentials or large payloads. Prefer an explicit `to_public_dict()` method with an allowlist and a schema version. Equality of dataclasses compares fields by value; do not confuse equality with identity (`is`).

## 8. SRE/DBRE use cases

| Domain | Immutable model | Derived property |
|---|---|---|
| PostgreSQL | ReplicationLagSnapshot | Lag severity |
| Elasticsearch | SearchLatencySnapshot | Threshold status |
| Kafka | ConsumerOffsetSnapshot | Backlog health |
| Kubernetes | WorkloadHealthSnapshot | Ready fraction |
| Redis | MemorySnapshot | Utilization ratio |

Units, timestamps, freshness, ownership and environment must be explicit in real production telemetry.

## 9. Troubleshooting

| Symptom | Cause | Remediation |
|---|---|---|
| `FrozenInstanceError` | Mutating frozen instance | Construct a new snapshot or use `replace()` |
| Unexpected nested mutation | Frozen outer object holds dict/list | Convert to immutable tuples |
| Shared observations | Mutable class/default state | Use `default_factory` |
| `ZeroDivisionError` | Invalid request count | Validate in `__post_init__` |
| `TypeError` during JSON encoding | Dataclass not serializable directly | Use allowlisted mapping |
| Sensitive data in logs | Automatic `repr` or `asdict` | Redact and serialize explicitly |
| Invalid NaN accepted | Type hints not enforced | Runtime finite validation |
| High memory use | Unbounded telemetry buffer | Bound retention and test it |

## 10. Production runbooks

**Schema drift:** stop report publication, compare fixture to documented schema, preserve sanitized failing example, add regression test, then deploy compatible parser.

**Unexpected mutation:** identify mutable nested references, switch to immutable normalized data and verify copy boundaries.

**Incorrect health status:** check units, threshold policy, denominator validation and inclusive boundary conditions before escalating.

**Release and rollback:** run unit tests, pin Python/runtime dependencies, stage on synthetic fixtures, validate JSON consumers and preserve previous artifact.

## 11. Hands-on and acceptance

[Chapter 036 — Immutable SRE/DBRE Telemetry Object Models Lab](labs/036-immutable-sre-dbre-telemetry-object-models-lab.md) contains full source code, CLI, synthetic fixture, **32 automated tests**, failure injection and operational runbooks.

**Next: Chapter 037 — Magic Methods, Dunder Protocols and Operator Overloading.**
