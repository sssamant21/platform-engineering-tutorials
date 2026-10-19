# Chapter 092 — Enterprise drift detection architecture

**Desired:** protected Git commit, reviewed IaC config and policy.

**Managed:** versioned Terraform/OpenTofu/Pulumi/CloudFormation/Bicep state.

**Actual:** independently observed AWS/Azure/GCP inventory, Kubernetes/GitOps and DBRE state.

**Quality:** freshness, pagination completeness, read-only identity, provenance and evidence chain.

**Intelligence:** join actor, ticket, immutable source, time, exception, SLO and impact.

**Decision:** unknown/high-risk/destructive/database/identity/policy -> quarantine; eligible low-risk non-prod -> proposal only.

**Closure:** independent approval, controlled reconciliation, rollback, SLO/RPO/RTO, zero orphans and audit.

**Lab boundary:** all inputs are synthetic and do not call provider APIs.
