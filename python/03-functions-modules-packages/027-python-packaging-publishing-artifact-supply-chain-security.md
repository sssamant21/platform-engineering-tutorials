# Chapter 027 — Python Packaging, Publishing and Artifact Supply-Chain Security

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 2–3 hours**

## Learning objectives
Distinguish wheels and source distributions; implement PEP 517/518/621 packaging metadata; choose versions; build and inspect artifacts; verify hashes, contents and metadata; produce a local provenance manifest; stage a secure release; understand trusted publishing, indexes, SBOMs, vulnerability scans, rollback and artifact immutability.

## 1. Why SREs need packaging discipline
Operational utilities may inspect PostgreSQL, Elasticsearch, Kubernetes, Kafka and cloud environments. Installing an unreviewed artifact on a privileged SRE workstation can be as dangerous as deploying an unreviewed container. Treat Python distributions as deployable software with approvals, provenance, tests and rollback.

## 2. Source tree, wheel and sdist
```text
reviewed source + pyproject.toml
              |
              v
         PEP 517 builder
           /       \
          v         v
      .whl        .tar.gz
    installed     source build
    artifact      archive
```
A **wheel** is a built distribution with `*.dist-info/METADATA`, `WHEEL` and `RECORD`. A **source distribution** (sdist) packages source plus metadata for rebuilding. A wheel avoids running a local build step during install, but installation and imports must still be treated as potentially unsafe for untrusted code. Sdist builds execute a build backend and may run arbitrary build-time code.

## 3. Versioning and immutable releases
Use PEP 440 versions such as `0.1.0`, `0.2.0rc1`, and `1.0.0`. Avoid overwriting published release artifacts; publish a new version instead. Define a change log, compatibility policy, release tag, and rollback plan. Version strings alone do not guarantee compatibility or reproducibility.

## 4. pyproject.toml
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sre-artifact-audit-lab"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []
description = "Offline SRE packaging security lab"

[tool.setuptools.packages.find]
where = ["src"]
```
Build requirements are examples. In production pin vetted build tooling, use a controlled index, and record interpreter/backend versions. A `src/` layout reduces accidental imports from the checkout.

## 5. Artifact verification
Review:
1. Exact filename, digest, size and release version.
2. Wheel `METADATA` for name, version, dependencies and Python compatibility.
3. Wheel `RECORD` for installed-file integrity metadata.
4. Zip member paths and unexpected executable content.
5. Sdist member paths and embedded secrets.
6. Reinstallation and smoke tests from a fresh environment.

A SHA-256 digest proves equality to an expected artifact, not publisher identity or safety. The expected digest must come from an independently trusted release channel. Wheel `RECORD` is useful for consistency but is not a signature.

## 6. Provenance, attestations and SBOM
A release manifest can record artifact SHA-256, build time, source commit, Python version, builder, CI job and policy results. This lab generates a local manifest without asserting cryptographic provenance. Strong provenance requires authenticated builders, signed attestations, verifiable identities and a trusted source-to-artifact relationship. An SBOM inventories components; it does not prove that components are vulnerability-free.

## 7. Package registries and trusted publishing
A registry can be public PyPI, a staging registry such as TestPyPI, or an approved private index. Production publication should use organization-approved identity-based trusted publishing (OIDC) where supported, scoped environments, immutable release controls and least privilege. Never hardcode upload tokens in CI YAML or Markdown. Verify repository ownership, registry namespace and index configuration to mitigate dependency confusion.

**This lab deliberately does not upload any package.** It prepares and validates artifacts locally. Publishing requires an explicit, separately approved release workflow.

## 8. Threat model
| Threat | Example | Mitigation |
|---|---|---|
| Dependency confusion | Public package impersonates private name | Private index policy and namespace controls |
| Typosquatting | Lookalike package name | Review names and provenance |
| Compromised build | CI runner injects code | Isolated builders, restricted credentials, attestations |
| Artifact substitution | Wheel changed after review | Verify trusted digest before promotion |
| Secret leakage | Tokens embedded in sdist | Scan archive and review contents |
| Vulnerable transitive dependency | Unsafe library version | Lock, scan, patch and retest |
| Registry token theft | Static upload secret | Prefer scoped OIDC trusted publishing |

## 9. CI/CD reference workflow
```text
PR review → lint/tests → dependency scan → build wheel + sdist
 → inspect archive contents + metadata → artifact digest manifest
 → fresh install + smoke tests → provenance/SBOM validation
 → approval → registry upload → post-publish verification
```
Do not rebuild between staging and production; promote the exact validated bytes where the registry supports it.

## 10. Rollback and incident runbook
1. Identify the affected package version and exact artifact hash.
2. Stop promotion and revoke compromised publishing credentials if indicated.
3. Preserve CI logs, release manifests and package artifacts.
4. Restore a previously approved immutable version; do not silently overwrite.
5. Rotate any exposed credentials and assess installation scope.
6. Rebuild in a trusted environment and revalidate.
7. Document root cause, impact, corrective actions and release controls.

## 11. Troubleshooting
| Symptom | Cause | Action |
|---|---|---|
| `python -m build` unavailable | Build frontend missing | Provision approved build tooling |
| Wheel/sdist versions differ | Stale build directory or metadata | Clean build output, rebuild |
| Unexpected wheel files | Packaging configuration too broad | Restrict package discovery |
| Digest mismatch | Modified artifact | Halt promotion and investigate |
| `twine upload` denied | Publishing identity/permissions | Check approved trusted-publishing setup |
| TLS/index failures | Proxy/CA or registry configuration | Use approved CA and mirror; never disable verification |
| Reproducibility differs | Timestamps/build environment | Record inputs; compare normalized contents |

## 12. Hands-on
[Chapter 027 — SRE Artifact Provenance and Packaging Lab](labs/027-sre-artifact-provenance-packaging-lab.md) includes a complete package, wheel/sdist build instructions, an archive inspection and SHA-256 manifest tool, 24 unit tests, failure injection and a release checklist.

**Next: Chapter 028 — Python Project Configuration, Environment Variables and Secrets Hygiene.**
