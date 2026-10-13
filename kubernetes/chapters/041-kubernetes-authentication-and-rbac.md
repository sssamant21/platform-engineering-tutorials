# Chapter 041 — Kubernetes Authentication and RBAC

**Track:** Kubernetes Administration · **Part 09 — Kubernetes Security**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers, Kubernetes administrators  
**Prerequisites:** Chapters 011–015, 036–040; kubectl, Windows PowerShell, isolated cluster with permissions to manage RBAC and impersonate lab identities

## 1. Production scenario

An application team reports `Forbidden` errors when reading Pod logs, while a service account in the same namespace can unexpectedly list Secrets. During incident response, the SRE must identify the authenticated principal, trace authorization grants, restore only the required access and eliminate excessive permissions without interrupting other workloads.

This chapter teaches how Kubernetes API authentication, authorization and admission interact, with a reproducible least-privilege lab. **RBAC permissions are additive**: a narrow Role does not override permissions granted by another RoleBinding or ClusterRoleBinding.

### Learning objectives

1. Explain Kubernetes authentication, authorization and admission.
2. Distinguish human identities, groups and workload ServiceAccounts.
3. Create namespaced Roles and ClusterRoles with scoped permissions.
4. Bind roles to subjects and validate access with `kubectl auth can-i`.
5. Investigate Forbidden responses and effective permissions.
6. Detect excessive Secret access and safely remove the offending binding.
7. Produce a production RBAC review and incident-response acceptance report.

## 2. Request authorization flow

```text
kubectl / controller / application
          |
      TLS to API server
          |
   Authentication (Who?)
    certificate / OIDC / token
          |
   Authorization (Allowed?)
      RBAC / configured modes
          |
    Admission controls
     validation / mutation
          |
      API operation
```

**Authentication** establishes a user or ServiceAccount identity. **Authorization** determines whether that identity may perform an action on a resource. **Admission** can validate or mutate requests after authorization. Network reachability to the API server is not equivalent to authorization.

Common managed-cluster authentication integrations include cloud identity providers and Kubernetes OIDC support. Kubernetes RBAC governs Kubernetes API permissions, not necessarily cloud IAM permissions, underlying node access or permissions inside an application.

## 3. RBAC objects and scope

| Resource | Scope | Purpose |
|---|---|---|
| Role | Namespace | Rules for resources in one namespace |
| ClusterRole | Cluster | Rules reusable across namespaces or for cluster-scoped resources |
| RoleBinding | Namespace | Grants a Role or ClusterRole within a namespace |
| ClusterRoleBinding | Cluster | Grants a ClusterRole across the cluster |
| ServiceAccount | Namespace | Workload identity represented to Kubernetes API |

RBAC rules specify `apiGroups`, `resources`, `verbs` and optionally `resourceNames` or non-resource URLs. `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`, `deletecollection`, `bind`, `escalate` and `impersonate` have distinct implications.

A RoleBinding can refer to a ClusterRole and constrain its grant to the binding's namespace. A ClusterRoleBinding grants cluster-wide permissions described by its ClusterRole, including applicable namespaced resources.

**Dangerous patterns:** wildcards (`*`), broad access to Secrets, Pod creation, `pods/exec`, `pods/attach`, `serviceaccounts/token`, impersonation, and RBAC modification. A principal able to create Pods may indirectly access Secrets and ServiceAccount identities within that namespace.

## 4. Lab safety and prerequisites

Use a disposable cluster. Impersonation checks require the caller to have `impersonate` permission; on managed clusters this may be unavailable. If impersonation is denied, record the limitation rather than modifying production RBAC to enable it.

```powershell
kubectl config current-context
kubectl get nodes
kubectl auth can-i create namespaces
kubectl auth can-i create roles -n default
kubectl auth can-i impersonate serviceaccounts -n default
kubectl create namespace ch041
```

The labs create only namespaced resources. Do not change built-in `cluster-admin` bindings or provider-managed identities.

