# Chapter 084 — Zero Trust SRE/DBRE runbooks

1. **AWS overprivilege:** isolate role, inspect trust, PassRole, boundaries, SCP, CloudTrail.
2. **OIDC mismatch:** compare exact issuer/audience/subject and protected branch/environment.
3. **AWS SCP outage:** identify deny impact, use separately approved emergency role and audit.
4. **Azure federation:** inspect tenant, subject, scope, RBAC and Key Vault.
5. **GCP WIF compromise:** revoke bindings, inspect principal attributes and audit.
6. **Kubernetes RBAC:** test namespace scope, ServiceAccount and admission.
7. **NetworkPolicy incident:** verify CNI, DNS, service egress and health before rollback.
8. **GitOps escalation:** quarantine controller, inspect AppProjects/Flux impersonation.
9. **State/KMS:** preserve encrypted state, audit reads, rotate compromised credentials.
10. **DBRE rotation:** prepare/distribute/verify/revoke; monitor pools, PITR and restore.
11. **Break-glass:** two-person approval, time-box, scope, audit and expiry.
12. **Postmortem:** record affected identities, blast radius, SLO, restore and controls.
