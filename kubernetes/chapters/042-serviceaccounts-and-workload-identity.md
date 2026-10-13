# Chapter 042 — ServiceAccounts and Workload Identity

**Track:** Kubernetes Administration · **Part 09 — Kubernetes Security**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapter 041; kubectl, PowerShell, isolated Kubernetes cluster; cloud CLI/provider permissions only for optional exercises

## 1. Production scenario

A workload accesses Kubernetes resources and a cloud secret manager. It currently uses a long-lived cloud access key stored in a Kubernetes Secret, and the application's Kubernetes ServiceAccount has broad API permissions. Security requires moving to short-lived workload identity while retaining only the minimum Kubernetes API access. During migration, a Pod fails with `403 Forbidden` from the cloud API; the team must distinguish cloud IAM, Kubernetes RBAC, token audience, identity federation and network errors.

### Learning objectives

1. Explain Kubernetes ServiceAccounts and default token behavior.
2. Understand TokenRequest, projected ServiceAccount tokens, audience and expiration.
3. Use least-privilege RBAC and disable unnecessary token mounts.
4. Validate in-Pod identity without logging credentials.
5. Explain AWS EKS Pod Identity/IRSA, AKS Workload Identity and GKE Workload Identity Federation.
6. Investigate cloud federation failures and credential-rotation edge cases.
7. Complete seven labs and a workload-identity migration acceptance exercise.

## 2. Identity architecture

```text
Pod ──> Kubernetes ServiceAccount
  |            |
  |            +── Kubernetes RBAC ──> Kubernetes API
  |
  +── projected short-lived token
              |
        trusted issuer / audience
              |
     cloud identity federation
              |
         cloud IAM policy
              |
     cloud API / secret manager
```

A ServiceAccount is a namespaced Kubernetes API identity. Its conventional principal name is `system:serviceaccount:<namespace>:<name>`. Kubernetes RBAC grants Kubernetes API actions; AWS IAM, Azure RBAC and GCP IAM control their respective cloud APIs. These systems must be configured and verified separately.

## 3. Token lifecycle and security model

Modern Kubernetes uses the TokenRequest API and projected, time-limited ServiceAccount tokens for Pods. The kubelet can rotate projected tokens. A token's **audience** must match the intended relying party; a Kubernetes API audience token should not be reused indiscriminately for unrelated services. Token expiry and rotation must be handled by the client library.

Important distinctions:
- `automountServiceAccountToken: false` disables the usual automatic Pod token mount but does not remove the ServiceAccount identity or RBAC grants.
- A manually requested token may still be created when authorized.
- Static, long-lived ServiceAccount token Secrets should generally be avoided.
- Cloud workload identity does not necessarily require broad Kubernetes RBAC.
- A token issued for a Pod may be bound to that Pod's lifetime, depending on how it was requested.
- Short-lived credentials reduce exposure duration but do not eliminate the need for RBAC, IAM, audit logging and secure application handling.

## 4. Lab setup

Use a disposable namespace and synthetic values only:

```powershell
kubectl config current-context
kubectl get nodes
kubectl create namespace ch042
kubectl auth can-i create serviceaccounts -n ch042
kubectl auth can-i create token -n ch042
```

Token issuance and Pod creation may be restricted by policy. Never weaken production controls solely to run the labs.

## 5. Lab 1 — Create a dedicated ServiceAccount with least-privilege RBAC

Save `ch042-identity.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-reader
  namespace: ch042
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: configmap-reader
  namespace: ch042
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-reader-configmap-reader
  namespace: ch042
subjects:
  - kind: ServiceAccount
    name: app-reader
    namespace: ch042
roleRef:
  kind: Role
  name: configmap-reader
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply -f .\ch042-identity.yaml
kubectl -n ch042 get sa,role,rolebinding
kubectl -n ch042 describe sa app-reader
```

**Expected:** a dedicated identity with ConfigMap read permission and no automatic token mount. Avoid reusing the namespace's `default` ServiceAccount for application-specific access.

## 6. Lab 2 — Verify RBAC and deny unnecessary privileges

With authorization to impersonate this ServiceAccount:

```powershell
$sa = "system:serviceaccount:ch042:app-reader"
kubectl auth can-i get configmaps -n ch042 --as=$sa
kubectl auth can-i list configmaps -n ch042 --as=$sa
kubectl auth can-i get secrets -n ch042 --as=$sa
kubectl auth can-i delete pods -n ch042 --as=$sa
kubectl auth can-i get configmaps -n default --as=$sa
```

**Expected:** ConfigMap read allowed in `ch042`; Secret read, Pod delete and access in unrelated namespaces denied, assuming no other grants. If impersonation itself is forbidden, record that limitation and use an authorized test method. RBAC is additive; inspect all applicable bindings if results differ.

## 7. Lab 3 — Request a short-lived token without exposing it

A TokenRequest token is a sensitive bearer credential. Request a short-lived token only in a disposable cluster and avoid printing it.

```powershell
$token = kubectl -n ch042 create token app-reader --duration=10m
if ([string]::IsNullOrWhiteSpace($token)) { throw "TokenRequest failed" }
"Token issued (value intentionally not displayed)"
Remove-Variable token
```

