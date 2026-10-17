# Chapter 041 — Safe Filesystem and Atomic SRE Report Lab

**Python 3.10+ | Standard library | Private local sandbox only**

## Objectives

Build a filesystem-backed, sandbox-scoped SRE/DBRE JSON report store with validated simple filenames, bounded reads and writes, private temporary files, atomic replacement, deterministic JSON, and failure-injection tests.

### Layout

```text
ch041/
  safe_files.py
  cli.py
  test_safe_files.py
  fixture.json
  reports/            # create this private local directory
```

### 1. safe_files.py

```python
"""Sandbox-scoped report storage; not a hostile multiuser security boundary."""
import json
import os
from pathlib import Path
import stat
import tempfile

MAX_BYTES = 1024 * 1024

class StorageError(ValueError):
    pass

class ReportStore:
    def __init__(self, root):
        root = Path(root)
        if not root.is_dir() or root.is_symlink():
            raise StorageError("root must be an existing real directory")
        self.root = root.resolve(strict=True)

    def _path(self, name):
        if not isinstance(name, str) or not name or name in (".", ".."):
            raise StorageError("invalid filename")
        if "/" in name or "\\" in name or Path(name).name != name or not name.endswith(".json"):
            raise StorageError("only simple .json filenames allowed")
        path = self.root / name
        if path.is_symlink():
            raise StorageError("symlinks forbidden")
        if path.exists() and not path.is_file():
            raise StorageError("target must be a regular file")
        return path

    def read(self, name):
        path = self._path(name)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise StorageError("not a regular file")
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise StorageError("report too large")
        try:
            result = json.loads(data.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(StorageError("invalid JSON number")))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise StorageError("invalid JSON") from exc
        if not isinstance(result, dict):
            raise StorageError("report must be an object")
        return result

    def write(self, name, report):
        target = self._path(name)
        if not isinstance(report, dict):
            raise StorageError("report must be an object")
        try:
            payload = (json.dumps(report, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        except (TypeError, ValueError, OverflowError) as exc:
            raise StorageError("report not JSON serializable") from exc
        if len(payload) > MAX_BYTES:
            raise StorageError("report too large")
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(prefix=".pending-", suffix=".tmp", dir=self.root)
            if os.name == "posix":
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            self._path(name)
            os.replace(tmp, target)
            tmp = None
            if os.name == "posix":
                dirfd = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(dirfd)
                finally:
                    os.close(dirfd)
            return target
        finally:
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except FileNotFoundError:
                    pass

    def list_reports(self):
        return tuple(sorted(p.name for p in self.root.iterdir() if p.suffix == ".json" and p.is_file() and not p.is_symlink()))
```

### 2. cli.py

