# Chapter 027 — Hands-on Lab: SRE Artifact Provenance and Packaging

**Python 3.10+ | Standard-library runtime | Local build, no publishing**

## Goal
Build a read-only SRE package into wheel and sdist, inspect archive paths, record hashes and metadata, verify artifacts before offline wheel installation, and run unit tests. A package build frontend and backend must be provisioned from an approved source.

## 1. Directory structure
```text
sre-artifact-audit/
  pyproject.toml
  src/sre_artifact_audit/__init__.py
  src/sre_artifact_audit/policy.py
  src/sre_artifact_audit/__main__.py
  scripts/__init__.py
  scripts/audit_artifacts.py
  tests/test_policy.py
  tests/test_artifacts.py
```

## 2. `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sre-artifact-audit-lab"
version = "0.1.0"
description = "Offline SRE artifact validation exercise"
requires-python = ">=3.10"
dependencies = []

[tool.setuptools.packages.find]
where = ["src"]
```

## 3. `src/sre_artifact_audit/policy.py`
```python
"""Pure read-only SRE health policy."""
import math


def classify_latency(value, *, warning_ms=200, critical_ms=500):
    for name, candidate in (("value", value), ("warning_ms", warning_ms),
                            ("critical_ms", critical_ms)):
        if isinstance(candidate, bool) or not isinstance(candidate, (int, float)):
            raise TypeError(f"{name} must be numeric")
        if not math.isfinite(candidate):
            raise ValueError(f"{name} must be finite")
    if value < 0 or not 0 < warning_ms < critical_ms:
        raise ValueError("invalid latency or thresholds")
    return "critical" if value >= critical_ms else "warning" if value >= warning_ms else "healthy"
```

## 4. `src/sre_artifact_audit/__init__.py`
```python
from .policy import classify_latency

__all__ = ["classify_latency"]
```

## 5. `src/sre_artifact_audit/__main__.py`
```python
import argparse
import json
from .policy import classify_latency


def main():
    parser = argparse.ArgumentParser(description="Offline SRE artifact audit demo")
    parser.add_argument("--latency-ms", type=float, required=True)
    args = parser.parse_args()
    try:
        status = classify_latency(args.latency_ms)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"latency_ms": args.latency_ms, "status": status}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 6. `scripts/audit_artifacts.py`
```python
"""Inspect wheel/sdist paths and create or verify SHA-256 manifests."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


def digest_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def safe_member(name: str) -> bool:
    """Reject absolute paths, traversal and Windows-style separators."""
    if not name or "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    return not any(part in ("..", "") for part in path.parts)


def inspect_archive(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("duplicate wheel members")
            if any(not safe_member(name) for name in names):
                raise ValueError("unsafe wheel path")
            if not any(name.endswith(".dist-info/METADATA") for name in names):
                raise ValueError("wheel missing METADATA")
            if not any(name.endswith(".dist-info/RECORD") for name in names):
                raise ValueError("wheel missing RECORD")
            return sorted(names)
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            if len(names) != len(set(names)):
                raise ValueError("duplicate sdist members")
            if any(not safe_member(name) for name in names):
                raise ValueError("unsafe sdist path")
            if any(not (member.isfile() or member.isdir()) for member in members):
                raise ValueError("sdist contains non-file member")
            return sorted(names)
    raise ValueError("expected .whl or .tar.gz artifact")


def create_manifest(paths: list[Path]) -> dict:
    if not paths:
        raise ValueError("no artifacts")
    artifacts = []
    for path in sorted(paths, key=lambda p: p.name):
        members = inspect_archive(path)
        artifacts.append({
            "filename": path.name,
            "sha256": digest_file(path),
            "size_bytes": path.stat().st_size,
            "member_count": len(members),
        })
    return {"schema_version": 1, "artifacts": artifacts}


def verify_manifest(manifest: dict, directory: Path) -> bool:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("invalid manifest schema")
    entries = manifest.get("artifacts")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest has no artifacts")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"filename", "sha256", "size_bytes", "member_count"}:
            raise ValueError("invalid artifact entry")
        name = entry["filename"]
        if not isinstance(name, str) or not name or Path(name).name != name or "\\" in name:
            raise ValueError("invalid artifact filename")
        path = directory / name
        if not path.is_file() or digest_file(path) != entry["sha256"]:
            return False
        if path.stat().st_size != entry["size_bytes"]:
            return False
        if len(inspect_archive(path)) != entry["member_count"]:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Local wheel/sdist audit")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--manifest", type=Path, default=Path("artifact-manifest.json"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            if not verify_manifest(manifest, args.dist):
                parser.error("artifact verification failed")
            print("VERIFIED")
        else:
            paths = list(args.dist.glob("*.whl")) + list(args.dist.glob("*.tar.gz"))
            manifest = create_manifest(paths)
            args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"wrote {args.manifest}")
    except (OSError, ValueError, TypeError, zipfile.BadZipFile, tarfile.TarError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create an empty `scripts/__init__.py` to support test imports.

**Security note:** This tool validates archive member names and simple structural metadata, but it is **not** a complete malicious-archive scanner. Do not extract untrusted archives or treat a passing manifest as publisher authentication. Production scanners should also inspect metadata, package contents, decompression limits, signatures and SBOMs.

## 7. `tests/test_policy.py`
```python
import unittest
from sre_artifact_audit import classify_latency


