# Chapter 047 — Hands-on Lab: Kubernetes Pod Templates, Limits and Agent Security

**Environment:** Disposable Kubernetes cluster, Jenkins Kubernetes plugin, isolated `jenkins-build` namespace and two distinct service accounts: provisioner and build.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins/plugin/K8s versions | Baseline |
| 02 | Trust map | Separate provisioner/build identities | Diagram |
| 03 | Build SA | Create `jenkins-build` SA | Manifest |
| 04 | Token control | Disable automount | Pod spec |
| 05 | RBAC negative | Verify no Secrets listing | `can-i` |
| 06 | Template | Define Node tool container | YAML |
| 07 | Numeric UID | Set runAsUser/runAsGroup 1000 | Pod spec |
| 08 | Seccomp | Set RuntimeDefault | Pod spec |
| 09 | Capabilities | Drop ALL and no escalation | Pod spec |
| 10 | Resources | Configure requests/limits | Manifest |
| 11 | Quota | Apply lab ResourceQuota | Quota |
| 12 | LimitRange | Apply defaults | LimitRange |
| 13 | Launch | Run Jenkins dynamic Pod Pipeline | Build URL |
| 14 | Inspect | Compare effective injected Pod YAML | Diff |
| 15 | Workspace | Write/collect evidence | Artifact |
| 16 | Cleanup | Confirm ephemeral Pod removed | Event |
| 17 | Scheduling fault | Exceed lab quota | Rejection |
| 18 | UID fault | Force invalid nonroot startup | Event |
| 19 | OOM fault | Use disposable low memory limit | OOMKilled |
| 20 | Recovery | Restore template and rerun | Pass |

## 12 troubleshooting drills

1. Pod Pending from quota.
2. Node affinity mismatch.
3. Pod Security admission rejection.
4. `runAsNonRoot` startup failure.
5. Workspace permission denied.
6. Injected inbound agent cannot connect.
7. CPU throttling.
8. OOMKilled.
9. Ephemeral-storage eviction.
10. ImagePullBackOff.
11. Wrong inherited service account.
12. Pod cleanup or cache contamination.

Use small synthetic workloads only; do not intentionally destabilize shared nodes. Capture exact Kubernetes events and recovery evidence.

## Starter build service account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-build
  namespace: jenkins-build
automountServiceAccountToken: false
```

## Operational commands

```sh
kubectl apply -f build-serviceaccount.yaml
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl get resourcequota,limitrange -n jenkins-build
kubectl top pods -n jenkins-build --containers
```

The `kubectl top` command requires metrics-server. The expected Secrets listing result is `no`; any `yes` is a security failure requiring investigation.

## Evidence template

```text
UTC timestamp:
Jenkins core / Kubernetes plugin:
Cluster version / namespace:
Provisioner SA:
Build SA:
Effective Pod YAML / hash:
Container UID and security context:
Requests/limits/QoS:
Quota/LimitRange:
Queue and Pod startup time:
Build URL / artifact:
Injected failure and Kubernetes event:
Root cause and recovery:
Cleanup verification:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or marked blocked.
- [ ] Build SA cannot list Secrets or create Pods.
- [ ] Tool container runs as numeric nonroot UID.
- [ ] Effective injected `jnlp` container inspected.
- [ ] Resource sizing and quota validated.
- [ ] Failure and recovery evidence preserved.
- [ ] Workspace artifacts archived before Pod deletion.
- [ ] No privileged Docker socket or unnecessary token.
- [ ] Reviewer signs off.

**Related:** [Chapter 047 — Jenkins Kubernetes Pod Templates, Resource Limits and Agent Security](../047-jenkins-kubernetes-pod-templates-resource-limits-agent-security.md).
