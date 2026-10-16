# Chapter 049 — Hands-on Lab: Jenkins on Azure AKS

**Environment:** Disposable AKS cluster with OIDC issuer and Microsoft Entra Workload ID enabled, Azure CLI, kubectl, Jenkins Kubernetes plugin, test ACR/storage and narrowly scoped managed identity. Azure resources incur cost; clean up when complete.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Cluster inventory | Record AKS/K8s version and region | Baseline |
| 02 | Architecture | Map Jenkins and Azure trust boundaries | Diagram |
| 03 | OIDC check | Verify AKS OIDC issuer | URL |
| 04 | Workload ID check | Verify feature enabled | Output |
| 05 | Namespace | Create `jenkins-build` | Namespace |
| 06 | Provisioner RBAC | Check Pod lifecycle permission | `can-i` |
| 07 | Build SA | Confirm no Kubernetes Secret access | Denied |
| 08 | Managed identity | Create scoped test identity | Client ID |
| 09 | Federated credential | Bind exact issuer/subject/audience | Credential |
| 10 | Pod label | Apply workload identity label | Pod YAML |
| 11 | Token injection | Verify projected token env/path | Redacted evidence |
| 12 | Azure login | Exchange federated token | Identity |
| 13 | Positive access | Access approved test resource | Success |
| 14 | Negative access | Attempt unauthorized action | Denied |
| 15 | ACR | Verify pull/push role separation | RBAC |
| 16 | Node pools | Inspect system/user pools | Inventory |
| 17 | Autoscaling | Observe synthetic burst | Queue/node metrics |
| 18 | Identity fault | Use wrong test subject | AADSTS error |
| 19 | Recovery | Restore binding, rerun | Success |
| 20 | Cleanup | Remove test resources and record cost | Audit |

## 12 troubleshooting drills

1. AKS OIDC issuer disabled or incorrect.
2. Workload identity Pod label missing.
3. Service account client ID annotation missing.
4. Federated credential subject mismatch.
5. Federated credential audience mismatch.
6. Managed identity lacks Azure RBAC.
7. Wrong Azure credential chain selected.
8. ACR kubelet pull denied.
9. ACR publisher push denied.
10. Node pool max capacity/quota reached.
11. Spot node interruption.
12. Agent remoting or private endpoint DNS failure.

Use synthetic identities and nonproduction resources. Never print federated tokens or weaken production RBAC to pass a drill. Mark unavailable features explicitly blocked.

## Minimal workload identity service account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-artifacts
  namespace: jenkins-build
  annotations:
    azure.workload.identity/client-id: REPLACE_WITH_CLIENT_ID
```

Pod metadata must include `azure.workload.identity/use: "true"` for webhook injection. Use a trusted Azure CLI image and verify effective Pod spec before testing.

## Commands

```sh
az aks show -g "$AKS_RG" -n "$AKS_NAME" \
  --query '{oidc:oidcIssuerProfile.issuerUrl,workload:securityProfile.workloadIdentity.enabled}' -o json
az aks nodepool list -g "$AKS_RG" --cluster-name "$AKS_NAME" -o table
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

## Evidence template

```text
UTC timestamp:
Subscription/region/AKS version:
AKS OIDC issuer:
Workload identity feature status:
Jenkins controller and agent namespace:
Provisioner Kubernetes SA:
Agent Kubernetes SA:
Managed identity client ID (nonsecret):
Federated subject and audience:
Positive/denied Azure API actions:
ACR role and result:
Node pool/autoscaler:
Queue p95 and Pod startup:
Fault injection and AADSTS/Kubernetes error:
Root cause/recovery:
Resource cleanup and cost:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Federated credential matches exact service account.
- [ ] Azure API identity verified inside agent Pod.
- [ ] Unauthorized Azure action denied.
- [ ] Build SA has no excess Kubernetes RBAC.
- [ ] ACR roles and node pool capacity validated.
- [ ] No static Azure client secrets in Jenkinsfile.
- [ ] Test resources cleaned up.
- [ ] Reviewer signs off.

**Related:** [Chapter 049 — Jenkins on Azure AKS](../049-jenkins-azure-aks-workload-identity-node-pools-operations.md).
