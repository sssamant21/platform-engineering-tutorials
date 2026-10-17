# Chapter 032 — Instance Methods, Class Methods, Static Methods and Object Lifecycle

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Objectives

Distinguish bound instance methods, class methods, and static methods; use alternative constructors for validated SRE/DBRE configurations; understand `__new__`, `__init__`, object references, and garbage collection; design explicit resource lifecycle with context managers; ensure idempotent cleanup; implement a safe read-only adapter; test failure paths.

## 1. The three method types

| Method | First argument | Primary purpose | Example |
|---|---|---|---|
| Instance method | `self` | Work with one object's state | `probe.sample()` |
| Class method | `cls` | Alternate constructors and polymorphic factories | `Probe.from_mapping(data)` |
| Static method | None injected | Pure helper logically grouped with class | `Probe.validate_name(name)` |

```python
class Probe:
    def __init__(self, service):
        self.service = service

    def describe(self):  # instance method
        return self.service

    @classmethod
    def from_mapping(cls, mapping):  # alternative constructor
        return cls(mapping["service"])

    @staticmethod
    def is_valid_name(name):  # utility
        return isinstance(name, str) and bool(name.strip())
```

Instance methods are descriptors: accessing `obj.describe` produces a bound method that supplies `self`. Class methods bind `cls` and preserve subclass construction. Static methods do not automatically receive either object.

## 2. Factory methods and validation

Factories provide named construction paths such as `from_mapping`, `from_json`, and `for_staging`. Validate inputs before opening a resource; fail with safe error messages that never echo credentials. A class method calling `cls(...)` respects subclasses better than hard-coding the base class.

```python
@classmethod
def for_staging(cls, service):
    return cls(service=service, environment="staging")
```

Factories are not dependency injection by themselves: pass a transport, clock, or data source explicitly when external interactions are introduced.

## 3. Object lifecycle

```text
__new__ allocates object → __init__ validates and initializes
  → object used through methods
  → close() releases owned resources
  → references may be collected later
```

Do **not** depend on `__del__` for timely cleanup. Reference cycles, interpreter shutdown, and implementation-specific garbage collection make finalizers unreliable. For files, connections, sessions and locks, use explicit `close()` plus `with` (context manager) or `contextlib.closing`. An object may be reused only if its lifecycle contract permits it.

## 4. Context managers

```python
with resource as handle:
    handle.read()
# __exit__ runs even if body raises
```

`__enter__` returns the managed object; `__exit__` performs cleanup. Returning `False` (or `None`) does not suppress exceptions. Cleanup should be idempotent, including repeated `close()`. If resource acquisition fails before entering the context, the factory/acquisition method must clean up partial state.

## 5. SRE/DBRE architecture

```text
reviewed synthetic fixture
      |
      v
ProbeConfig.from_mapping()  [classmethod]
      |
      v
ProbeSession(config, source) [instance state]
      |
      +-- validate_service() [staticmethod]
      +-- sample()           [instance method]
      +-- __enter__/__exit__ [lifecycle]
      |
      v
sanitized JSON summary
```

The lab's source is an in-memory sequence; it never contacts PostgreSQL, Elasticsearch, Kafka, Kubernetes, or cloud APIs. Production adapters should be separately authorized, read-only, bounded by timeouts, and observable.

## 6. Production reliability patterns

- **Ownership:** the creator of a connection should have an explicit contract for who closes it.
- **Retries:** never retry non-idempotent actions automatically; this lab has no mutations.
- **Cancellation:** cleanup must run on ordinary exceptions; test the context-manager path.
- **Concurrency:** do not share a mutable session across threads without synchronization.
- **Leak prevention:** track active resources, ensure no hidden allocation in imports or constructors.
- **Secrets:** use references/identity, not passwords in object representations or exceptions.
- **Error taxonomy:** distinguish bad configuration, closed-session use, and source failures.
- **Observability:** emit sanitized lifecycle state and durations without raw payloads.

## 7. Common mistakes

| Mistake | Result | Better design |
|---|---|---|
| Missing `self` | `TypeError` | Define instance method correctly |
| Calling instance method on class | Missing argument | Use instance or explicit classmethod |
| Hard-coded base class in factory | Subclass not preserved | Return `cls(...)` |
| Static method needs mutable state | Hidden globals | Make it instance method |
| I/O inside `__init__` | Hard-to-test partial failures | Separate `open()` / context manager |
| Relying on `__del__` | Leaked resources | Explicit close + `with` |
| Returning `True` from `__exit__` | Exception suppressed | Return `False` |
| Reusing closed session | Stale state | Raise clear lifecycle error |
| Repeated close crashes | Fragile cleanup | Make close idempotent |

## 8. Incident and change runbooks

**Resource leak:** inspect active session count, compare opens/closes, reproduce exception path, and add a regression test before release.

**Unexpected closed-session error:** verify the session's ownership boundary and whether it escaped a `with` block; create a new session rather than bypassing the state check.

**Factory mismatch:** inspect input schema and version; reject unknown fields, correct the reviewed configuration and retest.

**Production rollout:** validate in staging, use read-only identity, monitor errors and resource counts, pin the package version, and keep a rollback artifact.

## 9. Hands-on lab

[Chapter 032 — SRE/DBRE Probe Factories and Lifecycle Lab](labs/032-sre-dbre-probe-factories-lifecycle-lab.md) includes a complete offline package, sample data, 32 automated unit tests, exception-injection exercises, troubleshooting and acceptance.

**Next: Chapter 033 — Inheritance, Method Overriding and super().**
