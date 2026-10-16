# Chapter 008 — Hands-on Lab: SRE Inventory Reconciliation

## Scenario
Compare an expected node inventory with an observed node inventory. Identify missing and unexpected nodes without changing any infrastructure.

## Prerequisites
Python 3.10+; standard library only.

## Step 1 — Create `expected.json`
```json
[
  {"name": "node-a", "environment": "prod"},
  {"name": "node-b", "environment": "prod"},
  {"name": "node-c", "environment": "staging"}
]
```

## Step 2 — Create `observed.json`
```json
[
  {"name": "node-a", "environment": "prod"},
  {"name": "node-c", "environment": "staging"},
  {"name": "node-x", "environment": "dev"}
]
```

## Step 3 — Create `inventory_reconcile.py`
```python
"""Read-only JSON inventory reconciliation."""
import argparse
import json
from pathlib import Path

ALLOWED_ENVIRONMENTS = {"prod", "staging", "dev"}


def index_inventory(records: object) -> dict[str, str]:
    if not isinstance(records, list):
        raise ValueError("inventory must be a JSON array")
    result = {}
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"entry {number} must be an object")
        name = record.get("name")
        environment = record.get("environment")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"entry {number}: invalid name")
        if not isinstance(environment, str) or environment not in ALLOWED_ENVIRONMENTS:
            raise ValueError(f"entry {number}: invalid environment")
        if name in result:
            raise ValueError(f"duplicate node: {name}")
        result[name] = environment
    return result


def reconcile(expected: object, observed: object) -> dict:
    desired = index_inventory(expected)
    actual = index_inventory(observed)
    desired_names = set(desired)
    actual_names = set(actual)
    missing = sorted(desired_names - actual_names)
    unexpected = sorted(actual_names - desired_names)
    mismatched = [
        {"name": name, "expected": desired[name], "observed": actual[name]}
        for name in sorted(desired_names & actual_names)
        if desired[name] != actual[name]
    ]
    return {
        "expected_count": len(desired),
        "observed_count": len(actual),
        "missing": missing,
        "unexpected": unexpected,
        "environment_mismatches": mismatched,
        "in_sync": not (missing or unexpected or mismatched),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only inventory reconciliation")
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.expected.open(encoding="utf-8") as source:
            expected = json.load(source)
        with args.observed.open(encoding="utf-8") as source:
            observed = json.load(source)
        result = reconcile(expected, observed)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["in_sync"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 4 — Create `test_inventory_reconcile.py`
```python
import unittest
from inventory_reconcile import index_inventory, reconcile

def item(name, environment="prod"):
    return {"name": name, "environment": environment}

class InventoryTests(unittest.TestCase):
    def test_in_sync(self):
        self.assertTrue(reconcile([item("a")], [item("a")])["in_sync"])
    def test_missing(self):
        self.assertEqual(reconcile([item("a")], [])["missing"], ["a"])
    def test_unexpected(self):
        self.assertEqual(reconcile([], [item("x")])["unexpected"], ["x"])
    def test_environment_mismatch(self):
        report = reconcile([item("a", "prod")], [item("a", "dev")])
        self.assertEqual(len(report["environment_mismatches"]), 1)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            index_inventory([item("a"), item("a")])
    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            index_inventory([item("")])
    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            index_inventory([item("a", "unknown")])
    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            index_inventory({"name": "a"})
    def test_invalid_entry(self):
        with self.assertRaises(ValueError):
            index_inventory([42])
    def test_deterministic_order(self):
        result = reconcile([item("z"), item("a")], [])
        self.assertEqual(result["missing"], ["a", "z"])

if __name__ == "__main__":
    unittest.main()
```

## Step 5 — Run
```bash
python inventory_reconcile.py --expected expected.json --observed observed.json
python -m unittest -v test_inventory_reconcile.py
python -m py_compile inventory_reconcile.py
```
Expected: `missing=["node-b"]`, `unexpected=["node-x"]`, `in_sync=false`. The CLI exits 1 intentionally when drift exists. Ten unit tests should pass.

## Step 6 — Failure injection
1. Duplicate `node-a` in expected inventory: validation error.
2. Change observed `node-a` to `dev`: environment mismatch.
3. Use invalid JSON: parse error.
4. Change environment to `unknown`: validation error.
5. Restore fixtures after each test.

## Operational guardrails
- This is a **report-only** lab. Never auto-delete an unexpected node.
- Validate source freshness and ownership before remediation.
- Review cloud autoscaling and ephemeral resources before treating drift as an incident.
- Keep inventory snapshots free of credentials and sensitive metadata.

## Acceptance checklist
- [ ] Missing and unexpected nodes detected
- [ ] Environment mismatch detected
- [ ] Duplicate names rejected
- [ ] Stable sorted output
- [ ] Ten tests pass
- [ ] No infrastructure changes made

## Cleanup
Remove only files created for this lab.
