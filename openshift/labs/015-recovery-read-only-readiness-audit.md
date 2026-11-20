# Lab 015 — Read-only Recovery Readiness Audit

**Status:** Documentation-only exercise; no OCP cluster execution recorded. **Time:** 20–25 minutes. **Baseline:** OCP 4.22; confirm exact installed release before applying any recovery procedure.

## Prerequisites and safety
Authorized `oc` CLI access, a separately approved expected API server URL (non-secret) for identity pinning, confirmed target context, read-only access to ClusterVersion, ClusterOperators, nodes and Infrastructure where permitted, and a sanitized backup inventory supplied by the backup owner. No access to raw snapshot files is needed. Do not run `cluster-backup.sh`, `cluster-restore.sh`, `oc config view --raw`, or read Secret objects. Stop on an unexpected cluster identity. These commands do not mutate cluster resources.

## Procedure — Linux/macOS (Bash)
```bash
# Set EXPECTED_API_SERVER to the approved URL obtained out of band; do not guess.
: "${EXPECTED_API_SERVER:?STOP: expected API server URL is required}"
oc whoami >/dev/null || { echo "STOP: identity lookup failed" >&2; exit 1; }
oc config current-context >/dev/null || { echo "STOP: context lookup failed" >&2; exit 1; }
actual_server="$(oc config view --minify -o jsonpath='{.clusters[0].cluster.server}')" || { echo "STOP: API server lookup failed" >&2; exit 1; }
[ -n "$actual_server" ] && [ "$actual_server" = "$EXPECTED_API_SERVER" ] || { echo "STOP: API server mismatch or empty" >&2; exit 1; }
oc version || { echo "STOP: version lookup failed" >&2; exit 1; }
# Each authorization/read failure is surfaced; never infer success from a skipped check.
check_read() {
  local description="$1"; shift
  local permission="$1"; shift
  local answer rc
  answer="$(oc auth can-i $permission)" && rc=0 || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "UNKNOWN: authorization check failed for $description (exit $rc)" >&2
    return 1
  fi
  if [ "$answer" != "yes" ]; then
    echo "SKIP: $description (permission=$answer)"
    return 2
  fi
  if ! oc "$@"; then
    echo "ERROR: resource read failed for $description" >&2
    return 1
  fi
  return 0
}
# Only static, audited arguments are passed; no user-provided command strings.
failures=0
check_read 'ClusterVersion/version' 'get clusterversions.config.openshift.io --resource-name=version' get clusterversion version || { [ "$?" -eq 2 ] || failures=1; }
check_read 'ClusterOperators' 'list clusteroperators.config.openshift.io' get clusteroperators || { [ "$?" -eq 2 ] || failures=1; }
check_read 'control-plane nodes' 'list nodes' get nodes -l node-role.kubernetes.io/master || { [ "$?" -eq 2 ] || failures=1; }
check_read 'Infrastructure/cluster' 'get infrastructures.config.openshift.io --resource-name=cluster' get infrastructure cluster || { [ "$?" -eq 2 ] || failures=1; }
[ "$failures" -eq 0 ] || { echo 'INCOMPLETE: one or more authorization or resource queries failed' >&2; exit 1; }
echo 'Read-only checks completed; SKIP entries still require evidence review.'
```

## Procedure — Windows PowerShell
```powershell
# Set $ExpectedApiServer to the approved non-secret URL obtained out of band.
if ([string]::IsNullOrWhiteSpace($ExpectedApiServer)) { throw 'STOP: expected API server URL required' }
$null = oc whoami
if ($LASTEXITCODE -ne 0) { throw 'STOP: identity lookup failed' }
$null = oc config current-context
if ($LASTEXITCODE -ne 0) { throw 'STOP: context lookup failed' }
$actualServer = oc config view --minify -o 'jsonpath={.clusters[0].cluster.server}'
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($actualServer) -or $actualServer -ne $ExpectedApiServer) {
  throw 'STOP: API server lookup failed or server mismatch'
}
$null = oc version
if ($LASTEXITCODE -ne 0) { throw 'STOP: version lookup failed' }
function Invoke-ReadIfAuthorized {
  param([string]$Description, [string[]]$PermissionArgs, [string[]]$ReadArgs)
  $answer = & oc auth can-i @PermissionArgs
  $authExit = $LASTEXITCODE
  if ($authExit -ne 0) {
    Write-Error "UNKNOWN: authorization check failed for $Description (exit $authExit)" -ErrorAction Continue
    return 'ERROR'
  }
  if (($answer -join '').Trim() -cne 'yes') {
    Write-Output "SKIP: $Description (permission not confirmed)"
    return 'SKIP'
  }
  & oc @ReadArgs
  $readExit = $LASTEXITCODE
  if ($readExit -ne 0) {
    Write-Error "ERROR: resource read failed for $Description (exit $readExit)" -ErrorAction Continue
    return 'ERROR'
  }
  return 'OK'
}
$results = @(
  (Invoke-ReadIfAuthorized 'ClusterVersion/version' @('get','clusterversions.config.openshift.io','--resource-name=version') @('get','clusterversion','version'))
  (Invoke-ReadIfAuthorized 'ClusterOperators' @('list','clusteroperators.config.openshift.io') @('get','clusteroperators'))
  (Invoke-ReadIfAuthorized 'control-plane nodes' @('list','nodes') @('get','nodes','-l','node-role.kubernetes.io/master'))
  (Invoke-ReadIfAuthorized 'Infrastructure/cluster' @('get','infrastructures.config.openshift.io','--resource-name=cluster') @('get','infrastructure','cluster'))
)
if ($results -contains 'ERROR') { throw 'INCOMPLETE: one or more authorization or resource queries failed' }
Write-Output 'Read-only checks completed; SKIP entries still require evidence review.'
```

The expected server must be supplied from a trusted change record, not discovered from the same kubeconfig being checked. Do not print server URLs in shared evidence. These preflights verify client context identity only; they do not establish that a backup is valid.

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