## 5. Lab 1 — Inspect current identity and permissions

```powershell
kubectl config current-context
kubectl config view --minify
kubectl auth whoami
kubectl auth can-i get pods -n ch041
kubectl auth can-i list secrets -n ch041
kubectl auth can-i --list -n ch041
```

**Expected:** the output identifies your current API identity and effective permissions, subject to cluster configuration. `kubectl auth whoami` requires a compatible kubectl/API version. Avoid copying client certificate material, tokens or kubeconfig credentials into incident notes.

Explain the difference between a successful login and permission to perform an API operation.

## 6. Lab 2 — Create a least-privilege reader ServiceAccount and Role

Save `ch041-reader.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: incident-reader
  namespace: ch041
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-observer
  namespace: ch041
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: incident-reader-pod-observer
  namespace: ch041
subjects:
  - kind: ServiceAccount
    name: incident-reader
    namespace: ch041
roleRef:
  kind: Role
  name: pod-observer
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply -f .\ch041-reader.yaml
kubectl -n ch041 get serviceaccount,role,rolebinding
kubectl -n ch041 describe role pod-observer
kubectl -n ch041 describe rolebinding incident-reader-pod-observer
```

**Expected:** namespaced read access to Pods, logs, events and selected workload metadata; no write access or Secret read access. `automountServiceAccountToken: false` avoids automatically mounting a token in Pods using this ServiceAccount; it does not prevent API-side impersonation checks.

## 7. Lab 3 — Verify effective permissions with impersonation

```powershell
$sa = "system:serviceaccount:ch041:incident-reader"
kubectl auth can-i get pods -n ch041 --as=$sa
kubectl auth can-i get pods --subresource=log -n ch041 --as=$sa
kubectl auth can-i list deployments.apps -n ch041 --as=$sa
kubectl auth can-i delete pods -n ch041 --as=$sa
kubectl auth can-i list secrets -n ch041 --as=$sa
kubectl auth can-i get pods -n default --as=$sa
```

**Expected:** `yes` for allowed namespaced reads; `no` for Pod deletion, Secret listing and access in `default`, provided no other grants exist. If the request itself returns an impersonation `Forbidden`, the **caller** lacks permission to impersonate; this does not prove the ServiceAccount has or lacks the tested permission.

`kubectl auth can-i --list --as=$sa -n ch041` can be useful, but evaluate sensitive privileges with explicit resource/verb checks as well.

## 8. Lab 4 — Diagnose a Forbidden response

Create a disposable Pod for log inspection:

```powershell
kubectl -n ch041 run log-source --image=busybox:1.36 --restart=Never -- sh -c "echo ch041-log-ready; sleep 36000"
kubectl -n ch041 wait --for=condition=Ready pod/log-source --timeout=120s
kubectl -n ch041 logs log-source
```

Now attempt a prohibited action with the lab ServiceAccount identity:

```powershell
kubectl -n ch041 delete pod log-source --as=$sa
```

**Expected:** a `Forbidden` error (or an impersonation authorization failure if the caller lacks impersonation rights). The Pod must remain running if RBAC denied deletion.

Investigate:

```powershell
kubectl auth can-i delete pods -n ch041 --as=$sa
kubectl -n ch041 describe role pod-observer
kubectl -n ch041 describe rolebinding incident-reader-pod-observer
kubectl -n ch041 get pod log-source
```

Do not grant `delete pods` merely to suppress a Forbidden error; first establish the legitimate operational requirement.

## 9. Lab 5 — Demonstrate RoleBinding to ClusterRole without cluster-wide grant

Kubernetes commonly includes an aggregated, built-in `view` ClusterRole. Confirm its existence:

```powershell
kubectl get clusterrole view
```

