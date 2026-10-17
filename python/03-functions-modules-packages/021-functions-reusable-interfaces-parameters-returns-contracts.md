# Chapter 021 — Functions as Reusable Interfaces: Parameters, Return Values and Contracts

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 90–120 minutes**

## Learning objectives
Design reusable functions with explicit contracts, choose positional and keyword parameters, understand positional-only and keyword-only arguments, avoid mutable defaults, use type hints and return values consistently, separate pure logic from I/O, and build a testable SRE alert-classification library.

## 1. Why functions matter to SREs
Operational scripts often begin as command sequences. As workflows grow, unstructured code increases risk: validation gets duplicated, threshold definitions drift, and testing requires production access. Functions establish a stable boundary between data, decision logic and side effects.

A reliable function answers:
- What inputs are accepted?
- What does it return?
- What errors can it raise?
- Does it mutate input or external systems?
- Are boundary conditions defined?
- Can it be tested without cloud credentials?

## 2. Function anatomy
```python
def is_slow(latency_ms: float, threshold_ms: float = 250.0) -> bool:
    """Return whether a sample meets or exceeds a latency threshold."""
    return latency_ms >= threshold_ms
```
The function name describes intent, parameters carry inputs, and `return` produces a value. The annotation `-> bool` documents expected output; Python does **not** enforce annotations at runtime. Validation remains necessary for untrusted data.

## 3. Parameters and arguments
```python
def classify_latency(latency_ms: float, *, warning_ms: float, critical_ms: float) -> str:
    if latency_ms >= critical_ms:
        return "critical"
    if latency_ms >= warning_ms:
        return "warning"
    return "healthy"

assert classify_latency(300, warning_ms=200, critical_ms=500) == "warning"
```
The `*` makes threshold arguments keyword-only. This prevents accidentally swapping warning and critical thresholds. A `/` marker can declare positional-only parameters, useful for APIs that do not want to commit to parameter names.

```python
def ratio(numerator: float, denominator: float, /) -> float:
    if denominator == 0:
        raise ValueError("denominator must not be zero")
    return numerator / denominator
```

## 4. Return values and error signaling
Prefer explicit return types and a single predictable output shape. For invalid input, raise `ValueError` or `TypeError` rather than returning a misleading default such as `0` or `"healthy"`. Catch exceptions at application boundaries, where a CLI can print an actionable error without masking the underlying problem.

```python
def error_rate(errors: int, total: int) -> float:
    if isinstance(errors, bool) or isinstance(total, bool):
        raise TypeError("counts must be integers")
    if not isinstance(errors, int) or not isinstance(total, int):
        raise TypeError("counts must be integers")
    if total <= 0 or not 0 <= errors <= total:
        raise ValueError("invalid counts")
    return errors / total
```

## 5. Function contracts: preconditions and postconditions
A **precondition** specifies valid inputs. A **postcondition** describes guarantees after success. For `error_rate`:
- Preconditions: both inputs are integers, `total > 0`, `0 <= errors <= total`.
- Postcondition: result is a finite float between 0 and 1.
- Side effects: none.

Avoid using `assert` to validate untrusted inputs: assertions can be disabled with `python -O`. Use explicit exceptions.

## 6. Mutable default arguments
```python
# Wrong: one list is shared across calls.
def append_bad(item, items=[]):
    items.append(item)
    return items

# Correct: allocate per invocation.
def append_good(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```
Default expressions are evaluated once when a function is defined, not once per call.

## 7. Scope, purity and dependency boundaries
Local variables belong to a function invocation. Avoid global mutable counters and hidden configuration. A **pure** decision function returns the same result for the same inputs and does not perform external I/O. Keep reading JSON, printing, sending notifications and writing databases in separate adapters.

```python
def should_escalate(error_rate_value: float, *, minimum_rate: float = 0.05) -> bool:
    return error_rate_value >= minimum_rate
```
In production, escalation requires traffic floors, freshness, error budgets and multiwindow checks. This example illustrates a reusable predicate, not a complete paging policy.

## 8. Type hints and documentation
Use Python 3.10+ unions (`float | int`), typed dictionaries or dataclasses when a contract grows. Write docstrings that describe units, inclusivity, error conditions and side effects. Static type checking can detect many interface mismatches but cannot replace runtime validation or unit tests.

## 9. Composition
Small functions are easier to reason about:
```python
def describe_latency(latency_ms: float, warning_ms: float, critical_ms: float) -> dict:
    return {
        "latency_ms": latency_ms,
        "classification": classify_latency(
            latency_ms, warning_ms=warning_ms, critical_ms=critical_ms
        ),
    }
```
Prefer explicit composition over deeply nested branches.

## 10. Complexity and performance
A scalar threshold function is O(1) time and space. Applying it to n events is O(n). Avoid repeatedly parsing configuration or making network calls inside pure classification functions. Benchmark only when there is a demonstrated performance problem.

## 11. Operational use cases
- Elasticsearch query-latency classification.
- PostgreSQL replication lag threshold checks.
- Kubernetes pod restart severity classification.
- Kafka consumer lag classification.
- Redis memory pressure signals.
- Snowflake warehouse credit-usage categorization.

Units and policy thresholds vary by system. Keep them configurable, versioned and reviewed by the owning team.

## 12. Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| `TypeError: missing argument` | Required keyword not supplied | Pass named argument |
| Thresholds silently swapped | Positional arguments | Use keyword-only parameters |
| Inconsistent results across calls | Shared mutable default | Use `None` sentinel |
| Invalid value labeled healthy | Missing validation | Reject invalid inputs |
| Hard-to-test code | Network I/O embedded in decision function | Separate pure core from adapters |
| `None` returned unexpectedly | Missing `return` branch | Define explicit return contract |
| Boolean accepted as numeric | `bool` subclasses `int` | Reject boolean explicitly |

## 13. Hands-on lab
[Chapter 021 — SRE Alert Classification Functions Lab](labs/021-sre-alert-classification-functions-lab.md) implements a reusable, validated library and CLI for latency/error-rate classification, with deterministic JSON reports, strict function contracts, unit tests and failure injection.

## 14. Exercises
1. Refactor a script that reads JSON and prints decisions into pure functions plus CLI.
2. Explain the difference between `return`, `yield`, and `print`.
3. Add a keyword-only threshold and test swapped values.
4. Write preconditions/postconditions for a disk-usage percentage function.
5. Explain why runtime validation is required even with type hints.

**Next: Chapter 022 — Function Scope, Closures and Higher-Order Functions.**
