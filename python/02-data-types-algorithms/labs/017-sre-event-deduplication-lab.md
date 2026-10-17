# Chapter 017 — Hands-on Lab: SRE Event Deduplication

## Scenario
Analyze synthetic SRE events from a local JSON file. Group events by validated `(environment, service, signature)` keys, count occurrences, preserve first-seen information and emit a deterministic report. **No alerts are deleted, suppressed or sent.**

## Step 1 — `events.json`
```json
[
  {"id":"EV-003","environment":"prod","service":"api","signature":"timeout"},
  {"id":"EV-001","environment":"prod","service":"api","signature":"timeout"},
  {"id":"EV-002","environment":"prod","service":"db","signature":"slow-query"},
  {"id":"EV-004","environment":"staging","service":"api","signature":"timeout"},
  {"id":"EV-005","environment":"prod","service":"api","signature":"timeout"}
]
```

## Step 2 — `event_dedupe.py`
```python
"""Read-only, deterministic batch event deduplication."""
import argparse
import json
from pathlib import Path

FIELDS = {"id", "environment", "service", "signature"}


def validate(records: object) -> list[dict]:
    if not isinstance(records, list):
        raise ValueError("expected a JSON array")
    seen_ids = set()
    result = []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ValueError(f"event {index}: incorrect fields")
        for field in FIELDS:
            value = record[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"event {index}: invalid {field}")
        if record["id"] in seen_ids:
            raise ValueError(f"duplicate event id: {record['id']}")
        seen_ids.add(record["id"])
        result.append(dict(record))
    return result


def summarize(records: object) -> dict:
    events = validate(records)
    groups = {}
    for event in events:
        key = (event["environment"], event["service"], event["signature"])
        if key not in groups:
            groups[key] = {"environment": key[0], "service": key[1],
                           "signature": key[2], "first_seen_id": event["id"],
                           "count": 0, "event_ids": []}
        groups[key]["count"] += 1
        groups[key]["event_ids"].append(event["id"])
    ordered = []
    for key in sorted(groups):
        item = groups[key]
        item["event_ids"].sort()
        ordered.append(item)
    return {
        "input_count": len(events),
        "unique_identity_count": len(ordered),
        "duplicate_occurrence_count": len(events) - len(ordered),
        "groups": ordered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SRE event deduplication report")
    parser.add_argument("--input", required=True, type=Path)
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

## Step 3 — `test_event_dedupe.py`
```python
import unittest
from event_dedupe import summarize, validate

def event(identifier="E1", env="prod", service="api", signature="timeout"):
    return {"id": identifier, "environment": env, "service": service,
            "signature": signature}

class EventDedupeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(summarize([])["unique_identity_count"], 0)
    def test_single(self):
        self.assertEqual(summarize([event()])["input_count"], 1)
    def test_same_identity(self):
        self.assertEqual(summarize([event("a"), event("b")])["unique_identity_count"], 1)
    def test_duplicate_occurrence_count(self):
        self.assertEqual(summarize([event("a"), event("b")])["duplicate_occurrence_count"], 1)
    def test_distinct_environment(self):
        self.assertEqual(summarize([event("a"), event("b", env="staging")])["unique_identity_count"], 2)
    def test_distinct_service(self):
        self.assertEqual(summarize([event("a"), event("b", service="db")])["unique_identity_count"], 2)
    def test_distinct_signature(self):
        self.assertEqual(summarize([event("a"), event("b", signature="latency")])["unique_identity_count"], 2)
    def test_first_seen(self):
        self.assertEqual(summarize([event("z"), event("a")])["groups"][0]["first_seen_id"], "z")
    def test_sorted_event_ids(self):
        self.assertEqual(summarize([event("z"), event("a")])["groups"][0]["event_ids"], ["a", "z"])
    def test_sorted_groups(self):
        rows = [event("z", service="z"), event("a", service="a")]
        self.assertEqual(summarize(rows)["groups"][0]["service"], "a")
    def test_duplicate_id(self):
        with self.assertRaises(ValueError):
            validate([event(), event()])
    def test_missing_field(self):
        with self.assertRaises(ValueError):
            validate([{"id": "x"}])
    def test_extra_field(self):
        bad = event()
        bad["secret"] = "value"
        with self.assertRaises(ValueError):
            validate([bad])
    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            validate([event(signature=42)])
    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            validate({})
    def test_original_unchanged(self):
        rows = [event()]
        summarize(rows)
        self.assertEqual(rows[0]["id"], "E1")

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python event_dedupe.py --input events.json
python -m unittest -v test_event_dedupe.py
python -m py_compile event_dedupe.py
```
Expected: five input events, three unique composite identities, two duplicate occurrences, and a `prod/api/timeout` group with count three and first-seen ID EV-003. Sixteen unit tests are provided.

## Step 5 — Failure injection
1. Repeat the same event ID: reject input.
2. Remove `signature`: reject input.
3. Change `service` to `null`: reject input.
4. Add an unknown field: reject input.
5. Use malformed JSON: reject input.

## Production considerations
This lab only deduplicates **within a single batch**. It has no retention window, persistent state, concurrency control or alert-delivery guarantees. A production pipeline must define event identity, replay semantics, storage durability, audit trails, and safe handling of critical events.

## Acceptance
- [ ] Composite identity grouping correct
- [ ] First-seen ID preserved
- [ ] Counts and sorted output correct
- [ ] Invalid records rejected
- [ ] Sixteen tests pass
- [ ] No production mutations

## Cleanup
Delete only local files created for this lab.
