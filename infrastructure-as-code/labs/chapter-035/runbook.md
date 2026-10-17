# Chapter 035 — SRE/DBRE operational runbooks

## Release and promotion
1. Inventory root modules, source revisions, owners and isolated backend identities.
2. Verify immutable source provenance, code review, contract compatibility and provider lockfile.
3. Run `bash run-preflight.sh` and retain CI logs/commit hashes.
4. Create disposable dev plan; inspect delete/replacement actions and drift.
5. Verify staging with separate state and least-privilege credentials.
6. Obtain DBRE backup/PITR and change approval for stateful production resources.
7. Apply only reviewed plan under backend lock; verify runtime SLO, replication and backup.
8. Record evidence in acceptance.md; mark incomplete gates pending.

## Failed quality gate
Freeze release. Reproduce with pinned toolchain. Inspect module contracts, dependency cycles, source SHA, plan and failed negative test. Fix the cause; never disable a gate to force success.

## Unexpected replacement
Freeze deployment; capture sanitized plan, current state version and approved backup. Determine whether address changes need `moved` blocks, provider arguments changed, or resource recreation is unavoidable. Obtain DBRE approval and validated recovery plan before proceeding.

## Post-deploy DB incident
Stop concurrent applies; preserve evidence; verify state lock, service endpoints, database health, replication and backup. Escalate to DBRE. Use a reviewed forward-fix or compatible release; a Git revert does not restore database data.

## Supply-chain compromise
Quarantine module release, revoke publishing credentials, inventory consumers, pin reviewed commit, rotate exposed secrets, inspect IAM/state access and file incident RCA.

## Disaster recovery
Restore Terraform state only via approved backend controls, and restore actual data independently. Validate RPO/RTO, drift, service health and consistency before reopening deployments.
