# Lab 015 — Read-only Recovery Readiness Audit

**Status:** Documentation-only exercise; no OCP cluster execution recorded. **Time:** 20–25 minutes.

## Prerequisites
Authorized `oc` CLI access, confirmed target context, read-only access to ClusterVersion, ClusterOperators and nodes where permitted, a sanitized backup inventory supplied by the backup owner. No access to raw snapshot files is needed.

## Procedure (Linux/macOS/PowerShell)
```sh
oc whoami
oc config current-context
oc version
oc auth can-i get clusterversion
oc auth can-i list clusteroperators
oc auth can-i list nodes
oc get clusterversion
oc get co
oc get nodes -l node-role.kubernetes.io/master
oc get infrastructure cluster
```
Stop on an unexpected cluster identity. The commands do not create, delete or mutate cluster resources. Do not run `oc config view --raw` or retrieve Secret objects.

## Expected and failure observations
- `yes` to authorization checks means only that the current identity has the tested permission; it does **not** certify backup rights or recoverability.
- `no` / `Forbidden`: record limited visibility and request approved access through RBAC owner.
- API timeout / TLS failure: verify connectivity and approved client configuration; escalate before diagnosing backup health.
- Missing or stale backup inventory: mark readiness **unknown/failed evidence gate**; never fabricate success.

## Evidence (sanitized)
| Field | Observation |
| --- | --- |
| Timestamp / reviewer | Not tested |
| Cluster alias / exact OCP release | Not tested |
| Platform and control-plane topology | Not tested |
| ClusterOperator health | Not tested |
| Last approved snapshot + static resources age | Owner attestation pending |
| Encrypted off-cluster retention and access review | Pending |
| Application/database restore evidence | Pending |
| RPO/RTO targets and measured rehearsal | Pending |
| Decision | Not certified |

**Pass criteria for documentation exercise:** distinguish etcd from PV/database backup, enumerate missing evidence, and route failures to correct owners. **Runtime pass** requires actual authorized output and independent review. No snapshot or restore operation is permitted in this lab.

[Chapter 015](../chapters/015-etcd-backup-platform-and-application-recovery.md) · [Runbook](../runbooks/etcd-backup-recovery-readiness-triage.md)
