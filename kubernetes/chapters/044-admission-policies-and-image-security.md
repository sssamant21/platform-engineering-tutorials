# Chapter 044 — Admission Policies and Image Security

**Track:** Kubernetes Administration · **Part 09 — Kubernetes Security**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 041–043; kubectl, Windows PowerShell, isolated Kubernetes cluster with ValidatingAdmissionPolicy support (Kubernetes 1.30+ recommended)

## 1. Production scenario

An application deployment is rejected because its image uses an unapproved registry and mutable `latest` tag. Another team has bypassed normal deployment review by creating Pods directly. The SRE must determine which admission layer denied the request, test the policy safely, apply a compliant manifest and ensure existing workloads remain available.

This chapter demonstrates Kubernetes native **ValidatingAdmissionPolicy (VAP)** using CEL, Pod Security Admission, image provenance controls and the operational boundaries of admission enforcement.

### Learning objectives

1. Trace Kubernetes API requests through authentication, authorization, mutation and validation.
2. Understand ValidatingAdmissionPolicy and ValidatingAdmissionPolicyBinding.
3. Write CEL expressions that reject unapproved image references.
4. Test enforcement safely with namespace scoping and dry-run.
5. Distinguish direct Pods from Deployment Pod templates and controller-created Pods.
6. Explain image digests, scanning, signatures and policy engines.
7. Complete seven labs and a production admission-incident acceptance exercise.

## 2. Admission and supply-chain architecture

```text
Developer / GitOps / controller
           |
        API server
           |
 Authentication + authorization
           |
    Mutating admission
           |
    Validating admission
      PSA / VAP / webhooks
           |
    Kubernetes resource
           |
 Scheduler / kubelet / runtime
           |
 Image pull + container startup
```

Admission evaluates API requests before persistence. It does not continuously scan already running containers. A policy that checks an image name cannot verify image contents, signatures or vulnerability state by itself.

### Security control comparison

| Control | What it checks | What it does not guarantee |
|---|---|---|
| Registry allowlist | Image reference origin string | Registry contents are safe |
| Digest pinning | Immutable content reference | Content is trusted or vulnerability-free |
| Vulnerability scanner | Known vulnerability findings | Runtime behavior or full provenance |
| Signature/attestation verification | Signed artifact and identity policy | Application correctness |
| Pod Security Admission | Pod security settings | Image provenance |
| Runtime security | Observed container activity | Prevention of all malicious code |

## 3. Lab prerequisites and isolation

Use an isolated test cluster with a Kubernetes API version supporting `admissionregistration.k8s.io/v1` ValidatingAdmissionPolicy and its binding. Verify:

```powershell
kubectl config current-context
kubectl version
kubectl api-resources --api-group=admissionregistration.k8s.io
kubectl auth can-i create validatingadmissionpolicies.admissionregistration.k8s.io
kubectl auth can-i create validatingadmissionpolicybindings.admissionregistration.k8s.io
kubectl create namespace ch044
kubectl label namespace ch044 security-lab=ch044 --overwrite
```

VAP resources are **cluster-scoped** even when their matching rules target one namespace. Creating them requires elevated permissions. If you lack these permissions, complete the rendering and review exercises without applying policies. Do not modify shared production admission configuration.

## 4. Lab 1 — Inspect admission capabilities and baseline workload

```powershell
kubectl get validatingadmissionpolicies
kubectl get validatingadmissionpolicybindings
kubectl get namespace ch044 --show-labels
kubectl -n ch044 run baseline --image=nginx:1.27 --restart=Never
kubectl -n ch044 get pod baseline
```

**Expected:** Pod creation is permitted unless other existing policies block it. This initial image is deliberately unpinned; the lab will later reject such images. Record the current policy inventory before adding a new policy.

## 5. Lab 2 — Create a scoped image-reference policy

The policy below requires direct Pod containers to use a digest reference under `registry.k8s.io/`. The example is intentionally narrow to make behavior observable; real policy must cover initContainers, ephemeralContainers and workload Pod templates too.

Save `ch044-policy.yaml`:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: ch044-image-policy
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: "!has(object.spec.containers) || object.spec.containers.all(c, c.image.startsWith('registry.k8s.io/') && c.image.contains('@sha256:'))"
      message: "Images must use registry.k8s.io and a sha256 digest"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: ch044-image-policy-binding
spec:
  policyName: ch044-image-policy
  validationActions: ["Deny"]
  matchResources:
    namespaceSelector:
      matchLabels:
        security-lab: ch044