```python
import argparse
import json
from pathlib import Path
from safe_files import ReportStore, StorageError

def main(argv=None):
    parser = argparse.ArgumentParser(description="Sandbox-only atomic SRE JSON report store")
    parser.add_argument("--root", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("name")
    write.add_argument("--input", type=Path, required=True)
    read = sub.add_parser("read")
    read.add_argument("name")
    sub.add_parser("list")
    args = parser.parse_args(argv)
    try:
        store = ReportStore(args.root)
        if args.command == "write":
            if args.input.stat().st_size > 1024 * 1024:
                raise StorageError("input too large")
            value = json.loads(args.input.read_text(encoding="utf-8"))
            store.write(args.name, value)
            result = {"written": args.name}
        elif args.command == "read":
            result = store.read(args.name)
        else:
            result = {"reports": store.list_reports()}
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### 3. fixture.json

```json
{"environment":"synthetic","engine":"postgresql","replication_lag_seconds":12,"status":"healthy"}
```

### 4. test_safe_files.py — 35 automated tests

```python
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from safe_files import ReportStore, StorageError, MAX_BYTES
from cli import main

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ReportStore(self.root)

    def test_root(self): self.assertEqual(self.store.root, self.root.resolve())
    def test_missing_root(self):
        with self.assertRaises(StorageError): ReportStore(self.root / "missing")
    def test_file_root(self):
        p = self.root / "file"; p.write_text("x")
        with self.assertRaises(StorageError): ReportStore(p)
    def test_write_read(self):
        self.store.write("a.json", {"ok": True})
        self.assertEqual(self.store.read("a.json"), {"ok": True})
    def test_sorted_json(self):
        self.store.write("a.json", {"z": 1, "a": 2})
        self.assertEqual((self.root / "a.json").read_text(), '{"a":2,"z":1}\n')
    def test_overwrite(self):
        self.store.write("a.json", {"v": 1}); self.store.write("a.json", {"v": 2})
        self.assertEqual(self.store.read("a.json")["v"], 2)
    def test_list(self):
        self.store.write("z.json", {}); self.store.write("a.json", {})
        self.assertEqual(self.store.list_reports(), ("a.json", "z.json"))
    def test_empty_list(self): self.assertEqual(self.store.list_reports(), ())
    def test_traversal(self):
        with self.assertRaises(StorageError): self.store.write("../escape.json", {})
    def test_absolute(self):
        with self.assertRaises(StorageError): self.store.write("/tmp/x.json", {})
    def test_subdirectory(self):
        with self.assertRaises(StorageError): self.store.write("dir/a.json", {})
    def test_wrong_extension(self):
        with self.assertRaises(StorageError): self.store.write("a.txt", {})
    def test_empty_name(self):
        with self.assertRaises(StorageError): self.store.write("", {})
    def test_backslash(self):
        with self.assertRaises(StorageError): self.store.write("a\\b.json", {})
    def test_bad_payload(self):
        with self.assertRaises(StorageError): self.store.write("a.json", [])
    def test_nonserializable(self):
        with self.assertRaises(StorageError): self.store.write("a.json", {"bad": object()})
    def test_nan(self):
        with self.assertRaises(StorageError): self.store.write("a.json", {"bad": float("nan")})
    def test_inf(self):
        with self.assertRaises(StorageError): self.store.write("a.json", {"bad": float("inf")})
    def test_size_limit(self):
        with self.assertRaises(StorageError): self.store.write("a.json", {"v": "x" * MAX_BYTES})
    def test_read_missing(self):
        with self.assertRaises(FileNotFoundError): self.store.read("missing.json")
    def test_read_invalid_json(self):
        (self.root / "a.json").write_text("{bad")
        with self.assertRaises(StorageError): self.store.read("a.json")
    def test_read_array(self):
        (self.root / "a.json").write_text("[]")
        with self.assertRaises(StorageError): self.store.read("a.json")
    def test_read_oversized(self):
        (self.root / "a.json").write_bytes(b" " * (MAX_BYTES + 1))
        with self.assertRaises(StorageError): self.store.read("a.json")
    def test_read_utf8(self):
        self.store.write("a.json", {"label": "café"})
        self.assertEqual(self.store.read("a.json")["label"], "café")
    def test_temp_cleanup(self):
        self.store.write("a.json", {"x": 1})
        self.assertFalse(any(p.name.startswith(".pending-") for p in self.root.iterdir()))
    def test_target_directory(self):
        (self.root / "a.json").mkdir()
        with self.assertRaises(StorageError): self.store.write("a.json", {})
    def test_symlink_target(self):
        if not hasattr(os, "symlink"): self.skipTest("symlink unavailable")
        external = self.root / "external"; external.write_text("original")
        try: (self.root / "a.json").symlink_to(external)
        except OSError: self.skipTest("symlink permission unavailable")
        with self.assertRaises(StorageError): self.store.write("a.json", {})
        self.assertEqual(external.read_text(), "original")
    def test_no_partial_on_serialization_failure(self):
        self.store.write("a.json", {"v": 1})
        with self.assertRaises(StorageError): self.store.write("a.json", {"v": object()})
        self.assertEqual(self.store.read("a.json"), {"v": 1})
    def test_no_partial_on_replace_failure(self):
        self.store.write("a.json", {"v": 1})
        with patch("safe_files.os.replace", side_effect=OSError("injected")):
            with self.assertRaises(OSError): self.store.write("a.json", {"v": 2})
        self.assertEqual(self.store.read("a.json"), {"v": 1})
        self.assertFalse(any(p.name.startswith(".pending-") for p in self.root.iterdir()))
    def test_mode_posix(self):
        if os.name != "posix": self.skipTest("POSIX only")
        self.store.write("a.json", {})
        self.assertEqual((self.root / "a.json").stat().st_mode & 0o777, 0o600)
    def test_cli_list(self):
        self.assertEqual(main(["--root", str(self.root), "list"]), 0)
    def test_cli_write_read(self):
        fixture = self.root / "fixture.txt"; fixture.write_text(json.dumps({"ok": 1}))
        self.assertEqual(main(["--root", str(self.root), "write", "a.json", "--input", str(fixture)]), 0)
        self.assertEqual(main(["--root", str(self.root), "read", "a.json"]), 0)
    def test_cli_missing_root(self):
        with self.assertRaises(SystemExit): main(["--root", str(self.root / "no"), "list"])
    def test_read_symlink(self):
        if not hasattr(os, "symlink"): self.skipTest("symlink unavailable")
        target = self.root / "target.txt"; target.write_text("{}")
        try: (self.root / "a.json").symlink_to(target)
        except OSError: self.skipTest("symlink permission unavailable")
        with self.assertRaises(StorageError): self.store.read("a.json")
    def test_invalid_json_number(self):
        (self.root / "a.json").write_text('{"x":NaN}')
        with self.assertRaises(StorageError): self.store.read("a.json")

