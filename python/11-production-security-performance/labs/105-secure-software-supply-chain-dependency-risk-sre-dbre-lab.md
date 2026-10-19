# Chapter 105 — Secure Software Supply Chain and Dependency Risk SRE/DBRE Lab

[Python simulator](105/supply_chain_lab.py) · [Automated tests](105/test_supply_chain_lab.py) · [Project README](105/README.md)

## Mission

Your platform team is preparing a Python automation release that can manage Kubernetes workloads and PostgreSQL/Elasticsearch maintenance. A transitive dependency receives a critical advisory, an artifact hash changes unexpectedly, and CI provenance is incomplete. Build a safe supply-chain assessment and advisory release gate.

```text
Synthetic PyPI lock metadata -> normalized dependency inventory
          -> educational JSON SBOM (NOT CycloneDX/SPDX)
          -> synthetic advisory matching and completeness
          -> artifact SHA-256 comparison + dependency drift
          -> immutable commit/artifact/SBOM release fingerprint
          -> independent approval, expiry, rollback evidence
          -> advisory JSON / zero installs, scans, signing or writes
```

## Lab 1 — Execute

```bash
cd python/11-production-security-performance/labs/105
python -m compileall -q supply_chain_lab.py test_supply_chain_lab.py
python -m unittest -v test_supply_chain_lab.py
python supply_chain_lab.py --dry-run
python supply_chain_lab.py --partial
```

## Lab 2 — Python dependency and SBOM governance

Inspect direct and transitive synthetic packages, normalized PyPI names, pinned versions and digest fields. Explain fully hashed `requirements.lock` workflows, isolated builds and dependency confusion. Compare educational inventory fields with actual CycloneDX/SPDX schemas. Do not treat sample hashes as real package digests.

## Lab 3 — Vulnerability and provenance risk

Match a synthetic advisory to a package/version. Demonstrate why incomplete inventory or stale advisory feeds invalidate a clean result. Validate local byte hash comparison, then design a trusted SLSA provenance attestation and Sigstore signing/verification workflow. The lab does **not** verify signatures.

## Lab 4 — GitHub Actions and CI/CD hardening

Design a GitHub Actions pipeline with least-privilege `GITHUB_TOKEN`, pinned actions, untrusted PR isolation, protected environments, OIDC federation, dependency scanning, SBOM generation, signed provenance and immutable release promotion. Include Kubernetes/GitOps deployment gates and DBRE rollback.

## Lab 5 — Approval and incident response

Bind release plan to repository, immutable commit, artifact SHA-256, SBOM digest and change ticket. Require separate approver, expiry and rollback evidence. Reject mismatches and produce an advisory-only result with no writes.

## Production incident simulations

| # | Incident | Expected result | Mode |
|---|---|---|---|
| 1 | Valid pinned dependency | Accept | Automated |
| 2 | Invalid package name | Reject | Automated |
| 3 | Mutable version | Reject | Automated |
| 4 | Malformed digest | Reject | Automated |
| 5 | Invalid direct/source field | Reject | Automated |
| 6 | Normalized name collision | Reject duplicate | Automated |
| 7 | Invalid inventory record | Reject | Automated |
| 8 | SBOM deterministic ordering | Stable | Automated |
| 9 | Educational SBOM format | Clearly labeled | Automated |
| 10 | Incomplete inventory | Risk unknown | Automated |
| 11 | Synthetic vulnerable version | Review | Automated |
| 12 | No advisory match | Synthetic feed only | Automated |
| 13 | Invalid advisory severity | Reject | Automated |
| 14 | Removed dependency | Detect | Automated |
| 15 | Changed dependency | Detect | Automated |
| 16 | Partial inventory drift | Unknown | Automated |
| 17 | Artifact digest match | Verify bytes | Automated |
| 18 | Artifact tampering | Reject match | Automated |
| 19 | Invalid artifact input | Reject | Automated |
| 20 | Pagination normal | Collect | Automated |
| 21 | Page/item budget exceeded | Fail closed | Automated |
| 22 | Pagination loop/bad page | Reject | Automated |
| 23 | Release fingerprint stable | Deterministic | Automated |
| 24 | Changed SBOM digest | Fingerprint changes | Automated |
| 25 | Invalid commit digest | Reject | Automated |
| 26 | No approval | Hold | Automated |
| 27 | Valid independent approval | Advisory only | Automated |
| 28 | Expired/self approval | Hold | Automated |
| 29 | Wrong digest/no rollback | Hold | Automated |
| 30 | Approved dry_run=false | Zero writes | Automated |
| 31 | Dependency confusion | Restrict indexes/namespace | Guided |
| 32 | Typosquatted package | Quarantine and investigate | Guided |
| 33 | Compromised GitHub Action | Revoke and isolate runner | Guided |
| 34 | Poisoned build artifact | Verify provenance/signature | Guided |
| 35 | Stale CVE feed | Mark unknown and refresh | Guided |
| 36 | Missing SBOM in release | Block promotion | Guided |
| 37 | SLSA builder identity mismatch | Block release | Guided |
| 38 | Sigstore issuer mismatch | Block release | Guided |
| 39 | PostgreSQL migration dependency risk | Test rollback and backups | Guided |
| 40 | Elasticsearch maintenance tool compromise | Contain API keys and audit | Guided |

## Troubleshooting and operational runbooks

**Dependency compromise:** identify affected versions and lockfiles, quarantine artifacts, revoke CI credentials, rebuild from reviewed source and verify downstream deployment.

**Critical CVE:** assess actual affected versions, exposure, reachability, mitigation, fix and SLO risk. Stage patch and rollback.

**Signature/provenance mismatch:** stop promotion, verify expected identity, issuer, builder, commit, artifact digest and trust roots.

**CI runner breach:** isolate runner, freeze releases, revoke credentials, preserve logs and rebuild trusted artifacts.

**DBRE deployment rollback:** validate database schema compatibility, PostgreSQL backups, Elasticsearch indices, app SLO and safe recovery.

**SBOM missing or incomplete:** regenerate from the actual artifact/build environment, validate CycloneDX/SPDX schema and re-scan.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| Python dependency pinning, hashes and packaging | 20 |
| SBOM and vulnerability risk management | 20 |
| SLSA, signing and provenance architecture | 20 |
| GitHub Actions/CI/CD hardening | 15 |
| Release approvals and incident response | 15 |
| Automated tests, runbooks and DBRE rollback | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, local tests executed, no-write evidence, reviewed release trust chain, valid production SBOM/signature design and independently reviewed CI policy.

**Validation:** Test code published; exact committed runtime execution, live vulnerability scans, actual SBOM generation, signing and CI remain pending.
