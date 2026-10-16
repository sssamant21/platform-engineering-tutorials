# Chapter 012 — Advanced Dictionaries, Sets and Data Modeling

**Part 02 — Data Types and Algorithms | Python 3.10+ | 75–100 minutes**

## Learning objectives
Model operational inventory with nested dictionaries, apply set algebra for reconciliation, aggregate data safely, avoid duplicate-key overwrites, choose deterministic output, understand shallow copying and hashability, and test a read-only SRE configuration drift detector.

## 1. Dictionary internals and semantics
Dictionaries map unique hashable keys to values and preserve insertion order (Python 3.7+ language guarantee). Lookup, insert and delete are typically O(1) average, but hash collisions can degrade performance. Reassigning a key replaces its value without changing its insertion position.

```python
inventory = {"api": {"replicas": 3, "tier": "critical"}}
inventory["worker"] = {"replicas": 2, "tier": "standard"}
print(inventory["api"]["replicas"])
print(inventory.get("scheduler"))  # None
```
Use `key in mapping` to distinguish a missing key from a key whose value is `None`.

## 2. Nested mappings and safe access
```python
node = {"name": "node-a", "labels": {"environment": "prod"}}
environment = node.get("labels", {}).get("environment", "unknown")
```
This shortcut assumes `labels` is a mapping. If it is `None` or a list, an exception occurs. For untrusted JSON, validate the schema first rather than chaining `.get()` calls.

## 3. Dictionary comprehensions
```python
nodes = [{"name": "a", "cpu": 4}, {"name": "b", "cpu": 8}]
by_name = {node["name"]: node for node in nodes}
```
Duplicate names are silently overwritten. Explicitly reject duplicates when keys represent unique resources.

## 4. Set algebra for drift
```python
expected = {"api", "worker", "scheduler"}
actual = {"api", "worker", "debug"}
missing = expected - actual
unexpected = actual - expected
common = expected & actual
combined = expected | actual
symmetric = expected ^ actual
print(sorted(missing), sorted(unexpected), sorted(common))
```
Sets are unordered. Sort for stable CI and audit output. Membership is typically O(1) average. Use `frozenset` when an immutable set is needed as a key.

## 5. Aggregation with collections
```python
from collections import Counter, defaultdict
statuses = ["healthy", "warning", "healthy", "critical"]
print(Counter(statuses))
by_environment = defaultdict(list)
for name, env in [("api", "prod"), ("worker", "staging")]:
    by_environment[env].append(name)
print(dict(by_environment))
```
`Counter` is useful for totals; `defaultdict` avoids repeated initialization. Validate input types before aggregation.

## 6. Merging and conflict policy
```python
defaults = {"replicas": 2, "timeout": 30}
overrides = {"replicas": 4}
merged = defaults | overrides
print(merged)  # overrides win
```
The `|` mapping union operator requires Python 3.9+. A merge is shallow. For production configuration, document override precedence and never silently merge conflicting security settings.

## 7. Copying and aliasing
```python
original = {"api": {"labels": ["prod"]}}
shallow = original.copy()
shallow["api"]["labels"].append("tier1")
assert original["api"]["labels"] == ["prod", "tier1"]
```
Use `copy.deepcopy` if you require fully independent nested structures; avoid copying large inventories unnecessarily.

## 8. Data modeling for SRE/DBRE
A service record can include `name`, `environment`, `owner`, `replicas`, and `tier`. Make identity explicit: a resource name alone may not be globally unique across environments. For reconciliation, use a composite key such as `(environment, name)` and validate uniqueness.

Do not automatically remove unexpected services or apply configuration changes. Differences may reflect autoscaling, maintenance, staged rollouts or an outdated source of truth. Seek owner approval and a change ticket before remediation.

## 9. Practical example: composite keys
```python
records = [
    {"environment": "prod", "name": "api", "replicas": 3},
    {"environment": "staging", "name": "api", "replicas": 1},
]
index = {(row["environment"], row["name"]): row for row in records}
assert len(index) == 2
```

## 10. Common failures
| Symptom | Cause | Resolution |
|---|---|---|
| `KeyError` | Missing mapping key | Validate or use explicit fallback |
| `TypeError: unhashable type` | Mutable key | Use tuple or immutable identifier |
| Lost inventory entry | Duplicate key overwrite | Reject duplicates |
| Nondeterministic report | Unsorted set iteration | Sort output |
| Nested mutation affects source | Shallow copy | Deep-copy deliberately |
| Unexpected override | Merge precedence | Document conflict policy |
| False drift | Stale inventory | Validate timestamps and ownership |

## 11. Hands-on lab
Complete [Chapter 012 — Configuration Drift and Inventory Reconciliation](labs/012-configuration-drift-inventory-lab.md). It builds a local, read-only CLI that compares two JSON service inventories, detects missing/unexpected services and changed configuration, and emits deterministic JSON with unit tests.

## 12. Exercises
1. Add an owner mismatch check.
2. Explain why a composite key is safer than service name alone.
3. Compare `Counter` and a manual dictionary accumulator.
4. Write tests for duplicates and nested schema errors.
5. Explain why configuration drift should not automatically trigger deletion.

**Next:** Chapter 013 — Tuples, NamedTuples, Dataclasses and Structured Records.
