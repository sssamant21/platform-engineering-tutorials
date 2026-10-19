# Chapter 082 — Policy as Code SRE/DBRE runbooks

1. **OPA unavailable:** freeze privileged promotion, verify bundle and service health, do not fail open.
2. **Rego regression:** isolate changed rule, replay deny cases, restore signed known-good bundle.
3. **Sentinel bypass:** inspect policy-set attachment, advisory/soft/hard mandatory and overrides.
4. **Bundle tampering:** quarantine registry artifact, revoke signer, preserve logs and reissue.
5. **Sensitive plan exposure:** restrict artifacts, revoke access, rotate secrets, audit state.
6. **CloudFormation:** block destructive change sets, inspect stack policies and recovery.
7. **Azure Policy:** validate scope, exemption owner, expiration and RBAC.
8. **Pulumi:** pin policy pack, verify stack target and partial update recovery.
9. **Kubernetes admission:** verify failurePolicy, webhook availability, Gatekeeper/Kyverno enforcement.
10. **GitOps drift:** verify controller owner and PR-based change authority.
11. **DBRE:** stop destructive changes; verify PITR, backup, restore, lag/quorum, RPO/RTO.
12. **Emergency override:** independent approval, narrow scope, expiry, compensating controls, audit.
