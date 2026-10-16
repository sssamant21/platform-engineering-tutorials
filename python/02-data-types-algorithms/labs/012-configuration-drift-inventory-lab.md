# Chapter 012 — Hands-on Lab: SRE Configuration Drift Detector

## Scenario
Compare desired and observed service configuration inventories stored in local JSON. Identify missing/unexpected services and changed replica counts or owners. This tool is report-only.

## Prerequisites
Python 3.10+; standard library only.

## Step 1 — Create `desired.json`
```json
[
  {"environment":"prod","name":"api","replicas":3,"owner":"platform"},
  {"environment":"prod","name":"worker","replicas":2,"owner":"data"},
  {"environment":"staging","name":"api","replicas":1,"owner":"platform"}
]
```

## Step 2 — Create `observed.json`
```json
[
  {"environment":"prod","name":"api","replicas":2,"owner":"platform"},
  {"environment":"staging","name":"api","replicas":1,"owner":"platform"},
  {"environment":"dev","name":"debug","replicas":1,"owner":"platform"}
]
```

## Step 3 — Create `drift_check.py`
```python
"""Read-only SRE service configuration reconciliation."""
import argparse
import json
from pathlib import Path

ENVIRONMENTS = {"dev", "staging", "prod"}


def index_records(records: object) -> dict[tuple[str, str], dict]:
    if not isinstance(records, list):
        raise ValueError("inventory must be a JSON array")
    indexed = {}
    for position, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"entry {position} must be an object")
        env = record.get("environment")
        name = record.get("name")
        owner = record.get("owner")
        replicas = record.get("replicas")
        if not isinstance(env, str) or env not in ENVIRONMENTS:
            raise ValueError(f"entry {position}: invalid environment")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"entry {position}: invalid service name")
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError(f"entry {position}: invalid owner")
        if isinstance(replicas, bool) or not isinstance(replicas, int) or not 0 <= replicas <= 10000:
            raise ValueError(f"entry {position}: invalid replicas")
        key = (env, name)
        if key in indexed:
            raise ValueError(f"duplicate service: {env}/{name}")
        indexed[key] = {"environment": env, "name": name,
                        "owner": owner, "replicas": replicas}
    return indexed


def reconcile(desired: object, observed: object) -> dict:
    expected = index_records(desired)
    actual = index_records(observed)
    expected_keys = set(expected)
    actual_keys = set(actual)
    missing = [{"environment": env, "name": name} for env, name in sorted(expected_keys - actual_keys)]
    unexpected = [{"environment": env, "name": name} for env, name in sorted(actual_keys - expected_keys)]
    changed = []
    for key in sorted(expected_keys & actual_keys):
        differences = {}
        for field in ("owner", "replicas"):
            if expected[key][field] != actual[key][field]:
                differences[field] = {"expected": expected[key][field], "observed": actual[key][field]}
        if differences:
            changed.append({"environment": key[0], "name": key[1], "differences": differences})
    return {"missing": missing, "unexpected": unexpected, "changed": changed,
            "in_sync": not (missing or unexpected or changed),
            "desired_count": len(expected), "observed_count": len(actual)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only service configuration drift report")
    parser.add_argument("--desired", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.desired.open(encoding="utf-8") as source:
            desired = json.load(source)
        with args.observed.open(encoding="utf-8") as source:
            observed = json.load(source)
        report = reconcile(desired, observed)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["in_sync"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 4 — Create `test_drift_check.py`
```python
import unittest
from drift_check import index_records, reconcile

def service(name="api", env="prod", replicas=3, owner="platform"):
    return {"name": name, "environment": env, "replicas": replicas, "owner": owner}

class DriftTests(unittest.TestCase):
    def test_in_sync(self):
        self.assertTrue(reconcile([service()], [service()])["in_sync"])
    def test_missing(self):
        self.assertEqual(len(reconcile([service()], [])["missing"]), 1)
    def test_unexpected(self):
        self.assertEqual(len(reconcile([], [service()])["unexpected"]), 1)
    def test_replicas_changed(self):
        report = reconcile([service()], [service(replicas=2)])
        self.assertIn("replicas", report["changed"][0]["differences"])
    def test_owner_changed(self):
        report = reconcile([service()], [service(owner="data")])
        self.assertIn("owner", report["changed"][0]["differences"])
    def test_composite_key(self):
        self.assertEqual(len(index_records([service(env="prod"), service(env="staging")])), 2)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            index_records([service(), service()])
    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            index_records({})
    def test_invalid_replicas_bool(self):
        with self.assertRaises(ValueError):
            index_records([service(replicas=True)])
    def test_invalid_replicas_negative(self):
        with self.assertRaises(ValueError):
            index_records([service(replicas=-1)])
    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            index_records([service(env="unknown")])
    def test_deterministic_missing(self):
        report = reconcile([service("z"), service("a")], [])
        self.assertEqual([item["name"] for item in report["missing"]], ["a", "z"])

if __name__ == "__main__":
    unittest.main()
```

## Step 5 — Run
```bash
python drift_check.py --desired desired.json --observed observed.json
python -m unittest -v test_drift_check.py
python -m py_compile drift_check.py
```
Expected: one missing service (`prod/worker`), one unexpected service (`dev/debug`), one changed replica count (`prod/api`), and `in_sync=false`. Exit code 1 means drift detected. Twelve unit tests should pass.

## Step 6 — Failure injection
1. Duplicate `prod/api` in desired: schema error.
2. Set replicas to `true` or `-1`: schema error.
3. Remove owner: schema error.
4. Supply invalid JSON: parse error.
5. Restore the fixtures after each test.

## Production safety
- This tool does **not** perform deletions, scaling or updates.
- Inventory freshness, resource ownership and autoscaling policies must be reviewed before remediation.
- A change request and rollback plan are required for production modifications.
- Do not place secrets or sensitive information in inventory fixtures.

## Acceptance checklist
- [ ] Missing, unexpected and changed services detected
- [ ] Composite keys support identical service names across environments
- [ ] Stable sorted output
- [ ] Duplicate and invalid records rejected
- [ ] Twelve tests pass
- [ ] No production changes

## Cleanup
Delete only files created for this lab.
