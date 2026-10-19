# Chapter 083 — Security scanning SRE/DBRE runbooks

1. **Secret in source:** revoke token, isolate exposure, inspect history, rescan and rotate.
2. **State or plan leak:** restrict artifacts, rotate all exposed values and audit backend access.
3. **Runner compromise:** quarantine runner, revoke OIDC sessions, preserve forensic evidence.
4. **Provider tampering:** pin trusted digest, rebuild lockfile and attest provenance.
5. **SBOM/provenance failure:** reject release and rebuild from trusted builder.
6. **Scanner outage:** fail closed; restore scanner database and rule pack.
7. **False positives:** exact finding fingerprint, owner, compensating control, independent expiring approval.
8. **Cloud drift:** inspect AWS Config/Azure Defender/GCP SCC and reconcile approved change.
9. **Kubernetes/GitOps:** validate admission, image provenance, RBAC and controller ownership.
10. **DBRE rotation:** stage credential overlap, monitor connections, PITR and restore.
11. **Critical CVE:** assess reachability, contain, patch, canary and SLO.
12. **Audit handover:** retain signed evidence, scan versions, findings, owner and closure.
