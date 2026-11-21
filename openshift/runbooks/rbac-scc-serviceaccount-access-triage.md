# Runbook — RBAC, SCC and ServiceAccount Access Triage

**Severity:** security-sensitive | **Default mode:** read-only | **Audience:** platform on-call, security, application and DBRE | **Status:** draft.

## Trigger
A user receives `Forbidden`, an Operator/workload cannot access the API, or a pod is rejected for an SCC/securityContext violation.

## 1. Contain and identify
Record incident ID, time, affected namespace, sanitized error, impact and whether the failure began after a deployment or RBAC/SCC change. Confirm current cluster and context with `oc whoami` and `oc config current-context`. Never share bearer tokens, kubeconfig, Secret data or full admission logs containing credentials.

## 2. Classify
- **401 Unauthorized:** authentication/credential/identity provider problem; engage identity platform.
- **403 Forbidden:** authenticated but unauthorized for a specific verb/resource/scope; inspect bindings.
- **Pod admission denied:** inspect SCC requirements, workload service account, UID/SELinux strategy, privileged flags, capabilities, volumes and host access. A service account's API RBAC and pod SCC eligibility are different checks.
- **Running pod with API 403:** verify the pod's actual service account and namespace-specific bindings; do not assume the human deployer's permissions transfer to the pod.

## 3. Authorized diagnostics

**Prerequisites:** Use an approved, least-privileged incident identity with access to the affected namespace. Confirm the context and namespace before querying. `oc auth can-i` evaluates the current identity unless impersonation is explicitly authorized. Each collection read requires its own `list` permission; describing a named pod requires `get` on that pod. A denied or inconclusive check means **skip that read**, document the limitation and request the appropriate owner to collect evidence—never elevate privileges for triage.

Linux/macOS Bash (replace the placeholders locally; do not paste angle brackets into a shell):

```bash
NS="your-namespace"
POD="your-pod"
oc whoami
oc config current-context
for resource in rolebindings serviceaccounts events; do
  if [ "$(oc auth can-i list "$resource" -n "$NS" 2>/dev/null)" = "yes" ]; then
    oc get "$resource" -n "$NS"
  else
    printf 'SKIP %s: list not authorized or check failed\n' "$resource"
  fi
done
if [ "$(oc auth can-i get pods --resource-name="$POD" -n "$NS" 2>/dev/null)" = "yes" ]; then
  oc describe pod "$POD" -n "$NS"
else
  echo "SKIP named pod: get not authorized or check failed"
fi
```

Windows PowerShell:

```powershell
$Ns = "your-namespace"
$Pod = "your-pod"
oc whoami
oc config current-context
foreach ($Resource in @("rolebindings", "serviceaccounts", "events")) {
    $Allowed = oc auth can-i list $Resource -n $Ns 2>$null
    if ($LASTEXITCODE -eq 0 -and $Allowed -eq "yes") {
        oc get $Resource -n $Ns
    } else {
        Write-Output "SKIP $Resource: list not authorized or check failed"
    }
}
$Allowed = oc auth can-i get pods --resource-name=$Pod -n $Ns 2>$null
if ($LASTEXITCODE -eq 0 -and $Allowed -eq "yes") {
    oc describe pod $Pod -n $Ns
} else {
    Write-Output "SKIP named pod: get not authorized or check failed"
}
```

Expected authorization result is `yes` or `no`; API connectivity failures, expired credentials and `Forbidden` are **not** evidence of permission. Event and pod descriptions can contain sensitive values; minimize scope and redact before sharing. A namespace-scoped RoleBinding may reference a ClusterRole, but this does not itself grant cluster-wide access.

For designated security administrators **only**, separately check cluster-scoped permissions before running the matching reads:

```sh
oc auth can-i list clusterrolebindings
oc auth can-i get securitycontextconstraints.security.openshift.io --resource-name=restricted-v2
oc auth can-i use securitycontextconstraints.security.openshift.io --resource-name=restricted-v2
```

Run `oc get clusterrolebindings` only if the first result is `yes`; run `oc describe scc restricted-v2` only if the second is `yes`. The `use` result tests the current identity's authorization and is **not** proof that a particular workload will pass SCC admission. `oc adm policy who-can use scc restricted-v2` is an optional security-administrator diagnostic; its visibility and RBAC requirements must be validated on the target cluster before use. SCC RBAC grants, direct SCC users/groups and the actual workload admission outcome must be evaluated together. Do not treat a denied check as justification to add privileges.

## 4. Decision and ownership
- Identity provider/OAuth problem: identity team + platform on-call.
- Namespace RoleBinding missing or mis-scoped: application owner requests change; platform/security reviews and executes under least privilege.
- SCC admission conflict: application adjusts workload security context/image first; DBRE validates database image/UID/volume constraints; platform/security approves any exceptional SCC access.
- Cluster-wide privilege request: formal security exception, change record and time-bounded access review; never emergency-grant `cluster-admin` or `privileged` SCC merely to bypass a failed lab.

## 5. Approved remediation gates
Require cluster identity, exact target, before-state export stored securely, risk/impact assessment, least-privilege alternative, change window, approval, rollback owner and post-change test. Use an isolated namespace first. Changes to OAuth configuration or SCC policy may impact many workloads; no blanket rollback command is safe. For a newly created binding, rollback only that specific binding after confirming ownership and no other consumers.

## 6. Verification and closure
Verify only the intended subject gained the intended verb/resource/namespace access; confirm pod admission and application health without broadening privilege. Audit for unintended ClusterRoleBindings, SCC access, or token exposure. Record before/after authorization, incident timeline, reviewers and follow-up prevention. Do not label production-ready until an independent security/platform review and authorized runtime evidence exist.

References: [OCP 4.22 authentication/authorization](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/authentication_and_authorization/index), [RBAC](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/authentication_and_authorization/using-rbac), [Chapter 010](../chapters/010-authentication-rbac-scc-and-serviceaccounts.md).
