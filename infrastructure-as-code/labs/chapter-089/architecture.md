# Chapter 089 — Drift assurance architecture

**Desired state:** protected Git revision, module/provider pins, approved policy bundle.

**Observation:** read-only cloud inventory, Terraform/OpenTofu refresh, Kubernetes/GitOps status, DBRE backup/replication/SLO, trusted timestamp.

**Decision:** normalize, classify drift, verify target, owner, exception, risk, evidence freshness.

**Response:** notify low-risk; independently approve high-risk; quarantine destructive/unknown.

**Reconcile:** immutable plan, least privilege, canary, rollback and DBRE recovery checks.

**Audit:** trusted signed evidence, hash chain, immutable retention and exception closure.

**Boundary:** offline lab only models declarations; no actual cloud or DB inspection.
