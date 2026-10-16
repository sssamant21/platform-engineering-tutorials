# Chapter 002 — Hands-on Lab: Reproducible Python Development Environment

## Scenario
As an SRE, create a portable, read-only health-check project that a teammate can reproduce without elevated privileges or external packages.

## Prerequisites
Python 3.10+, Git, VS Code with Python extension, terminal access and a writable local workspace. No cloud credentials required.

## Step 1 — Create the environment
Windows PowerShell:
```powershell
mkdir python-ch02
cd python-ch02
py -3 -m venv .venv
.\.venv\Scripts\python.exe --version
New-Item -ItemType Directory -Force src, tests
```
Linux/macOS:
```bash
mkdir python-ch02 && cd python-ch02
python3 -m venv .venv
./.venv/bin/python --version
mkdir -p src tests
```

## Step 2 — Create `src/healthcheck.py`
```python
"""Read-only runtime health check with no external dependencies."""
import argparse
import json
import sys
from pathlib import Path


def check_runtime() -> dict[str, object]:
    return {
        "python_ok": sys.version_info >= (3, 10),
        "virtualenv_active": sys.prefix != sys.base_prefix,
        "interpreter": str(Path(sys.executable).resolve()),
        "python_version": ".".join(map(str, sys.version_info[:3])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check_runtime()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0 if result["python_ok"] and result["virtualenv_active"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `tests/test_healthcheck.py`
```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from healthcheck import check_runtime


class RuntimeTest(unittest.TestCase):
    def test_runtime(self):
        data = check_runtime()
        self.assertTrue(data["python_ok"])
        self.assertTrue(data["virtualenv_active"])
        self.assertTrue(Path(data["interpreter"]).exists())


if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Run and verify
Windows PowerShell:
```powershell
.\.venv\Scripts\python.exe src\healthcheck.py --json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src tests
```
Linux/macOS:
```bash
./.venv/bin/python src/healthcheck.py --json
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python -m compileall -q src tests
```
Expected: `python_ok: true`, `virtualenv_active: true`, and one passing unit test. Paths and versions depend on your machine.

## Step 5 — Initialize Git safely
Create `.gitignore`:
```gitignore
.venv/
__pycache__/
*.py[cod]
.env
.pytest_cache/
```
Then:
```bash
git init
git add .gitignore src tests
git status --short
git status --ignored --short
```
Confirm `.venv/` is ignored and not staged. Do not push this lab to a production repository without review.

## Step 6 — Failure injection and recovery
1. Run the script with the **system interpreter** instead of the venv interpreter. It should return nonzero when no other venv is active. Restore the correct interpreter.
2. In VS Code, temporarily select the wrong interpreter. Observe `sys.executable` and restore `.venv`.
3. Run an unknown flag, e.g. `--unknown`. Confirm argparse exits with a usage error.
4. Verify `git check-ignore .venv` returns the ignored path.

## Troubleshooting
- `ModuleNotFoundError`: verify test discovery and project layout.
- `virtualenv_active: false`: invoke `.venv`'s Python directly.
- `PermissionError`: move the project to a writable directory.
- Missing `python3-venv`: install the OS package and recreate the environment.

## Acceptance checklist
- [ ] Python 3.10+ confirmed
- [ ] Virtual environment created
- [ ] VS Code interpreter configured
- [ ] JSON health check succeeds
- [ ] Unit test passes
- [ ] Bytecode compilation succeeds
- [ ] Git ignores environment and secret files
- [ ] Failure scenarios reproduced and recovered

## Cleanup
Delete only the dedicated `python-ch02` lab directory if you no longer need it. Do not remove shared Python installations or modify global execution policies.
