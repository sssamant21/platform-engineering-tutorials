# Chapter 031 — Python Classes, Objects and Encapsulation

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Learning objectives
Explain classes, instances, attributes, methods, constructors, identity and encapsulation; distinguish class attributes from instance state; enforce invariants with properties and validated methods; design immutable snapshots and mutable aggregates; apply composition and dependency injection; test a read-only SRE/DBRE domain model; diagnose operational failures.

## 1. Why object-oriented design matters to SRE/DBRE

A health probe combines a target, thresholds, measurements and a reporting policy. Plain functions are excellent for stateless transformations, but classes can keep related state and invariants together. Poorly designed classes introduce shared mutable state, hidden network calls and surprising behavior during incidents.

An object is an instance of a class. Its **identity** distinguishes it from other instances, **state** represents its data, and **behavior** is exposed through methods. Python uses reference semantics: assigning an object to another variable does not copy it.

```python
class Target:
    def __init__(self, name: str):
        self.name = name

first = Target("postgres")
alias = first
assert alias is first
```

## 2. Constructor and instance attributes

`__init__` initializes an already-created instance; it does not allocate it. Use it to validate required invariants and establish a complete usable object. Avoid I/O, credentials retrieval, or production connections in constructors.

```python
class Endpoint:
    def __init__(self, name: str, timeout: float = 5.0):
        if not name.strip() or timeout <= 0:
            raise ValueError("invalid endpoint")
        self.name = name
        self.timeout = timeout
```

**Class attributes** are shared through the class, whereas **instance attributes** belong to an instance. Avoid class-level mutable lists and dictionaries:

```python
# Anti-pattern: all instances share this list
class BadMonitor:
    observations = []

# Prefer:
class Monitor:
    def __init__(self):
        self.observations = []
```

## 3. Encapsulation and properties

Python convention uses `_attribute` for nonpublic implementation details. Double-underscore name mangling reduces accidental subclass collisions; it is **not** a security boundary. Expose safe behavior through methods and read-only `@property` values.

```python
class Threshold:
    def __init__(self, warning: float, critical: float):
        if not 0 < warning < critical:
            raise ValueError("invalid thresholds")
        self._warning = warning
        self._critical = critical

    @property
    def warning(self):
        return self._warning
```

A property with no setter blocks ordinary assignment but does not make an object fully immutable. `dataclass(frozen=True)` helps model immutable snapshots, yet nested mutable members still require care.

## 4. Architecture for operational monitoring

```text
Synthetic JSON input
       |
       v
MetricSnapshot (frozen value object)
       |
       v
ThresholdPolicy (validated, read-only properties)
       |
       v
ServiceMonitor (private bounded history)
       |
       v
MonitoringFleet (composition and unique service IDs)
       |
       v
Deterministic JSON report (no credentials)
```

**Separation of concerns:** snapshots validate data, policy decides severity, monitor owns per-service history, fleet coordinates monitors, CLI performs input/output. The lab does not create any cloud client.

## 5. Composition vs inheritance

Prefer composition when a fleet **has** monitors, or a monitor **has** a policy. Use inheritance when a true substitutable “is-a” relationship exists and the abstraction is stable. Avoid giant base classes that mix transport, retry, configuration, metrics and business logic. Later chapters will cover inheritance, protocols and polymorphism.

## 6. State lifecycle and invariants

A monitor must reject nonfinite latency, negative counts, duplicate/invalid services, and invalid thresholds. Its history is bounded to prevent unbounded memory growth. Return tuples or copies of internal collections rather than exposing mutable lists. Never store live secrets in report objects or `repr` output.

## 7. Production considerations

- **Concurrency:** a private list is not automatically safe for cross-thread concurrent updates; use synchronization or immutable event streams.
- **Memory:** bounded history prevents an operational diagnostic process from growing indefinitely.
- **Failure isolation:** invalid input should fail before state mutation.
- **Observability:** log stable identifiers and sanitized summaries; avoid raw connection URLs.
- **Testing:** use synthetic data and deterministic policies; isolate I/O at boundaries.
- **Security:** encapsulation is API discipline, not authentication or authorization.

## 8. SRE/DBRE applications

| Domain | Model | Operational invariant |
|---|---|---|
| PostgreSQL | ReplicationLagSnapshot / Monitor | Lag nonnegative, time bounded |
| Elasticsearch | SearchLatencySnapshot / Policy | Thresholds ordered |
| Kafka | ConsumerGroupHealth / Fleet | Unique group identity |
| Kubernetes | WorkloadState / Monitor | Cluster context explicit |
| Snowflake | QueryLatencySnapshot / Report | No query text or credentials in output |

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| State leaks across objects | Mutable class attribute | Initialize per-instance state |
| Unexpected mutation | Internal list returned directly | Return immutable tuple or copy |
| Invalid thresholds accepted | No constructor validation | Enforce invariants on creation |
| Property assignment fails | No setter | Use supported method/new instance |
| `AttributeError` on instance | `__init__` skipped field | Initialize all required state |
| `TypeError` on method | Missing `self` | Declare instance method correctly |
| Stale status | Cached report not updated | Derive status from latest snapshot |
| Memory pressure | Unbounded history | Set and test retention bound |
| Data races | Shared object updated concurrently | Add explicit synchronization |
| Sensitive data in logs | Dumping `__dict__` | Use allowlisted summary |

## 10. Runbooks

**Preflight:** verify Python version, input schema, policy thresholds, retention limit, read-only mode and expected service names.

**Validation failure:** stop ingestion, preserve sanitized failing fixture and error class, correct source data; do not bypass invariants.

**Unexpected classification:** compare latest immutable snapshot with policy boundaries and expected severity; reproduce in unit tests.

**Memory growth:** inspect history length and object count, verify retention bounds, restart only after collecting evidence.

**Change control:** require review for threshold changes, test boundary cases, document rollback to previous policy.

## 11. Hands-on and assessment

[Chapter 031 — Object-Oriented SRE/DBRE Monitoring Lab](labs/031-object-oriented-sre-dbre-monitoring-lab.md) provides complete code, a synthetic fixture, 30 automated tests, failure injection and an operational checklist.

**Acceptance:** all tests run locally, independent monitor state, immutable snapshots, bounded history, validated thresholds, deterministic output, and no network or destructive actions. Test code is published; local execution must be performed separately.

**Next: Chapter 032 — Instance Methods, Class Methods, Static Methods and Object Lifecycle.**
