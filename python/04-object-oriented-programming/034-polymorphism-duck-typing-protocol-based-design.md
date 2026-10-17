# Chapter 034 — Polymorphism, Duck Typing and Protocol-Based Design

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Learning outcomes

Design interchangeable SRE/DBRE adapters using structural polymorphism, duck typing, `typing.Protocol`, `@runtime_checkable`, and dependency injection. Separate metric collection from policy and reporting; test against fakes; understand runtime versus static type checking; build a deterministic, offline, read-only health reporter.

## 1. What is polymorphism?

Polymorphism lets one consumer use objects with different concrete types through the same behavioral interface. Python naturally supports **duck typing**: if an object provides the required methods, callers can use it without inheritance.

```python
def summarize(adapter):
    return adapter.read_metric()

class PostgreSQLAdapter:
    def read_metric(self):
        return 42.0

class ElasticsearchAdapter:
    def read_metric(self):
        return 180.0
```

The consumer does not need `isinstance(adapter, BaseAdapter)`. Unlike inheritance-based designs, this approach permits independent adapters to implement the same contract.

## 2. Structural typing with Protocol

```python
from typing import Protocol

class MetricReader(Protocol):
    def read_metric(self) -> float: ...

def collect(reader: MetricReader) -> float:
    return reader.read_metric()
```

Static type checkers can verify structural conformance without explicit subclassing. Python does **not** enforce Protocol annotations at runtime. `@runtime_checkable` supports limited presence-based `isinstance` checks but does **not** validate method signatures, return types, exception safety, read-only permissions, or semantic behavior. Explicit input validation and contract tests remain essential.

## 3. Dependency injection

Instead of constructing a database client inside a reporter, inject a reader:

```python
class Reporter:
    def __init__(self, reader: MetricReader):
        self._reader = reader

    def report(self):
        return self._reader.read_metric()
```

The production adapter could later use approved read-only APIs, while a test passes an in-memory fake. Constructor injection is simple, explicit, and avoids global state. Factories can select adapters from an **allowlist**, not arbitrary module names from untrusted input.

## 4. Architecture

```text
            synthetic JSON fixture
                     |
               adapter factory
                     |
        +------------+------------+
        |            |            |
    PG lag       ES latency     Kafka lag
        |            |            |
        +------------+------------+
                     |
              MetricReader
                Protocol
                     |
              HealthReporter
           validated policy/units
                     |
           deterministic JSON output
```

The reader contract returns a finite nonnegative numeric metric. A reporter applies threshold policy; adapters never perform remediation. This lab makes **no network calls**.

## 5. Contracts and operational safety

A protocol documents the shape of an interface, but production correctness requires semantic constraints: unit identity, timeout budget, freshness, authentication scope, retries, and failure handling. Distinguish “reader exists” from “reader is safe.” Never pass untrusted configuration directly to a dynamic import or unrestricted plugin loader.

Use strict threshold validation: `0 < warning < critical`; warning/critical comparisons are inclusive. Reject `bool`, NaN, infinity and negative values. Report a stable JSON schema with service, adapter kind, unit, value and status.

## 6. Choosing an abstraction

| Technique | Best use | Caution |
|---|---|---|
| Duck typing | Small, flexible APIs | Contract discoverability |
| `Protocol` | Structural static typing | No runtime validation by default |
| `ABC` | Shared base invariants | Tight inheritance coupling |
| Composition | Swap policy, reader, logger | Requires explicit wiring |
| Adapter factory | Approved implementation selection | Allowlist and validation required |

Use a Protocol for the reader boundary, composition for the reporter, and a factory for reviewed adapter selection.

## 7. Production SRE/DBRE applications

- PostgreSQL: read-only replication-lag query adapter with statement timeout and scoped identity.
- Elasticsearch: search-latency metrics adapter with request timeout and index-safe permissions.
- Kafka: consumer-lag adapter using approved metrics endpoints.
- Kubernetes: status reader scoped to a namespace with RBAC `get/list` only.
- Snowflake: query-duration metrics adapter with minimum required role and query tagging.

These are future integration patterns; the executable lab intentionally uses synthetic fixtures rather than real infrastructure.

## 8. Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| `AttributeError: read_metric` | Adapter misses protocol method | Add method / static check |
| Runtime `isinstance` passes but method fails | Signature/return not checked | Validate values and contract-test |
| Wrong units | Adapter and policy disagree | Enforce unit metadata |
| Unexpected real API call in test | Hidden dependency | Inject fake reader |
| Invalid metric accepted | Missing finite check | Validate at boundary |
| Different JSON schemas | Reporter coupled to adapter | Centralize reporting |
| Unknown adapter selected | Unsafe dynamic dispatch | Use explicit allowlist |
| Slow tests | External dependencies | Use deterministic in-memory fakes |
| False green health | Stale sample | Add freshness checks to production adapters |

## 9. Operational runbooks

**Adapter contract failure:** halt report generation, record sanitized adapter kind and exception, compare with protocol and contract tests, revert incompatible adapter.

**Wrong classification:** confirm unit, metric freshness and threshold policy; reproduce with synthetic boundary fixtures and review SLOs.

**Unexpected network activity:** stop execution, inspect dependency construction and import-time side effects, replace with offline fake for tests, require explicit authorization for live adapters.

**Release:** run unit and integration tests, static type checking in CI if available, scan dependencies, pin artifacts, review least privilege and preserve rollback.

## 10. Lab and acceptance

[Chapter 034 — Protocol-Based SRE/DBRE Adapter Lab](labs/034-protocol-based-sre-dbre-adapters-lab.md) includes full runnable source, a synthetic fixture, 32 unit tests, failure injection, runbooks and acceptance checklist.

**Next: Chapter 035 — Abstract Base Classes, Interfaces and Composition Patterns.**
