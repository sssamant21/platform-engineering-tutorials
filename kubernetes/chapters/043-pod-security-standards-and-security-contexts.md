# Chapter 043 — Pod Security Standards and Security Contexts

**Track:** Kubernetes Administration · **Part 09 — Kubernetes Security**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 016–020 and 041–042; kubectl, Windows PowerShell, isolated cluster with Pod Security Admission (PSA) enabled

## 1. Production scenario

A Deployment upgrade is rejected with `violates PodSecurity "restricted"`. The previous workload used root, allowed privilege escalation and omitted a seccomp profile. The on-call team must diagnose the admission response, modify the Pod template, verify the workload starts and preserve the namespace's security posture.

This chapter covers **Pod Security Standards (PSS)**, **Pod Security Admission (PSA)** and Linux security contexts. PSS defines policy profiles; PSA enforces or reports them through namespace labels. Security contexts define runtime privileges on Pods and containers.

### Learning objectives

1. Distinguish Privileged, Baseline and Restricted profiles.
2. Explain PSA enforce, audit and warn modes.
3. Apply namespace policies safely in a disposable lab.
4. Reproduce an admission rejection and interpret the error.
5. Configure non-root users, privilege escalation and Linux capabilities.
6. Apply seccomp RuntimeDefault and a read-only root filesystem.
7. Complete seven labs and a production security-incident acceptance exercise.

## 2. Security control layers

```text
User / CI / controller
          |
     Kubernetes API
          |
  Authentication + RBAC
          |
    Pod Security Admission
  (enforce / audit / warn)
          |
   Pod scheduled to node
          |
   Runtime security context
  (UID, capabilities, seccomp)
          |
    Container process
```

PSA checks Pod specifications against policy; it does not replace RBAC, image scanning, network policies, node hardening or runtime threat detection. Security contexts apply at Pod and/or container scope; container-specific settings may override relevant Pod-level defaults.

## 3. PSS profiles and admission modes

| Profile | Intent | Typical impact |
|---|---|---|
| Privileged | Unrestricted | Permits dangerous host and container privileges |
| Baseline | Prevent known privilege escalations | Restricts privileged containers, host namespaces and other risky settings |
| Restricted | Stronger hardening | Requires non-root-oriented controls, seccomp and capability restrictions |

| PSA mode | Behavior |
|---|---|
| `enforce` | Rejects violating Pod creation/updates covered by enforcement |
| `warn` | Returns warnings to the requesting client |
| `audit` | Annotates audit events for policy violations |

Namespace labels use `pod-security.kubernetes.io/enforce`, `warn`, `audit`, with optional `*-version` labels such as `latest` or a pinned supported Kubernetes minor version. In production, pin policy versions deliberately and test upgrades.

**Important:** a namespace labeled `restricted` is not proof every running Pod is compliant. Existing Pods are not automatically evicted when policy changes, and certain workload/controller checks can produce warnings rather than blocking a controller resource itself. Inspect new Pods and the actual admission results.

## 4. Lab prerequisites and safety

