# Chapter 017 — Hashing, Lookup Tables and Deduplication

**Part 02 — Data Types and Algorithms | Python 3.10+ | 90–120 minutes**

## Outcomes
Explain hashing, equality and collision handling; use sets and dictionaries for efficient lookups; distinguish Python's process-dependent `hash()` from stable cryptographic digests; choose deduplication keys and retention windows; and build a safe, deterministic SRE event deduplication tool.

## 1. What hashing does
A hash function maps a key to an integer used by hash tables. Python dictionaries and sets provide average-case O(1) insertion, membership and lookup, with possible worst-case degradation under adversarial collisions. Equal keys must have equal hashes; unequal keys may share a hash.

```python
owners = {"api": "platform", "db": "data"}
assert owners["api"] == "platform"
assert "cache" not in owners
seen = {"INC-001", "INC-002"}
assert "INC-001" in seen
```

## 2. Hashable keys and equality
Immutable strings, integers and tuples of hashable values can be dictionary keys. Lists and dictionaries cannot.

```python
key = ("prod", "api")
index = {key: {"replicas": 3}}
```

A frozen dataclass is hashable only if its fields are hashable. Do not mutate fields that participate in equality or hashing while objects are used as keys.

## 3. Collisions and complexity
Python manages collisions internally; do not assume unique hashes. Lookup is generally O(1) average but can degrade toward O(n) in pathological cases. Hash-table indexes consume additional O(n) memory.

## 4. Why `hash()` is not a durable ID
`hash("example")` is not stable across all interpreter runs or machines due to randomized hashing and implementation differences. Do not store it as an event fingerprint. Use an explicit canonical identity or, when needed, a digest such as SHA-256 of canonical serialized data.

```python
import hashlib
import json
payload = {"service": "api", "event": "timeout"}
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

A digest is not a substitute for deciding which fields define event identity. Cryptographic hashes have theoretical collisions, and a digest alone does not establish authenticity.

## 5. Event identity versus occurrence
Two alerts may have the same service and signature but represent separate occurrences. Deduplication policy must define scope and window. For this lab, identity is the tuple `(environment, service, signature)` and duplicates are collapsed **within one input batch**. This is not temporal suppression, persistent deduplication or delivery assurance.

## 6. First-seen versus last-seen policy
```python
events = [("api", "timeout"), ("db", "slow"), ("api", "timeout")]
seen = set()
unique = []
for event in events:
    if event not in seen:
        seen.add(event)
        unique.append(event)
```
This preserves first occurrence order. For counts, use a dictionary indexed by the same key. Always document whether the first, last or most severe occurrence wins.

## 7. Common mistakes
- Deduplicating on message text alone may merge unrelated incidents.
- Including timestamps in the key may prevent any deduplication.
- Dropping duplicates without counts destroys useful frequency evidence.
- Unbounded `seen` sets cause memory growth.
- Python's `hash()` is unsuitable for persisted fingerprints.
- Normalization (case folding, trimming) must follow a documented identifier policy.
- Deduplication must not silently acknowledge or delete production alerts.

## 8. Production SRE considerations
For event streams, define a time window, key schema/version, eviction policy, durable storage, concurrency semantics, replay handling, auditability and metrics for suppressed occurrences. For Kafka or other brokers, deduplication is distinct from exactly-once processing guarantees and must account for retries and replays.

## 9. Complexity
For n events, set/dict-backed in-memory batch deduplication takes O(n) expected time and O(u) memory for u unique identities. Sorting unique identities for deterministic reports adds O(u log u).

## 10. Lab
[Chapter 017 — SRE Event Deduplication Lab](labs/017-sre-event-deduplication-lab.md) provides a full JSON CLI, strict validation, composite-key deduplication, counts, deterministic reports, 16 unit tests and failure injection.

## 11. Troubleshooting
| Problem | Cause | Fix |
|---|---|---|
| `TypeError: unhashable type` | Mutable key | Use tuple of validated strings |
| Duplicate not detected | Inconsistent key normalization | Establish policy |
| Unrelated events merged | Key too broad | Include environment/service/signature |
| Huge memory use | Unbounded identity index | Add bounded windows/eviction |
| Unstable output | Unsorted set/dict-derived keys | Sort report |
| Different fingerprint across runs | Using `hash()` | Use canonical SHA-256 if persistent digest needed |

## Exercises
1. Compare first-seen and last-seen policies.
2. Add a count threshold for noisy event groups.
3. Design a time-windowed policy without dropping critical alerts.
4. Explain hash collision versus duplicate event identity.
5. Describe safe Kafka replay and idempotency behavior.

**Next:** Chapter 018 — Iterators, Generators and Lazy Data Processing.
