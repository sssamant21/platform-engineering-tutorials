# Chapter 025 — Python Modules, Imports and Package Organization

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 2–3 hours**

## Outcomes
Understand modules versus packages, absolute and relative imports, `sys.path`, `__name__`, `__init__.py`, `__main__.py`, package boundaries, CLI entry points, editable installs, `pyproject.toml`, import side effects, namespace collisions, test discovery and packaging a reusable read-only SRE tool.

## 1. Why packaging matters for SRE/DBRE
A single-file script is convenient for experiments, but copied scripts diverge across teams and environments. A package gives versionable interfaces, repeatable installation, isolated tests, explicit dependency boundaries and a consistent CLI. Treat package distribution as software supply chain: pin trusted sources, review artifacts and do not install unreviewed dependencies on production hosts.

## 2. Module, package and distribution
- **Module:** an importable Python file, such as `policy.py`.
- **Regular package:** directory with `__init__.py`, containing modules/subpackages.
- **Distribution:** an installable wheel/sdist, described by packaging metadata; distribution names can differ from import names.
- **Namespace package:** a package without `__init__.py` supported by Python's import system; useful for coordinated namespaces, but regular packages are simpler for this lab.

```text
sre-probe-kit/
  pyproject.toml
  src/
    sre_probe_kit/
      __init__.py
      __main__.py
      cli.py
      models.py
      policy.py
      reporting.py
  tests/
    test_policy.py
    test_cli.py
```

The **src layout** reduces accidental imports from the repository root and helps tests exercise the installed package.

## 3. Import mechanics and sys.path
```python
import sre_probe_kit.policy
from sre_probe_kit.policy import classify
```
Python resolves modules using import finders and search paths including `sys.path`. The current working directory or script directory may be present, so files named `json.py`, `typing.py`, `logging.py` or `requests.py` can shadow standard or third-party modules. Inspect `module.__file__` when debugging. Avoid changing `sys.path` inside production application code to make imports work.

Imports cache module objects in `sys.modules` within a process. Repeated imports do not rerun normal top-level code; however, import-time side effects can still create hidden coupling, and explicit reload has additional caveats.

## 4. Absolute and relative imports
Inside a package:
```python
from .policy import classify
from .reporting import build_report
```
These are explicit relative imports. For application code, absolute imports are often easier to navigate; relative imports are useful within a cohesive package. Avoid `from module import *`, which hides names and makes review harder.

Running `python src/sre_probe_kit/cli.py` may break relative imports because that file is treated as a script without package context. Use `python -m sre_probe_kit` after installing the package, or the declared console entry point.

## 5. __init__, __main__ and entry points
- `__init__.py` initializes a regular package and can expose a small public API.
- `__main__.py` supports `python -m sre_probe_kit`.
- A `[project.scripts]` entry in `pyproject.toml` creates an installed CLI command.
- `if __name__ == "__main__":` prevents CLI execution during normal imports.

Avoid file I/O, cloud SDK clients, credential discovery or network calls during import. Keep startup logic in `main()`.

## 6. Public APIs and dependency direction
```text
CLI adapter (argparse, files)
       |
       v
reporting (aggregation)
       |
       v
policy + models (pure validation)
```
Low-level policy modules should not import CLI code. Circular imports often indicate poor boundaries; move shared types and contracts into a small foundational module.

`__all__` documents intended wildcard-export names but is not a security boundary. Python module internals are not private access controls.

## 7. Packaging with pyproject.toml
Use a modern PEP 517 build backend and declare supported Python versions. The lab uses setuptools with an explicit `src` package directory. Install in a virtual environment using `python -m pip install -e .` for development; a regular wheel install is more representative of deployment. Editable installs are for development, not immutable production releases.

## 8. Reproducibility and security
- Use an isolated virtual environment.
- Keep dependencies minimal; this lab has no runtime third-party dependencies.
- Pin and review build tooling in controlled CI; consider an approved internal index.
- Build wheels in CI, scan and attest artifacts where available.
- Avoid printing raw environment variables or credentials in diagnostics.
- Use `python -m pip` to target the intended interpreter.
- Do not rely on `PYTHONPATH` hacks or copying source folders into production images.

## 9. Testing imports and execution paths
Test from outside the package's source directory after installation. Exercise `python -m sre_probe_kit` and the console script. Unit tests should import public interfaces and assert import itself performs no external I/O. Use `python -m unittest discover -s tests -v`.

## 10. Operational use cases
- Reusable PostgreSQL replication-lag classifier consumed by a CLI and scheduled report.
- Elasticsearch slow-query analysis library shared across SRE workstations.
- Kubernetes read-only inventory package with a separately reviewed API adapter.
- Kafka consumer-lag diagnostics with a pure policy core.
- Snowflake metadata audit reporting with independent configuration and I/O layers.

## 11. Troubleshooting and runbooks

| Symptom | Likely cause | Resolution |
|---|---|---|
| `ModuleNotFoundError` | Package not installed in active interpreter | Activate venv; `python -m pip install -e .` |
| Relative import failure | Executed module file as script | Use `python -m sre_probe_kit` |
| Standard library import acts strangely | Local filename shadows module | Rename and clear stale caches |
| Circular import | Inverted dependency direction | Move common contracts to models |
| CLI command missing | Environment or entry point not installed | Check venv and reinstall |
| Tests pass only from repository root | Source-tree import leakage | Use src layout and installed-package tests |
| Unexpected import side effect | Work executed at module top level | Move work into main or explicit factory |
| Different Python version | Multiple interpreters | Check `python -V` and `python -m pip -V` |

## 12. Hands-on lab
[Chapter 025 — Packaged SRE Health Classifier Lab](labs/025-packaged-sre-health-classifier-lab.md) provides a complete installable package, JSON CLI, deterministic reporting, unit tests, negative-path validation, and local cleanup.

## 13. Review and acceptance
Explain the difference between module, package and distribution; why src layout matters; when to use `-m`; how to avoid circular imports; and how to build an artifact that does not execute cloud calls on import.

**Next: Chapter 026 — Virtual Environments, Dependency Management and Reproducible Builds.**
