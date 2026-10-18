# Chapter 048 — GCP Security Acceptance

**Status: NOT ACCEPTED.** Offline contracts and authored tests do not prove live IAM, KMS or secret recovery.

| Gate | Points | Evidence | Reviewer | Status |
|---|---:|---|---|---|
| IAM hierarchy, deny, least privilege | 20 | Pending | Pending | Pending |
| WIF, service accounts, identity recovery | 20 | Pending | Pending | Pending |
| KMS, CMEK, Secret Manager, protected state | 20 | Pending | Pending | Pending |
| Terraform and automated negative tests | 15 | Pending | Pending | Pending |
| SRE/DBRE incidents and recovery | 15 | Pending | Pending | Pending |
| Audit, monitoring, cost and approvals | 10 | Pending | Pending | Pending |

**Pass:** >=85/100 and zero critical failures. Attach sanitized CI logs, reviewed plan, effective IAM/WIF evidence, CMEK restore test, secret rotation proof, state access audit and DBRE/Security sign-off.