class PolicyTests(unittest.TestCase):
    def test_healthy(self): self.assertEqual(classify_latency(100), "healthy")
    def test_warning_boundary(self): self.assertEqual(classify_latency(200), "warning")
    def test_critical_boundary(self): self.assertEqual(classify_latency(500), "critical")
    def test_custom_threshold(self): self.assertEqual(classify_latency(75, warning_ms=50, critical_ms=100), "warning")
    def test_negative(self):
        with self.assertRaises(ValueError): classify_latency(-1)
    def test_bool(self):
        with self.assertRaises(TypeError): classify_latency(True)
    def test_nan(self):
        with self.assertRaises(ValueError): classify_latency(float("nan"))
    def test_inf(self):
        with self.assertRaises(ValueError): classify_latency(float("inf"))
    def test_bad_thresholds(self):
        with self.assertRaises(ValueError): classify_latency(10, warning_ms=500, critical_ms=200)
    def test_string(self):
        with self.assertRaises(TypeError): classify_latency("300")
    def test_no_network_import(self):
        import sre_artifact_audit
        self.assertTrue(hasattr(sre_artifact_audit, "classify_latency"))
    def test_boundary_below(self): self.assertEqual(classify_latency(199), "healthy")


if __name__ == "__main__":
    unittest.main()
```

## 8. `tests/test_artifacts.py`
```python
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
from scripts.audit_artifacts import (
    create_manifest, digest_file, inspect_archive, safe_member, verify_manifest,
)


