# Chapter 035 — Abstract Base Classes, Interfaces and Composition Patterns

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Learning objectives

Design explicit interfaces with `abc.ABC` and `@abstractmethod`; distinguish abstract contracts from `typing.Protocol`; apply composition over inheritance; inject metrics sources, policies and sinks; implement an allowlisted plugin registry; validate read-only behavior and stable JSON output; build unit and contract tests.

## 1. Why interfaces matter in SRE and DBRE

A health checker should not need to know whether its metric originates from PostgreSQL, Elasticsearch, Kafka or a synthetic fixture. Separating collection, classification and output prevents a large inheritance hierarchy from accumulating network calls, policy rules, secrets and presentation logic.

An abstract base class (ABC) is useful when an explicit implementation contract and nominal registration are desirable. Python prevents instantiation while abstract methods remain unimplemented, but it does not enforce the semantic correctness of overrides.

```python
from abc import ABC, abstractmethod

class MetricSource(ABC):
    @abstractmethod
    def read(self) -> float:
        """Return a finite, nonnegative metric."""
```

A subclass must implement `read`. The base class can also provide shared concrete methods. Unlike a Protocol, an ABC requires explicit inheritance (or virtual registration); an ABC is not a security boundary.

## 2. Interfaces versus structural protocols

| Concern | ABC | Protocol |
|---|---|---|
| Type relationship | Nominal | Structural |
| Requires explicit inheritance | Usually yes | No |
| Runtime abstract-method enforcement | Yes | No |
| Static typing | Yes | Yes |
| Shared implementation | Supported | Possible, but use deliberately |
| Semantic contract verification | Requires tests | Requires tests |

Choose a Protocol for independently implemented third-party readers; choose an ABC when you own a controlled hierarchy and need runtime abstract-method enforcement.

## 3. Composition over inheritance

Prefer a `HealthService` that **has a** metric source, policy and sink to a single base class that both fetches metrics, classifies them and writes files.

```text
             HealthService
           /       |       \
     MetricSource  Policy  ResultSink
       /   |   \     |         |
      PG   ES  Kafka  Threshold  JSON memory
            (synthetic lab implementations)
```

Each component has one responsibility and can be replaced independently. Constructor injection makes tests deterministic, prevents implicit production connections, and clarifies resource ownership.

## 4. Strategy and adapter patterns

A **strategy** encapsulates interchangeable policy behavior (threshold classification). An **adapter** maps a domain-specific data source to the common `MetricSource.read()` contract. A **sink** accepts a validated report and stores or emits it. The orchestration service coordinates these without implementing their internals.

Keep plugins on an explicit allowlist. Never import arbitrary user-provided module names or execute dynamic code based on a configuration file. The lab's plugin registry maps reviewed names to synthetic classes only.

## 5. Safety contracts

- All metric values must be finite, numeric, nonnegative and not booleans.
- Thresholds must satisfy `0 < warning < critical`.
- Reader methods must not perform writes, remediation or unexpected network calls.
- A sink receives sanitized, schema-stable reports, not credentials.
- Duplicate `(kind, service)` records fail closed.
- A failing reader must not produce a false `healthy` result.
- The synthetic lab uses no network, secrets or infrastructure changes.

## 6. Resource ownership and failure behavior

Production readers need bounded timeouts, cancellation, retry budgets and explicit connection ownership. Keep construction side-effect free where possible. Do not retry destructive operations. A failing source should surface a typed error and preserve the incident context without leaking connection strings.

## 7. SRE/DBRE architecture examples

| System | Source adapter | Policy | Safe sink |
|---|---|---|---|
| PostgreSQL | Replica lag in seconds | Approved lag thresholds | Structured report |
| Elasticsearch | Query latency in ms | Approved latency thresholds | Structured report |
| Kafka | Consumer lag messages | Approved backlog thresholds | Structured report |
| Kubernetes | Pod readiness summary | Availability policy | Audit report |
| Redis | Memory utilization | Capacity policy | Alert evaluation |

Thresholds in this lab are illustrative; production SLOs require workload-specific baselines and service-owner approval.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Abstract class instantiation fails | Missing implementation | Implement required method |
| Reader returns a string | Violated interface semantics | Validate at orchestration boundary |
| Fake cannot replace production adapter | Hidden dependency | Inject interface |
| Wrong threshold applied | Policy/source coupling | Inject reviewed policy |
| Unknown plugin accepted | Unsafe dynamic loading | Enforce allowlist |
| JSON varies by adapter | Reporting scattered across subclasses | Centralize report construction |
| Sink publishes partial results | Writes during validation | Validate full batch first |
| Silent healthy result after failure | Exception swallowed | Fail closed and surface error |

## 9. Production runbooks

**Plugin incident:** disable unreviewed adapter, capture sanitized error, verify registry and package provenance, restore approved implementation.

**Misclassification:** verify units, thresholds, metric freshness and boundary conditions; reproduce with synthetic tests before change.

**Partial report risk:** validate all entries and construct the complete result before calling a sink. For real sinks, use transactional or atomic publication where available.

**Release and rollback:** test contract and integration behavior, review least privilege, pin versions, stage deployment, monitor error rates and retain rollback artifact.

## 10. Hands-on lab and acceptance

[Chapter 035 — Composable SRE/DBRE Health Service Lab](labs/035-composable-sre-dbre-health-service-lab.md) contains complete source, CLI, synthetic fixtures, **32 unit tests**, failure injection and acceptance criteria.

**Next: Chapter 036 — Dataclasses, Properties and Python Object Models.**