Use a disposable namespace and verify cluster support. These labs assume Linux nodes with an OCI-compatible container runtime.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl create namespace ch043
kubectl get namespace ch043 --show-labels
```

Do not relabel production namespaces. Some managed clusters enforce additional admission policies; record any differences rather than disabling protections.

## 5. Lab 1 — Establish Baseline policy and observe a safe Pod

```powershell
kubectl label namespace ch043 pod-security.kubernetes.io/enforce=baseline --overwrite
kubectl label namespace ch043 pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace ch043 pod-security.kubernetes.io/audit=restricted --overwrite
kubectl get namespace ch043 --show-labels
```

Save `ch043-baseline.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: baseline-demo
  namespace: ch043
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
```

```powershell
kubectl apply -f .\ch043-baseline.yaml
kubectl -n ch043 get pod baseline-demo
```

**Expected:** Baseline may admit the Pod while Restricted warnings identify missing hardening fields. Warning output depends on API version and admission configuration. The Pod may run as root even though it passes Baseline.

## 6. Lab 2 — Reproduce a Restricted admission rejection

Switch only the disposable namespace to Restricted enforcement:

```powershell
kubectl label namespace ch043 pod-security.kubernetes.io/enforce=restricted --overwrite
```

Save `ch043-insecure.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: insecure-demo
  namespace: ch043
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
kubectl apply -f .\ch043-insecure.yaml
kubectl -n ch043 get pod insecure-demo
```

**Expected:** Pod creation is rejected; no insecure Pod should exist. Capture the rejection reason without changing the namespace policy. The message may identify privileged mode, non-root, capabilities and seccomp requirements.

## 7. Lab 3 — Apply a Restricted-compatible security context

Save `ch043-restricted.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-demo
  namespace: ch043
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "id; sleep 36000"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        readOnlyRootFilesystem: true
```

```powershell
kubectl apply -f .\ch043-restricted.yaml
kubectl -n ch043 wait --for=condition=Ready pod/restricted-demo --timeout=120s
kubectl -n ch043 logs restricted-demo
kubectl -n ch043 get pod restricted-demo -o yaml
```

**Expected:** Pod is admitted and runs as UID/GID 10001. `readOnlyRootFilesystem` is an additional hardening control and is not itself required by the Restricted PSS profile. Image compatibility and node runtime support determine whether a Pod actually starts.

## 8. Lab 4 — Investigate UID, group and filesystem permissions

```powershell
kubectl -n ch043 exec restricted-demo -- id
kubectl -n ch043 exec restricted-demo -- sh -c 'test ! -w / && echo root-filesystem-not-writable'
kubectl -n ch043 describe pod restricted-demo
```

**Expected:** process uses non-root UID and root filesystem is not writable. Some applications require writable paths such as `/tmp`; provide a narrowly scoped `emptyDir` or persistent volume mount rather than disabling all hardening.

For a real application, inspect image `USER`, file ownership, supplemental groups, `fsGroup` behavior and storage driver semantics. `runAsNonRoot` can prevent startup when the image's effective user cannot be verified as non-root.

## 9. Lab 5 — Capabilities and privilege escalation

Compare the Restricted Pod configuration with an unsafe container specification:

```yaml
securityContext:
  allowPrivilegeEscalation: true
  capabilities:
    add: ["SYS_ADMIN"]
