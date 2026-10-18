# Chapter 063 — Advanced Ansible SRE/DBRE Runbooks

## R1 Preflight
Pin Ansible, review inventory, list-hosts, --limit, serial, syntax, check mode, backups, SLO and approval.

## R2 Canary failure
Stop later batches; record changed hosts and root cause; reconcile partial configuration.

## R3 Delegation
Check actual delegate, variable context, credentials, delegate_facts and authorization.

## R4 Retry/async
Bound retries; inspect job IDs, timeout and side effects before retry.

## R5 Rescue semantics
Do not mask failures; assert post-rescue health and fail explicitly when unsafe.

## R6 DBRE rollout
Preserve quorum, replication, PITR, connection budget and SLO; use canary.

## R7 Secret incident
Revoke and rotate credentials; restrict logs/artifacts.

## R8 Recovery
Restore last-known-good configuration; audit changed hosts and recheck health.

## R9 Post-change
Verify idempotence, drift, monitoring, backup and handover.
