# Chapter 047 — Jenkins Kubernetes Pod Templates, Resource Limits and Agent Security

**Part 10 — Jenkins on Kubernetes, EKS and AKS**  
**Audience:** SRE, Jenkins administrators, Kubernetes platform and security engineers  
**Prerequisites:** Chapter 046; disposable cluster; Jenkins Kubernetes plugin; dedicated agent namespace and low-privilege build service account.

## Learning objectives

Engineer repeatable Pod templates, understand Jenkins Kubernetes plugin YAML merging and agent injection, enforce resource requests/limits and Pod security, isolate credentials and workspaces, troubleshoot scheduling/OOM/eviction, and operate an auditable template rollout.

## 1. Pod-template architecture

```text
Reviewed Jenkinsfile or shared library
          ↓
Kubernetes cloud configuration
          ↓
Pod template (labels, containers, volumes, security, resources)
          ↓
Admission controls (PSS, policies, quotas)
          ↓
Kubernetes scheduler and node autoscaler
          ↓
Ephemeral Pod
  ├─ inbound Jenkins agent / remoting
  ├─ node/maven/python build container
  └─ emptyDir workspace / approved caches
```

Treat the controller's Kubernetes API provisioner identity and the Pod's workload service account as **different trust boundaries**. A template may be valid YAML but still fail Jenkins agent connection, admission policy, or scheduling.

## 2. Pod template configuration matrix

| Setting | Purpose | Operational consideration |
|---|---|---|
| `serviceAccountName` | Workload API identity | Prefer unprivileged account |
| `automountServiceAccountToken` | Token injection | Disable when API unused |
| `securityContext.runAsNonRoot` | Nonroot execution | Check image UID compatibility |
| `seccompProfile` | Syscall restriction | Use RuntimeDefault |
| `allowPrivilegeEscalation` | Block escalation | Set false per container |
| `capabilities.drop` | Reduce Linux capabilities | Drop ALL |
| `requests.cpu/memory` | Scheduling/capacity | Size from measured p95 |
| `limits.cpu/memory` | Bound usage | Avoid excessive throttling/OOM |
| `emptyDir` | Ephemeral workspace | Set sizeLimit where useful |
| `nodeSelector` / affinity | Workload placement | Avoid hard constraints without capacity |
| `tolerations` | Tainted nodes | Only trusted dedicated pools |
| `imagePullSecrets` | Private images | Namespace-scoped and rotated |
| `activeDeadlineSeconds` | Maximum Pod runtime | Coordinate with Jenkins timeout |

## 3. Dedicated build identity

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-build
  namespace: jenkins-build
automountServiceAccountToken: false
```

The build identity should not receive the controller provisioner's Role. Validate:

```sh
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create pods -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

Both should return `no` for this lab. For production, review all namespace roles and inherited cluster-wide bindings; an explicit lack of local RoleBinding is not proof of zero effective privileges.

## 4. Hardened agent Pod YAML

This is a **Pod template**, not a standalone Jenkins agent manifest. Jenkins injects or configures its inbound-agent container; validate its UID, workspace mount and Pod Security admission compatibility.

```yaml
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-build
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: node
      image: node:22-bookworm-slim
      command: ["sleep"]
      args: ["99d"]
      tty: true
      resources:
        requests:
          cpu: "250m"
          memory: "512Mi"
          ephemeral-storage: "512Mi"
        limits:
          cpu: "1"
          memory: "1Gi"
          ephemeral-storage: "2Gi"
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
```

For a production environment, pin the image to an approved registry digest. Node's official image normally provides a nonroot `node` user, but image default user may not be that user: set and verify `runAsUser` or use a custom approved image. `runAsNonRoot` alone does not choose the UID; it can cause Pod startup failure if the image defaults to root. See the corrected runnable lab Pod below, which sets `runAsUser: 1000` and `runAsGroup: 1000` for the tool container. Inbound-agent UID compatibility must be verified separately.

## 5. Jenkins Declarative Pipeline

```groovy
pipeline {
    agent {
        kubernetes {
            defaultContainer 'node'
            yaml '''
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-build
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: node
      image: node:22-bookworm-slim
      command: ["sleep"]
      args: ["99d"]
      tty: true
      resources:
        requests: {cpu: "250m", memory: "512Mi"}
        limits: {cpu: "1", memory: "1Gi"}
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
'''
        }
    }
    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
    }
    stages {
        stage('Identity') {
            steps {
                sh 'id; node --version; pwd'
            }
        }
        stage('Unit test') {
            steps {
                sh 'node -e "if (2 + 2 !== 4) process.exit(1)"'
            }
        }
        stage('Workspace evidence') {
            steps {
                sh 'printf "agent=%s\\n" "$(hostname)" > agent-evidence.txt'
                archiveArtifacts artifacts: 'agent-evidence.txt'
            }
        }
    }
}
```

**Important:** The plugin's injected `jnlp` container may have different security settings; validate it separately and harden the effective generated Pod, not only the YAML fragment. In some Jenkins/Kubernetes plugin combinations, `defaultContainer` changes where `sh` runs while the agent remoting container remains separate.

## 6. Resource sizing and QoS

CPU requests affect scheduler placement; CPU limits can cause throttling. Memory requests reserve scheduler capacity; exceeding memory limit typically causes OOM kill. A Pod is Guaranteed QoS only if **all** relevant containers specify equal CPU/memory requests and limits. A Pod with the example requests/limits will usually be Burstable. The injected agent container must be included in resource accounting.