Save `ch041-view-binding.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: incident-reader-view
  namespace: ch041
subjects:
  - kind: ServiceAccount
    name: incident-reader
    namespace: ch041
roleRef:
  kind: ClusterRole
  name: view
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply -f .\ch041-view-binding.yaml
kubectl auth can-i list configmaps -n ch041 --as=$sa
kubectl auth can-i list configmaps -n default --as=$sa
kubectl auth can-i list secrets -n ch041 --as=$sa
```

**Expected on a standard cluster:** ConfigMap listing is allowed in `ch041`, not in `default`, and Secret listing remains denied. The built-in `view` role generally excludes Secret access, but inspect the actual ClusterRole rules because aggregation or distribution customization can change them.

Remove this additional binding before the next exercise to isolate its effects:

```powershell
kubectl -n ch041 delete rolebinding incident-reader-view
```

## 10. Lab 6 — Detect and remove an excessive Secret grant

This lab deliberately creates an overprivileged Role in the **disposable** namespace.

Save `ch041-excessive.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: excessive-secret-reader
  namespace: ch041
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: accidental-secret-grant
  namespace: ch041
subjects:
  - kind: ServiceAccount
    name: incident-reader
    namespace: ch041
roleRef:
  kind: Role
  name: excessive-secret-reader
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply -f .\ch041-excessive.yaml
kubectl auth can-i list secrets -n ch041 --as=$sa
kubectl -n ch041 get rolebindings
```

**Expected:** Secret listing changes to `yes`. Do not actually list Secret contents. Removing or narrowing the original `pod-observer` Role would **not** remove this additional grant because RBAC is additive.

Recover:

```powershell
kubectl -n ch041 delete rolebinding accidental-secret-grant
kubectl auth can-i list secrets -n ch041 --as=$sa
kubectl auth can-i get pods -n ch041 --as=$sa
```

**Expected:** Secret listing returns `no` while permitted Pod reads remain `yes`. Delete the unused lab Role if desired:

```powershell
kubectl -n ch041 delete role excessive-secret-reader
```

## 11. Lab 7 — Namespaced access review and acceptance

Perform a final audit:

```powershell
kubectl -n ch041 get serviceaccounts,roles,rolebindings
kubectl -n ch041 describe role pod-observer
kubectl -n ch041 describe rolebinding incident-reader-pod-observer
kubectl auth can-i get pods -n ch041 --as=$sa
kubectl auth can-i get pods --subresource=log -n ch041 --as=$sa
kubectl auth can-i delete pods -n ch041 --as=$sa
kubectl auth can-i list secrets -n ch041 --as=$sa
kubectl auth can-i get pods -n default --as=$sa
```

| Acceptance criterion | Expected |
|---|---|
| Namespaced Pod read | Allowed |
| Pod logs read | Allowed |
| Pod delete | Denied |
| Secret list | Denied after remediation |
| Access in unrelated namespace | Denied unless independently granted |
| Excessive binding | Removed |
| Incident log | No tokens or Secret values exposed |
| Change record | Reason, owner, approval and rollback documented |

If actual results differ, inspect all applicable bindings, groups and authorizer modes. Do not declare least privilege based on one Role manifest alone.

## 12. Production authentication patterns

### Human users

Human authentication may use OIDC, cloud provider authentication plugins, short-lived certificates or other configured authenticators. Kubernetes does not store ordinary human User objects in the same way as ServiceAccounts. RBAC bindings can reference authenticated user and group strings.

### ServiceAccounts

ServiceAccounts are namespaced API identities, conventionally named `system:serviceaccount:<namespace>:<name>`. Modern Kubernetes favors short-lived projected tokens obtained via TokenRequest over manually created long-lived Secret-backed tokens. Disable automatic token mounting where not needed and use explicit ServiceAccounts for workloads.

### Cloud identity is separate

In EKS or AKS, cloud identity determines access to cloud APIs and may participate in Kubernetes authentication. Kubernetes RBAC still controls Kubernetes API operations, subject to provider-specific access management. A Kubernetes RoleBinding does not automatically grant AWS or Azure resource access.

