# Chapter 013 — Tuples, NamedTuples, Dataclasses and Structured Records

**Part 02 — Data Types and Algorithms | Python 3.10+ | 75–100 minutes**

## Learning objectives
Compare positional tuples, `typing.NamedTuple`, `dataclasses.dataclass` and dictionaries; model immutable SRE inventory records; understand equality, hashing, type annotations, default factories, validation, serialization and safe configuration handling.

## 1. Tuples and unpacking
```python
endpoint = ("api.internal", 443)
host, port = endpoint
print(host, port)
```
Tuples preserve order and cannot be resized or have elements reassigned. They may still contain mutable objects. A tuple is hashable only when all its elements are hashable.

## 2. NamedTuple
```python
from typing import NamedTuple

class Endpoint(NamedTuple):
    host: str
    port: int

endpoint = Endpoint("api.internal", 443)
print(endpoint.host, endpoint[1])
```
Named tuples are immutable tuple subclasses with named fields. Type annotations are documentation and static-checking inputs, not runtime validation.

## 3. Dataclasses
```python
from dataclasses import dataclass

@dataclass
class Node:
    name: str
    cpu: int
    region: str = "us-east-1"

node = Node("node-a", 4)
print(node.name, node)
```
Dataclasses generate an initializer, representation and equality comparison. Ordinary dataclasses are mutable and generally unhashable by default.

## 4. Frozen dataclasses and validation
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Service:
    name: str
    replicas: int

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("service name cannot be empty")
        if isinstance(self.replicas, bool) or not isinstance(self.replicas, int) or self.replicas < 0:
            raise ValueError("replicas must be a nonnegative integer")
```
`frozen=True` prevents normal field reassignment but does **not** recursively freeze nested lists or dictionaries. For immutable collections, prefer tuples and frozensets or create defensive copies.

## 5. Mutable defaults
```python
from dataclasses import dataclass, field

@dataclass
class NodeLabels:
    name: str
    labels: dict[str, str] = field(default_factory=dict)
```
Use `default_factory` for mutable per-instance state. Sharing one mutable default across instances creates hard-to-debug cross-resource contamination.

## 6. Serialization
```python
from dataclasses import asdict, dataclass
import json

@dataclass
class Metric:
    service: str
    latency_ms: int

print(json.dumps(asdict(Metric("api", 120))))
```
`asdict` recursively copies nested dataclass structures; use carefully on large inventories. JSON decoding returns ordinary dict/list structures, not validated dataclass instances. Explicitly construct and validate objects after decoding.

## 7. Comparison and data modeling
| Structure | Fields | Mutable? | Best use |
|---|---|---|---|
| tuple | Positional | No (shallow) | Small fixed keys |
| NamedTuple | Named + positional | No (shallow) | Lightweight immutable records |
| dataclass | Named | Yes by default | Rich domain objects |
| frozen dataclass | Named | No normal reassignment | Validated immutable-ish records |
| dict | Dynamic keys | Yes | Raw JSON and flexible payloads |

For SRE/DBRE automation, prefer explicit schemas for infrastructure inventory. Composite identifiers such as `(environment, name)` prevent collisions across environments.

## 8. Pattern matching and unpacking
Python 3.10+ supports structural pattern matching. Use it when branches are genuinely clearer than `if/elif`, but do not assume it performs schema validation.

## 9. Operational pitfalls
- Do not assume type hints enforce runtime types.
- Reject `True` as an integer when validating replica counts.
- Avoid secrets in dataclass `repr` output; use `field(repr=False)` for sensitive fields, but this is not a security boundary.
- Keep identifiers normalized only according to an agreed resource naming policy.
- Sort report output to make CI and incident evidence deterministic.
- Do not auto-remediate inventory discrepancies without owner approval.

## 10. Troubleshooting
| Symptom | Cause | Resolution |
|---|---|---|
| `FrozenInstanceError` | Assigning frozen field | Create replacement via `dataclasses.replace` |
| `TypeError: unhashable type` | Mutable dataclass or nested field | Use immutable hashable fields |
| Shared labels unexpectedly | Mutable default aliasing | Use `default_factory` |
| Invalid type accepted | Hints only | Validate in `__post_init__` |
| JSON output fails | Custom object not serializable | Use `asdict` or explicit mapping |
| Duplicate host overwritten | Dict keyed by name | Validate composite identity |

## 11. Hands-on lab
Complete [Chapter 013 — Typed SRE Infrastructure Inventory Lab](labs/013-typed-infrastructure-inventory-lab.md). Build validated frozen dataclasses from local JSON, index by composite identity, filter and summarize records, and run unit tests.

## 12. Exercises
1. Add a region field and validate it.
2. Demonstrate frozen dataclass behavior.
3. Explain shallow versus deep immutability.
4. Compare `NamedTuple` and `dataclass` ergonomics.
5. Add a unit test for invalid boolean replica counts.

**Next:** Chapter 014 — Stacks, Queues and Deques for Operational Workflows.
