# Chapter 001 — Hands-on Lab: System Information CLI

## Goal
Build a dependency-free, read-only Python command-line tool for SRE inventory. No elevated privileges or cloud credentials are required.

## Prerequisites
Python 3.10+ on Windows, macOS or Linux. Check with `python --version` (or `py -3 --version` on Windows).

## Step 1 — Create `system_info.py`
```python
import argparse
import json
import platform
import sys
from datetime import datetime, timezone


def collect_info() -> dict[str, str]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only system inventory")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()
    info = collect_info()
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        for key, value in info.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
```

## Step 2 — Execute
```bash
python system_info.py
python system_info.py --json
python system_info.py --help
```

On Windows, substitute `py -3` if necessary.

## Step 3 — Validate
Create `test_system_info.py` alongside the script:

```python
import unittest
from datetime import datetime
from system_info import collect_info


class SystemInfoTests(unittest.TestCase):
    def test_expected_fields(self):
        data = collect_info()
        self.assertEqual(
            set(data),
            {"timestamp_utc", "python_version", "platform", "architecture"},
        )
        self.assertTrue(data["python_version"])
        self.assertIsNotNone(datetime.fromisoformat(data["timestamp_utc"]).tzinfo)


if __name__ == "__main__":
    unittest.main()
```

Run:
```bash
python -m unittest -v test_system_info.py
python -m py_compile system_info.py
```

Expected: one passing test and successful compilation. JSON mode should produce a JSON object with four keys.

## Step 4 — Failure experiments
- Run `python system_info.py --invalid`: argparse should reject the unknown argument with a nonzero exit code.
- Temporarily remove a colon after a `def` statement and run the script: observe `SyntaxError`, then restore it.
- Run from a different directory without a path to the file: observe a file-not-found error, then correct the path.

## Step 5 — Operational review
This utility performs no writes, does not collect credentials and needs no third-party packages. It intentionally avoids hostnames, usernames and environment variables, which can contain sensitive information.

## Completion checklist
- [ ] Interpreter version verified
- [ ] Text output verified
- [ ] JSON output parsed successfully
- [ ] Unit test passed
- [ ] Syntax error experiment recovered
- [ ] Script committed to a lab repository or saved locally

## Cleanup
Remove only files created for this lab when no longer needed.
