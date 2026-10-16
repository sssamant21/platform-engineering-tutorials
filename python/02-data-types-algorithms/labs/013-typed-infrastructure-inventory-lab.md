# Chapter 013 — Hands-on Lab: Typed SRE Infrastructure Inventory

## Scenario
Convert local JSON inventory records into validated frozen dataclasses, detect duplicate composite identifiers, and generate deterministic aggregate reports. This is a read-only educational lab.

## Prerequisites
Python 3.10+; standard library only.

## Step 1 — Create `inventory.json`
```json
[
  {"environment":"prod","name":"api","replicas":3,"owner":"platform"},
  {"environment":"staging","name":"api","replicas":1,"owner":"platform"},
  {"environment":"prod","name":"worker","replicas":2,"owner":"data"}
]
```

## Step 2 — Create `typed_inventory.py`
```python
"""Read-only validated infrastructure inventory."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

ENVIRONMENTS = frozenset({"dev", "staging", "prod"})


@dataclass(frozen=True, slots=True)
class Service:
    environment: str
    name: str
    replicas: int
    owner: str

    def __post_init__(self):
        if not isinstance(self.environment, str) or self.environment not in ENVIRONMENTS:
            raise ValueError("invalid environment")
        for field in ("name", "owner"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"invalid {field}")
        if isinstance(self.replicas, bool) or not isinstance(self.replicas, int) or not 0 <= self.replicas <= 10000:
            raise ValueError("replicas must be an integer in [0,10000]")

    @property
    def identity(self) -> tuple[str, str]:
        return (self.environment, self.name)


def load_inventory(records: object) -> list[Service]:
    if not isinstance(records, list):
        raise ValueError("inventory must be a JSON array")
    result = []
    seen = set()
    required = {"environment", "name", "replicas", "owner"}
    for number, record in enumerate(records, 1):
        if not isinstance(record, dict) or set(record) != required:
            raise ValueError(f"entry {number}: incorrect fields")
        service = Service(**record)
        if service.identity in seen:
            raise ValueError(f"duplicate service: {service.identity}")
        seen.add(service.identity)
        result.append(service)
    return sorted(result, key=lambda item: item.identity)


def summarize(records: object) -> dict:
    services = load_inventory(records)
    environments = sorted({item.environment for item in services})
    return {
        "service_count": len(services),
        "total_replicas": sum(item.replicas for item in services),
        "by_environment": {
            env: {
                "services": sum(1 for item in services if item.environment == env),
                "replicas": sum(item.replicas for item in services if item.environment == env),
            }
            for env in environments
        },
        "services": [
            {"environment": item.environment, "name": item.name,
             "replicas": item.replicas, "owner": item.owner}
            for item in services
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only typed inventory summary")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            records = json.load(source)
        report = summarize(records)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_typed_inventory.py`
```python
import unittest
from dataclasses import FrozenInstanceError
from typed_inventory import Service, load_inventory, summarize

def record(name="api", env="prod", replicas=3, owner="platform"):
    return {"name": name, "environment": env, "replicas": replicas, "owner": owner}

class TypedInventoryTests(unittest.TestCase):
    def test_construct(self):
        self.assertEqual(Service(**record()).name, "api")
    def test_identity(self):
        self.assertEqual(Service(**record()).identity, ("prod", "api"))
    def test_frozen(self):
        service = Service(**record())
        with self.assertRaises(FrozenInstanceError):
            service.name = "changed"
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            load_inventory([record(), record()])
    def test_same_name_different_env(self):
        self.assertEqual(len(load_inventory([record(), record(env="staging")])), 2)
    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            Service(**record(env="unknown"))
    def test_empty_name(self):
        with self.assertRaises(ValueError):
            Service(**record(name=""))
    def test_empty_owner(self):
        with self.assertRaises(ValueError):
            Service(**record(owner=""))
    def test_bool_replicas(self):
        with self.assertRaises(ValueError):
            Service(**record(replicas=True))
    def test_negative_replicas(self):
        with self.assertRaises(ValueError):
            Service(**record(replicas=-1))
    def test_wrong_fields(self):
        with self.assertRaises(ValueError):
            load_inventory([{"name": "api"}])
    def test_sorted(self):
        items = load_inventory([record("z"), record("a")])
        self.assertEqual([item.name for item in items], ["a", "z"])
    def test_total_replicas(self):
        self.assertEqual(summarize([record(), record("worker", replicas=2)])["total_replicas"], 5)
    def test_empty_inventory(self):
        self.assertEqual(summarize([])["service_count"], 0)

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Run
```bash
python typed_inventory.py --input inventory.json
python -m unittest -v test_typed_inventory.py
python -m py_compile typed_inventory.py
```
Expected: three services, six total replicas, two prod services with five replicas, one staging service with one replica, and fourteen passing tests.

## Step 5 — Failure injection
1. Duplicate `prod/api`: validation error.
2. Change replicas to `true`: validation error.
3. Remove owner: validation error.
4. Add an unexpected field: validation error.
5. Use invalid JSON: parser error.

## Safety and interpretation
The report summarizes static fixture values. It does not measure actual running replicas or reconcile with Kubernetes. Production inventory requires authoritative source validation, freshness checks and owner approval before any changes.

## Acceptance checklist
- [ ] Frozen dataclass validation
- [ ] Composite identities
- [ ] Deterministic sorting
- [ ] Per-environment aggregates
- [ ] Fourteen tests pass
- [ ] No infrastructure changes

## Cleanup
Delete only the files created for this lab.
