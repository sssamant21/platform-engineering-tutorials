# Chapter 045 — Kubernetes Security Hardening Project

**Track:** Kubernetes Administration · **Part 09 — Kubernetes Security (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers and Kubernetes administrators  
**Prerequisites:** Chapters 041–044; Windows PowerShell, kubectl, disposable Kubernetes 1.30+ cluster with Pod Security Admission and ValidatingAdmissionPolicy APIs enabled

## 1. Production scenario

A patient-facing application has four weaknesses: an application ServiceAccount can read Secrets unnecessarily; containers mount Kubernetes API credentials despite not calling the API; a workload runs with insufficient runtime hardening; and deployment automation accepts mutable, unapproved image references. The team must correct the weaknesses without disrupting legitimate read-only diagnostics or relaxing cluster-wide policy.

**Capstone objective:** combine RBAC, ServiceAccount token management, Pod Security Standards, native admission policies and image security into a reproducible defense-in-depth hardening exercise.

### Learning outcomes

1. Inventory and reduce excessive Kubernetes API permissions.
2. Disable automatic token mounts for workloads that do not require Kubernetes API access.
3. Validate short-lived token behavior without disclosing bearer tokens.
4. Enforce Restricted Pod Security Standards in an isolated namespace.
5. Test non-root execution, seccomp, Linux capabilities and filesystem restrictions.
6. Enforce an image-reference admission rule with CEL and understand its limitations.
7. Perform negative authorization/admission tests and a controlled recovery.
8. Produce a security hardening report, operational runbook and acceptance evidence.

## 2. Security architecture and ownership

```text
Human / CI / GitOps
       |
 Kubernetes authentication
       |
      RBAC ──────────────> Kubernetes API operations
       |
   Admission
    |      |
    PSA    ValidatingAdmissionPolicy (CEL)
    |      |
  Pod security    image reference policy
       |
   kubelet + container runtime
       |
 non-root, no privilege escalation, seccomp, dropped capabilities
       |
 Workload ServiceAccount
       |
 projected short-lived token (only when needed)
       |
 cloud federation + separate cloud IAM
```

**Critical boundaries:** RBAC does not validate container privileges; Pod Security Admission does not validate image signatures; image-name restrictions do not scan for vulnerabilities; Kubernetes ServiceAccount RBAC does not grant cloud IAM permissions.

## 3. Safety prerequisites

This lab creates cluster-scoped admission resources, so use an isolated cluster with approval. **Do not apply the VAP to a shared production namespace or change global admission configuration.** If you cannot create VAP resources, complete manifest reviews and dry-run exercises where possible, and mark enforcement tests unvalidated.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes
kubectl api-resources --api-group=admissionregistration.k8s.io
kubectl auth can-i create validatingadmissionpolicies.admissionregistration.k8s.io
kubectl auth can-i create validatingadmissionpolicybindings.admissionregistration.k8s.io
kubectl create namespace ch045
kubectl label namespace ch045 security-capstone=ch045 --overwrite
```

Use only dummy data. Never print ServiceAccount tokens, cloud credentials or Secret values. Record cluster context and baseline state before changes.

## 4. Lab 1 — Establish a deliberately excessive RBAC baseline

Save `ch045-rbac.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-identity
  namespace: ch045
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: excessive-reader
  namespace: ch045
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets", "pods"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: excessive-binding
  namespace: ch045
subjects:
  - kind: ServiceAccount
    name: app-identity
    namespace: ch045
roleRef:
  kind: Role
  name: excessive-reader
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply -f .\ch045-rbac.yaml
$sa = "system:serviceaccount:ch045:app-identity"
kubectl auth can-i list secrets -n ch045 --as=$sa
kubectl auth can-i get configmaps -n ch045 --as=$sa
```

**Expected:** both return `yes` when the caller is authorized to impersonate this ServiceAccount. This is an intentionally excessive **lab-only** permission. Do not actually read Secret contents. If impersonation is denied, document the test limitation.

## 5. Lab 2 — Remediate RBAC and verify negative permissions

Save `ch045-least-privilege.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: configmap-observer
  namespace: ch045
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-configmap-observer
  namespace: ch045
subjects:
  - kind: ServiceAccount
    name: app-identity
    namespace: ch045
roleRef:
  kind: Role
  name: configmap-observer
  apiGroup: rbac.authorization.k8s.io
```

```powershell
kubectl apply -f .\ch045-least-privilege.yaml
kubectl auth can-i list secrets -n ch045 --as=$sa
kubectl -n ch045 delete rolebinding excessive-binding
kubectl auth can-i list secrets -n ch045 --as=$sa
kubectl auth can-i get configmaps -n ch045 --as=$sa
kubectl auth can-i delete pods -n ch045 --as=$sa
```

**Expected:** before deleting `excessive-binding`, Secret listing remains `yes` because RBAC is additive. After deletion, Secret listing and Pod deletion return `no`, while ConfigMap read remains `yes`, assuming no other grants.

```powershell
kubectl -n ch045 delete role excessive-reader
```

**Security checkpoint:** narrow roles do not override other grants; enumerate all RoleBindings and ClusterRoleBindings during a real access review.

## 6. Lab 3 — Prove token mounting is opt-in

Save `ch045-no-token.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: no-token
  namespace: ch045
spec:
  serviceAccountName: app-identity
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        readOnlyRootFilesystem: true
```

```powershell
kubectl apply -f .\ch045-no-token.yaml
kubectl -n ch045 wait --for=condition=Ready pod/no-token --timeout=120s
kubectl -n ch045 exec no-token -- sh -c 'test ! -e /var/run/secrets/kubernetes.io/serviceaccount/token && echo auto-token-absent'
kubectl -n ch045 get pod no-token -o jsonpath='{.spec.serviceAccountName}'
```

**Expected:** the Pod runs with the named ServiceAccount but no automatically mounted Kubernetes API token. `automountServiceAccountToken: false` does not revoke the ServiceAccount's RBAC permissions; it reduces credential exposure to the container.

For workloads that must call the API, use explicitly scoped, short-lived projected tokens and refresh-capable clients. Never embed a long-lived ServiceAccount token in a container image.

## 7. Lab 4 — Enforce Restricted Pod Security Standards

```powershell
kubectl label namespace ch045 pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace ch045 pod-security.kubernetes.io/audit=restricted --overwrite
kubectl label namespace ch045 pod-security.kubernetes.io/enforce=restricted --overwrite
kubectl get namespace ch045 --show-labels
```

Save `ch045-insecure.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: insecure
  namespace: ch045
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      securityContext:
        privileged: true
        allowPrivilegeEscalation: true
```

```powershell
kubectl apply --dry-run=server -f .\ch045-insecure.yaml
kubectl apply -f .\ch045-insecure.yaml
kubectl -n ch045 get pod insecure
```

**Expected:** the insecure Pod is rejected by PSA; the compliant `no-token` Pod remains running. Do not remove Restricted enforcement to make the unsafe Pod start.

## 8. Lab 5 — Validate security contexts and writable-volume exceptions

Inspect the compliant Pod:

```powershell
kubectl -n ch045 exec no-token -- id
kubectl -n ch045 exec no-token -- sh -c 'test ! -w / && echo root-filesystem-read-only'
kubectl -n ch045 get pod no-token -o jsonpath='{.spec.securityContext.seccompProfile.type}'
kubectl -n ch045 get pod no-token -o jsonpath='{.spec.containers[0].securityContext.allowPrivilegeEscalation}'
kubectl -n ch045 get pod no-token -o jsonpath='{.spec.containers[0].securityContext.capabilities.drop}'
```

**Expected:** non-root UID, read-only root filesystem, `RuntimeDefault`, `false`, `ALL`. For real applications that need writable scratch space, mount a narrowly scoped `emptyDir` at the required path. Do not disable hardening globally to solve a filesystem permission problem.

**Caveat:** read-only root filesystems are a recommended hardening measure but are not themselves required by Restricted PSS.

## 9. Lab 6 — Apply a namespace-scoped native admission policy

The following learning policy rejects direct Pods with mutable image tags. It does not inspect actual image contents or signatures, and it does not cover all workload templates.

Save `ch045-admission.yaml`:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: ch045-image-reference
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: "object.spec.containers.all(c, c.image.contains('@sha256:'))"
      message: "Container images must be pinned to a sha256 digest"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: ch045-image-reference-binding
spec:
  policyName: ch045-image-reference
  validationActions: ["Deny"]
  matchResources:
    namespaceSelector:
      matchLabels:
        security-capstone: ch045
```

```powershell
kubectl apply --dry-run=server -f .\ch045-admission.yaml
kubectl apply -f .\ch045-admission.yaml
kubectl get validatingadmissionpolicy ch045-image-reference
kubectl get validatingadmissionpolicybinding ch045-image-reference-binding
kubectl apply --dry-run=server -f .\ch045-no-token.yaml
```

**Expected:** the final dry-run is denied because `busybox:1.36` lacks a digest. The existing `no-token` Pod is **not automatically deleted** when the policy is introduced. An actual Pod update may be blocked by the new policy, depending on the fields and operation.

**Policy limitations:** this CEL rule only checks the literal `@sha256:` substring, not digest validity, provenance or vulnerabilities. Production policy should cover initContainers, ephemeralContainers, Deployment/StatefulSet/DaemonSet/Job/CronJob templates and signature verification through appropriate controls.

## 10. Lab 7 — Security incident drill and controlled recovery

Simulated incident: an application update fails because a new Pod uses an unpinned image. The security team also detects a past excessive Secret grant. Respond without weakening Restricted PSA or silently disabling the image policy.

### Evidence collection

```powershell
kubectl config current-context
kubectl get namespace ch045 --show-labels
kubectl -n ch045 get serviceaccounts,roles,rolebindings,pods
kubectl auth can-i list secrets -n ch045 --as=$sa
kubectl auth can-i get configmaps -n ch045 --as=$sa
kubectl get validatingadmissionpolicy ch045-image-reference -o yaml
kubectl get validatingadmissionpolicybinding ch045-image-reference-binding -o yaml
kubectl -n ch045 get events --sort-by=.lastTimestamp
```

### Recovery procedure

1. Confirm the error originates from admission rather than scheduling or image pull.
2. Identify the exact image field in the rendered workload manifest.
3. Retrieve a **real verified digest** from the trusted registry or CI artifact record; do not invent one.
4. Replace the mutable tag with the approved digest in the source manifest.
5. Run server-side dry-run and validate PSA requirements.
6. Deploy the corrected image and verify Pod readiness and application health.
7. Confirm excessive RBAC binding remains absent and the application ServiceAccount has no unnecessary token mount.
8. Record the policy decision, audit evidence, change approval and preventive action.

### Acceptance matrix

| Security control | Positive test | Negative test |
|---|---|---|
| RBAC | ConfigMap read allowed | Secret read denied |
| ServiceAccount | Pod uses dedicated identity | No automatic token file |
| Pod Security | Restricted-compatible Pod runs | Privileged Pod rejected |
| Runtime hardening | Non-root, seccomp, dropped capabilities | Privilege escalation disabled |
| Image admission | Verified digest passes review | Mutable tag rejected |
| Operational recovery | Corrected workload becomes Ready | Policy not weakened |

**Important:** a digest-pinned image is not automatically trusted. Require registry policy, vulnerability scanning, signatures/attestations and runtime monitoring appropriate to your risk model.

## 11. Cloud workload identity review

Cloud workload identity is a separate trust boundary from Kubernetes RBAC:

- **EKS:** validate IRSA or Pod Identity association, IAM trust, scope and credential refresh.
- **AKS:** validate OIDC issuer, federated credential, ServiceAccount annotation, Pod mutation and Azure RBAC.
- **GKE:** validate Workload Identity Federation principal mapping, metadata server and Google Cloud IAM.

This capstone's cloud review is **design-only** unless the cluster is configured with a cloud provider and the operator has authorized access. Never assume that `kubectl auth can-i` proves cloud IAM access. A cloud API `403` requires cloud audit and policy investigation.

## 12. Production security hardening checklist

- Dedicated ServiceAccounts per workload/security boundary.
- Minimal namespace-scoped RBAC; periodic review of all additive grants.
- No automatic API token mounts where unused.
- Short-lived projected tokens and safe rotation where needed.
- Restricted PSA with staged warn/audit rollout and pinned policy versions.
- Non-root UID, `allowPrivilegeEscalation: false`, dropped capabilities and RuntimeDefault seccomp.
- Read-only root filesystem with explicit writable mounts where compatible.
- Digest-pinned images, trusted registries, vulnerability scans and signature verification.
- Admission policies scoped and tested before enforcement; avoid broad exceptions.
- Separate cloud IAM review and audit logging.
- CI rendering, policy testing and production canary deployment.
- Documented emergency response and rollback that preserves security controls.

## 13. Troubleshooting matrix

| Symptom | Likely cause | First check |
|---|---|---|
| `Forbidden` Kubernetes API | RBAC | Subject, verb, namespace, all bindings |
| Unexpected Secret read | Additive RBAC grant | RoleBindings and ClusterRoleBindings |
| Token absent in Pod | Automatic mount disabled | Pod/ServiceAccount settings |
| `violates PodSecurity` | PSA Restricted | Namespace labels and Pod securityContext |
| Pod runtime permission error | UID/GID, read-only root | Pod events, volume permissions |
| Pod CREATE rejected by CEL | Image reference policy | VAP binding, message, rendered manifest |
| Deployment exists, no Pods | ReplicaSet Pod CREATE denied | ReplicaSet events |
| Cloud API `403` | Federation/IAM | Cloud trust, audit, role policy |
| ImagePullBackOff | Registry/digest/network | Pod events and image reference |

## 14. Production incident runbook

1. **Scope and impact:** identify cluster, namespace, workload, rollout, user-facing SLIs and security risk.
2. **Preserve evidence:** API errors, policy versions, RBAC grants, Pod spec, controller events and cloud audit references; redact credentials.
3. **Classify:** authentication, authorization, admission, scheduling, image pull, runtime or cloud IAM.
4. **Contain:** freeze competing changes and prevent new overprivileged deployments without deleting healthy workloads.
5. **Remediate narrowly:** remove excessive bindings, correct securityContext and use approved image digests.
6. **Validate both directions:** legitimate application actions succeed; prohibited actions remain denied.
7. **Review external identity:** ensure no compromised token or cloud key remains valid after RBAC changes.
8. **Close:** timeline, impact, RTO, control failures, ownership, CI checks, access recertification and follow-up tests.

## 15. Cleanup

**Delete cluster-scoped lab policy first, then the disposable namespace.** Confirm resource names before executing:

```powershell
kubectl delete validatingadmissionpolicybinding ch045-image-reference-binding
kubectl delete validatingadmissionpolicy ch045-image-reference
kubectl delete namespace ch045
```

Do not delete shared cluster policies, built-in ClusterRoles, provider identity components or other namespaces.

## 16. Part 09 capstone acceptance checklist

- [ ] Chapter 041: RBAC overgrant reproduced, remediated and verified.
- [ ] Chapter 042: dedicated ServiceAccount and token-mount behavior verified.
- [ ] Chapter 043: Restricted PSA rejection and compliant security context demonstrated.
- [ ] Chapter 044: VAP image-reference denial demonstrated and limitations documented.
- [ ] Positive and negative authorization tests recorded.
- [ ] No bearer tokens, real Secrets or cloud credentials exposed.
- [ ] Image digest obtained from trusted source, not fabricated.
- [ ] Incident drill and recovery report completed.
- [ ] Lab cluster-scoped admission resources cleaned up safely.
- [ ] Independent technical review and actual execution completed before marking Lab Validated.

**Part 09 writing milestone:** Chapters 041–045 drafted. Runtime validation and technical review remain pending.

## 17. References

- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes ServiceAccounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Kubernetes Images](https://kubernetes.io/docs/concepts/containers/images/)
- [Sigstore](https://docs.sigstore.dev/)

**Next:** Chapter 046 — Node Architecture, Kubelet and Node Conditions (Part 10).