def wheel(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("sre_artifact_audit/__init__.py", "")
        archive.writestr("sre_artifact_audit_lab-0.1.0.dist-info/METADATA", "Name: sre-artifact-audit-lab\nVersion: 0.1.0\n")
        archive.writestr("sre_artifact_audit_lab-0.1.0.dist-info/RECORD", "")


class ArtifactTests(unittest.TestCase):
    def test_safe_member(self): self.assertTrue(safe_member("package/module.py"))
    def test_traversal(self): self.assertFalse(safe_member("../secret"))
    def test_absolute(self): self.assertFalse(safe_member("/etc/passwd"))
    def test_backslash(self): self.assertFalse(safe_member("..\\secret"))
    def test_empty_name(self): self.assertFalse(safe_member(""))
    def test_wheel_inspect(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.whl"
            wheel(path)
            self.assertEqual(len(inspect_archive(path)), 3)
    def test_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.whl"
            wheel(path)
            manifest = create_manifest([path])
            self.assertTrue(verify_manifest(manifest, Path(folder)))
    def test_modified_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.whl"
            wheel(path)
            manifest = create_manifest([path])
            with path.open("ab") as out:
                out.write(b"tampered")
            self.assertFalse(verify_manifest(manifest, Path(folder)))
    def test_missing_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.whl"
            wheel(path)
            manifest = create_manifest([path])
            path.unlink()
            self.assertFalse(verify_manifest(manifest, Path(folder)))
    def test_empty_manifest(self):
        with self.assertRaises(ValueError):
            create_manifest([])
    def test_bad_manifest_schema(self):
        with self.assertRaises(ValueError):
            verify_manifest({}, Path("."))
    def test_unknown_archive(self):
        with self.assertRaises(ValueError):
            inspect_archive(Path("file.zip"))


if __name__ == "__main__":
    unittest.main()
```

## 9. Build and validate

**Linux/macOS/WSL**
```bash
python3 -m venv .venv
./.venv/bin/python -m pip install 'setuptools>=68' build
./.venv/bin/python -m pip install -e . --no-build-isolation
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python -m build --no-isolation
./.venv/bin/python scripts/audit_artifacts.py --dist dist --manifest artifact-manifest.json
./.venv/bin/python scripts/audit_artifacts.py --dist dist --manifest artifact-manifest.json --verify
```

**Windows PowerShell**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "setuptools>=68" build
.\.venv\Scripts\python.exe -m pip install -e . --no-build-isolation
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m build --no-isolation
.\.venv\Scripts\python.exe scripts/audit_artifacts.py --dist dist --manifest artifact-manifest.json
.\.venv\Scripts\python.exe scripts/audit_artifacts.py --dist dist --manifest artifact-manifest.json --verify
```

Build dependencies may require access to an approved index or a preprovisioned wheelhouse. **No registry upload is performed.** Expected: wheel and sdist in `dist/`, a local manifest, `VERIFIED` output and **24 unit tests**.

## 10. Offline wheel smoke test
Create a fresh virtual environment and install the exact wheel you verified, without contacting any index.

```bash
python3 -m venv .venv-smoke
./.venv-smoke/bin/python -m pip install --no-index --no-deps dist/sre_artifact_audit_lab-0.1.0-py3-none-any.whl
(cd /tmp && "$OLDPWD/.venv-smoke/bin/python" -m sre_artifact_audit --latency-ms 300)
```

PowerShell:
```powershell
py -3 -m venv .venv-smoke
.\.venv-smoke\Scripts\python.exe -m pip install --no-index --no-deps dist/sre_artifact_audit_lab-0.1.0-py3-none-any.whl
$python = (Resolve-Path .\.venv-smoke\Scripts\python.exe).Path
Push-Location $env:TEMP
& $python -m sre_artifact_audit --latency-ms 300
Pop-Location
```

Expected: `{"latency_ms": 300.0, "status": "warning"}`.

## 11. Failure injection
1. Modify a copy of the wheel after manifest generation: verification must fail.
2. Delete the wheel: verification must fail.
3. Add a `../secret` member to a synthetic wheel: path inspection must reject it.
4. Set invalid latency: CLI exits nonzero.
5. Change project version without rebuilding: metadata/version audit should identify mismatch; regenerate release artifacts and manifest.
6. Attempt offline install with missing wheel: fail rather than reaching an index.

## 12. Operational runbook
If verification fails, stop release promotion, preserve the artifact and manifest, identify the source commit/build runner, compare trusted digests, inspect build logs and dependencies, and rebuild in an approved environment. Do not regenerate the expected manifest from a suspect artifact merely to make verification pass.

## 13. Acceptance
- [ ] 24 unit tests pass locally.
- [ ] Wheel and sdist both built.
- [ ] Artifact manifest created and independently verified.
- [ ] Offline fresh-venv wheel smoke test passes.
- [ ] No package published to any registry.
- [ ] Artifact provenance limitations documented.
