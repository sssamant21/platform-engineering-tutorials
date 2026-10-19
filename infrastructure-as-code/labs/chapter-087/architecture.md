# Chapter 087 — Ephemeral integration architecture

**Trust:** protected source -> unprivileged CI -> signed artifact -> exact-subject OIDC -> isolated test account -> bounded lease.

**Provision:** Terraform/OpenTofu, Pulumi, CloudFormation or Bicep with unique state, tags, run ID and TTL.

**Verify:** Terratest/native API assertions, Ansible Molecule converge/idempotence, Kubernetes admission/RBAC, Argo CD/Flux, database restore and SLO.

**Cleanup:** destroy -> cloud inventory check -> zero orphan resources -> credential revocation -> lease closure.

**Safety:** production targets forbidden, no shared state, no production secrets, no uncontrolled destructive tests.
