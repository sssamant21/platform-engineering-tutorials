# Lab 010 — Read-only RBAC, SCC and ServiceAccount Audit

**Duration:** 20–25 minutes | **Environment:** authorized non-production namespace | **Mutation:** none | **Status:** draft, not executed.

## Preconditions
Obtain approved read access; identify a non-sensitive sample deployment and namespace. Confirm the cluster is non-production or that read-only production diagnostics are authorized. Do not run `oc login --token` in shared terminals, do not print tokens, Secrets or kubeconfig, and do not attempt impersonation without explicit rights.

### Linux/macOS
```sh
NS=training-project
DEPLOY=sample-app
oc whoami
oc config current-context
oc version
oc auth can-i get deployments -n "$NS"
oc auth can-i list rolebindings -n "$NS"
oc get rolebindings -n "$NS"
oc get serviceaccounts -n "$NS"
oc get deployment "$DEPLOY" -n "$NS" -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}'
oc get pods -n "$NS" -o custom-columns='NAME:.metadata.name,SA:.spec.serviceAccountName,SCC:.metadata.annotations.openshift\.io/scc'
```

### Windows PowerShell
```powershell
$Namespace = 'training-project'
$Deployment = 'sample-app'
oc whoami
oc config current-context
oc version
oc auth can-i get deployments -n $Namespace
oc auth can-i list rolebindings -n $Namespace
oc get rolebindings -n $Namespace
oc get serviceaccounts -n $Namespace
oc get deployment $Deployment -n $Namespace -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}'
oc get pods -n $Namespace -o custom-columns='NAME:.metadata.name,SA:.spec.serviceAccountName,SCC:.metadata.annotations.openshift\.io/scc'
```

If the deployment omits serviceAccountName, Kubernetes defaults to `default` for the pod. An empty JSONPath output is therefore not proof that no service account is used. A pod's SCC annotation is evidence of the admitted SCC when present, not proof of all eligible SCCs.

## Expected interpretation
- `oc auth can-i` prints `yes` or `no` for the active identity; `no` is expected for actions outside assigned duties.
- `Forbidden` on a listing indicates insufficient authorization; stop that step, record the verb/resource and contact the namespace owner. Do not request cluster-admin merely to finish a lab.
- `NotFound` on the deployment: confirm namespace/name, do not create or change anything.
- No pods: record `none`; do not invent an SCC outcome.
- SCC annotations may vary by workload and cluster configuration.

## Review questions
1. Why does a namespace RoleBinding to a ClusterRole not necessarily grant cluster-wide access?
2. Why can `can-i use scc` omit directly listed SCC users/groups?
3. Why should a database image be adapted to an allocated UID rather than immediately granting `anyuid`?
4. How would you verify the application service account without revealing its token?

## Evidence worksheet
| Field | Actual evidence (fill only after execution) |
| --- | --- |
| Date/time (UTC) | Not run |
| Cluster/version (sanitized) | Not run |
| Namespace / workload | Not run |
| Identity role (no token) | Not run |
| RBAC result | Not run |
| ServiceAccount / SCC observations | Not run |
| Denials / escalation | Not run |
| Reviewer / sign-off | Pending |

**Completion gate:** independent reviewer confirms least-privilege interpretation and evidence redaction. This document does not constitute a successful lab execution.