**Expected:** TokenRequest succeeds if supported and authorized. Requested duration is advisory: the API server may issue a different lifetime. A production application should obtain and refresh tokens through supported client libraries rather than storing a one-time token in an environment variable.

**Security note:** assigning the token to a PowerShell variable avoids printing it, but the credential is still present in process memory temporarily. Do not write it to a file, command history, logs or ticket. Do not paste it into JWT decoding websites.

## 8. Lab 4 — Compare Pods with and without automatic token mounts

Save `ch042-pods.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: no-auto-token
  namespace: ch042
spec:
  serviceAccountName: app-reader
  automountServiceAccountToken: false
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
---
apiVersion: v1
kind: Pod
metadata:
  name: projected-token
  namespace: ch042
spec:
  serviceAccountName: app-reader
  automountServiceAccountToken: false
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: api-identity
          mountPath: /var/run/workload-identity
          readOnly: true
  volumes:
    - name: api-identity
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 600
              audience: https://kubernetes.default.svc
```

```powershell
kubectl apply -f .\ch042-pods.yaml
kubectl -n ch042 wait --for=condition=Ready pod/no-auto-token --timeout=120s
kubectl -n ch042 wait --for=condition=Ready pod/projected-token --timeout=120s
kubectl -n ch042 describe pod no-auto-token
kubectl -n ch042 describe pod projected-token
```

**Expected:** the first Pod has no automatically injected API token volume; the second has an explicitly projected token volume. The audience string here is illustrative; the actual Kubernetes API audience varies by cluster. This lab only inspects mount configuration and does not attempt API authentication with the custom audience token.

Inspect the presence of the token file **without printing its contents**:

```powershell
kubectl -n ch042 exec projected-token -- sh -c 'test -s /var/run/workload-identity/token && echo token-file-present'
kubectl -n ch042 exec no-auto-token -- sh -c 'test ! -e /var/run/secrets/kubernetes.io/serviceaccount/token && echo auto-token-absent'
```

## 9. Lab 5 — Inspect projected token rotation safely

The projected token is managed by kubelet and refreshed as needed. Inspect metadata, not the token:

```powershell
kubectl -n ch042 exec projected-token -- ls -l /var/run/workload-identity
kubectl -n ch042 get pod projected-token -o jsonpath='{.spec.volumes[0].projected.sources[0].serviceAccountToken.expirationSeconds}'
kubectl -n ch042 get pod projected-token -o jsonpath='{.spec.volumes[0].projected.sources[0].serviceAccountToken.audience}'
```

**Expected:** token projection configured with a requested 600-second lifetime and specified audience. Actual refresh timing is implementation-dependent; do not assert that a token rotated merely because the projection exists. Long-running applications must reread tokens or use a client library that refreshes them.

Avoid using `subPath` for rotating projected tokens: a subPath mount does not receive normal projected volume updates.

## 10. Lab 6 — Simulated workload identity federation design

No cloud credentials are needed for this design lab. Write a mapping table for a hypothetical application:

| Layer | Example | Verification |
|---|---|---|
| Kubernetes namespace | ch042 | Namespace exists |
| Kubernetes ServiceAccount | app-reader | Pod uses expected identity |
| OIDC issuer | Cluster-specific issuer URL | Matches cloud trust configuration |
| Token audience | Provider-required audience | Matches federation configuration |
| Cloud role/identity | Dedicated least-privilege role | Trust and permissions reviewed |
| Cloud resource | One secret or bucket prefix | Access policy narrowly scoped |
| Application SDK | Default credential chain | Refreshes credentials without static keys |

**Expected:** each trust boundary and owner is documented. Do not fabricate an issuer, provider principal, role ARN or Azure/GCP identity; retrieve these from the actual environment when implementing the optional provider exercise.

## 11. Lab 7 — Workload identity failure investigation

Simulated incident: a Pod can start but its cloud API request returns `403`. Distinguish four classes of failures:

1. **Kubernetes identity:** wrong ServiceAccount, wrong namespace or Pod mutation missing.
2. **Federation:** issuer, subject or audience does not match cloud trust.
3. **Cloud authorization:** identity exchange succeeds but IAM policy denies the resource/action.
4. **Runtime/network:** token refresh, SDK configuration, DNS, proxy, endpoint or clock skew.

Start with safe Kubernetes checks:

```powershell
kubectl -n ch042 get pods -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName
kubectl -n ch042 get sa app-reader -o yaml
kubectl -n ch042 describe pod projected-token
kubectl auth can-i get secrets -n ch042 --as=$sa
kubectl -n ch042 get events --sort-by=.lastTimestamp
```

**Expected:** identity and token projection are observable without credential disclosure. A Kubernetes `can-i` result cannot prove cloud IAM access. Record which system produced the `403`, then inspect the appropriate cloud audit trail and trust configuration.

## 12. Cloud provider integration patterns (optional, not automatically executable)

### AWS EKS

**IRSA** associates a Kubernetes ServiceAccount with an IAM role through the cluster OIDC provider and a trust policy restricted by issuer, subject and audience. Supported AWS SDKs exchange the projected token for temporary credentials. Validate the IAM role annotation, OIDC provider, trust policy and SDK credential chain.

