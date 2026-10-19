# Chapter 081 — Security SRE/DBRE runbooks

1. **Threat model:** enumerate assets, actors, trust boundaries, STRIDE threats and risk owner.
2. **Credential leak:** revoke, rotate, isolate runner and preserve logs.
3. **OIDC federation:** verify exact issuer/audience/subject and least-privilege permissions.
4. **State leak:** quarantine backend, audit reads, rotate exposed secrets and preserve checkpoint.
5. **Secret rotation:** prepare/distribute/verify/revoke/audit with application health checks.
6. **Supply chain:** quarantine untrusted dependencies, pin digest and rebuild provenance.
7. **Provider-specific:** review Pulumi secrets, CloudFormation dynamic refs and Bicep secure params.
8. **GitOps/Ansible/K8s:** audit Vault, controller credentials, namespace RBAC and external secrets.
9. **DBRE:** validate backup isolation, PITR, restore rehearsal, KMS access and RPO/RTO.
10. **Policy exception:** time-box, approve, record compensating controls and expiry.
11. **Detection:** correlate IAM, runner, backend access, secret manager and SLO alerts.
12. **Postmortem:** document blast radius, rotation, recovery, owner and prevention.
