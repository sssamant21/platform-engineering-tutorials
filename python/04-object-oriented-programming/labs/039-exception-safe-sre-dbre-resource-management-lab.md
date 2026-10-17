# Chapter 039 — Exception-Safe SRE/DBRE Resource Management Lab

**Python 3.10+ | Standard library | Synthetic, offline, dry-run only**

## Goal

Implement a class-based session manager, a generator-based audit scope, `ExitStack` orchestration and exception-safe cleanup. Simulate maintenance preflight tasks without making infrastructure changes.

## Project layout

```text
ch039/
  resources.py
  cli.py
  sample.json
  test_resources.py
```

## 1. resources.py

```python
"""Exception-safe dry-run operational resource scopes."""
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass


ALLOWED_ACTIONS = frozenset({"inspect_index", "check_replication", "validate_backup"})


@dataclass(frozen=True, slots=True)
class WorkItem:
    service: str
    action: str
    approved: bool

    def __post_init__(self):
        if not isinstance(self.service, str) or not self.service.strip() or len(self.service) > 64:
            raise ValueError("invalid service")
        if not isinstance(self.action, str) or self.action not in ALLOWED_ACTIONS:
            raise ValueError("unapproved action")
        if not isinstance(self.approved, bool):
            raise ValueError("approved must be boolean")


class ResourceClosed(RuntimeError):
    pass


class SyntheticSession:
    active = 0

    def __init__(self, events, name):
        self._events = events
        self._name = name
        self._state = "new"

    @property
    def state(self):
        return self._state

    def __enter__(self):
        if self._state != "new":
            raise ResourceClosed("session cannot reopen")
        self._state = "open"
        type(self).active += 1
        self._events.append(f"open:{self._name}")
        return self

    def check(self):
        if self._state != "open":
            raise ResourceClosed("session not open")
        return True

    def close(self):
        if self._state == "open":
            type(self).active -= 1
            self._events.append(f"close:{self._name}")
        self._state = "closed"

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


@contextmanager
def audit_scope(events, name):
    events.append(f"audit_start:{name}")
    try:
        yield
    except Exception:
        events.append(f"audit_failure:{name}")
        raise
    else:
        events.append(f"audit_success:{name}")
    finally:
        events.append(f"audit_end:{name}")


@contextmanager
def guard_scope(events, name):
    events.append(f"guard_enter:{name}")
    try:
        yield
    finally:
        events.append(f"guard_exit:{name}")


def validate_row(row):
    if not isinstance(row, dict) or set(row) != {"service", "action", "approved"}:
        raise ValueError("invalid work item schema")
    return WorkItem(**row)


def run_item(item, events, fail=False):
    if not isinstance(item, WorkItem):
        raise TypeError("expected WorkItem")
    if not item.approved:
        events.append(f"rejected:{item.service}")
        return {"service": item.service, "action": item.action, "status": "rejected"}
    with ExitStack() as stack:
        stack.enter_context(audit_scope(events, item.service))
        session = stack.enter_context(SyntheticSession(events, item.service))
        stack.enter_context(guard_scope(events, item.service))
        session.check()
        if fail:
            raise RuntimeError("injected synthetic failure")
        events.append(f"validated:{item.service}")
        return {"service": item.service, "action": item.action, "status": "validated"}


def run_batch(rows, fail_service=None):
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    items = [validate_row(row) for row in rows]
    seen = set()
    for item in items:
        identity = (item.service, item.action)
        if identity in seen:
            raise ValueError("duplicate work item")
        seen.add(identity)
    events = []
    results = []
    for item in items:
        results.append(run_item(item, events, fail=item.service == fail_service))
    results.sort(key=lambda item: (item["service"], item["action"]))
    return {"schema_version": 1, "dry_run": True, "items": results, "events": events}
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from resources import run_batch


def run(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        rows = json.loads(
            raw,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("input file unreadable or invalid") from exc
    return run_batch(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline SRE resource management dry run")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.input)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. sample.json

```json
[
  {"service":"postgresql","action":"check_replication","approved":true},
  {"service":"elasticsearch","action":"inspect_index","approved":true},
  {"service":"kafka","action":"validate_backup","approved":false}
]
```

## 4. test_resources.py — 32 unit tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
from resources import (
    WorkItem, SyntheticSession, ResourceClosed, audit_scope,
    guard_scope, validate_row, run_item, run_batch,
)
from cli import run


class ResourceTests(unittest.TestCase):
    def item(self, **changes):
        row={"service":"pg","action":"check_replication","approved":True}
        row.update(changes)
        return WorkItem(**row)

    def test_item(self): self.assertEqual(self.item().service,"pg")
    def test_bad_service(self):
        with self.assertRaises(ValueError): self.item(service="")
    def test_bad_action(self):
        with self.assertRaises(ValueError): self.item(action="delete_index")
    def test_bad_approval(self):
        with self.assertRaises(ValueError): self.item(approved="yes")
    def test_bad_schema(self):
        with self.assertRaises(ValueError): validate_row({"service":"pg"})
    def test_session_enter(self):
        events=[]
        with SyntheticSession(events,"pg") as session: self.assertTrue(session.check())
        self.assertEqual(events,["open:pg","close:pg"])
    def test_session_closed(self):
        session=SyntheticSession([],"pg")
        with self.assertRaises(ResourceClosed): session.check()
    def test_session_idempotent_close(self):
        session=SyntheticSession([],"pg")
        session.close()
        session.close()
        self.assertEqual(session.state,"closed")
    def test_session_reopen(self):
        session=SyntheticSession([],"pg")
        with session: pass
        with self.assertRaises(ResourceClosed):
            with session: pass
    def test_session_exception_cleanup(self):
        session=SyntheticSession([],"pg")
        with self.assertRaises(RuntimeError):
            with session: raise RuntimeError("boom")
        self.assertEqual(session.state,"closed")
    def test_active_count(self):
        before=SyntheticSession.active
        with SyntheticSession([],"pg"): self.assertEqual(SyntheticSession.active,before+1)
        self.assertEqual(SyntheticSession.active,before)
    def test_audit_success(self):
        events=[]
        with audit_scope(events,"pg"): pass
        self.assertEqual(events,["audit_start:pg","audit_success:pg","audit_end:pg"])
    def test_audit_failure(self):
        events=[]
        with self.assertRaises(RuntimeError):
            with audit_scope(events,"pg"): raise RuntimeError("boom")
        self.assertEqual(events,["audit_start:pg","audit_failure:pg","audit_end:pg"])
    def test_guard_cleanup(self):
        events=[]
        with guard_scope(events,"pg"): pass
        self.assertEqual(events,["guard_enter:pg","guard_exit:pg"])
    def test_exitstack_lifo(self):
        events=[]
        with ExitStack() as stack:
            stack.enter_context(audit_scope(events,"pg"))
            stack.enter_context(guard_scope(events,"pg"))
        self.assertLess(events.index("guard_exit:pg"),events.index("audit_end:pg"))
    def test_run_validated(self):
        result=run_item(self.item(),[])
        self.assertEqual(result["status"],"validated")
    def test_run_rejected(self):
        result=run_item(self.item(approved=False),[])
        self.assertEqual(result["status"],"rejected")
    def test_rejected_no_session(self):
        events=[]
        run_item(self.item(approved=False),events)
        self.assertFalse(any(e.startswith("open:") for e in events))
    def test_run_injected_failure(self):
        events=[]
        with self.assertRaises(RuntimeError): run_item(self.item(),events,fail=True)
        self.assertIn("audit_failure:pg",events)
    def test_failure_closes(self):
        events=[]
        with self.assertRaises(RuntimeError): run_item(self.item(),events,fail=True)
        self.assertIn("close:pg",events)
    def test_failure_guard(self):
        events=[]
        with self.assertRaises(RuntimeError): run_item(self.item(),events,fail=True)
        self.assertIn("guard_exit:pg",events)
    def test_failure_propagates(self):
        with self.assertRaisesRegex(RuntimeError,"injected"): run_item(self.item(),[],fail=True)
    def test_cleanup_order(self):
        events=[]
        run_item(self.item(),events)
        self.assertLess(events.index("guard_exit:pg"),events.index("close:pg"))
    def test_audit_end_last(self):
        events=[]
        run_item(self.item(),events)
        self.assertEqual(events[-1],"audit_end:pg")
    def test_batch_dry_run(self):
        row={"service":"pg","action":"check_replication","approved":True}
        self.assertTrue(run_batch([row])["dry_run"])
    def test_batch_rejected(self):
        row={"service":"pg","action":"check_replication","approved":False}
        self.assertEqual(run_batch([row])["items"][0]["status"],"rejected")
    def test_batch_duplicate(self):
        row={"service":"pg","action":"check_replication","approved":True}
        with self.assertRaises(ValueError): run_batch([row,row])
    def test_batch_invalid_preflight(self):
        rows=[{"service":"pg","action":"check_replication","approved":True},{"service":"x","action":"delete_index","approved":True}]
        with self.assertRaises(ValueError): run_batch(rows)
    def test_batch_empty(self): self.assertEqual(run_batch([])["items"],[])
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sample.json"
            path.write_text(json.dumps([{"service":"pg","action":"check_replication","approved":True}]),encoding="utf-8")
            self.assertTrue(run(path)["dry_run"])
    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"
            path.write_text("{bad",encoding="utf-8")
            with self.assertRaises(ValueError): run(path)
    def test_session_after_failure_no_leak(self):
        before=SyntheticSession.active
        with self.assertRaises(RuntimeError): run_item(self.item(),[],fail=True)
        self.assertEqual(SyntheticSession.active,before)


if __name__ == "__main__":
    unittest.main()
```

