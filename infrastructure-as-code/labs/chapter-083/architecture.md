# Chapter 083 — Enterprise scanning architecture

**Source:** signed PR, CODEOWNERS, secret scanning and history analysis.

**CI:** Checkov/Trivy/Terrascan, SAST, SBOM and dependency CVE scans; fail closed on scanner outages, stale databases and unresolved critical findings.

**Supply chain:** immutable provider/collection/image digests, lockfiles, trusted builder, verified Sigstore/in-toto provenance, SBOM inventory and controlled registries.

**Deployment:** protected OIDC, independent approval, policy-as-code, state encryption, DBRE PITR and restore rehearsal.

**Runtime:** cloud Config/Defender/SCC, Kubernetes admission, GitOps reconciliation, scheduled drift detection and audit evidence.

**Incidents:** revoke exposed credentials, isolate runner, preserve logs, rebuild trusted artifacts, validate backup and SLO before promotion.
