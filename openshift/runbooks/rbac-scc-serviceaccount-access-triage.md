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
```sh
oc auth can-i get pods -n <namespace>
oc get rolebindings -n <namespace>
oc get serviceaccounts -n <namespace>
oc describe pod <pod> -n <namespace>
oc get events -n <namespace> --sort-by=.metadata.creationTimestamp
```
For security administrators only, with appropriate privileges:
```sh
oc get clusterrolebindings
oc describe scc restricted-v2
oc adm policy who-can use scc restricted-v2
```
**Critical caveat:** SCC `who-can`/ `can-i` report RBAC grants only; `describe scc` reports direct SCC users/groups only. Correlate both before drawing conclusions. Restrict event output to the incident and redact before sharing.

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
