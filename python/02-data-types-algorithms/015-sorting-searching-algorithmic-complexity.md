# Chapter 015 — Sorting, Searching and Algorithmic Complexity

**Part 02 — Data Types and Algorithms | Python 3.10+ | 90–120 minutes**

## Objectives
Analyze algorithmic time and space complexity, distinguish linear and binary search, use stable sorting and multi-key ordering, apply `bisect` safely, benchmark without misleading conclusions, and build a deterministic SRE latency analysis tool.

## 1. Big O and scaling
Big O describes asymptotic upper bounds, not exact elapsed time. Common growth classes include O(1), O(log n), O(n), O(n log n), and O(n²). Real performance also depends on allocation, caching, input distribution, I/O, runtime and hardware.

| Operation | Typical time | Additional memory |
|---|---|---|
| List indexing | O(1) | O(1) |
| Linear scan | O(n) | O(1) |
| Dict/set membership | O(1) average | O(n) for index |
| Binary search sorted list | O(log n) | O(1) |
| Python `sorted` | O(n log n) worst-case | O(n) worst-case |
| Nested all-pairs comparison | O(n²) | O(1) if streamed |

## 2. Linear search
```python
events = [{"id": "a", "ms": 40}, {"id": "b", "ms": 180}]
match = next((row for row in events if row["id"] == "b"), None)
```
Linear search works without sorting and is often simplest for small datasets. If `None` could be a legitimate value, use a unique sentinel instead.

## 3. Stable sorting
```python
events = [
    {"service": "api", "latency_ms": 90},
    {"service": "db", "latency_ms": 90},
    {"service": "cache", "latency_ms": 150},
]
ranked = sorted(events, key=lambda row: (-row["latency_ms"], row["service"]))
```
`sorted()` returns a new list; `list.sort()` mutates and returns `None`. Python sorting is stable: equal keys retain their original relative order. Explicit secondary keys produce deterministic reports even when input order varies.

## 4. Binary search with bisect
```python
from bisect import bisect_left, bisect_right
latencies = [12, 30, 30, 80, 200]
assert bisect_left(latencies, 30) == 1
assert bisect_right(latencies, 30) == 3
```
The input **must already be sorted** according to the same ordering. `bisect_left` returns an insertion point; check bounds and equality before treating it as an exact match.

## 5. Range counts with bisect
```python
from bisect import bisect_left
values = sorted([90, 10, 200, 50])
count_at_or_above_90 = len(values) - bisect_left(values, 90)
assert count_at_or_above_90 == 2
```
Sorting costs O(n log n); each later binary-search query costs O(log n). For a single threshold scan, O(n) may be cheaper than sorting.

## 6. Percentiles and interpretation
Nearest-rank percentile for n > 0 uses index `ceil(p*n)-1` for p in (0,1]. This is one valid quantile convention; other systems interpolate and can produce different answers. State the method in every report. A point-in-time p95 does not by itself establish an SLO violation.

## 7. Benchmarking
```python
from timeit import repeat
data = list(range(10000))
timings = repeat("9999 in data", globals={"data": data}, number=100, repeat=5)
print(min(timings))
```
Warm up, repeat, vary input sizes and compare equivalent operations. Avoid treating microbenchmarks as production throughput predictions. Never benchmark against production databases or APIs without approval.

## 8. Choosing a data structure
For frequent exact lookup, build a dict keyed by validated unique ID. For membership checks, use a set. For ordered threshold queries, sort once and use bisect. For continuous streaming or memory-constrained processing, consider bounded aggregation rather than materializing all samples.

## 9. Failure modes
- Binary search on unsorted data returns misleading results.
- NaN values can violate ordering assumptions; reject non-finite telemetry.
- Sorting string-form numbers produces lexicographic rather than numeric order.
- `bool` is an `int` subclass; reject booleans for numeric metrics.
- Empty inputs make percentile calculations undefined.
- Ties require documented secondary ordering.
- Do not equate a latency spike with an incident without sustained windows and context.

## 10. Hands-on lab
[Chapter 015 — SRE Latency Sorting and Search Lab](labs/015-latency-sorting-search-lab.md) builds a local read-only JSON CLI that validates latency samples, ranks slow requests, computes nearest-rank p50/p95/p99, counts requests over a threshold using binary search and verifies results with automated tests.

## 11. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| Wrong binary search index | Unsorted data | Sort first |
| `IndexError` in percentile | Empty list | Validate nonempty |
| Unexpected ties | No secondary sort key | Sort by latency and ID |
| `TypeError` during sorting | Mixed types | Validate schema |
| Wrong percentile | Different quantile definition | Document nearest-rank |
| Slow repeated lookups | Repeated O(n) scan | Build index where justified |

## Exercises
1. Compare a one-off linear scan to sort-plus-bisect.
2. Implement exact-match binary search with a bounds check.
3. Explain the impact of repeated sorting on runtime.
4. Compare nearest-rank p95 with interpolated p95.
5. Design a bounded-memory strategy for a million samples.

**Next:** Chapter 016 — Recursion, Iteration and Recursive Data Structures.
