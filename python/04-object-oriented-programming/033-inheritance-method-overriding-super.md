# Chapter 033 — Inheritance, Method Overriding and `super()`

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Objectives

Explain base and derived classes, inherited state and behavior, method overriding, `super()`, method resolution order (MRO), cooperative multiple inheritance, substitutability, and composition tradeoffs. Build safe read-only SRE/DBRE diagnostic adapters and verify behavior with automated tests.

## 1. Why inheritance matters in operational tooling

An SRE fleet may share a validation/reporting contract while applying different health policies for PostgreSQL replication lag, Elasticsearch search latency and Kafka consumer lag. A base class can own shared invariants; subclasses can implement domain-specific classification. Inheritance is appropriate only when subclasses truly satisfy the base contract. Otherwise use composition and explicit strategy objects.

```text
                   BaseHealthCheck
                   /      |      \
                  /       |       \
       PostgreSQLLag  Elasticsearch  KafkaLag
          Check          Check       Check
```

The lab uses **synthetic metrics only**; no database or cluster is contacted.

## 2. Base and derived classes

```python
class BaseCheck:
    def __init__(self, service):
        self.service = service

    def describe(self):
        return {"service": self.service}

class PostgreSQLCheck(BaseCheck):
    def describe(self):
        result = super().describe()
        return {**result, "engine": "postgresql"}
```

The subclass inherits the base constructor unless it overrides it. `super()` delegates to the next implementation in the class's MRO; it is **not always equivalent to calling the direct parent by name**.

## 3. Method overriding and contracts

An override replaces inherited behavior for instances of the subclass. Preserve input and output contracts, exception behavior, safety guarantees and the base class's documented invariants. Do not make a subclass require unexpected credentials, perform mutations, or change JSON field types.

**Liskov substitution principle:** code that expects a base check should be able to use a derived check without breaking assumptions. Keep all adapters read-only, deterministic, and bounded.

## 4. Abstract base classes

`abc.ABC` and `@abstractmethod` can enforce implementation of a required method:

```python
from abc import ABC, abstractmethod

class BaseCheck(ABC):
    @abstractmethod
    def classify(self, value):
        raise NotImplementedError
```

Instantiating an abstract class before implementing required methods raises `TypeError`. An ABC enforces interface presence, not correctness or authorization. Tests must validate behavioral contracts.

## 5. `super()` and method resolution order

Python uses C3 linearization to determine MRO. Inspect `SomeClass.__mro__` or `SomeClass.mro()`. Cooperative mixins should call `super()` when their chain is designed for it, and avoid directly invoking a named parent, which can skip or duplicate work in diamond inheritance.

```python
class Root:
    def tags(self):
        return ["root"]

class AuditMixin(Root):
    def tags(self):
        return ["audit", *super().tags()]

class RetryMixin(Root):
    def tags(self):
        return ["retry", *super().tags()]

class Tool(AuditMixin, RetryMixin):
    pass

assert Tool().tags() == ["audit", "retry", "root"]
```

MRO for `Tool`: `Tool → AuditMixin → RetryMixin → Root → object`. Be cautious with multiple inheritance and incompatible constructor signatures.

## 6. Architecture and safety

```text
JSON fixture → strict input validation → BaseHealthCheck contract
                                          |
                              +-----------+-----------+
                              |           |           |
                            PG lag       ES query     Kafka lag
                              |           |           |
                              +-----------+-----------+
                                          |
                                 Fleet report + JSON
```

Base class owns service identity, threshold validation, sanitized report schema and severity ordering. Derived classes supply domain names and units; overriding classification is permitted only within a documented contract. Do not allow subclasses to bypass validation.

## 7. Production SRE/DBRE scenarios

| Adapter | Synthetic metric | Example operational policy |
|---|---|---|
| PostgreSQL | replication lag seconds | warning 30 s, critical 120 s |
| Elasticsearch | query latency milliseconds | warning 200 ms, critical 500 ms |
| Kafka | consumer lag messages | warning 1,000, critical 10,000 |

These thresholds are **illustrative**, not universal production SLOs. Actual values require workload-specific baselines and service-owner approval.

## 8. Troubleshooting

| Symptom | Cause | Response |
|---|---|---|
| `TypeError: abstract class` | Required method not implemented | Implement override |
| Unexpected method selected | MRO misunderstanding | Inspect `__mro__` |
| Base initialization skipped | Missing `super().__init__` | Call cooperative constructor |
| Duplicate initialization | Explicit parent calls in diamond | Use consistent `super()` chain |
| Derived class breaks JSON | Incompatible override | Add contract tests |
| Unsafe subclass mutation | Inheritance used as privilege boundary | Enforce auth at adapter boundary |
| Class explosion | Overusing inheritance | Prefer composition/strategy |
| Shared mutable class state | Mutable class attribute | Use per-instance state |
| Wrong severity at boundary | Inclusive threshold mismatch | Test exact warning/critical limits |

## 9. Runbooks

**Preflight:** confirm adapter type, approved thresholds, source schema, read-only mode, Python version and test results.

**Incorrect classification:** reproduce with synthetic boundary values, inspect MRO and override, compare base contract, revert unsafe subclass changes.

**Unexpected initialization error:** inspect constructor chain and verify every required base invariant was initialized.

**Incident response:** stop automated action on schema drift, preserve sanitized JSON and package version, roll back the adapter, and escalate to service owners. Never infer production health from a synthetic fixture.

## 10. Hands-on lab and assessment

[Chapter 033 — Inheritance and Health Adapter Lab](labs/033-inheritance-sre-dbre-health-adapters-lab.md) includes complete code, executable synthetic fixtures, 32 unit tests, failure injection, operational runbooks and acceptance criteria.

**Next: Chapter 034 — Polymorphism, Duck Typing and Protocol-Based Design.**
