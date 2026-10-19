# Chapter 087 — Integration testing acceptance

**NOT ACCEPTED:** 105 offline Python tests authored, execution not verified; native Terratest/Molecule/cloud and real database restore pending.

| Domain | Points | Evidence |
|---|---:|---|
| Architecture, isolation and security | 15 | Pending |
| Terraform/OpenTofu/Terratest and multi-cloud | 20 | Pending |
| Molecule, Kubernetes and GitOps | 20 | Pending |
| Offline labs, negative tests and lifecycle | 20 | Authored, not executed |
| DBRE recovery and SLO | 15 | Pending |
| Cost, cleanup, audit and runbooks | 10 | Pending |
| **Total** | **100** | **Not accepted** |

Pass >=85 with no critical failure. Require real ephemeral cloud account, Terratest/Molecule runs, native cloud resource assertions, measured RPO/RTO, DB restore, zero orphan inventory, cost and signed SRE/DBRE/security approval.