```

```powershell
kubectl apply --dry-run=server -f .\ch044-policy.yaml
kubectl apply -f .\ch044-policy.yaml
kubectl get validatingadmissionpolicy ch044-image-policy
kubectl get validatingadmissionpolicybinding ch044-image-policy-binding
```

**Expected:** policy and binding exist; only namespaces with `security-lab=ch044` match the binding. Policy creation itself may be rejected by API validation if unsupported CEL syntax or an incompatible cluster version is used. Fix syntax rather than disabling admission.

**Scope limitation:** `image.contains('@sha256:')` checks string shape, not digest validity or signature verification. It is a learning control, not a complete supply-chain policy.

## 6. Lab 3 — Reproduce a denied image

Save `ch044-denied.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: denied-image
  namespace: ch044
spec:
  containers:
    - name: app
      image: nginx:latest
      command: ["sh", "-c", "sleep 36000"]
```

```powershell
kubectl apply --dry-run=server -f .\ch044-denied.yaml
kubectl apply -f .\ch044-denied.yaml
kubectl -n ch044 get pod denied-image
```

**Expected:** server-side dry-run and actual create are denied by the VAP. The Pod is not created. Record the exact policy name and validation message from the API error. If the Pod is admitted, inspect the binding namespace selector, policy readiness and admission plugin availability.

## 7. Lab 4 — Test an approved digest without inventing an image hash

Obtain an **actual published digest** from a trusted registry or your organization's artifact repository. Do not substitute a made-up hash or assume a tag equals a digest.

Save `ch044-approved.yaml` after replacing the placeholder with a verified reference:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: approved-image
  namespace: ch044
spec:
  containers:
    - name: app
      image: registry.k8s.io/pause@sha256:REPLACE_WITH_VERIFIED_DIGEST
```

The placeholder above is deliberately invalid. Replace it with a verified 64-character digest from your trusted source, then run:

```powershell
kubectl apply --dry-run=server -f .\ch044-approved.yaml
kubectl apply -f .\ch044-approved.yaml
kubectl -n ch044 get pod approved-image -o wide
kubectl -n ch044 describe pod approved-image
```

**Expected after replacement:** the admission rule accepts the image string. Pod readiness additionally depends on the digest existing, platform compatibility, registry reachability and runtime behavior. The `pause` image is a minimal lab container, not a production application.

## 8. Lab 5 — Observe policy gaps in workload templates

The Lab 2 policy matches `pods`, not Deployment objects. A Deployment with an unapproved image may be **created** successfully, but its ReplicaSet's attempts to create Pods can be rejected.

Save `ch044-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-template
  namespace: ch044
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bad-template
  template:
    metadata:
      labels:
        app: bad-template
    spec:
      containers:
        - name: app
          image: nginx:latest
```

```powershell
kubectl apply -f .\ch044-deployment.yaml
kubectl -n ch044 get deployment,replicaset,pods
kubectl -n ch044 describe replicaset -l app=bad-template
kubectl -n ch044 get events --sort-by=.lastTimestamp
```

**Expected:** Deployment object can exist, but its ReplicaSet cannot create the violating Pod; events identify the admission rejection. This is an important availability risk: a deployment controller may accept desired state while actual Pods fail to materialize.

**Production improvement:** add policy rules for Deployment, StatefulSet, DaemonSet, Job and CronJob Pod templates, or use a mature policy engine with maintained policy libraries. Cover `containers`, `initContainers` and `ephemeralContainers` where applicable. Validate update semantics, including ephemeral container subresources.

## 9. Lab 6 — Change enforcement to Warn safely

Use the existing policy and binding to demonstrate nonblocking warnings in the disposable namespace.

Save `ch044-warn-binding.yaml`:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: ch044-image-policy-binding
spec:
  policyName: ch044-image-policy
  validationActions: ["Warn"]
  matchResources:
    namespaceSelector:
      matchLabels:
        security-lab: ch044