**EKS Pod Identity** uses an EKS-managed Pod Identity association and agent-based credential delivery, with a different trust mechanism from IRSA. Verify association, agent availability, SDK compatibility and IAM permissions. Do not assume IRSA and Pod Identity are configured identically.

### Azure AKS

**Microsoft Entra Workload ID** federates a Kubernetes ServiceAccount token to an Entra application or managed identity. Verify the AKS OIDC issuer, federated identity credential subject/audience, ServiceAccount client-ID annotation, required Pod label for workload identity mutation and Azure RBAC on the target resource.

### Google GKE

**Workload Identity Federation for GKE** maps Kubernetes workloads to Google Cloud identities and IAM permissions. Depending on the access model, permissions may be granted to a Kubernetes principal directly or through IAM ServiceAccount impersonation. Verify workload identity pool configuration, principal mapping, metadata server availability and resource IAM grants.

All provider configurations are version- and environment-dependent. Follow your organization's supported implementation and test in a nonproduction account first.

## 13. Migration runbook: static key to workload identity

1. Inventory every consumer of the static cloud credential, including CronJobs, sidecars and rollback versions.
2. Define the minimum required cloud actions and resource scope.
3. Create a dedicated Kubernetes ServiceAccount and cloud identity trust configuration.
4. Deploy one canary Pod using workload identity with supported SDKs.
5. Verify token exchange, cloud API access, audit identity and refresh across credential expiry.
6. Migrate remaining consumers gradually; monitor error rate, latency and auth failures.
7. Confirm no consumers depend on the static key, including scheduled and infrequent jobs.
8. Revoke and delete the old cloud key at the authority; remove Kubernetes Secret references and CI variables.
9. Review audit trails for unexpected old-key use and record change evidence.

**Rollback:** before old-key revocation, restore a known-good configuration only under approved controls. After revocation, rolling back a Deployment alone will not restore the old key; fix federation or rotate forward. Avoid re-enabling a compromised key.

## 14. Troubleshooting matrix

| Symptom | Likely cause | Action |
|---|---|---|
| Kubernetes API 401 | Invalid/expired token, wrong audience | Check issuer, audience and refresh |
| Kubernetes API 403 | RBAC denies verb/resource | Review effective RBAC |
| Cloud token exchange fails | OIDC trust mismatch | Check issuer, subject and audience |
| Cloud API 403 | Cloud IAM denies action | Inspect cloud policy and audit |
| Pod lacks token projection | ServiceAccount/Pod mount config | Inspect Pod spec and mutation |
| Token refresh failures | Client caches expired token | Use supported refresh-capable SDK |
| Works in one namespace | Subject trust is namespace-specific | Verify subject string |
| EKS Pod Identity unavailable | Agent/association issue | Inspect association and agent |
| AKS federation unavailable | Missing label/annotation/federated credential | Inspect Pod and Entra setup |
| GKE permission denied | Wrong principal binding or metadata setup | Inspect Workload Identity and IAM |

## 15. Security best practices

- Prefer short-lived identity over static cloud access keys.
- Use a dedicated ServiceAccount per workload or security boundary.
- Disable automatic Kubernetes API token mounting where unnecessary.
- Limit projected token audiences to intended relying parties.
- Minimize Kubernetes RBAC and cloud IAM independently.
- Avoid `get secrets`, Pod exec, ServiceAccount token creation and broad IAM grants without justification.
- Never log bearer tokens, JWTs, temporary credentials or decoded token claims that contain sensitive context.
- Review provider trust subject/issuer/audience precisely; avoid wildcard trust.
- Use cloud audit logging and Kubernetes audit policy to detect unusual identity use.
- Validate token refresh, application restart and provider outages before production migration.
- Treat cloud identity association changes as security-sensitive infrastructure changes.

## 16. Cleanup

Only in the disposable namespace:

```powershell
kubectl -n ch042 get pods,serviceaccounts,roles,rolebindings
kubectl delete namespace ch042
```

Do not delete shared cloud roles, OIDC providers, identity associations or cluster add-ons. Optional cloud exercises require separate, reviewed cleanup.

## 17. Acceptance checklist

- [ ] ServiceAccount created with explicit token-mount behavior.
- [ ] RBAC allowed/denied actions verified.
- [ ] TokenRequest issued without printing credential.
- [ ] Pods with and without automatic token mounts compared.
- [ ] Explicit projected token configuration inspected safely.
- [ ] Audience, expiry and refresh semantics explained.
- [ ] EKS, AKS and GKE federation trust boundaries documented.
- [ ] Cloud 403 and Kubernetes 403 failure modes distinguished.
- [ ] Static-key migration and revocation plan documented.
- [ ] Runtime lab validation and independent technical review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 18. References

- [Kubernetes ServiceAccounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [ServiceAccount Token Projection](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Amazon EKS Pod Identities](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Azure Workload Identity](https://azure.github.io/azure-workload-identity/)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)

**Next:** Chapter 043 — Pod Security Standards and Security Contexts.
