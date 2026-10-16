# Chapter 008 — Lists, Tuples, Sets and Dictionaries

**Part 01 — Python Fundamentals | Python 3.10+ | Study: 75–100 minutes**

## Learning objectives
Choose the appropriate collection for an operational workload; understand mutability, iteration, membership, sorting, comprehensions, shallow copying, dictionary keys and sets; build a deterministic SRE inventory validator with tests.

## 1. Choosing a collection
| Type | Ordered? | Mutable? | Duplicate elements? | Typical SRE use |
|---|---|---|---|---|
| `list` | Yes | Yes | Yes | Ordered node inventory |
| `tuple` | Yes | No | Yes | Fixed host/port pair |
| `set` | No guaranteed order | Yes | No | Deduplicate service names |
| `dict` | Insertion ordered | Yes | Keys unique | Node name → metadata |

Membership in a list is typically O(n); dictionary and set membership are typically O(1) average, with worst cases dependent on hashing. Lists support O(1) amortized append, but insertion at the front shifts elements.

## 2. Lists
```python
nodes = ["node-a", "node-b"]
nodes.append("node-c")
nodes.extend(["node-d"])
print(nodes[0], nodes[-1], nodes[1:3])
for node in nodes:
    print(node)
```
Indexing an empty list raises `IndexError`. Slicing creates a new list. `list.sort()` modifies the list in place; `sorted(list)` creates a new list.

## 3. Tuples and unpacking
```python
endpoint = ("api.internal", 443)
host, port = endpoint
print(host, port)
```
Tuple immutability does not freeze mutable objects stored inside a tuple.

## 4. Sets
```python
expected = {"api", "worker", "scheduler"}
observed = {"api", "worker", "worker"}
print(expected - observed)  # {'scheduler'}
print(expected & observed)  # common elements
print(expected | observed)  # union
```
Do not rely on set iteration order for reports. Sort before emitting deterministic results.

## 5. Dictionaries
```python
inventory = {
    "node-a": {"region": "us-east-1", "cpu": 4},
    "node-b": {"region": "us-west-2", "cpu": 8},
}
for name, info in inventory.items():
    print(name, info["region"])
print(inventory.get("node-c"))  # None
```
Use `in` to distinguish a missing key from a key mapped to `None`. Dictionary keys must be hashable; lists and dictionaries cannot be keys.

## 6. Comprehensions
```python
nodes = [{"name": "a", "cpu": 4}, {"name": "b", "cpu": 8}]
large_nodes = [item["name"] for item in nodes if item["cpu"] >= 8]
by_name = {item["name"]: item for item in nodes}
```
**Caution:** The dictionary comprehension above silently overwrites duplicate names. Validate duplicates before indexing. Avoid dense nested comprehensions in incident tooling.

## 7. Copying and aliasing
```python
original = {"node": {"labels": ["prod"]}}
shallow = original.copy()
shallow["node"]["labels"].append("critical")
assert original["node"]["labels"] == ["prod", "critical"]
```
A shallow copy preserves references to nested objects. Use `copy.deepcopy` only when you need independent nested structures and understand the cost.

## 8. Sorting and determinism
```python
nodes = [{"name": "b", "cpu": 8}, {"name": "a", "cpu": 4}]
for node in sorted(nodes, key=lambda item: item["name"]):
    print(node["name"])
```
Deterministic output makes CI diffs, incident evidence and audits easier to review.

## 9. Operational design: inventory reconciliation
A reconciliation process compares expected versus observed resources, identifies missing/unexpected entries, validates unique identifiers, and reports discrepancies. Do not automatically delete unexpected resources: reconcile with owners and approved change controls first.

## 10. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `KeyError` | Missing dictionary key | Validate required keys |
| `IndexError` | Invalid list position | Check bounds |
| `TypeError: unhashable type` | Mutable set/dict key | Use immutable hashable key |
| Lost duplicate entries | Dict overwrite | Detect duplicates first |
| Nondeterministic report | Unsorted set iteration | Use `sorted()` |
| Accidental nested mutation | Shallow copy | Copy nested data intentionally |
| Slow repeated membership | Linear list scans | Use set/dict for lookup |

## 11. Hands-on lab
Complete [Chapter 008 — SRE Inventory Reconciliation Lab](labs/008-sre-inventory-reconciliation-lab.md). It uses local JSON fixtures, validates schema and duplicates, reports missing/unexpected resources, and includes ten unit tests.

## Exercises
1. Add environment filtering to the inventory.
2. Compare the runtime cost of list versus set membership.
3. Explain why dict key uniqueness requires explicit duplicate detection.
4. Sort reconciliation results for stable CI output.
5. Design a safe owner-approval step before any remediation.

**Next:** Chapter 009 — User Input, Output and Formatting.
