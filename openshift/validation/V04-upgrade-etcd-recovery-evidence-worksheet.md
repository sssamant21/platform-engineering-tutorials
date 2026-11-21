# V04 — OCP 4.22 Upgrade and etcd Recovery Evidence Worksheet (Draft)

**Status:** documentation-only template; NOT executed, lab-tested, independently reviewed or production-approved. Use alongside [V03 change review matrix](V03-high-risk-change-review-matrix.md), Chapter 014 (upgrade) and Chapter 015 (etcd backup/recovery). This is an evidence worksheet, not an executable recovery runbook.

## Scope and prerequisite gate

- Record cluster identifier **without** copying kubeconfig, tokens, certificates or credentials; environment (isolated lab/staging/production); OCP version; platform (bare metal/vSphere/cloud); control-plane topology; change ticket; named platform owner, SRE/DBRE reviewer and business owner.
- Confirm the *installed* OCP release and supported upgrade graph with Red Hat's 4.22 documentation and the cluster's available update recommendations. Do not infer an upgrade path from the target version alone.
- Record current cluster health before proposing any change. Collect only metadata approved for the evidence store; redact internal addresses, usernames and sensitive annotations.
- Require an approved maintenance window, verified recent restore-capable backups, storage capacity, incident communications, and a documented stop/escalation decision. A backup file existing is not proof of a successful restore.

## Read-only evidence capture (authorized operator)

Run each command only if its resource permission is granted. These are **examples for an approved diagnostic session**, not claims of execution:

```sh
# Linux/macOS — evaluate authorization separately for each read.
# Abort the session if the client cannot establish authenticated identity.
if ! oc whoami >/dev/null; then
  echo "STOP: authentication or API connectivity failed" >&2
  exit 1
fi
# Verify the expected cluster/context against the approved inventory before proceeding.
[ -n "${EXPECTED_CONTEXT:-}" ] || { echo 'STOP: EXPECTED_CONTEXT not supplied from approved inventory' >&2; exit 1; }
actual_context=$(oc config current-context) || { echo 'STOP: unable to determine active context' >&2; exit 1; }
[ "$actual_context" = "$EXPECTED_CONTEXT" ] || { echo 'STOP: active context does not match approved inventory' >&2; exit 1; }
# Context names are local labels; also pin the expected API endpoint from inventory.
[ -n "${EXPECTED_SERVER:-}" ] || { echo 'STOP: EXPECTED_SERVER not supplied from approved inventory' >&2; exit 1; }
actual_server=$(oc config view --minify -o jsonpath='{.clusters[0].cluster.server}') || { echo 'STOP: unable to determine API endpoint' >&2; exit 1; }
[ -n "$actual_server" ] && [ "$actual_server" = "$EXPECTED_SERVER" ] || { echo 'STOP: API endpoint mismatch or empty endpoint' >&2; exit 1; }
oc version >/dev/null || { echo "STOP: version query failed" >&2; exit 1; }
if ! authorization=$(oc auth can-i get clusterversions.config.openshift.io --resource-name=version); then
  echo 'STOP: authorization API check failed; evidence incomplete' >&2; exit 1
fi
case "$authorization" in
  yes)
  oc get clusterversion version || { echo 'STOP: authorized diagnostic read failed' >&2; exit 1; }
  no) echo "SKIP: named ClusterVersion read not authorized" ;;
  *) echo 'STOP: ambiguous authorization response' >&2; exit 1 ;;
esac
if ! authorization=$(oc auth can-i list clusteroperators.config.openshift.io); then
  echo 'STOP: authorization API check failed; evidence incomplete' >&2; exit 1
fi
case "$authorization" in
  yes)
  oc get clusteroperators || { echo 'STOP: authorized diagnostic read failed' >&2; exit 1; }
  no) echo "SKIP: ClusterOperator inventory not authorized" ;;
  *) echo 'STOP: ambiguous authorization response' >&2; exit 1 ;;
esac
if ! authorization=$(oc auth can-i list nodes); then
  echo 'STOP: authorization API check failed; evidence incomplete' >&2; exit 1
fi
case "$authorization" in
  yes)
  oc get nodes || { echo 'STOP: authorized diagnostic read failed' >&2; exit 1; }
  no) echo "SKIP: node inventory not authorized" ;;
  *) echo 'STOP: ambiguous authorization response' >&2; exit 1 ;;
esac
if ! authorization=$(oc auth can-i list machineconfigpools.machineconfiguration.openshift.io); then
  echo 'STOP: authorization API check failed; evidence incomplete' >&2; exit 1
fi
case "$authorization" in
  yes)
  oc get machineconfigpools || { echo 'STOP: authorized diagnostic read failed' >&2; exit 1; }
  no) echo "SKIP: MachineConfigPool inventory not authorized" ;;
  *) echo 'STOP: ambiguous authorization response' >&2; exit 1 ;;
esac
```

