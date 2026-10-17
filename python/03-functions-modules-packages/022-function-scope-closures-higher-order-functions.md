# Chapter 022 — Function Scope, Closures and Higher-Order Functions

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 90–120 minutes**

## Learning outcomes
Understand LEGB name resolution, local/global/nonlocal scope, lexical closures, late binding, function factories, callbacks, decorators, higher-order functions, and testable SRE policy composition. Build an offline telemetry filter with injectable policies and isolated per-instance state.

## 1. Why scope matters in SRE automation
A script that relies on mutable module-level state can mix results between environments or incident investigations. Hidden state makes concurrency, testing and retries difficult. Explicit parameters and function-local state keep operational tools predictable.

## 2. LEGB: local, enclosing, global, built-in
Python resolves an unqualified name by searching **L**ocal, **E**nclosing, **G**lobal and **B**uilt-in scopes, in that order.

```python
label = "global"

def outer():
    label = "enclosing"
    def inner():
        label = "local"
        return label
    return inner()

assert outer() == "local"
```

Assignments within a function create local bindings unless declared `global` or `nonlocal`. A local read before assignment can raise `UnboundLocalError`.

## 3. global versus nonlocal
```python
def counter_factory():
    count = 0
    def increment():
        nonlocal count
        count += 1
        return count
    return increment

a = counter_factory()
b = counter_factory()
assert (a(), a(), b()) == (1, 2, 1)
```

`nonlocal` rebinds a variable in the nearest enclosing function scope. `global` rebinds a module variable. Prefer explicit dependency injection or isolated closures over mutable globals in operational tooling.

## 4. Closures and function factories
A closure retains references to values from its lexical environment after the outer function returns.

```python
def threshold_policy(threshold_ms):
    def is_slow(latency_ms):
        return latency_ms >= threshold_ms
    return is_slow

slow_prod = threshold_policy(250)
slow_lab = threshold_policy(500)
assert slow_prod(300) is True
assert slow_lab(300) is False
```

A closure captures a **binding**, not an immutable snapshot of an object. If it captures a mutable dictionary, later mutations can change behavior. Prefer immutable configuration values for policies.

## 5. Late binding trap
```python
# Incorrect: all lambdas use the final loop variable.
bad = [lambda: index for index in range(3)]
assert [fn() for fn in bad] == [2, 2, 2]

# Capture the current value as a default argument.
good = [lambda index=index: index for index in range(3)]
assert [fn() for fn in good] == [0, 1, 2]
```

## 6. Higher-order functions
A higher-order function accepts or returns another function. Python functions are first-class objects.

```python
def count_matching(events, predicate):
    return sum(1 for event in events if predicate(event))

events = [{"latency_ms": 100}, {"latency_ms": 500}]
slow = lambda event: event["latency_ms"] >= 250
assert count_matching(events, slow) == 1
```

Use named functions for nontrivial logic; anonymous lambdas are best for short expressions. Validate data before invoking callbacks, and never execute arbitrary callback code from untrusted sources.

## 7. Decorators
Decorators wrap callable behavior. `functools.wraps` preserves metadata such as `__name__` and `__doc__`.

```python
from functools import wraps

def count_calls(function):
    calls = 0
    @wraps(function)
    def wrapper(*args, **kwargs):
        nonlocal calls
        calls += 1
        return function(*args, **kwargs)
    wrapper.get_calls = lambda: calls
    return wrapper

@count_calls
def classify(value):
    return value >= 250

assert classify(300)
assert classify.get_calls() == 1
assert classify.__name__ == "classify"
```

The counter is for a single-process educational example, **not** thread-safe or a production metric. In production use a metrics client with proper synchronization and cardinality controls. Decorators must not accidentally swallow exceptions or expose secrets in logs.

## 8. Callbacks and dependency injection
Pass a policy function as an argument rather than hardcoding alert rules:

```python
def evaluate(records, predicate):
    return [record for record in records if predicate(record)]
```

This makes a dry-run policy, testing stub and approved production policy interchangeable without embedding network I/O in the decision function. Keep callbacks pure and avoid passing sensitive data to unknown plugins.

## 9. Scope, state and concurrency
Closures are useful for encapsulation, but mutable closure state is not automatically thread-safe. In multiworker Kubernetes jobs, each process has separate memory; a closure cannot provide global deduplication or distributed rate limits. Use an external, durable state store when cross-process coordination is required.

## 10. Complexity
For n events, a predicate-based filter evaluates each event once: O(n) time. Streaming counts require O(1) additional memory if the predicate and iterator are constant-space. Materializing selected events requires O(m) memory for m matches.

## 11. SRE/DBRE scenarios
- Environment-specific Elasticsearch slow-query thresholds.
- PostgreSQL replication-lag classification policies.
- Kafka consumer-lag callback selection.
- Kubernetes pod restart severity rules.
- Synthetic Redis memory-pressure event filters.
- Unit-testable dry-run incident triage.

## 12. Troubleshooting

| Symptom | Root cause | Fix |
|---|---|---|
| `UnboundLocalError` | Local assigned after attempted read | Pass argument or use `nonlocal` when appropriate |
| All callbacks use last loop value | Late binding | Capture with default argument or factory |
| Test state leaks between cases | Shared global or mutable closure | Create fresh function factory per test |
| Decorator hides function metadata | Missing `functools.wraps` | Apply `@wraps` |
| Unexpected side effects | Callback performs I/O | Keep policy pure |
| Incorrect distributed counts | Per-process closure state | Use shared durable store |
| Hard-to-debug wrapper | Exceptions swallowed | Propagate failures with context |

## 13. Hands-on lab
[Chapter 022 — SRE Policy Factory and Callback Lab](labs/022-sre-policy-factory-callback-lab.md) implements a policy factory, higher-order streaming evaluator, per-instance closure counters, and an offline JSON CLI with unit tests.

## 14. Exercises
1. Explain how two calls to the same factory isolate state.
2. Reproduce and fix the loop-lambda late binding bug.
3. Write a decorator that preserves function metadata.
4. Describe when `nonlocal` is appropriate and when a dataclass is clearer.
5. Explain why a closure cannot coordinate incident counts across replicas.

**Next: Chapter 023 — Lambda Expressions, map, filter, reduce and Functional Composition.**
