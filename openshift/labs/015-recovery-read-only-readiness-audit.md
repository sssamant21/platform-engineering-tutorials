# Lab 015 — Read-only Recovery Readiness Audit

**Status:** Documentation-only exercise; no OCP cluster execution recorded. **Time:** 20–25 minutes. **Baseline:** OCP 4.22; confirm exact installed release before applying any recovery procedure.

## Prerequisites and safety
Authorized `oc` CLI access, confirmed target context, read-only access to ClusterVersion, ClusterOperators, nodes and Infrastructure where permitted, and a sanitized backup inventory supplied by the backup owner. No access to raw snapshot files is needed. Do not run `cluster-backup.sh`, `cluster-restore.sh`, `oc config view --raw`, or read Secret objects. Stop on an unexpected cluster identity. These commands do not mutate cluster resources.

## Procedure — Linux/macOS (Bash)
```bash
oc whoami
oc config current-context
oc version
# Check authorization for the precise verb and resource before each read.
if [ "$(oc auth can-i get clusterversions.config.openshift.io --resource-name=version)" = yes ]; then
  oc get clusterversion version
else
  echo "SKIP: cannot get named ClusterVersion/version"
fi
if [ "$(oc auth can-i list clusteroperators.config.openshift.io)" = yes ]; then
  oc get clusteroperators
else
  echo "SKIP: cannot list ClusterOperators"
fi
if [ "$(oc auth can-i list nodes)" = yes ]; then
  oc get nodes -l node-role.kubernetes.io/master
else
  echo "SKIP: cannot list nodes"
fi
if [ "$(oc auth can-i get infrastructures.config.openshift.io --resource-name=cluster)" = yes ]; then
  oc get infrastructure cluster
else
  echo "SKIP: cannot get named Infrastructure/cluster"
fi
```

## Procedure — Windows PowerShell
```powershell
oc whoami
oc config current-context
oc version
if ((oc auth can-i get clusterversions.config.openshift.io --resource-name=version) -eq 'yes') {
  oc get clusterversion version
} else { Write-Output 'SKIP: cannot get named ClusterVersion/version' }
if ((oc auth can-i list clusteroperators.config.openshift.io) -eq 'yes') {
  oc get clusteroperators
} else { Write-Output 'SKIP: cannot list ClusterOperators' }
if ((oc auth can-i list nodes) -eq 'yes') {
  oc get nodes -l node-role.kubernetes.io/master
} else { Write-Output 'SKIP: cannot list nodes' }
if ((oc auth can-i get infrastructures.config.openshift.io --resource-name=cluster) -eq 'yes') {
  oc get infrastructure cluster
} else { Write-Output 'SKIP: cannot get named Infrastructure/cluster' }
```

Authorization queries can themselves fail (API unavailable or RBAC evaluation error). Treat any response other than an explicit `yes` as **not authorized/unknown** and skip the corresponding read; never auto-elevate. `get` on a named resource is different from `list` on a collection. Cluster-scoped access cannot be inferred from namespace access. The control-plane node selector may not expose nodes on hosted or managed topologies; record applicability rather than assuming a failure.

## Expected and failure observations
- `yes` only confirms the tested permission for the current identity; it does **not** certify backup rights or recoverability.
- `no` / `Error from server (Forbidden)`: record limited visibility and request approved access through the RBAC owner.
- API timeout / TLS failure: verify connectivity and approved client configuration; escalate before diagnosing backup health.
- Missing or stale backup inventory: mark readiness **unknown/failed evidence gate**; never fabricate success.
- Do not include tokens, kubeconfig, raw snapshots, Secret values, or unsanitized infrastructure identifiers in evidence.

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

**Pass criteria for documentation exercise:** distinguish etcd from PV/database backup, enumerate missing evidence, and route failures to correct owners. **Runtime pass** requires actual authorized output and independent review. No snapshot or restore operation is permitted in this lab. Any recovery action needs separate incident/change approval, release-specific supported procedure, data-owner sign-off, and explicit recovery/stop plan; an etcd restore is not a reversible rollback.

[Chapter 015](../chapters/015-etcd-backup-platform-and-application-recovery.md) · [Runbook](../runbooks/etcd-backup-recovery-readiness-triage.md)
