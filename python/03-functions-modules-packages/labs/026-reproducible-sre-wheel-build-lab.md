# Chapter 026 — Hands-on Lab: Reproducible SRE Wheel Build and Integrity Checks

**Python 3.10+ | Standard library runtime | Offline wheel installation**

## Goals
Build a tiny, read-only SRE utility, create isolated environments, produce a wheel, verify its SHA-256, install it without an index into a clean environment, and run automated tests. The lab has **no third-party runtime dependencies**. A build backend such as setuptools must be available in the controlled build environment.

## 1. Directory structure
```text
sre-wheel-lab/
  pyproject.toml
  src/sre_wheel_lab/__init__.py
  src/sre_wheel_lab/policy.py
  src/sre_wheel_lab/__main__.py
  tests/test_policy.py
  scripts/check_artifact.py
  dist/
```

## 2. `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sre-wheel-lab"
version = "0.1.0"
description = "Read-only SRE wheel integrity exercise"
requires-python = ">=3.10"
dependencies = []

[tool.setuptools.packages.find]
where = ["src"]
```

The build requirement range is for a learning lab; production builds should pin a vetted backend version and use an approved index. Avoid naming this project identically to a public package in a shared registry.

## 3. `src/sre_wheel_lab/policy.py`
```python
"""Pure latency classification; no external side effects."""
import math


def classify_latency(value: object, *, warning_ms: float = 200.0,
                     critical_ms: float = 500.0) -> str:
    for name, candidate in (("latency", value), ("warning", warning_ms),
                            ("critical", critical_ms)):
        if isinstance(candidate, bool) or not isinstance(candidate, (int, float)):
            raise TypeError(f"{name} must be numeric")
        if not math.isfinite(candidate):
            raise ValueError(f"{name} must be finite")
    if value < 0 or not 0 < warning_ms < critical_ms:
        raise ValueError("invalid latency or thresholds")
    if value >= critical_ms:
        return "critical"
    if value >= warning_ms:
        return "warning"
    return "healthy"
```

## 4. `src/sre_wheel_lab/__init__.py`
```python
from .policy import classify_latency

__all__ = ["classify_latency"]
```

## 5. `src/sre_wheel_lab/__main__.py`
```python
import argparse
import json
from .policy import classify_latency


def main():
    parser = argparse.ArgumentParser(description="Offline latency classifier")
    parser.add_argument("--latency-ms", type=float, required=True)
    args = parser.parse_args()
    try:
        status = classify_latency(args.latency_ms)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"latency_ms": args.latency_ms, "status": status}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 6. `scripts/check_artifact.py`
```python
"""Create or verify an explicit SHA-256 artifact manifest."""
import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(path: Path, expected: str) -> bool:
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected.lower()):
        raise ValueError("expected a 64-character SHA-256 hex digest")
    return sha256_file(path) == expected.lower()


def main():
    parser = argparse.ArgumentParser(description="SHA-256 wheel integrity verifier")
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--expected", help="expected SHA-256 hex digest")
    args = parser.parse_args()
    try:
        digest = sha256_file(args.wheel)
        if args.expected is not None and not check(args.wheel, args.expected):
            parser.error("artifact checksum mismatch")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 7. `tests/test_policy.py`
```python
import tempfile
from pathlib import Path
import unittest
from sre_wheel_lab import classify_latency
from sre_wheel_lab.policy import classify_latency as from_module
from scripts.check_artifact import check, sha256_file


