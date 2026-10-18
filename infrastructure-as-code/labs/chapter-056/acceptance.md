# Chapter 056 — OpenTofu Migration Acceptance

**Status: NOT ACCEPTED.** Local declared-evidence tests do not establish real backend or state compatibility.

| Gate | Points | Evidence | Reviewer | Status |
|---|---:|---|---|---|
| Architecture and compatibility inventory | 20 | Pending | Pending | Pending |
| State safety, locks, backup and rollback | 25 | Pending | Pending | Pending |
| Terraform/OpenTofu parity and migration | 15 | Pending | Pending | Pending |
| Security, identity, policy and CI | 15 | Pending | Pending | Pending |
| SRE/DBRE incidents and recovery | 15 | Pending | Pending | Pending |
| Governance, FinOps and change | 10 | Pending | Pending | Pending |

**Pass:** >=85/100 and zero critical failures. Require actual isolated state restore, exclusive lock verification, native-plan inspection, cloud/database validation and approvals.
