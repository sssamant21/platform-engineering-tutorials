# Chapter 081 — Security architecture

**Threat actors:** malicious PR contributor, compromised CI runner, stolen cloud credential, supply-chain attacker, privileged insider.

**Assets:** production identities, IaC state/plan, secrets, KMS keys, database backups, Kubernetes credentials, audit trails.

**Trust boundaries:** source -> CI -> artifact registry -> protected CD -> OIDC -> cloud control plane -> backend/state -> workload/database.

**Controls:** exact OIDC subject/audience, least privilege, short-lived identity, state encryption/versioning/audit, secret-manager delivery, verified provider pins and provenance, approval separation, cloud-side deny guardrails and DBRE restore rehearsal.

**Response:** isolate, revoke, rotate, preserve evidence, restore service, verify SLO, perform post-incident review.
