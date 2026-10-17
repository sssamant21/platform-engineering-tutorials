# Chapter 023 — Lambda Expressions, map, filter, reduce and Functional Composition

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 90–120 minutes**

## Learning objectives
Use anonymous functions, `map`, `filter`, `functools.reduce`, comprehensions and generator expressions appropriately; compose validated, lazy transformations; understand iterator exhaustion, failure timing and numeric aggregation; and build a reproducible SRE telemetry processing pipeline.

## 1. Functions as values
Functions are first-class objects: assign them, pass them as callbacks and return them from factories.

```python
def milliseconds_to_seconds(value):
    return value / 1000

converter = milliseconds_to_seconds
assert converter(250) == 0.25
```

This enables separation of policy decisions from file reading, network I/O and incident response.

## 2. Lambda expressions
A lambda creates an anonymous function limited to **one expression**:

```python
severity_rank = lambda severity: {"info": 0, "warning": 1, "critical": 2}[severity]
assert severity_rank("critical") == 2
```

Prefer `def` for reusable functions needing validation, annotations, documentation, multiple branches or debugging. Lambda closures follow the same lexical scope and late-binding rules as named functions.

## 3. map: transform each item
```python
samples_ms = [100, 250, 500]
seconds = map(lambda ms: ms / 1000, samples_ms)
assert list(seconds) == [0.1, 0.25, 0.5]
```

`map` is lazy in Python 3. Transformations occur during iteration, so errors may arise long after pipeline construction. Do not mistake `map` for parallel execution.

## 4. filter: retain matching items
```python
events = [{"latency_ms": 80}, {"latency_ms": 420}]
slow = filter(lambda event: event["latency_ms"] >= 250, events)
assert list(slow) == [{"latency_ms": 420}]
```

`filter` returns an iterator and does not copy the entire source. Validate events **before** evaluating predicates on untrusted fields.

## 5. reduce: fold into one result
```python
from functools import reduce

total = reduce(lambda subtotal, value: subtotal + value, [3, 5, 7], 0)
assert total == 15
```

Always consider an explicit initializer: `reduce` without one fails on empty inputs. For sums use `sum()`, for counts use `Counter`, and for maximum use `max(..., default=...)` when clearer. Use `reduce` for genuinely custom associative or sequential accumulation, not as a readability contest.

## 6. Comprehensions versus functional operators
```python
latencies = [100, 500, 800]
slow_seconds = [ms / 1000 for ms in latencies if ms >= 250]
lazy_slow_seconds = (ms / 1000 for ms in latencies if ms >= 250)
```

A list comprehension eagerly materializes results; a generator expression remains lazy. For ordinary Python transformations, comprehensions are often more readable than nested `map(filter(...))` calls.

## 7. Composition and ordering
A safe pipeline is **read → parse → validate → normalize → filter → aggregate → report**. The order matters: filtering malformed records before validation can silently conceal data-quality incidents.

```python
def compose(*functions):
    def run(value):
        for function in reversed(functions):
            value = function(value)
        return value
    return run

double_then_increment = compose(lambda x: x + 1, lambda x: x * 2)
assert double_then_increment(3) == 7
```

This `compose` applies right-to-left, as in mathematical function composition. In operational code, an explicit sequence of named transformations is often easier to troubleshoot.

## 8. Iterator lifetime and exhaustion
```python
source = map(str, range(3))
assert list(source) == ["0", "1", "2"]
assert list(source) == []  # already consumed
```

Create a new pipeline for another pass. If a generator holds an open file, consume it within the file context. Do not use `itertools.tee` on an unbounded stream without considering its internal buffering.

## 9. Complexity and memory
For n events, one map/filter pipeline is O(n) time with O(1) per-item auxiliary memory, excluding source buffering and aggregation. A dictionary of k services adds O(k) memory. Building a list of all events costs O(n) memory. Nested scans and repeated sorting can dominate performance.

## 10. Correctness and numerical stability
Reject `bool` for numeric latency even though `bool` subclasses `int`. Reject `NaN` and infinities using `math.isfinite`. Floating-point sums can accumulate error; `math.fsum` improves precision but needs iterable inputs, while incremental O(1) memory accumulation trades precision for bounded state. This lab reports counts and maximum latency, avoiding floating-point sum ambiguity.

## 11. SRE/DBRE use cases
- Filter sanitized Elasticsearch slow-query events.
- Transform Kubernetes restart event exports.
- Classify PostgreSQL query latency by service.
- Count Kafka consumer errors by environment.
- Aggregate synthetic Redis memory-pressure warnings.
- Prepare deterministic dry-run reports for incident analysis.

## 12. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| Empty second result | Iterator exhausted | Recreate iterator |
| Error occurs at iteration time | Lazy evaluation | Validate and catch errors at consumption boundary |
| Malformed event silently omitted | Filter before validation | Validate first |
| `TypeError` on empty reduction | No initializer | Provide initial accumulator |
| Excessive memory | `list()` on large stream | Stream and aggregate |
| Hard-to-debug traceback | Nested anonymous functions | Use named functions |
| Different output order | Unsorted aggregate keys | Sort final summary |
| Incorrect numeric comparisons | Boolean/NaN input | Explicit strict validation |

## 13. Hands-on lab
Complete [Chapter 023 — Functional SRE Telemetry Pipeline Lab](labs/023-functional-sre-telemetry-pipeline-lab.md). It implements a read-only JSONL pipeline with `map`, `filter`, `reduce`, generator iteration, CLI configuration, unit tests and failure injection.

## 14. Acceptance and review
- Explain eager versus lazy evaluation.
- Compare a comprehension to `map` and `filter`.
- Explain why `reduce` needs an initializer for empty input.
- Demonstrate validation before filtering.
- Produce deterministic, bounded-memory aggregation.
- Run all lab tests locally before operational use.

**Next: Chapter 024 — Decorators, functools and Reusable Operational Instrumentation.**