## 13. RBAC security design principles

- Prefer namespace-scoped Roles and RoleBindings for application teams.
- Use narrowly scoped ClusterRoles only when cluster-wide resources or reusable rule sets are necessary.
- Bind groups rather than individual users when possible; use short-lived human access.
- Avoid wildcards and unnecessary `secrets`, `pods/exec`, `pods/attach`, `pods/portforward`, `serviceaccounts/token` and RBAC mutation permissions.
- Treat `create pods` and privileged workload admission as potential paths to other namespace credentials.
- Treat `bind`, `escalate` and `impersonate` as high-risk permissions.
- Audit all RoleBindings and ClusterRoleBindings, including default/provider-managed grants.
- Require review for permission increases and periodically recertify access.
- Combine RBAC with Pod Security Admission, network isolation, admission policies and audit logging.
- Do not assume `resourceNames` limits `create` requests; a new object's name may not be known to the authorizer at authorization time. `list`/`watch` restrictions using resourceNames require matching field selectors.
- Review aggregated ClusterRoles; labels can dynamically add rules to built-in or custom aggregated roles.

## 14. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| `Unauthorized` | Missing/invalid authentication | kubeconfig, token expiry, identity provider |
| `Forbidden` | Authenticated but unauthorized | user/group, verb, API group, resource, namespace |
| Impersonation denied | Caller cannot impersonate target | caller's impersonate grant |
| Pod logs denied | Missing `pods/log` rule | subresource and verb |
| Access works in one namespace | RoleBinding scoped to namespace | bindings and namespace |
| Unexpected Secret access | Another additive binding or authorizer | all grants and audit |
| Cloud API access denied | Cloud IAM/workload identity | provider policies, not only Kubernetes RBAC |
| Access persists after Role edit | Additional binding, cached credentials or other authorization mode | complete effective authorization path |

## 15. Production incident runbook

1. **Scope:** identify caller identity, namespace, API operation, time, response code and workload impact.
2. **Preserve evidence:** API audit records, error text, relevant RBAC manifests and approved identity details; redact tokens.
3. **Classify:** authentication failure, authorization denial, admission rejection or cloud-provider access issue.
4. **Evaluate effective access:** inspect all applicable RoleBindings/ClusterRoleBindings and use `kubectl auth can-i` with authorized impersonation.
5. **Assess blast radius:** Secret access, workload creation, exec, token requests, impersonation and privilege escalation.
6. **Remediate narrowly:** add the smallest legitimate permission or remove the specific excessive binding; preserve unrelated access.
7. **Verify:** allowed actions work; prohibited actions remain denied; application health is restored.
8. **Close:** record owner, approval, access-review finding, detection improvements and follow-up recertification.

For suspected credential compromise, revoke or rotate affected credentials through their authoritative system and inspect audit logs; RBAC remediation alone may not invalidate an already exfiltrated token.

## 16. Cleanup

Only after confirming `ch041` is a disposable namespace:

```powershell
kubectl -n ch041 get pods,serviceaccounts,roles,rolebindings
kubectl delete namespace ch041
```

Do not remove built-in ClusterRoles, production RoleBindings or provider-managed identity configuration.

## 17. Acceptance checklist

- [ ] Authentication, authorization and admission explained.
- [ ] Current context and identity reviewed without exposing credentials.
- [ ] Namespaced least-privilege ServiceAccount, Role and RoleBinding created.
- [ ] Allowed and denied actions tested.
- [ ] Forbidden error reproduced and investigated.
- [ ] ClusterRole referenced through namespaced RoleBinding.
- [ ] Excessive Secret access demonstrated and removed.
- [ ] Effective permissions verified across applicable grants.
- [ ] Incident runbook and audit findings documented.
- [ ] Lab execution and independent review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 18. References

- [Kubernetes Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes ServiceAccounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [kubectl auth can-i](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/)

**Next:** Chapter 042 — ServiceAccounts and Workload Identity.
