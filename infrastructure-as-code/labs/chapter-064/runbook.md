# Chapter 064 — Ansible Security, Vault and Inventory Runbooks

## R1 Inventory preflight
Review dynamic source, account/tenant/region, owner, host count, cache, list-hosts and --limit.

## R2 Vault incident
Stop execution, revoke vault identities, rotate secrets, audit access and re-encrypt.

## R3 CI identity
Revoke OIDC/runner trust, quarantine artifacts, restore signed runner.

## R4 Supply chain
Pin and verify collection and role digests; block untrusted dependencies.

## R5 Privilege escalation
Audit become rules, SSH identity and task scope; remove excess permissions.

## R6 DBRE rollout
Verify PITR, backup, replication/quorum, connection budget and SLO; canary and approval.

## R7 Secret leak
Restrict logs, revoke/rotate credentials, fix no_log and callback settings.

## R8 Cross-tenant inventory
Freeze execution, preserve snapshot, reconcile ownership and change approval.

## R9 Post-change
Verify host state, SLO, backup, drift, credential audit and handover.
