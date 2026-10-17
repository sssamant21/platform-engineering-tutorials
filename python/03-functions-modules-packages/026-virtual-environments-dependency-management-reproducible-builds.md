# Chapter 026 — Virtual Environments, Dependency Management and Reproducible Builds

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 2–3 hours**

## Learning objectives
Isolate Python dependencies with `venv`; understand interpreters, pip and build backends; distinguish direct from transitive dependencies; use constraints, pinned versions and hash-verified installs; build wheels; validate provenance; and design a safe, repeatable SRE automation release pipeline.

## 1. Why this matters to SRE/DBRE
A shared workstation or CI runner can execute multiple operational tools. Installing packages into the system interpreter risks version conflicts and unauthorized changes. Reproducibility helps avoid "works on my laptop" failures during incidents, while supply-chain controls reduce the risk of compromised dependencies.

A virtual environment isolates site-packages and executable scripts, **not** the operating system, network, filesystem or Python interpreter implementation. It is not a security sandbox.

## 2. Interpreter and environment anatomy
```text
project/
  pyproject.toml
  requirements.in
  requirements.lock.txt
  src/
  tests/
  .venv/
    pyvenv.cfg
    bin/python        (Linux/macOS)
    Scripts/python.exe (Windows)
```

`python -m venv .venv` creates an environment tied to the chosen interpreter. Recreate rather than relocate it: environments can contain absolute paths and are not portable artifacts.

## 3. Windows/PowerShell and Linux/WSL
**Windows PowerShell**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

**Linux/macOS/WSL**
```bash
python3 -m venv .venv
./.venv/bin/python --version
./.venv/bin/python -m pip --version
```

Activation is optional: calling the environment's interpreter directly is often safer in automation. Do not disable execution policies globally to activate a virtual environment. Windows and WSL environments are distinct; create one in each runtime.

## 4. pip, direct dependencies and transitive dependencies
`pyproject.toml` declares project metadata and direct dependencies. A resolver selects transitive dependencies consistent with constraints. `pip freeze` records installed packages but does not distinguish direct from transitive packages, nor does it inherently record hashes, platform markers or artifact provenance.

| Mechanism | Purpose | Caveat |
|---|---|---|
| `pyproject.toml` | Project metadata and direct requirements | Ranges alone are not a lock |
| `requirements.in` | Human-maintained direct requirements | Needs resolution |
| Fully pinned requirements | Fixed versions | Platform differences remain |
| `--require-hashes` | Verify downloaded artifacts | All installed requirements must be pinned and hashed |
| Constraints file | Restrict resolver choices | Does not cause installation by itself |
| `pip check` | Detect installed dependency conflicts | Does not prove runtime correctness |
| Wheelhouse | Local artifact set | Must match Python ABI and platform |

## 5. Locking strategies
Pip's requirements format is widely used but is not a universal, cross-platform lock standard. Use a project-approved resolver/lock workflow (for example pip-tools or uv) with reviewed versions and hashes. For strict pip hash checking, every requirement—including transitives—must have hashes for all artifacts used in the target matrix.

**Do not invent hashes or copy example digests into production.** Generate them from verified downloaded artifacts. A `--hash=sha256:...` line is meaningful only for the exact artifact bytes.

## 6. Deterministic offline-first lab
The accompanying lab intentionally uses **zero third-party runtime dependencies**. It demonstrates venv isolation, a local wheel build, an artifact manifest with SHA-256, and repeatable offline installation. This avoids relying on external package indexes during the exercise and distinguishes artifact integrity from publisher trust.

## 7. Build isolation and wheels
A `pyproject.toml` build backend can install build dependencies into an isolated build environment. CI should use a controlled package index and pin/approve build tooling. A wheel is a distribution artifact; it is not a standalone executable or an isolation boundary. Build artifacts should be tested after installation into a fresh environment, not only from the source checkout.

## 8. Security controls
- Prefer organization-approved indexes and internal mirrors.
- Prevent dependency confusion by reviewing index configuration and namespace ownership.
- Verify package hashes, signatures or attestations when available.
- Run dependency and license scanning in CI.
- Use least-privilege build runners and short-lived credentials.
- Never execute unknown `setup.py` or install unreviewed packages on production hosts.
- Never commit `.venv/`, tokens, credentials, `pip.conf` with secrets, or private wheelhouse contents without review.
- Review SBOM/provenance generation, immutable releases and rollback processes.

Hash matching proves artifact integrity relative to an expected digest; it does **not** by itself establish that the artifact's author is trustworthy.

## 9. CI/CD release architecture
```text
reviewed source + metadata
          |
          v
controlled Python + build backend
          |
          v
unit tests / lint / security scans
          |
          v
wheel build + SHA-256 manifest
          |
          v
fresh venv install + smoke tests
          |
          v
artifact registry / approved promotion
```

Build once, test that exact wheel, and promote the same immutable artifact. Avoid rebuilding separately in staging and production.

## 10. Production SRE use cases
- Reproducible Elasticsearch maintenance CLI.
- PostgreSQL read-only diagnostic utilities.
- Kubernetes inventory tools with pinned client dependencies.
- Kafka metadata checkers deployed via CI artifacts.
- Snowflake metadata audit tools requiring controlled SDK versions.

## 11. Troubleshooting
| Symptom | Likely cause | Safe response |
|---|---|---|
| Wrong pip installs | Multiple interpreters | Use `python -m pip` from venv |
| `externally-managed-environment` | OS-managed Python | Create venv; do not bypass OS guardrails |
| Wheel incompatible | Python/ABI/platform mismatch | Rebuild for target matrix |
| Hash mismatch | Changed/corrupt artifact | Stop; investigate provenance |
| Resolver conflict | Incompatible requirements | Inspect direct/transitive constraints |
| SSL/proxy error | Trust store or network policy | Use approved CA/proxy; do not disable TLS verification |
| Windows activation blocked | Script policy | Invoke `.venv\Scripts\python.exe` directly |
| Offline install fails | Missing wheel or dependency | Prepare a complete reviewed wheelhouse |
| Unexpected global package | Venv not active | Check `sys.prefix` and `sys.base_prefix` |

## 12. Acceptance
- Separate environments for development and fresh-wheel smoke testing.
- Zero accidental global pip installs.
- Artifact checksum verified before installation.
- Offline installation succeeds with no network.
- Unit tests pass and installed wheel is importable outside source tree.
- Document Python version, artifact hash and build provenance.
- No production changes.

[Chapter 026 — Reproducible SRE Wheel Build Lab](labs/026-reproducible-sre-wheel-build-lab.md)

**Next: Chapter 027 — Python Packaging, Publishing and Artifact Supply-Chain Security.**
