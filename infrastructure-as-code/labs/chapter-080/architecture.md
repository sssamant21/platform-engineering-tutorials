# Chapter 080 — Enterprise control-plane architecture

**Source:** signed PR, CODEOWNERS, change ticket and immutable commit.

**CI:** isolated validation, provider/collection pinning, SAST/SBOM and offline policy tests. No privileged production secrets.

**Plan:** separate Terraform/OpenTofu saved plan, Pulumi preview, CloudFormation change set, Bicep what-if, Ansible check and GitOps diff. Do not treat previews as interchangeable.

**CD:** protected runner, OIDC workload federation, target verification, immutable artifact digest, independent SRE/security/DBRE approval, backend lock and backup.

**Promotion:** bounded canary/serial deployment, health/SLO check, GitOps reconciliation and audit. Failed promotion does not imply rollback.

**DR:** verified PITR, restore rehearsal, replica lag/quorum, fencing, RPO/RTO, DNS and application cutover. Infrastructure redeployment is not database recovery.
