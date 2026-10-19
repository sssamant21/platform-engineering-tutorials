# Chapter 085 — Production security and DR architecture

**Trust boundaries:** signed PR -> unprivileged CI -> trusted scanner and provenance -> protected OIDC CD -> cloud-side IAM/org policies -> Kubernetes admission/RBAC -> GitOps -> stateful services -> DR.

**Enforcement:** source and artifact immutability; no admin identities; exact issuer/audience/subject; encrypted locked state; OPA/Sentinel and cloud policy; namespace RBAC and network boundaries; verified restore; SLO.

**Independent evidence:** native cloud trust-policy and authorization tests, Kubernetes SubjectAccessReview, signed attestation verification, native policy tests, scanner reports, restore logs and audit retention.

**Incident:** freeze change, preserve logs, revoke identity, restore known-good policy, verify database backup/KMS/PITR, test canary, approve reconciliation and perform postmortem.