```powershell
# Windows PowerShell — separate authorization gates; no privilege escalation.
oc whoami | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'STOP: authentication or API connectivity failed' }
# Compare the active context to the approved cluster inventory before proceeding.
if ([string]::IsNullOrWhiteSpace($env:EXPECTED_CONTEXT)) { throw 'STOP: EXPECTED_CONTEXT not supplied from approved inventory' }
$actualContext = oc config current-context
if ($LASTEXITCODE -ne 0) { throw 'STOP: unable to determine active context' }
if ($actualContext.Trim() -ne $env:EXPECTED_CONTEXT) { throw 'STOP: active context does not match approved inventory' }
if ([string]::IsNullOrWhiteSpace($env:EXPECTED_SERVER)) { throw 'STOP: EXPECTED_SERVER not supplied from approved inventory' }
$actualServer = oc config view --minify -o "jsonpath={.clusters[0].cluster.server}"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($actualServer)) { throw 'STOP: unable to determine API endpoint' }
if ($actualServer.Trim() -cne $env:EXPECTED_SERVER) { throw 'STOP: API endpoint mismatch' }
oc version | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'STOP: version query failed' }
$authorization = oc auth can-i get clusterversions.config.openshift.io --resource-name=version
if ($LASTEXITCODE -ne 0) { throw 'STOP: authorization check failed; evidence incomplete' }
if ($authorization -eq 'yes') {
    oc get clusterversion version
    if ($LASTEXITCODE -ne 0) { throw 'STOP: authorized diagnostic read failed' }
} elseif ($authorization -eq 'no') { Write-Output 'SKIP: named ClusterVersion read not authorized' } else { throw 'STOP: ambiguous authorization response; evidence incomplete' }
$authorization = oc auth can-i list clusteroperators.config.openshift.io
if ($LASTEXITCODE -ne 0) { throw 'STOP: authorization check failed; evidence incomplete' }
if ($authorization -eq 'yes') {
    oc get clusteroperators
    if ($LASTEXITCODE -ne 0) { throw 'STOP: authorized diagnostic read failed' }
} elseif ($authorization -eq 'no') { Write-Output 'SKIP: ClusterOperator inventory not authorized' } else { throw 'STOP: ambiguous authorization response; evidence incomplete' }
$authorization = oc auth can-i list nodes
if ($LASTEXITCODE -ne 0) { throw 'STOP: authorization check failed; evidence incomplete' }
if ($authorization -eq 'yes') {
    oc get nodes
    if ($LASTEXITCODE -ne 0) { throw 'STOP: authorized diagnostic read failed' }
} elseif ($authorization -eq 'no') { Write-Output 'SKIP: node inventory not authorized' } else { throw 'STOP: ambiguous authorization response; evidence incomplete' }
$authorization = oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
if ($LASTEXITCODE -ne 0) { throw 'STOP: authorization check failed; evidence incomplete' }
if ($authorization -eq 'yes') {
    oc get machineconfigpools
    if ($LASTEXITCODE -ne 0) { throw 'STOP: authorized diagnostic read failed' }
} elseif ($authorization -eq 'no') { Write-Output 'SKIP: MachineConfigPool inventory not authorized' } else { throw 'STOP: ambiguous authorization response; evidence incomplete' }
```

**Prerequisites:** a configured `oc` client and kubeconfig for the intended cluster, permission to perform self-authorization checks, and an approved diagnostic scope. Confirm the active context and cluster identity through an approved inventory before running these commands. Do not publish raw `oc whoami`, server addresses, or unredacted JSON. The snippets intentionally avoid `oc get ... -o json` to minimize accidental collection of sensitive metadata.

