# Chapter 080 — Enterprise SRE/DBRE runbooks

1. **Change intake:** freeze until source provenance, ticket, owners and window verified.
2. **Identity:** verify OIDC audience/subject, scoped role, target and expiry.
3. **Supply chain:** pin CLI/providers/actions/images; quarantine tampering.
4. **Plan:** review destructive changes, signed digest, target and policy.
5. **State:** preserve encrypted checkpoints and lock owner; no blind force-unlock.
6. **DBRE:** PITR, checksum, restore drill, lag/quorum, RPO/RTO and approval.
7. **Progressive delivery:** bounded canary, PDB, SLO/error-budget stop conditions.
8. **GitOps:** inspect Argo/Flux health and remove dual writers.
9. **DR:** incident command, fencing, consistency, restore and cutover.
10. **Partial apply:** freeze promotions, preserve state, assess actual resources.
11. **Security incident:** revoke, quarantine runner, preserve logs, rebuild.
12. **Acceptance:** archive change evidence, metrics, backup, FinOps and handover.
