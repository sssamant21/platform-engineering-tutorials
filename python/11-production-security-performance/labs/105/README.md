# Chapter 105 — Secure Software Supply Chain Executable Lab

[Offline Python engine](supply_chain_lab.py) · [Automated tests](test_supply_chain_lab.py) · [Full SRE/DBRE lab](../105-secure-software-supply-chain-dependency-risk-sre-dbre-lab.md)

## Run offline

Python 3.11+ standard library only. No package installation, cloud credentials, network, signing keys, vulnerability-feed access or deployment writes.

```bash
cd python/11-production-security-performance/labs/105
python -m compileall -q supply_chain_lab.py test_supply_chain_lab.py
python -m unittest -v test_supply_chain_lab.py
python supply_chain_lab.py --dry-run
python supply_chain_lab.py --partial
```

PowerShell: `py -3 -m unittest -v test_supply_chain_lab.py`.

## Implemented

- Synthetic PyPI dependency records with normalized package name, exact version, SHA-256-shaped digest, direct/transitive marker and source.
- Deterministic **educational JSON** inventory labeled as **not CycloneDX/SPDX**.
- Synthetic advisory matching, incomplete-inventory unknown status, dependency drift and artifact hash comparison.
- Bounded pagination and duplicate detection.
- SHA-256 advisory release fingerprint bound to repository, commit, artifact, SBOM and ticket.
- Simulated independent, expiring approval with rollback evidence.
- **No live vulnerability scans, signature verification, provenance attestation, package installs, CI execution or mutations.**

## Exercises

1. Reject invalid package names, mutable versions and malformed hashes.
2. Detect normalized duplicate names and inspect transitive dependencies.
3. Produce deterministic educational SBOM inventory.
4. Design CycloneDX/SPDX generation with production tooling.
5. Compare synthetic advisory matching and feed-completeness status.
6. Detect dependency removal/changes only between complete snapshots.
7. Detect local artifact byte tampering against trusted expected hash.
8. Reject pagination loops and item/page budget violations.
9. Bind release approval to immutable commit, artifact and SBOM.
10. Reject self-approval, expired approval, wrong digest and missing rollback.
11. Design SLSA provenance and Sigstore verification for CI/CD.
12. Write compromised dependency and DBRE release rollback runbooks.

## Production extension blueprint — NOT implemented

- Generate a **valid** CycloneDX or SPDX SBOM using maintained tooling, validate schemas and include package URLs, licenses and dependency graph.
- Run `pip-audit`, OSV-Scanner or enterprise scanners with feed freshness and exception governance.
- Enforce `pip --require-hashes` with reviewed transitive lockfile and isolated build.
- Sign artifacts and provenance using Sigstore/cosign or managed keys; verify trusted issuer, identity, digest and attestation.
- Harden GitHub Actions with full commit SHA action pins, minimum token permissions, protected environments and OIDC workload federation.
- Integrate staged GitOps deployment, runtime SLO monitoring, idempotent release tracking and tested rollback.

## CI template (not enabled)

```yaml
name: chapter-105-supply-chain-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/105
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q supply_chain_lab.py test_supply_chain_lab.py
      - run: python -m unittest -v test_supply_chain_lab.py
```

Pin reviewed action commit SHAs before enabling. **Validation:** Test source published; execution of exact committed revision, CI, live scans, SBOM schema validation and signing acceptance remain pending.