**Context and endpoint gate:** The commands intentionally stop for failed authentication and require both `EXPECTED_CONTEXT` and `EXPECTED_SERVER` (exact API server URL including scheme and port, if any) from independently approved inventory. A matching local context name alone does not establish cluster identity. The examples compare the kubeconfig API endpoint without printing it; this does not cryptographically attest cluster identity and depends on trusted kubeconfig and TLS verification. Never use `--insecure-skip-tls-verify` to bypass a mismatch. Do **not** continue if the context is unknown, unexpected, or cannot be independently confirmed. `oc version` and subsequent reads also require exit-code review; a successful authorization check does not guarantee the following read succeeds. The Bash example uses `exit 1` and is intended to run as a standalone script, not pasted into a shared interactive shell without adapting that behavior.

**Failure handling:** `no`, `Forbidden`, an empty/failed authorization response, or an API/network error means **do not treat the read as authorized**. A failed `oc get` must also be recorded and escalated, not interpreted as an empty healthy inventory. Both Bash and PowerShell now stop on authorization API errors and ambiguous responses; only an explicit `no` skips a resource read. Do not treat a failed authorization query as a denial or as healthy evidence. The PowerShell example explicitly stops when an authorization check exits nonzero; an explicit `no` remains a skip. An authorized read or version query that fails terminates the standalone preflight with nonzero status; do not continue to subsequent reads or mark the evidence healthy. These examples have **not been executed against an OCP cluster**.

Record timestamp (UTC), sanitized output path, command exit code, and reviewer for each observation. Expected healthy signals include stable cluster version conditions, available/non-degraded Operators and ready nodes; do not equate these broad signals with full application health. Document every anomalous condition rather than silently accepting it.

## Upgrade review gates (Chapter 014)

| Gate | Evidence required | Decision |
| --- | --- | --- |
| Version and path | Installed version, target, supported graph, release notes and known issues | PASS / HOLD |
| Platform readiness | Operator conditions, node/MCP health, capacity, critical workloads and disruption budgets | PASS / HOLD |
| Recovery readiness | Supported backups, restore rehearsal evidence, owner and RPO/RTO | PASS / HOLD |
| Change approval | Named change authority, maintenance window, rollback/contingency plan and communications | PASS / HOLD |
| Post-change | Cluster version, Operators, nodes, routes, storage and application SLO checks | PASS / HOLD |

**Stop conditions:** degraded critical Operators, unready control-plane nodes, unresolved MCP rollout, missing restore evidence, unsupported upgrade path or absent approval. Upgrades are not assumed to support a simple downgrade; use Red Hat's release-specific recovery guidance and escalate before attempting any reversal.

## etcd backup and recovery gates (Chapter 015)

- Confirm the official OCP 4.22 procedure appropriate to the platform/topology and the exact release. Capture the official documentation URL and access date in the change ticket.
- Record backup timestamp, storage location (reference only), encryption/access controls, retention, restore test date, and measured RPO/RTO. Never commit snapshot archives, keys, kubeconfigs or credential-bearing output.
- Identify control-plane quorum, failure domain, static-pod/revision implications, and dependency impact. **Do not run backup/restore, node replacement, force quorum, or control-plane changes from this worksheet.**
- Require explicit incident commander and platform owner authorization plus an independent reviewer before any recovery operation. Confirm fencing/single-writer requirements where applicable.
- Restore execution must use an approved, version-matched Red Hat runbook in an isolated rehearsal first. Record failure cases and independent acceptance of post-restore cluster and application consistency.

## Evidence record

| Field | Value |
| --- | --- |
| UTC timestamp / change ID | PENDING |
| Cluster/version/topology (sanitized) | PENDING |
| Read-only authorization and output checks | NOT RUN |
| Upgrade support/path verification | NOT REVIEWED |
| Backup/restore rehearsal reference | NOT PROVIDED |
| Independent technical reviewer | PENDING |
| Platform/change approval | PENDING |
| Runtime/lab status | NOT TESTED |
| Production acceptance | NOT APPROVED |

## Authoritative references

- [Red Hat OpenShift Container Platform 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [OCP 4.22 Updating clusters](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/updating_clusters/index)
- [OCP 4.22 Backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/index)

**Validation boundary:** Links and exact version-specific commands must be checked against live official documentation before operational use; no cluster access or official release-specific command certification is claimed here.