Measure:
- Agent queue p50/p95 and Pod startup latency.
- Per-container CPU throttling and memory working set.
- OOMKilled, Evicted, Pending and image pull delays.
- Ephemeral storage usage and workspace growth.
- Autoscaler/Karpenter scale-up time and node fragmentation.

## 7. Quotas and LimitRanges

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: jenkins-build-quota
  namespace: jenkins-build
spec:
  hard:
    pods: "20"
    requests.cpu: "8"
    requests.memory: "16Gi"
    limits.cpu: "16"
    limits.memory: "32Gi"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: jenkins-agent-defaults
  namespace: jenkins-build
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: "100m"
        memory: "256Mi"
      default:
        cpu: "1"
        memory: "2Gi"
```

Values are **lab examples**, not production recommendations. Include the injected `jnlp` container and init containers when sizing. Validate quota against burst concurrency, autoscaling, and cluster capacity.

## 8. Pod template inheritance and merge risks

Kubernetes plugin templates can inherit named parent templates; merge strategy and container/volume overrides depend on plugin configuration/version. Do not assume YAML fragments always merge additively. Inspect the generated Pod YAML and test changes in staging. Avoid inherited privileged security contexts, unexpected service accounts, hostPath mounts or Docker socket access.

Use centrally reviewed shared libraries or centrally managed cloud templates for trusted build tiers, and keep untrusted PR agents separate from release identities.

## 9. Workspaces and caches

Default workspace lifecycle follows Pod lifetime. `emptyDir` is removed when the Pod is removed; `emptyDir.medium: Memory` counts toward memory use. PVC caches improve performance but can leak dependencies or secrets across builds. Scope cache keys by trust domain, sanitize artifacts, and define expiration and storage quotas.

Do not assume workspace files survive a Pod eviction; archive test and provenance evidence to durable Jenkins or object storage.

## 10. Failure diagnosis

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl describe pod -n jenkins-build <pod>
kubectl logs -n jenkins-build <pod> -c jnlp
kubectl get resourcequota,limitrange -n jenkins-build
kubectl top pods -n jenkins-build --containers
kubectl get pod -n jenkins-build <pod> -o yaml
```

`kubectl top` requires metrics-server. The injected agent container name can differ if overridden.

## 11. Troubleshooting matrix

| Failure | Diagnostic | Recovery |
|---|---|---|
| Pod Pending | Scheduler events | Fix capacity/affinity/quota |
| Admission rejected | PSS/policy events | Harden Pod template |
| RunAsNonRoot failure | Container startup events | Set approved numeric UID |
| Workspace permission denied | UID/fsGroup/mount | Align ownership |
| Agent never connects | `jnlp` logs | Fix URL/network/remoting |
| CPU throttling | cgroup metrics | Tune limits/requests |
| OOMKilled | Last termination state | Tune memory |
| Evicted | Node pressure/events | Capacity/storage |
| Ephemeral storage exceeded | Kubelet events | Quota/cleanup |
| ImagePullBackOff | Pull events | Fix digest/credentials |
| Wrong service account | Effective Pod spec | Fix inheritance |
| Unexpected token mount | SA/Pod automount | Disable and audit |
| Docker socket exposed | Pod volumes | Remove hostPath |
| Cache corruption | Shared PVC/cache keys | Isolate and rebuild |
| Template merge collision | Effective Pod YAML | Explicit strategy |
| Pod cleanup leak | Plugin logs/finalizers | Repair retention |
| LimitRange default mismatch | Effective resources | Adjust defaults |
| Node autoscaler delay | Node provisioning logs | Warm capacity |

## 12. Production runbooks

### A. Template onboarding
1. Approve image digest, service account and security context.
2. Validate admission, resources, quotas and placement.
3. Test Jenkins plugin injection and agent remoting.
4. Run unit test, archive evidence and confirm Pod cleanup.
5. Record template version and rollback reference.

### B. OOM and throttling
1. Capture container resource metrics, requests/limits and termination reason.
2. Identify workload change or resource regression.
3. Reproduce on disposable agents and tune limits.
4. Confirm queue latency and cost impact.
5. Publish updated template after review.

### C. Admission/RBAC failure
1. Inspect Pod events and Kubernetes audit logs.
2. Compare effective Pod against approved template.
3. Correct UID, capabilities, seccomp or service account.
4. Retest admission without broadening privileges.
5. Record policy exception only if formally approved.

### D. Agent compromise
1. Isolate affected Pod and preserve logs.
2. Revoke secrets and audit mounted tokens.
3. Inspect image provenance, Pod spec and network egress.
4. Rebuild trusted image and rotate credentials.
5. Verify namespace segmentation before resuming.

### E. Scheduling/eviction incident
1. Record Pending/Evicted events, quota and node pressure.
2. Review affinity, taints, topology and requests.
3. Restore capacity or tune template.
4. Validate agent startup p95 and cleanup.
5. Update SLO and capacity model.

## 13. Acceptance criteria

- [ ] Build Pod uses unprivileged service account.
- [ ] Agent Pod has no unnecessary API token.
- [ ] Tool container runs nonroot with dropped capabilities.
- [ ] Effective injected agent container inspected and hardened.
- [ ] Requests, limits, quota and QoS documented.
- [ ] Scheduling/OOM/admission failures exercised.
- [ ] Artifacts survive Pod cleanup.
- [ ] Template changes are versioned and reversible.

**Companion:** [Chapter 047 hands-on lab](labs/047-jenkins-kubernetes-pod-templates-resource-limits-agent-security-check.md).  
**Next:** Chapter 048 — Jenkins on Amazon EKS: IAM, IRSA/Pod Identity, Autoscaling and Operations.
