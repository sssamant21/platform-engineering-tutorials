# Chapter 014 — Stacks, Queues and Deques for Operational Workflows

**Part 02 — Data Types and Algorithms | Python 3.10+ | 90 minutes**

## Objectives
Understand LIFO and FIFO processing; choose between lists, `collections.deque`, `queue.Queue`, `LifoQueue` and `PriorityQueue`; model bounded incident backlogs; reason about fairness, ordering, retries and overload; implement a deterministic, read-only incident dispatcher.

## 1. Stacks: last in, first out (LIFO)
A stack processes the most recently added item first. It is useful for undo operations, nested traversal and rollback plans. A rollback plan must still respect dependencies and approvals.

```python
stack = ["step-1", "step-2"]
stack.append("step-3")
assert stack.pop() == "step-3"
```
List `append()` and `pop()` at the end are amortized O(1). Popping from an empty list raises `IndexError`.

## 2. Queues: first in, first out (FIFO)
FIFO queues preserve arrival order and can help prevent starvation when all work has equal priority.

```python
from collections import deque
pending = deque(["incident-a", "incident-b"])
pending.append("incident-c")
assert pending.popleft() == "incident-a"
```
`deque.append()` and `deque.popleft()` are O(1) at their respective ends. Avoid repeated `list.pop(0)`, which shifts remaining elements and costs O(n).

## 3. Double-ended queues
```python
from collections import deque
recent = deque(maxlen=3)
for event in ("a", "b", "c", "d"):
    recent.append(event)
assert list(recent) == ["b", "c", "d"]
```
A bounded `deque(maxlen=N)` automatically discards older entries when full. That behavior is useful for rolling histories but **unsafe for lossless work queues** unless eviction is explicitly intended.

## 4. Thread-safe queues
```python
from queue import Queue, Empty, Full
q = Queue(maxsize=2)
q.put_nowait("task-a")
try:
    task = q.get_nowait()
except Empty:
    task = None
else:
    q.task_done()
```
`queue.Queue` coordinates threads and supports blocking operations, `maxsize`, `task_done()` and `join()`. A plain `deque` does not replace a full producer/consumer coordination protocol. `queue.Queue` is not a distributed durable broker.

## 5. LIFO and priority queues
```python
from queue import LifoQueue, PriorityQueue
recovery = LifoQueue()
recovery.put("last-change")
assert recovery.get() == "last-change"

alerts = PriorityQueue()
alerts.put((0, "critical"))
alerts.put((2, "informational"))
assert alerts.get()[1] == "critical"
```
Lower numeric priority comes out first. Use a sequence number as a tie breaker for stable ordering; otherwise equal-priority payloads may be compared or processed in an unintended order. Prioritization may starve low-priority work.

## 6. Queueing and capacity
Bounded queues provide a backpressure point. Decide what happens when capacity is reached: reject with a visible error, block with a timeout, or persist to a durable store. Do **not** silently discard incidents. Track queue depth, oldest age, enqueue rate, processing rate, rejects and dead-letter counts.

## 7. Complexity
| Operation | List | deque |
|---|---:|---:|
| Append right | Amortized O(1) | O(1) |
| Pop right | O(1) | O(1) |
| Pop left | O(n) | O(1) |
| Random index | O(1) | O(n) in the middle |
| Membership | O(n) | O(n) |

For a small ordered set of incidents, a list may suffice. For FIFO dispatch, prefer a deque or thread-safe Queue depending on concurrency.

## 8. SRE incident workflow
A safe incident dispatcher validates records, enforces unique IDs, accepts only known severities, queues in arrival order, and emits a deterministic report. The accompanying lab supports FIFO and severity-priority modes. Priority mode is intentionally a **batch simulation**, not a claim of fair or durable real-time dispatch.

## 9. Safety and failure modes
- Never use a volatile in-memory queue as the only record of critical incidents.
- Do not acknowledge work as complete before durable downstream processing.
- Add retry limits, idempotency keys and dead-letter handling in production.
- Avoid unbounded queues and uncontrolled worker concurrency.
- Avoid auto-remediation without authorization.
- Redact secrets and personal data from incident summaries.
- Make shutdown and cancellation behavior explicit.

## 10. Troubleshooting
| Symptom | Cause | Mitigation |
|---|---|---|
| `IndexError` | Pop from empty list/deque | Check or catch |
| `queue.Empty` | Nonblocking read on empty queue | Handle or use timeout |
| `queue.Full` | Bounded queue at capacity | Backpressure and alert |
| `join()` never returns | Missing `task_done()` | Balance successful `get()` calls |
| Starved low-priority tasks | Strict priority ordering | Aging/fairness policy |
| Lost incidents | Silent eviction or process crash | Durable queue and acknowledgments |
| Unstable ordering | Missing tie breaker | Monotonic sequence number |

## 11. Hands-on lab
Complete [Chapter 014 — Incident Queue and Priority Dispatcher Lab](labs/014-incident-queue-priority-dispatcher-lab.md). It uses a synthetic local JSON fixture, FIFO and severity-priority dispatch, capacity validation, deterministic reports and unit tests.

## Exercises
1. Explain why `deque(maxlen=N)` is dangerous for lossless incident queues.
2. Compare FIFO with strict severity priority for a busy on-call rotation.
3. Design idempotency and durable acknowledgment requirements.
4. Add a fourth severity with a documented priority.
5. Discuss backpressure under sustained producer overload.

**Next:** Chapter 015 — Sorting, Searching and Algorithmic Complexity.