```

**Do not apply this unsafe configuration.** Under Restricted PSA, adding `SYS_ADMIN` and enabling privilege escalation violates the policy.

Inspect the safe Pod's configured controls:

```powershell
kubectl -n ch043 get pod restricted-demo -o jsonpath='{.spec.containers[0].securityContext.allowPrivilegeEscalation}'
kubectl -n ch043 get pod restricted-demo -o jsonpath='{.spec.containers[0].securityContext.capabilities.drop}'
kubectl -n ch043 get pod restricted-demo -o jsonpath='{.spec.securityContext.seccompProfile.type}'
```

**Expected:** `false`, `ALL`, `RuntimeDefault`. Linux capabilities are finer-grained privileges than full root access; dropping `ALL` is a useful default, and only explicitly justified capabilities should be reintroduced. Restricted PSS permits only tightly limited additions, subject to policy version.

## 10. Lab 6 — Namespace policy audit and staged rollout

Simulate a safe policy rollout in a second disposable namespace:

```powershell
kubectl create namespace ch043-audit
kubectl label namespace ch043-audit pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace ch043-audit pod-security.kubernetes.io/audit=restricted --overwrite
kubectl get namespace ch043-audit --show-labels
```

First review warnings in a non-enforcing namespace using a copied baseline Pod with `namespace: ch043-audit`. Save it as `ch043-audit-pod.yaml`, then:

```powershell
kubectl apply --dry-run=server -f .\ch043-audit-pod.yaml
```

**Expected:** warning output can reveal Restricted violations without creating a Pod. When ready, add `enforce=restricted` and deploy only compliant Pod templates. For production namespaces, inventory Deployments, DaemonSets, StatefulSets, Jobs, CronJobs and system add-ons before enforcing policy.

## 11. Lab 7 — Production security incident acceptance

Scenario: a rollout in a Restricted namespace fails after an image upgrade. The operator must distinguish admission rejection from a container runtime failure.

```powershell
kubectl get namespace ch043 --show-labels
kubectl -n ch043 get pods
kubectl -n ch043 get events --sort-by=.lastTimestamp
kubectl -n ch043 describe pod restricted-demo
kubectl -n ch043 get pod restricted-demo -o jsonpath='{.spec.securityContext}'
kubectl -n ch043 get pod restricted-demo -o jsonpath='{.spec.containers[0].securityContext}'
```

**Required diagnostic separation:**
- **Admission rejection:** the Pod object is not created; review API error and policy violations.
- **Scheduling failure:** Pod exists but remains Pending; inspect events and node resources.
- **Runtime/startup failure:** Pod exists but container fails; inspect status, logs, image user and filesystem permissions.
- **Readiness failure:** container runs but fails probes; inspect application and dependencies.

### Acceptance matrix

| Check | Evidence |
|---|---|
| Baseline | Namespace label and admitted baseline Pod |
| Restricted rejection | Rejected privileged Pod |
| Non-root | UID/GID verification |
| Privilege escalation | Disabled |
| Capabilities | ALL dropped |
| Seccomp | RuntimeDefault |
| Read-only filesystem | Write check denied |
| Staged policy | Warn/audit before enforce |
| Recovery | Corrected manifest accepted without policy downgrade |

## 12. Production hardening guidelines

- Enforce Restricted where application compatibility permits; use Baseline as a migration stage, not a permanent substitute for risk assessment.
- Apply warn/audit labels before enforce in existing namespaces.
- Pin policy versions and test Kubernetes upgrades.
- Run containers as non-root with an explicit, appropriate UID/GID.
- Set `allowPrivilegeEscalation: false` and drop unnecessary capabilities.
- Use `seccompProfile.type: RuntimeDefault`; consider AppArmor/SELinux where supported and required.
- Prefer read-only root filesystems with explicit writable mounts.
- Avoid privileged containers, hostNetwork, hostPID, hostIPC, hostPath and unnecessary host ports.
- Treat Pod Security Admission exemptions as sensitive cluster-wide configuration requiring strict review.
- Apply least-privilege RBAC, network policies, workload identity and image verification alongside PSS.
- Evaluate Linux and Windows workloads separately; supported PSS controls vary by OS and Kubernetes version.

## 13. Troubleshooting matrix

| Symptom | Likely cause | First check |
|---|---|---|
| `violates PodSecurity` | PSA policy rejection | API error, namespace labels |
| Pod Pending | Scheduler/resource constraints | Pod events |
| `runAsNonRoot` failure | Image user root or unverified | Pod status and image metadata |
| Permission denied on volume | UID/GID/fsGroup mismatch | Mount ownership, securityContext |
| Read-only filesystem error | App writes to image filesystem | Logs, writable mounts |
| Seccomp-related failure | Syscall restricted by profile | Runtime events, node logs |
| Capability required | Application expects privileged operation | Runtime requirement and risk review |
| Old Pods remain after policy change | PSA does not retroactively evict | Workload inventory and rollout |

## 14. Incident response runbook

1. Confirm namespace, workload, rollout time and affected SLI.
2. Capture admission error, Pod events and security-context manifests.
3. Identify exact Restricted/Baseline violation and whether it originates at Pod or container level.
4. Check image UID, filesystem needs, Linux capabilities, seccomp compatibility and storage ownership.
5. Correct the manifest or image; do not weaken namespace enforcement as the default recovery.
6. Validate in staging using server-side dry run and a representative runtime test.
7. Roll out gradually and verify Pods Ready, application transactions and error rates.
8. Document the exception process if a privileged workload is unavoidable; isolate and approve it separately.
9. Add CI policy validation and admission checks to prevent recurrence.

## 15. Cleanup

Only in disposable lab namespaces:

```powershell
kubectl -n ch043 get pods
kubectl delete namespace ch043
kubectl delete namespace ch043-audit
```

Do not remove or relabel shared namespaces or modify admission configuration cluster-wide.

## 16. Acceptance checklist

- [ ] PSS profiles and PSA modes explained.
- [ ] Baseline policy demonstrated.
- [ ] Restricted policy rejects unsafe Pod.
- [ ] Restricted-compatible Pod runs as non-root.
- [ ] Privilege escalation disabled and capabilities dropped.
- [ ] Seccomp RuntimeDefault verified.
- [ ] Read-only root filesystem behavior tested.
- [ ] Warn/audit rollout staged before enforce.
- [ ] Admission, scheduling and runtime failures distinguished.
- [ ] Production incident runbook and cleanup documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 17. References

- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Configure a Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [Pod Security Admission Namespace Labels](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/)

**Next:** Chapter 044 — Admission Policies and Image Security.
