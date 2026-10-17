# Chapter 037 — Magic Methods, Dunder Protocols and Operator Overloading

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Objectives

Understand Python's data model and special-method dispatch; implement safe `__repr__`, `__str__`, `__eq__`, `__lt__`, `__hash__`, `__len__`, `__iter__`, `__getitem__`, `__add__`, `__enter__`, and `__exit__`; handle `NotImplemented` correctly; preserve immutability, unit safety, resource ownership and predictable SRE/DBRE behavior.

## 1. Python's object protocols

Python operators and built-ins call special methods defined on an object's type. `len(x)` uses `__len__`, iteration uses `__iter__`, `x + y` uses `__add__`, and `with x:` uses context-manager hooks. These methods should honor familiar Python expectations and avoid surprising network calls or destructive operations.

```python
class Samples:
    def __init__(self, values):
        self._values = tuple(values)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)
```

Avoid implementing a special method simply because it is possible; an operational abstraction must remain understandable during an incident.

## 2. Safe representations

`__repr__` targets debugging, `__str__` targets human-readable display. Neither should reveal credentials, connection strings, query text, patient information or raw telemetry payloads. Do not assume `repr` is safe to log automatically.

```python
def __repr__(self):
    return f"MetricSeries(service={self.service!r}, count={len(self)})"
```

Explicitly allowlist safe fields. Prefer structured, sanitized JSON for machine consumers.

## 3. Equality, ordering and hashing

`__eq__` should compare meaningful values and return `NotImplemented` for unrelated types. Ordering must be clearly defined; for operational metrics, comparison is only meaningful if units and metric kinds match. An immutable value object may implement `__hash__` consistently with equality. Never hash mutable objects by fields that can change.

```python
def __eq__(self, other):
    if not isinstance(other, MetricValue):
        return NotImplemented
    return (self.kind, self.unit, self.value) == (other.kind, other.unit, other.value)
```

Do not compare milliseconds with seconds without an explicit conversion policy. The lab rejects mixed metric kinds or units.

## 4. Operator overloading

Use `__add__` only when addition is domain-meaningful. Combining two immutable series with identical service, kind and unit is reasonable; adding unrelated database metrics is not. For unsupported types, return `NotImplemented` so Python can try reflected operations or raise a clear `TypeError`.

```python
def __add__(self, other):
    if not isinstance(other, MetricSeries):
        return NotImplemented
    if self.identity != other.identity:
        raise ValueError("cannot combine different metric series")
    return MetricSeries(self.identity, self.samples + other.samples)
```

## 5. Collection protocols

`__len__` returns a nonnegative integer, `__iter__` returns an iterator, and `__getitem__` supports indexing or slicing. Immutable tuples provide defensive storage. Implement `__bool__` only when domain-specific truthiness is unambiguous; otherwise rely on `__len__`.

## 6. Context manager lifecycle

```python
with SyntheticSession(series) as session:
    for metric in session:
        ...
```

`__enter__` acquires or validates a resource; `__exit__` releases it even on ordinary exceptions. Return `False` to propagate exceptions. Do not depend on `__del__` for cleanup, and do not silently suppress incident errors. Explicit close should be idempotent.

## 7. Architecture

```text
reviewed synthetic JSON
          |
    MetricValue (frozen, unit-aware)
          |
    MetricSeries (immutable sequence)
       /       \
  __iter__    __add__
       \       /
    SyntheticSession (context manager)
          |
    deterministic sanitized JSON report
```

The lab models PostgreSQL replication lag, Elasticsearch query latency and Kafka consumer lag without live service access.

## 8. SRE/DBRE operational concerns

- **Correctness:** unit-aware comparison and addition prevent silent metric corruption.
- **Safety:** no I/O in comparison, hashing, representation or iteration.
- **Reliability:** context managers clean up on errors; repeated close is safe.
- **Memory:** immutable series are bounded by reviewed input limits; large production streams should use iterators with backpressure instead.
- **Observability:** expose service, metric kind, unit, count and status—not raw credentials.
- **Concurrency:** immutable values simplify sharing; session lifecycle remains single-owner unless explicitly synchronized.

## 9. Troubleshooting

| Symptom | Root cause | Resolution |
|---|---|---|
| `TypeError` comparing values | Unsupported operand | Check kind/unit or `NotImplemented` |
| Wrong equality results | Identity/value contract inconsistent | Align `__eq__` and `__hash__` |
| Hash changes unexpectedly | Mutable fields hashed | Use frozen immutable value |
| Iteration consumes hidden state | Stateful `__iter__` | Return a fresh iterator |
| `len()` fails | Invalid `__len__` return | Return nonnegative integer |
| `with` suppresses error | `__exit__` returned `True` | Return `False` |
| Session reused after close | Lifecycle contract bypassed | Create new session |
| Secrets appear in logs | Unsafe `repr` | Allowlist metadata only |
| Series grows without bound | Missing input cap | Enforce maximum sample count |

## 10. Production runbooks

**Unit mismatch:** halt aggregation, inspect metric identity and units, convert only through an approved explicit transform, add boundary regression tests.

**Lifecycle leak:** inspect opens/closes and exception paths; ensure `with` ownership and idempotent `close()`.

**Serialization incident:** preserve sanitized fixture, compare stable schema, remove sensitive fields, redeploy pinned artifact.

**Release:** run automated tests, validate Python version, review operator semantics and audit all I/O boundaries before enabling real adapters.

## 11. Hands-on lab

[Chapter 037 — Python Object Protocols for SRE/DBRE Metrics Lab](labs/037-python-object-protocols-sre-dbre-metrics-lab.md) provides complete executable source, fixture, **32 unit tests**, failure injection and acceptance criteria.

**Next: Chapter 038 — Iterators, Generators and Lazy Object-Oriented Pipelines.**