class WheelLabTests(unittest.TestCase):
    def test_healthy(self): self.assertEqual(classify_latency(100), "healthy")
    def test_warning(self): self.assertEqual(classify_latency(200), "warning")
    def test_critical(self): self.assertEqual(classify_latency(500), "critical")
    def test_warning_above(self): self.assertEqual(classify_latency(300), "warning")
    def test_critical_above(self): self.assertEqual(classify_latency(800), "critical")
    def test_negative(self):
        with self.assertRaises(ValueError): classify_latency(-1)
    def test_boolean(self):
        with self.assertRaises(TypeError): classify_latency(True)
    def test_nan(self):
        with self.assertRaises(ValueError): classify_latency(float("nan"))
    def test_infinite(self):
        with self.assertRaises(ValueError): classify_latency(float("inf"))
    def test_invalid_warning(self):
        with self.assertRaises(ValueError): classify_latency(10, warning_ms=0)
    def test_swapped_thresholds(self):
        with self.assertRaises(ValueError): classify_latency(10, warning_ms=500, critical_ms=200)
    def test_non_numeric(self):
        with self.assertRaises(TypeError): classify_latency("100")
    def test_public_import(self): self.assertIs(classify_latency, from_module)
    def test_custom_policy(self): self.assertEqual(classify_latency(75, warning_ms=50, critical_ms=100), "warning")
    def test_digest_length(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "wheel.whl"
            file.write_bytes(b"artifact")
            self.assertEqual(len(sha256_file(file)), 64)
    def test_digest_match(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "wheel.whl"
            file.write_bytes(b"artifact")
            self.assertTrue(check(file, sha256_file(file)))
    def test_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "wheel.whl"
            file.write_bytes(b"artifact")
            self.assertFalse(check(file, "0" * 64))
    def test_invalid_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "wheel.whl"
            file.write_bytes(b"artifact")
            with self.assertRaises(ValueError): check(file, "invalid")
    def test_digest_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "wheel.whl"
            file.write_bytes(b"one")
            first = sha256_file(file)
            file.write_bytes(b"two")
            self.assertNotEqual(first, sha256_file(file))
    def test_missing_artifact(self):
        with self.assertRaises(OSError):
            sha256_file(Path("nonexistent-ch026-artifact.whl"))


if __name__ == "__main__":
    unittest.main()
```

Create an empty `scripts/__init__.py` file so `scripts.check_artifact` is importable.

## 8. Environment setup and build

**Linux/macOS/WSL**
```bash
python3 -m venv .venv-build
./.venv-build/bin/python -m pip --version
# Use an approved index or preprovisioned build environment:
./.venv-build/bin/python -m pip install 'setuptools>=68' wheel
./.venv-build/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
./.venv-build/bin/python -m pip install -e . --no-build-isolation
./.venv-build/bin/python -m unittest discover -s tests -v
```

**Windows PowerShell**
```powershell
py -3 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install "setuptools>=68" wheel
.\.venv-build\Scripts\python.exe -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
.\.venv-build\Scripts\python.exe -m pip install -e . --no-build-isolation
.\.venv-build\Scripts\python.exe -m unittest discover -s tests -v
```

Build-tool installation can require network access unless tools are already present or provisioned from an internal mirror. Only the **wheel installation** below is explicitly offline.

## 9. Hash verification and fresh offline installation
Identify the exact built wheel file in `dist/`. Do not use an unreviewed file from another directory.

**Linux/macOS/WSL**
```bash
WHEEL=$(find dist -maxdepth 1 -name 'sre_wheel_lab-0.1.0-*.whl' -print -quit)
test -n "$WHEEL"
./.venv-build/bin/python scripts/check_artifact.py "$WHEEL"
# Save the printed digest in a reviewed build manifest as EXPECTED_SHA256.
./.venv-build/bin/python scripts/check_artifact.py "$WHEEL" --expected "$EXPECTED_SHA256"
python3 -m venv .venv-smoke
./.venv-smoke/bin/python -m pip install --no-index --no-deps "$WHEEL"
(cd /tmp && "$OLDPWD/.venv-smoke/bin/python" -m sre_wheel_lab --latency-ms 300)
```

**Windows PowerShell**
```powershell
$wheel = (Get-ChildItem dist/sre_wheel_lab-0.1.0-*.whl | Select-Object -First 1).FullName
.\.venv-build\Scripts\python.exe scripts/check_artifact.py $wheel
# Set $expected from the approved manifest, not from an untrusted download:
.\.venv-build\Scripts\python.exe scripts/check_artifact.py $wheel --expected $expected
py -3 -m venv .venv-smoke
.\.venv-smoke\Scripts\python.exe -m pip install --no-index --no-deps $wheel
Push-Location $env:TEMP
& (Join-Path $OLDPWD '.venv-smoke\Scripts\python.exe') -m sre_wheel_lab --latency-ms 300
Pop-Location
```

Expected smoke output: `{"latency_ms": 300.0, "status": "warning"}`. **20 unit tests** are provided.

## 10. Failure injection
1. Verify against `000...000` (64 zeros): checksum mismatch.
2. Change one byte of a copied wheel: checksum mismatch.
3. Attempt `--no-index` install with a missing wheel: fail.
4. Call classifier with NaN, boolean or negative latency: reject.
5. Delete the fresh venv and repeat install to demonstrate isolation.
6. Run smoke test outside the source checkout to avoid source-tree import leakage.

## 11. Troubleshooting
| Symptom | Cause | Resolution |
|---|---|---|
| setuptools unavailable | Build tool not provisioned | Use approved mirror/wheelhouse |
| Hash mismatch | Wrong or modified artifact | Stop promotion; investigate |
| Wheel cannot install | Unsupported interpreter/tag | Build for target runtime |
| pip targets system interpreter | Wrong Python executable | Use explicit venv interpreter |
| Tests cannot import scripts | Missing `scripts/__init__.py` or wrong working directory | Create file and run from project root |
| Offline install reaches index | Missing `--no-index` | Force offline flags and audit command |

## 12. Acceptance
- [ ] 20 tests pass locally.
- [ ] Build tool provenance documented.
- [ ] Wheel hash captured and independently verified.
- [ ] Fresh environment installs wheel with `--no-index`.
- [ ] Installed wheel runs outside source tree.
- [ ] No system-wide pip install or production changes.

## Cleanup
Delete only the two disposable lab virtual environments and build artifacts. Never remove shared caches or production Python installations.
