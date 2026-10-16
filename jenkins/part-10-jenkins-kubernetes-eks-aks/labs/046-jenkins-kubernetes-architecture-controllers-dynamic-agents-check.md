# Chapter 046 — Hands-on Lab: Jenkins Kubernetes Controllers and Dynamic Agents

**Environment:** Disposable Kubernetes cluster, Jenkins Kubernetes plugin, isolated controller and agent namespace. Use nonproduction credentials only.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Kubernetes/Jenkins/plugin versions | Baseline |
| 02 | Topology | Diagram controller, API, agents | Architecture |
| 03 | Namespace | Create `jenkins-build` | Namespace |
| 04 | Provisioner identity | Create `jenkins-provisioner` SA | SA |
| 05 | RBAC | Apply minimal Role/RoleBinding | Manifest |
| 06 | Auth check | Verify provisioner can create Pods | `can-i` |
| 07 | Build identity | Create unprivileged `jenkins-build` SA | SA |
| 08 | Negative auth | Verify build SA cannot list Secrets | Denied |
| 09 | Cloud config | Configure Kubernetes plugin | Settings |
| 10 | Pod template | Define Node.js agent container | YAML |
| 11 | Agent launch | Execute Jenkins Pipeline | Build URL |
| 12 | Pod inspection | Inspect generated Pod spec | YAML |
| 13 | Test | Run Node smoke expression | Pass |
| 14 | Workspace | Record workspace lifecycle | Evidence |
| 15 | Artifacts | Archive a test report | Artifact |
| 16 | Cleanup | Confirm agent Pod deletion | Event |
| 17 | Scheduling fault | Exceed disposable quota | Pending |
| 18 | Image fault | Use nonexistent test image | Pull failure |
| 19 | Recovery | Restore Pod template, rerun | Pass |
| 20 | Review | Assess isolation and ownership | Sign-off |

## 12 troubleshooting drills

1. Kubernetes cloud API unreachable.
2. Provisioner 403 creating Pods.
3. Agent Pod Pending due to quota.
4. Unschedulable CPU/memory request.
5. ImagePullBackOff.
6. Container CrashLoopBackOff.
7. Inbound agent remoting timeout.
8. Workspace permission denied.
9. OOMKilled.
10. Node pressure Evicted.
11. Pod template inheritance mismatch.
12. Agent Pod cleanup/retention failure.

## Starter manifests

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: jenkins-build
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-build
  namespace: jenkins-build
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-provisioner
  namespace: jenkins-build
```

Grant the provisioner only plugin-required Pod lifecycle permissions as documented in Chapter 046. Do not grant the build service account the provisioner's Role.

## Operational commands

```sh
kubectl apply -f namespace-and-serviceaccounts.yaml
kubectl get sa -n jenkins-build
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl get resourcequota,limitrange -n jenkins-build
```

Expected: the build service account must not list Secrets. The lab assumes kubectl has permission to create these objects in a disposable cluster.

## Evidence template

```text
UTC timestamp:
Jenkins core / Kubernetes plugin version:
Kubernetes version and cluster:
Controller namespace and identity:
Agent namespace and provisioner SA:
Build SA permissions:
Pod template hash:
Agent Pod name / node:
Build URL / test result:
Pod creation and connection latency:
Injected failure and events:
Root cause and recovery:
Cleanup result:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Provisioner identity scoped to agent namespace.
- [ ] Build identity cannot read Kubernetes Secrets.
- [ ] Ephemeral agent starts, executes and cleans up.
- [ ] Pod scheduling and remoting failures diagnosed.
- [ ] No rootful Docker socket mounted to untrusted builds.
- [ ] Controller state and backup policy documented.
- [ ] Reviewer signs off.

**Related:** [Chapter 046 — Jenkins on Kubernetes Architecture and Dynamic Agents](../046-jenkins-kubernetes-architecture-controllers-dynamic-agents.md).
