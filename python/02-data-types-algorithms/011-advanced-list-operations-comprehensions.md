# Chapter 011 — Advanced List Operations and Comprehensions

**Part 02 — Data Types and Algorithms | Python 3.10+ | 75–100 minutes**

## Learning objectives
Manipulate lists safely, use slicing and unpacking, distinguish in-place methods from functions returning new lists, apply comprehensions and generator expressions, understand aliasing and complexity, and implement a deterministic SRE metric transformation.

## 1. Lists and mutability
```python
nodes = ["node-a", "node-b"]
nodes.append("node-c")
nodes.extend(["node-d", "node-e"])
nodes.insert(1, "node-x")
removed = nodes.pop()
print(nodes, removed)
```
`append` adds one object; `extend` iterates over its argument. `pop` raises `IndexError` on an empty list. Appending is amortized O(1); inserting at the front is O(n).

## 2. Slicing and unpacking
```python
latencies = [20, 50, 90, 150, 300]
print(latencies[:3], latencies[-2:], latencies[::-1])
first, *middle, last = latencies
print(first, middle, last)
```
Slicing produces a shallow copy. For a very large dataset, copying slices repeatedly can waste memory.

## 3. Sorting
```python
hosts = [{"name": "b", "cpu": 80}, {"name": "a", "cpu": 30}]
ordered = sorted(hosts, key=lambda row: (row["cpu"], row["name"]))
print(ordered)
hosts.sort(key=lambda row: row["name"])
```
`sorted()` creates a new list. `list.sort()` sorts in place and returns `None`. Python's sort is stable, preserving original order for equal keys.

## 4. List comprehensions
```python
cpu_values = [15, 75, 90, 40]
warnings = [cpu for cpu in cpu_values if cpu >= 75]
labels = ["high" if cpu >= 75 else "normal" for cpu in cpu_values]
print(warnings, labels)
```
Comprehensions are concise for simple transformations. Prefer explicit loops when validation, exception handling, logging or multi-step business logic would make a comprehension difficult to read.

## 5. Nested comprehensions and flattening
```python
regions = [[{"name": "a"}], [{"name": "b"}, {"name": "c"}]]
flat = [node for region in regions for node in region]
```
The iteration order follows the equivalent nested loops: outer `for region`, then inner `for node`.

## 6. Generator expressions
```python
cpu = [20, 85, 91]
critical_count = sum(1 for value in cpu if value >= 90)
any_critical = any(value >= 90 for value in cpu)
```
Generator expressions yield items lazily; `any` and `all` short-circuit. `all([])` is `True` and `any([])` is `False`; validate empty telemetry sets explicitly.

## 7. Aliasing and copying
```python
original = [[1], [2]]
shallow = original.copy()
shallow[0].append(9)
assert original[0] == [1, 9]
```
A shallow copy does not clone nested objects. Use `copy.deepcopy` selectively when independent nested state is needed.

## 8. Common pitfalls
```python
# BAD: every row refers to the same inner list
bad = [[]] * 3
bad[0].append("x")
# GOOD: independent inner lists
good = [[] for _ in range(3)]
```
Avoid modifying a list while iterating over it; build a new list or iterate over a deliberate snapshot.

## 9. Complexity and operational considerations
| Operation | Typical cost |
|---|---|
| Index access | O(1) |
| Append | Amortized O(1) |
| Membership | O(n) |
| Front insert/delete | O(n) |
| Sort | O(n log n) |
| Full copy or slice | O(n) |

For large metrics files, streaming iteration and bounded memory may be preferable to constructing intermediate lists. Use deterministic sorting for reproducible CI and incident reports.

## 10. SRE example
```python
samples = [
    {"node": "a", "cpu_pct": 45},
    {"node": "b", "cpu_pct": 88},
    {"node": "c", "cpu_pct": 96},
]
high = [sample["node"] for sample in samples if sample["cpu_pct"] >= 80]
top = sorted(samples, key=lambda sample: (-sample["cpu_pct"], sample["node"]))
print(high, top)
```
Validate missing, non-finite or out-of-range values **before** calculating rankings.

## 11. Hands-on lab
[Chapter 011 — SRE Fleet Metrics Transformation Lab](labs/011-fleet-metrics-transformation-lab.md) builds a read-only JSON metrics ranking CLI with explicit validation, deterministic ordering, filters and unit tests.

## 12. Troubleshooting
| Problem | Cause | Fix |
|---|---|---|
| `TypeError: NoneType is not iterable` | Assigned `list.sort()` result | Use `sorted()` or sort then read list |
| `IndexError` | Empty list access | Validate nonempty input |
| Incorrect shared data | Nested list multiplication | Use comprehension |
| `KeyError` | Missing metric key | Validate schema |
| Unexpected NaN sorting | Non-finite values | Reject non-finite metrics |
| Excess memory | Repeated full copies | Stream or batch |

## Exercises
1. Compare `append` and `extend`.
2. Add a secondary sort key to break metric ties.
3. Explain why `all([])` should not mean healthy fleet.
4. Refactor a complex comprehension into a loop.
5. Analyze time and memory costs for one million samples.

**Next:** Chapter 012 — Advanced Dictionaries, Sets and Data Modeling.
