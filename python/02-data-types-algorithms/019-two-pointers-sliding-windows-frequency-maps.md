# Chapter 019 — Algorithmic Patterns: Two Pointers, Sliding Windows and Frequency Maps

**Part 02 — Data Types and Algorithms | Python 3.10+ | 100–140 minutes**

## Learning objectives
Apply two-pointer scanning, fixed and variable sliding windows, and frequency maps; reason about complexity and sorted-input assumptions; build deterministic SRE error-rate analysis; validate event ordering, timestamps and schemas; and test edge cases and production failure modes.

## 1. Why patterns matter
Repeated scans of telemetry can turn an O(n) analysis into O(n²). Algorithmic patterns reuse state to reduce repeated work. Choose the pattern based on the actual input contract, not just a familiar code shape.

| Pattern | Typical problem | Time | Auxiliary space |
|---|---|---|---|
| Two pointers | Merge or scan sorted sequences | O(n + m) | O(1) excluding output |
| Fixed-count sliding window | Last k samples | O(n) | O(k) |
| Time-based sliding window | Events in trailing interval | O(n) for sorted events | O(w) retained events |
| Frequency map | Counts by service or error code | O(n) expected | O(u) distinct keys |

## 2. Two pointers on sorted arrays
```python
def intersect_sorted(left: list[int], right: list[int]) -> list[int]:
    i = j = 0
    result = []
    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            result.append(left[i])
            i += 1
            j += 1
        elif left[i] < right[j]:
            i += 1
        else:
            j += 1
    return result

assert intersect_sorted([1, 3, 5], [2, 3, 5]) == [3, 5]
```
This implementation preserves duplicate matches up to the minimum multiplicity of each value. **Both inputs must be sorted.** For unordered collections, sort first or choose a set-based strategy.

## 3. Fixed-size sliding window
```python
from collections import deque

def rolling_sums(values, k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")
    window = deque()
    total = 0
    for value in values:
        window.append(value)
        total += value
        if len(window) > k:
            total -= window.popleft()
        if len(window) == k:
            yield total

assert list(rolling_sums([2, 4, 6, 8], 2)) == [6, 10, 14]
```
A generator avoids materializing all output windows. The deque retains O(k) values. A window of k samples is **not** the same as a window of k seconds when event arrival is irregular.

## 4. Time-based sliding window
For timestamp-sorted events, keep a deque of records in the trailing interval and evict old records from the left. This lab uses the explicit inclusive interval **[t − window_seconds, t]**. A record at exactly the left boundary is included; evict only when its timestamp is strictly less than the boundary.

```python
from collections import deque

def rolling_error_counts(events, window_seconds):
    pending = deque()
    errors = 0
    for event in events:
        now = event["timestamp"]
        pending.append(event)
        errors += int(event["is_error"])
        while pending and pending[0]["timestamp"] < now - window_seconds:
            errors -= int(pending.popleft()["is_error"])
        yield now, errors, len(pending)
```
This demonstration assumes already validated, nondecreasing timestamps and positive window size. Production code must also handle out-of-order delivery, duplicate events, lateness, and time-zone conventions.

## 5. Frequency maps
```python
from collections import Counter
codes = ["timeout", "timeout", "rate-limit", "timeout"]
counts = Counter(codes)
assert counts["timeout"] == 3
```
Use `Counter` for category counts and dictionaries for richer aggregates. Guard against unbounded label cardinality: unique request IDs should not become metric labels.

## 6. Error-rate and SLO interpretation
A rolling error rate is `errors / total_events` within a defined window. It is an event-weighted rate, not necessarily a request-weighted SLO unless every event corresponds to exactly one eligible request. This lab's alert threshold is an educational signal, not a production paging policy. Real burn-rate alerts need traffic floors, multiwindow checks, error-budget context and reliable telemetry.

## 7. Complexity analysis
A naive time-window implementation may rescan all prior events for each event: O(n²). With sorted timestamps, every event is inserted once and evicted once: O(n) total time. Memory is O(w), where w is the maximum number of events simultaneously in the window; a time limit alone does not cap memory during a high-volume burst.

## 8. Validation and ordering
Require strict record schemas, nonnegative finite timestamps, boolean `is_error`, nonempty service names, and nondecreasing timestamps. Reject unsorted input rather than silently sorting: sorting changes streaming semantics and consumes O(n) memory. For distributed systems, event time versus processing time must be defined separately.

## 9. Production SRE use cases
- API gateway rolling error rate and service-level incident triage.
- Kafka consumer retry and failure-event frequency.
- Kubernetes pod restart bursts from synthetic event exports.
- Database connection-failure trends.
- Elasticsearch timeout bursts and slow-query counts.

## 10. Failure modes and troubleshooting
| Symptom | Cause | Remediation |
|---|---|---|
| Wrong window count | Boundary inclusion mismatch | Document inclusive/exclusive interval |
| Negative counts | Incorrect eviction accounting | Update counters exactly once per event |
| Misleading alert | Very low event volume | Require minimum sample count |
| Out-of-order records | Clock skew or mixed streams | Reject or implement event-time buffering |
| Memory spike | High event density | Add bounded state / external aggregation |
| High CPU | Repeated full scans | Use deque and incremental counts |
| Wrong cross-service rate | Mixed service events | Maintain separate windows per service |
| Flaky test | Wall-clock timestamps | Use deterministic fixture timestamps |

## 11. Hands-on lab
Complete [Chapter 019 — Rolling SRE Error Rate Lab](labs/019-rolling-sre-error-rate-lab.md). Build a local read-only JSONL CLI using per-service deques, frequency maps, deterministic reporting, strict validation and automated tests.

## 12. Exercises
1. Implement a fixed-count moving average with a deque.
2. Explain why event ordering is a precondition for the time-window algorithm.
3. Add a count of errors by service and by error category.
4. Compare two-pointer intersection with set intersection.
5. Design a production policy for late-arriving telemetry.

**Next: Chapter 020 — Data Structures and Algorithms Capstone: SRE Telemetry Analyzer.**