```

```powershell
kubectl apply -f .\ch044-warn-binding.yaml
kubectl apply --dry-run=server -f .\ch044-denied.yaml
```

**Expected:** a policy warning is returned, but the request is not denied by this binding. Other admission policies may still reject it. Do **not** apply the insecure Pod during this exercise.

Restore enforcement:

```powershell
kubectl apply -f .\ch044-policy.yaml
kubectl apply --dry-run=server -f .\ch044-denied.yaml
```

**Expected:** denial returns. In production, use Warn/Audit rollout phases and policy metrics before enforcing a new rule, and never change enforcement mode casually during an incident.

## 10. Lab 7 — Admission incident response acceptance

Incident: a rollout is blocked after a new image policy is enabled.

```powershell
kubectl get validatingadmissionpolicy ch044-image-policy -o yaml
kubectl get validatingadmissionpolicybinding ch044-image-policy-binding -o yaml
kubectl get namespace ch044 --show-labels
kubectl -n ch044 get deployment,replicaset,pods
kubectl -n ch044 get events --sort-by=.lastTimestamp
kubectl -n ch044 describe deployment bad-template
kubectl -n ch044 describe replicaset -l app=bad-template
```

**Required investigation:**
1. Which API resource was admitted or denied?
2. Which namespace selector and binding matched?
3. Did the Pod fail admission, image pull, scheduling or readiness?
4. Is the image digest verified from a trusted registry?
5. Does the policy cover workload templates and init containers?
6. Can the application be corrected without relaxing enforcement?
7. What is the rollback plan for a faulty admission policy?

### Acceptance matrix

| Check | Required evidence |
|---|---|
| Admission capability | VAP API resources available |
| Scope | Binding limited to lab namespace |
| Denial | nginx:latest Pod rejected |
| Approved reference | Verified digest reference accepted |
| Controller gap | Deployment exists but Pods blocked |
| Warn rollout | Warning without denial |
| Enforcement restore | Deny reinstated |
| Cleanup | Cluster-scoped lab policy removed |

## 11. Image security and software supply chain

### Immutable images

Use digest-pinned references in production deployments where feasible. Tags can be overwritten; digests identify specific image content. A digest alone does not establish whether the artifact was built securely.

### Vulnerability scanning

Scan images in CI and registries for known vulnerabilities, apply severity and exploitability policies, and rescan deployed images as new advisories appear. Exceptions need owners, expiry dates and compensating controls.

### Signatures and attestations

Use image-signature verification and provenance attestations where supported. Tools and policy engines may integrate Sigstore/cosign, Notary or cloud-native signing services. Verify the signer identity, trust roots, digest binding and policy behavior; do not accept any valid signature indiscriminately.

### Admission engines

Native VAP supports CEL validation. Kyverno and OPA Gatekeeper can provide richer policy ecosystems, with additional operational dependencies. Image-signature verification generally requires a dedicated verifier or suitable policy engine; the basic CEL example here only checks an image-reference string.

## 12. Production operational safeguards

- Introduce policies with audit/warn, impact inventory and canary namespaces.
- Use namespace scoping and explicit exclusions for system components.
- Validate direct Pods and workload-controller Pod templates.
- Cover all container categories, including init and ephemeral containers.
- Avoid broad policy exemptions and unrestricted registries.
- Pin approved images to digests and verify signatures/attestations where required.
- Keep admission webhook availability, latency and failurePolicy under SLOs.
- Monitor API admission errors and controller `FailedCreate` events.
- Document emergency policy rollback with approval and compensating controls.
- Test Kubernetes version upgrades for CEL syntax and admission API compatibility.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Policy not found | API version/plugin unsupported | api-resources, server version |
| Policy exists but no denial | Binding selector mismatch | namespace labels, binding |
| CEL validation fails | Expression/type error | API validation response |
| Deployment accepted but no Pods | Pod CREATE denied | ReplicaSet events |
| ImagePullBackOff | Registry/auth/digest issue after admission | Pod events, registry |
| Webhook timeout | External admission service unavailable | Webhook health, failurePolicy |
| Unexpected exemption | Namespace/object selector or match rules | Policy/binding match |
| Approved image denied | Incorrect image string rule | Rendered manifest, policy expression |

## 14. Production incident runbook

1. Confirm affected cluster, namespace, workload, change window and user impact.
2. Capture API admission error, controller events and relevant policy/binding versions.
3. Determine whether failure is policy evaluation, scheduling, image pull or runtime.
4. Check namespace/object selectors and all applicable admission policies.
5. Compare the proposed image with approved registry, digest, signature and vulnerability policy.
6. Prefer correcting the workload manifest or image reference.
7. If a policy itself is faulty, use approved staged rollback or narrowly scoped exception with expiry and audit trail.
8. Validate Pods created and Ready, application SLIs recovered, and policy enforcement restored.
9. Record incident timeline, blast radius, corrective actions and CI prevention.

## 15. Cleanup

**Cluster-scoped resources are involved. Confirm names and permissions before deletion.**

```powershell
kubectl delete validatingadmissionpolicybinding ch044-image-policy-binding
kubectl delete validatingadmissionpolicy ch044-image-policy
kubectl delete namespace ch044
```

Do not delete other teams' admission policies or shared webhooks.

## 16. Acceptance checklist

- [ ] Admission request flow explained.
- [ ] VAP API availability verified.
- [ ] Namespace-scoped binding deployed.
- [ ] Unapproved image rejected.
- [ ] Real digest obtained and validated without inventing a hash.
- [ ] Controller Pod-creation failure diagnosed.
- [ ] Warn mode tested and Deny restored.
- [ ] Image scanning and signature verification distinguished from string matching.
- [ ] Production incident runbook documented.
- [ ] Cluster-scoped lab policy safely removed.
- [ ] Runtime execution and independent review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 17. References

- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Admission Controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Kubernetes Images](https://kubernetes.io/docs/concepts/containers/images/)
- [Sigstore](https://docs.sigstore.dev/)
- [Kyverno](https://kyverno.io/docs/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/)

**Next:** Chapter 045 — Kubernetes Security Hardening Project (Part 09 capstone).
