# Chapter 077 — Terraform/OpenTofu CI/CD runbooks

1. **Provenance:** Verify protected branch, commit, provider lockfile, runner digest and reviews.
2. **Identity:** Verify OIDC audience/subject, account/subscription/project and token expiry.
3. **Backend:** Preserve encrypted checkpoint; identify active lock owner; do not force-unlock blindly.
4. **Plan:** Inspect detailed exit code, saved plan, JSON, resource replacement and digest binding.
5. **Approvals:** Require independent SRE, security and DBRE approval for stateful changes.
6. **DBRE:** Verify PITR, backup checksums, replica quorum, restore drill, RPO and RTO.
7. **Partial apply:** Freeze later stages; capture logs and resource reality before recovery.
8. **GitOps:** Reconcile controller ownership; avoid conflicting Kubernetes writers.
9. **Canary:** Stop promotion on error-budget burn, lag or latency regression.
10. **Handover:** Archive change ticket, signed plan, approvals, metrics and recovery evidence.
