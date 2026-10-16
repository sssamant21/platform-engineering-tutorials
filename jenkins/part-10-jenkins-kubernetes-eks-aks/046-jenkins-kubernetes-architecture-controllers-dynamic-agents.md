# Chapter 046 — Jenkins on Kubernetes: Architecture, Controllers and Dynamic Agents

**Part 10 — Jenkins on Kubernetes, EKS and AKS**  
**Audience:** Jenkins SRE, Kubernetes platform engineering, DevOps and security teams  
**Prerequisites:** Chapters 001–045; disposable Kubernetes cluster; kubectl/Helm; isolated Jenkins controller; approved Jenkins Kubernetes plugin.

## Learning outcomes

Design controller/agent topology, provision ephemeral Jenkins agents as Kubernetes Pods, enforce RBAC and namespace boundaries, configure Pod templates and containerized build steps, diagnose scheduling and connection failures, and define operational recovery and acceptance checks.

## 1. Reference architecture

```text
Developers → Git provider → Jenkins controller (Deployment/StatefulSet)
                                │
                  Jenkins Kubernetes plugin
                                │ Kubernetes API
                                ▼
                   Namespace: jenkins-build
                ┌───────────────┴───────────────┐
                │ ephemeral agent Pods           │
                │ jnlp / inbound-agent container │
                │ tool container (maven/node)    │
                └───────────────┬───────────────┘
                                │
                  logs, workspace, artifact upload
                                ▼
                      registry/artifact store
```

The controller handles orchestration, credentials, scheduling and state; agents execute untrusted or semi-trusted builds with carefully bounded permissions. **Do not run arbitrary user workloads on the controller.** Jenkins controller persistence, backup, network ingress and upgrade strategy are separate from ephemeral agent lifecycles.

## 2. Controller versus agent

| Dimension | Controller | Kubernetes agent Pod |
|---|---|---|
| Lifetime | Long-lived, managed upgrade | Ephemeral per workload |
| State | JENKINS_HOME, configuration, jobs | Workspace and temporary files |
| Privileges | Jenkins administration and API access | Minimum job-specific rights |
| Resource profile | Predictable baseline | Bursty requests/limits |
| Storage | Durable PVC + backup | Ephemeral or job-specific PVC |
| Failure response | Restore service/state | Recreate agent and retry safe work |
| Network | SCM, identity, API, agent channel | Controller, dependencies, artifacts |

Avoid multiple active controllers sharing a single writable `JENKINS_HOME`. For HA, use a supported architecture rather than scaling controller replicas against one PVC.

## 3. Kubernetes plugin provisioning sequence

1. A Jenkins Pipeline requests a Kubernetes cloud agent with a Pod template.
2. Jenkins authenticates to Kubernetes using in-cluster service account or approved credentials.
3. Plugin creates Pod in authorized namespace.
4. Scheduler assigns node; image pull and volumes initialize.
5. Inbound agent connects to controller using supported remoting transport (typically WebSocket or TCP).
6. Jenkins executes stages in agent containers.
7. Workspace artifacts are archived and Pod is deleted/retained per policy.

Cloud connection, Pod scheduling, image pulls, agent remoting and tool-container commands are distinct failure domains.

## 4. Namespace and service account baseline

Use a dedicated namespace and service account for Jenkins agent provisioning. RBAC should be derived from the plugin's **documented minimum required permissions for the installed version** and tested in a disposable cluster. This illustrative Role supports agent Pod lifecycle and log access, but verify any additional required operations:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: jenkins-build
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-provisioner
  namespace: jenkins-build
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: jenkins-agent-manager
  namespace: jenkins-build
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch", "create", "delete", "patch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create", "get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: jenkins-agent-manager
  namespace: jenkins-build
subjects:
  - kind: ServiceAccount
    name: jenkins-provisioner
    namespace: jenkins-build
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: jenkins-agent-manager
```

**Important:** The provisioner service account belongs to the controller (or its dedicated Kubernetes API identity), not necessarily the build Pod. The build Pod should use a **separate low-privilege service account**, with `automountServiceAccountToken: false` when Kubernetes API access is not required. Never assign agent Pods the controller's provisioner token.

## 5. Jenkins controller deployment decisions

For a new deployment, use an organization-approved Jenkins Helm chart/version and pinned controller/plugins; validate the chart's current values schema rather than copying outdated values. Typical production controls: restricted ingress/TLS, persistent JENKINS_HOME, resource requests/limits, readiness/startup probes, admin authentication/authorization, plugin pinning, configuration-as-code, secrets integration, backup/restore, network policies, and maintenance/upgrade runbooks.

A lab controller may be deployed using Helm, but do not publish a hardcoded default admin password or expose it to the public internet.

## 6. Declarative Pipeline with dynamic Pod agent

Requires Jenkins Kubernetes plugin and a configured Kubernetes cloud:

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
        limits:
          cpu: "1"
          memory: "1Gi"
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
'''
        }
    }
    options { timestamps(); timeout(time: 20, unit: 'MINUTES') }
    stages {
        stage('Identity') {
            steps {
                sh 'id && uname -a'
                sh 'node --version'
            }
        }
        stage('Test') {
            steps {
                sh 'node -e "if (2+2!==4) process.exit(1)"'
            }
        }
    }
}
```

**Prerequisite:** Create the separate `jenkins-build` service account in the agent namespace with no RBAC grants by default. The plugin injects its inbound-agent container unless overridden; pod-level `runAsNonRoot` may require compatible image/UID settings for the injected agent. Validate the generated Pod before enforcing all controls. Production images should be pinned to approved digests, and long `sleep` is a teaching fixture rather than an application runtime pattern.