## 5. Run

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_resources.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile resources.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_resources.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile resources.py cli.py
```

Expected output: PostgreSQL and Elasticsearch validated, Kafka rejected, `dry_run: true`, and paired audit/session events.

## 6. Failure injection

1. Call `check()` outside `with`: raise `ResourceClosed`.
2. Raise inside a session: verify close runs and error propagates.
3. Inject failure after guard acquisition: verify reverse cleanup order.
4. Attempt reopening a closed session: reject.
5. Provide unapproved action `delete_index`: reject before any session opens.
6. Duplicate a work item: fail preflight.
7. Provide malformed JSON: CLI exits without a success report.
8. Run repeated sessions and verify `SyntheticSession.active` returns to baseline.

## 7. Production runbooks

**Leaked sessions:** verify active counters and `__exit__` paths; stop repeated execution and add exception-injection tests.

**Missing audit:** ensure audit scope is entered first and its failure event is recorded; treat unavailable audit storage as fail-closed.

**Exception suppression:** ensure context managers return `False` or re-raise; preserve original failure.

**Change control:** this lab is dry-run only. Real changes require an approved ticket, index/data owner review, backup and rollback plan.

## 8. Acceptance

- [ ] All 32 tests pass locally.
- [ ] Cleanup executes on success and injected failure.
- [ ] `ExitStack` cleanup order is verified.
- [ ] Audit events are emitted on success and failure.
- [ ] Unapproved actions are rejected.
- [ ] No network access, credentials or infrastructure mutations.

**Execution status:** Tests are included; local execution is required.