if __name__ == "__main__":
    unittest.main()
```

## 5. Execute

Linux/macOS/WSL:

```bash
mkdir -p reports
chmod 700 reports
python3 -m unittest -v test_safe_files.py
python3 -m py_compile safe_files.py cli.py
python3 cli.py --root reports write pg-health.json --input fixture.json
python3 cli.py --root reports read pg-health.json
python3 cli.py --root reports list
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force reports
py -3 -m unittest -v test_safe_files.py
py -3 -m py_compile safe_files.py cli.py
py -3 cli.py --root reports write pg-health.json --input fixture.json
py -3 cli.py --root reports read pg-health.json
py -3 cli.py --root reports list
```

The directory must be private to the current user. On Windows, use appropriate NTFS ACLs. This example does **not** implement hostile-directory race protection.

## 6. Failure injection

1. Try `../escape.json` and absolute filenames: reject traversal.
2. Try a symlink target: reject rather than follow.
3. Inject an `os.replace` error: preserve previous report and remove temporary file.
4. Supply NaN or infinity: reject serialization.
5. Supply a payload larger than 1 MiB: reject before publication.
6. Read a malformed JSON file: fail closed.
7. Confirm mode `0600` on POSIX.
8. Verify deterministic key order and stable JSON output.

## 7. Operational runbooks

**Permission failure:** verify current identity, parent directory ownership, POSIX mode or Windows ACL; avoid world-writable workspaces.

**Atomic replacement failure:** preserve old report, inspect filesystem space/locks and review `os.replace` failure; do not claim publication succeeded.

**Corrupt report:** quarantine sanitized evidence, inspect size and encoding, validate producer and replay test fixtures.

**Symlink attack:** stop processing and inspect directory ownership; this lab is intended only for a trusted sandbox.

## 8. Acceptance

- [x] All 35 automated tests executed successfully in a Linux sandbox.
- [x] Failure-injected replacement preserves old content.
- [x] Temporary files cleaned up on failure.
- [x] Deterministic JSON and strict filename checks.
- [ ] Re-run tests on the learner's operating system.
- [ ] Confirm sandbox directory permissions or ACLs before use.

**Test evidence:** `python -m unittest -q` reported `Ran 35 tests ... OK` in the authoring Linux sandbox. Windows behavior has not been independently validated.