## 7. Kubernetes manifests for low-privilege build identity

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-build
  namespace: jenkins-build
automountServiceAccountToken: false
```

Use dedicated identities for different job trust tiers (untrusted PR, trusted build, release). Never share publisher credentials with PR jobs.

## 8. Workspace, cache and artifacts

The default ephemeral workspace is deleted with the Pod. Archive build results to Jenkins artifact storage or external object storage before Pod termination. For large builds, consider workspace PVCs, but avoid cross-build contamination and concurrency hazards. Shared cache volumes may leak data across trust tiers; isolate by repository/identity and define cache eviction.

For Docker/OCI builds, do not expose rootful host Docker socket to untrusted agents. Use approved rootless BuildKit, isolated builders or managed build services.

## 9. Scheduling and capacity planning

| Signal | Check | Remediation |
|---|---|---|
| Agent queue time | Jenkins queue, Pod create latency | Tune concurrency/capacity |
| Pending Pods | `kubectl describe pod` | Requests, quota, node capacity |
| ImagePullBackOff | Pod events, registry auth | Correct image/secret |
| OOMKilled | Pod last state, limits | Size requests/limits |
| Evicted | Node pressure | Improve capacity/storage |
| Agent disconnect | Remoting logs/network | Restore controller route |
| API throttling | Controller logs, API metrics | Reduce burst/adjust quota |
| PVC pending | StorageClass events | Repair storage provisioning |
| Node scale-up delay | Cluster autoscaler/Karpenter | Right-size warm capacity |
| High cloud cost | Idle nodes, oversized agents | Right-size and lifecycle |

## 10. Operational diagnostics

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl describe pod -n jenkins-build <agent-pod>
kubectl logs -n jenkins-build <agent-pod> -c jnlp
kubectl auth can-i create pods -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-provisioner
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl get resourcequota,limitrange -n jenkins-build
```

Expected: the provisioner may create Pods; the low-privilege build identity should not list Secrets. Replace `<agent-pod>` with an actual Pod name. `jnlp` is the conventional injected container name, but inspect actual container names for customized templates.

## 11. Troubleshooting matrix

| Failure | Evidence | Recovery |
|---|---|---|
| Cloud connection failed | Jenkins plugin logs | Check API endpoint/TLS/identity |
| Pod create forbidden | Kubernetes 403 | Correct namespace Role |
| Pod Pending | Events and scheduler | Quota/capacity/affinity |
| ImagePullBackOff | Pull events | Fix digest/registry access |
| CrashLoopBackOff | Container logs | Correct entrypoint/config |
| Agent never connects | `jnlp` logs | Fix controller URL/WebSocket |
| Agent disconnects | Network/proxy logs | Repair routing/timeouts |
| Permission denied workspace | UID/fsGroup/PVC | Fix ownership policy |
| OOMKilled | Container status | Tune limits |
| Node pressure Evicted | Node events | Expand capacity |
| API rate limits | 429, controller logs | Smooth provisioning bursts |
| Wrong Pod template | Generated Pod YAML | Review inheritance/merge |
| Secret exposure | Pod spec/logs | Revoke, rotate, restrict |
| Token mounted unexpectedly | Service account config | Disable automount |
| Pod not cleaned | Plugin logs/finalizers | Review retention and cleanup |
| Cluster autoscaler delay | Node provisioning events | Capacity planning |

## 12. Production runbooks

### A. Controller/Kubernetes onboarding
1. Approve namespace, identity, RBAC, plugin/chart versions and network path.
2. Deploy controller with persistence, TLS, authentication and backup.
3. Configure Kubernetes cloud and separate provisioner/build identities.
4. Run a synthetic ephemeral agent pipeline.
5. Verify artifact capture, Pod cleanup and metrics.
6. Document failure and rollback procedures.

### B. Agent provisioning outage
1. Capture queue length, Pod create error, cloud config and API events.
2. Separate authorization, scheduling, image pull and remoting failures.
3. Stop repeated unsafe retries and preserve logs.
4. Correct root cause, launch one test agent.
5. Verify queue drain and Pod cleanup.

### C. Agent Pod security incident
1. Quarantine affected namespace/Pod and preserve evidence.
2. Revoke exposed credentials and audit Kubernetes API actions.
3. Validate Pod template, image provenance and network policies.
4. Rebuild from trusted image and restore approved identities.
5. Review blast radius and security sign-off.

### D. Controller outage
1. Confirm controller health, PVC and Kubernetes events.
2. Avoid parallel controllers sharing writable JENKINS_HOME.
3. Restore from tested backup or recover supported controller deployment.
4. Validate job configuration, credentials references and agents.
5. Rerun safe/idempotent jobs and document incident.

### E. Capacity and cost regression
1. Measure queue p95, Pod startup, resource requests/limits and node utilization.
2. Identify oversized templates, cold pulls and idle node pools.
3. Tune quotas, caching and node autoscaling safely.
4. Compare baseline and post-change SLO/cost.
5. Retain audit evidence.

## 13. Acceptance checklist

- [ ] Controller and agent responsibilities documented.
- [ ] Provisioner Role scoped to agent namespace.
- [ ] Build Pod service account has no unnecessary Kubernetes privileges.
- [ ] Ephemeral agent Pipeline passes.
- [ ] Pod events and remoting logs can be diagnosed.
- [ ] Pod cleanup and artifact retention verified.
- [ ] Scheduling/OOM/image pull failures rehearsed.
- [ ] Backup and rollback responsibilities documented.

**Companion:** [Chapter 046 hands-on lab](labs/046-jenkins-kubernetes-architecture-controllers-dynamic-agents-check.md).  
**Next:** Chapter 047 — Jenkins Kubernetes Pod Templates, Resource Limits and Agent Security.
