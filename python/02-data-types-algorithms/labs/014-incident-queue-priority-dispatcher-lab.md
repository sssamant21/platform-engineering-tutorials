# Chapter 014 — Hands-on Lab: SRE Incident Queue and Priority Dispatcher

## Goal
Simulate dispatching a fixed batch of synthetic incidents using FIFO or severity priority. The tool is **read-only**, does not send notifications, and never changes infrastructure.

## Prerequisites
Python 3.10+; standard library only.

## Step 1 — Create `incidents.json`
```json
[
  {"id":"INC-001","service":"api","severity":"warning"},
  {"id":"INC-002","service":"database","severity":"critical"},
  {"id":"INC-003","service":"worker","severity":"info"},
  {"id":"INC-004","service":"cache","severity":"critical"}
]
```

## Step 2 — Create `incident_dispatch.py`
```python
"""Deterministic, read-only batch incident dispatch simulator."""
import argparse
from collections import Counter, deque
import heapq
import json
from pathlib import Path

PRIORITY = {"critical": 0, "warning": 1, "info": 2}


def validate(records: object, capacity: int) -> list[dict]:
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("capacity must be a positive integer")
    if not isinstance(records, list):
        raise ValueError("incidents must be a JSON array")
    if len(records) > capacity:
        raise ValueError("queue capacity exceeded; no incidents were dispatched")
    clean = []
    seen = set()
    for position, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"incident {position} must be an object")
        identifier = record.get("id")
        service = record.get("service")
        severity = record.get("severity")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"incident {position}: invalid id")
        if identifier in seen:
            raise ValueError(f"duplicate incident id: {identifier}")
        if not isinstance(service, str) or not service.strip():
            raise ValueError(f"incident {position}: invalid service")
        if not isinstance(severity, str) or severity not in PRIORITY:
            raise ValueError(f"incident {position}: invalid severity")
        seen.add(identifier)
        clean.append({"id": identifier, "service": service, "severity": severity})
    return clean


def dispatch(records: object, mode: str = "fifo", capacity: int = 100) -> dict:
    if mode not in {"fifo", "priority"}:
        raise ValueError("mode must be fifo or priority")
    clean = validate(records, capacity)
    if mode == "fifo":
        pending = deque(clean)
        ordered = []
        while pending:
            ordered.append(pending.popleft())
    else:
        pending = [(PRIORITY[record["severity"]], index, record)
                   for index, record in enumerate(clean)]
        heapq.heapify(pending)
        ordered = []
        while pending:
            ordered.append(heapq.heappop(pending)[2])
    counts = Counter(record["severity"] for record in ordered)
    return {
        "mode": mode,
        "processed_count": len(ordered),
        "by_severity": {severity: counts[severity] for severity in ("critical", "warning", "info")},
        "dispatch_order": ordered,
    }


def positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("capacity must be an integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("capacity must be positive")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only incident dispatch simulator")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--mode", choices=("fifo", "priority"), default="fifo")
    parser.add_argument("--capacity", type=positive_int, default=100)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            records = json.load(source)
        report = dispatch(records, mode=args.mode, capacity=args.capacity)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_incident_dispatch.py`
```python
import argparse
import unittest
from incident_dispatch import dispatch, positive_int, validate

def incident(identifier="INC-001", severity="warning", service="api"):
    return {"id": identifier, "severity": severity, "service": service}

class IncidentDispatchTests(unittest.TestCase):
    def test_fifo_order(self):
        rows = [incident("a", "info"), incident("b", "critical")]
        self.assertEqual([x["id"] for x in dispatch(rows)["dispatch_order"]], ["a", "b"])
    def test_priority_order(self):
        rows = [incident("a", "info"), incident("b", "critical")]
        self.assertEqual([x["id"] for x in dispatch(rows, "priority")["dispatch_order"]], ["b", "a"])
    def test_stable_ties(self):
        rows = [incident("a", "critical"), incident("b", "critical")]
        self.assertEqual([x["id"] for x in dispatch(rows, "priority")["dispatch_order"]], ["a", "b"])
    def test_counts(self):
        rows = [incident("a", "warning"), incident("b", "critical")]
        self.assertEqual(dispatch(rows)["by_severity"]["critical"], 1)
    def test_empty(self):
        self.assertEqual(dispatch([])["processed_count"], 0)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate([incident(), incident()], 10)
    def test_invalid_severity(self):
        with self.assertRaises(ValueError):
            validate([incident(severity="urgent")], 10)
    def test_missing_service(self):
        with self.assertRaises(ValueError):
            validate([{"id":"a","severity":"info"}], 10)
    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            validate({}, 10)
    def test_capacity(self):
        with self.assertRaises(ValueError):
            dispatch([incident("a"), incident("b")], capacity=1)
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            dispatch([], mode="random")
    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            dispatch([], capacity=0)
    def test_bool_capacity(self):
        with self.assertRaises(ValueError):
            dispatch([], capacity=True)
    def test_positive_int(self):
        self.assertEqual(positive_int("5"), 5)
    def test_cli_capacity_reject(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")
    def test_input_not_mutated(self):
        rows = [incident()]
        dispatch(rows)
        self.assertEqual(rows[0]["id"], "INC-001")

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python incident_dispatch.py --input incidents.json --mode fifo
python incident_dispatch.py --input incidents.json --mode priority
python -m unittest -v test_incident_dispatch.py
python -m py_compile incident_dispatch.py
```
Expected FIFO order: INC-001, INC-002, INC-003, INC-004. Expected priority order: INC-002, INC-004, INC-001, INC-003. Counts: 2 critical, 1 warning, 1 info. Sixteen unit tests are provided.

## Step 5 — Failure injection
1. Set `--capacity 2` for four records: reject the entire batch.
2. Duplicate INC-001: reject the batch.
3. Change severity to `urgent`: reject the batch.
4. Use `--mode unknown`: argparse rejects the argument.
5. Use malformed JSON: parser reports an input error.

## Operational limitations
This is an **in-memory batch simulator**, not a durable incident queue. It does not provide acknowledgment, persistence, retries, worker concurrency, fairness guarantees or delivery to paging systems. Do not use it to dispatch real incidents without designing those controls.

## Acceptance checklist
- [ ] FIFO order preserved
- [ ] Severity-priority order correct
- [ ] Equal-severity arrival order preserved
- [ ] Capacity overflow rejected visibly
- [ ] Sixteen unit tests pass
- [ ] No external notifications or changes

## Cleanup
Delete only the lab's local files.
