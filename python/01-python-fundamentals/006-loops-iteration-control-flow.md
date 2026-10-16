# Chapter 006 — Loops, Iteration and Control Flow

**Part 01 — Python Fundamentals | Python 3.10+ | Estimated time: 75–100 minutes**

## Learning objectives
Use `for` and `while` loops, `range()`, `enumerate()`, `zip()`, `break`, `continue`, and loop `else`; distinguish iterables from iterators; avoid infinite loops; and implement bounded, testable SRE health checks.

## 1. Why loops matter to SRE
SRE tools often process many nodes, deployments, metrics or log entries. Loops enable consistent checks without duplicating code. Avoid unbounded retries and accidental API overload.

## 2. The `for` loop
```python
nodes = ["node-a", "node-b", "node-c"]
for node in nodes:
    print(f"Checking {node}")
```
A `for` loop asks an iterable for an iterator and consumes items until exhaustion. Dictionaries iterate over keys by default; use `.items()` for key-value pairs.

```python
metrics = {"node-a": 45, "node-b": 92}
for node, cpu_pct in metrics.items():
    print(node, cpu_pct)
```

## 3. `range()`, `enumerate()` and `zip()`
```python
for attempt in range(1, 4):
    print("attempt", attempt)

for position, node in enumerate(["a", "b"], start=1):
    print(position, node)

for node, latency in zip(["a", "b"], [30, 70], strict=True):
    print(node, latency)
```
`range(1, 4)` yields 1, 2, 3. `enumerate` gives index/item pairs. `zip(..., strict=True)` (Python 3.10+) rejects unequal lengths instead of silently dropping trailing values.

## 4. `while` loops and bounded retries
```python
attempt = 0
max_attempts = 3
while attempt < max_attempts:
    attempt += 1
    print(f"Attempt {attempt}/{max_attempts}")
```
In real network retries, also enforce per-request timeouts, total deadlines, exponential backoff with jitter, and idempotency; never retry every error indefinitely.

## 5. `break`, `continue`, and loop `else`
```python
for code in [200, 503, 200]:
    if code == 503:
        continue  # skip this iteration
    if code == 200:
        print("first success")
        break
else:
    print("no success found")
```
Loop `else` runs only if the loop finishes normally, without `break`. It is not the same as `if/else`.

## 6. Nested loops and complexity
```python
namespaces = ["staging", "prod"]
services = ["api", "worker"]
for namespace in namespaces:
    for service in services:
        print(namespace, service)
```
Two nested loops may process the product of their input sizes. For large fleets, use pagination, rate limiting, bounded concurrency, and backpressure.

## 7. Iterators and generators
```python
def batches(items: list[str], size: int):
    if size <= 0:
        raise ValueError("size must be positive")
    for start in range(0, len(items), size):
        yield items[start:start + size]

for batch in batches(["a", "b", "c"], 2):
    print(batch)
```
Generators yield results incrementally. They help avoid materializing every intermediate item, though the input list above is already in memory.

## 8. Safe SRE pattern: classify a fleet
```python
def status(cpu_pct: float) -> str:
    if cpu_pct >= 90:
        return "critical"
    if cpu_pct >= 75:
        return "warning"
    return "healthy"

fleet = {"node-a": 40, "node-b": 80, "node-c": 95}
for name, cpu in fleet.items():
    print(f"{name}: {status(cpu)}")
```
Validate data before classification; missing or non-finite telemetry should not be reported healthy.

## 9. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| Infinite loop | No progress or bound | Increment counter, add deadline |
| Off-by-one | Exclusive range end | Check `range` endpoints |
| Missing items | `zip` truncation | Use `strict=True` |
| `RuntimeError` on dict iteration | Mutating dictionary size | Iterate over snapshot or build new dict |
| Wrong loop `else` behavior | Misunderstood `break` | Test normal completion vs break |
| Slow fleet scan | Serial network calls | Add timeouts, batching and controlled concurrency |
| Empty input ignored | No validation | Handle empty fleet explicitly |

## 10. Lab and acceptance
Complete [Chapter 006 — Multi-Node Health Check Lab](labs/006-multi-node-health-check-lab.md). The lab processes a local JSON fixture, handles invalid/missing metrics, emits a summary and has unit tests. It makes no live network calls.

Acceptance: 10 unit tests pass; invalid metrics are unknown; nodes are processed in deterministic order; exit codes reflect fleet health.

## 11. Exercises
1. Change thresholds to 70/90 and update tests.
2. Use `enumerate` to number report rows.
3. Use `zip(strict=True)` to combine two equal-length input lists.
4. Explain why infinite retry loops are unsafe.
5. Implement a generator yielding critical nodes.

**Next:** Chapter 007 — Strings and Text Processing.
