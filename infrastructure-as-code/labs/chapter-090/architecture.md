# Chapter 090 — Enterprise reliability acceptance architecture

**Source:** protected Git, immutable artifact, signed provenance and independently reviewed changes.

**Testing:** static/unit/policy -> isolated Terraform/OpenTofu/Terratest/Molecule -> cloud/K8s/GitOps native assertions.

**Assurance:** policy enforcement, read-only drift, bounded exceptions, DBRE restore and SLO.

**Remediation:** quarantine unknown/high risk; independent approval; canary, rollback, zero orphan cleanup.

**Audit:** trusted native source, timestamps, signed chain, immutable retention and independent acceptance.

**Boundary:** Python labs validate self-declared synthetic evidence only; no native execution.
