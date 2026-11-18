# Chapter 010 — Authentication, RBAC, SCC and ServiceAccounts

**Audience:** Platform admins, SREs, DBREs | **Duration:** 60 minutes | **Reference:** OCP 4.22 | **Status:** Draft; not cluster-validated.

## Learning outcomes
Distinguish authentication from authorization and SCC admission; inventory effective namespace permissions; trace a workload's service account; recognize privilege escalation; and prepare an auditable access change.

## 60-minute agenda
- 0–10: identity provider, OAuth, users/groups and authentication boundaries
- 10–25: Roles, ClusterRoles, RoleBindings and ClusterRoleBindings
- 25–40: SCC, namespace UID ranges, Pod admission and service accounts
- 40–55: [Read-only Lab 010](../labs/010-security-rbac-scc-read-only-audit.md)
- 55–60: scenario review and escalation

## Model
1. **Authentication:** an identity provider authenticates a user; OpenShift OAuth integrates identity and access. Do not expose tokens, cookies, kubeconfig or Secret contents.
2. **Authorization:** RBAC checks a subject, verb, resource and scope. A RoleBinding can reference a ClusterRole while limiting the grant to its namespace; a ClusterRoleBinding grants cluster-wide scope. A user's groups and all applicable bindings matter. `oc auth can-i` checks effective authorization for the current identity; impersonation (`--as` / `--as-group`) requires explicit permission and is not a workaround for access denial.
3. **Pod admission:** OpenShift Security Context Constraints (SCCs) govern allowed pod security settings, including UID, privilege, host access, capabilities and volumes. RBAC alone does not prove a pod will be admitted. Namespace UID-range and SELinux allocation may matter. `restricted-v2` is generally the baseline; do not assume every workload is admitted under it.
4. **Service accounts:** each workload should use a purpose-specific namespace service account where API access is needed. A service account is `system:serviceaccount:<namespace>:<name>`. In OCP 4.22 newly created service accounts do not automatically receive long-lived API token Secrets (change introduced in 4.16); do not create long-lived credentials for labs. Avoid broad bindings to `system:serviceaccounts` or `system:authenticated`.
5. **SCC visibility caveat:** `oc auth can-i use scc/<name>` and `oc adm policy who-can use scc <name>` evaluate RBAC grants, not users/groups listed directly in the SCC. `oc describe scc` shows direct SCC entries, not RBAC grants. Combine evidence; neither command alone proves the full set of users allowed to use an SCC.

## Safe inspection (no mutation)
Prerequisites: approved read access to a test namespace, `oc` compatible with cluster, confirmed identity and context. Some commands below need additional permissions; a Forbidden response is a finding, not a reason to escalate credentials.

```sh
oc whoami
oc config current-context
oc version
oc auth can-i list rolebindings -n <namespace>
oc auth can-i list serviceaccounts -n <namespace>
oc auth can-i get deployments -n <namespace>
oc auth can-i list pods -n <namespace>
oc auth can-i create rolebindings -n <namespace>
# Execute each following read only if its matching check above returned yes.
oc get rolebindings -n <namespace>
oc get serviceaccounts -n <namespace>
oc get deployment <deployment> -n <namespace> -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}'
oc get pods -n <namespace> -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName,SCC:.metadata.annotations.openshift\.io/scc
```

For an authorized security administrator only (each read requires its own permission check):
```sh
oc auth can-i list clusterrolebindings
oc auth can-i list securitycontextconstraints.security.openshift.io
oc auth can-i get securitycontextconstraints.security.openshift.io/restricted-v2
# Run only the individually authorized reads:
oc get clusterrolebindings
oc get scc
oc describe scc restricted-v2
# who-can may require additional RBAC inspection rights; if denied, stop and escalate.
oc adm policy who-can use scc restricted-v2
```
A `no` response or `Forbidden` error means skip that read, record the denied verb/resource/scope and request authorized review; never elevate permissions simply to complete the lab. `get` of a named Deployment or SCC does not authorize `list` of a collection. The `create rolebindings` check is an authorization assessment only and does not create anything.
Do not collect full service-account YAML or pod environment variables into shared evidence; these can expose sensitive references or values.

**Windows PowerShell:** commands above work in PowerShell; replace angle-bracket placeholders with real names *without* typing the brackets. For a clean pod report, use `oc get pods -n $Namespace -o custom-columns='NAME:.metadata.name,SA:.spec.serviceAccountName,SCC:.metadata.annotations.openshift\.io/scc'`. Quote JSONPath arguments as shown.

## Approval-only change example (NOT part of lab)
Granting a dedicated service account read access is a namespace-scoped change. Requires ticket, data/application owner approval, security review, pre-change RBAC evidence, expiry/review date and rollback owner:
```sh
# NON-PRODUCTION EXAMPLE ONLY — DO NOT RUN WITHOUT CHANGE APPROVAL
oc adm policy add-role-to-user view -z app-reader -n <namespace>
# Approved rollback after verifying this binding was created for the change:
# oc delete rolebinding <specific-new-binding> -n <namespace>
```
Do not delete an existing shared binding as a rollback. Capture the precise binding name and prior state first. Do not grant `cluster-admin`, `privileged` SCC, `anyuid` SCC or broad group permissions to fix an application failure without a formal security exception.

## Production scenario: database pod rejected by SCC
A PostgreSQL pod requests a fixed UID, hostPath or elevated capabilities and admission fails. First check the sanitized admission event, workload service account, namespace UID allocation and SCC constraints. Prefer adjusting the image/pod to run within allowed security boundaries. A privileged SCC grant may bypass controls and introduce host compromise risk. DBRE owns database runtime requirements; application team owns manifest/image changes; platform/security own SCC policy and approvals. For details use [Security admission triage](../runbooks/rbac-scc-serviceaccount-access-triage.md).

## Acceptance and evidence
Pass documentation review only after command syntax, OCP minor-version behavior, scope and RBAC caveats are checked. Lab evidence requires timestamp, sanitized cluster version, namespace, actor role, expected/actual result and reviewer; no tokens or Secrets. No live test or independent production approval has been performed.

## Authoritative references
- [OCP 4.22 authentication and authorization](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/authentication_and_authorization/index)
- [OCP 4.22 RBAC](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/authentication_and_authorization/using-rbac)
- [Kubernetes administration prerequisite](../../kubernetes/README.md)
