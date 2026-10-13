# Chapter 004 — Control Plane, Worker Nodes and etcd

**Track:** Kubernetes Administration · **Part:** 01 — Kubernetes Fundamentals · **Level:** Intermediate · **Status:** Draft — lab execution pending

## 1. Learning objectives

After this chapter, you should be able to:
1. Explain control-plane and worker-node responsibilities, failure domains, and operational ownership.
2. Understand how API server, scheduler, controller manager, kubelet, runtime, and etcd interact.
3. Explain etcd consistency, quorum, membership, snapshots, and safe recovery boundaries.
4. Inspect control-plane and node health using Kubernetes APIs and a disposable kind cluster.
5. Simulate a worker-node outage without changing a production cluster.
6. Interpret node conditions, Pod placement, controller reconciliation, and workload availability.
7. Differentiate self-managed Kubernetes from EKS, AKS, and GKE operations.

## 2. Architecture and failure domains

```text
                        kubectl / GitOps / CI
                                |
                       Kubernetes API server
                         /       |        \
                 scheduler  controller mgr  etcd
                      |           |          |
                      +---- API state -------+
                                |
                    +-----------+-----------+
                    |                       |
                 Worker A                Worker B
                 kubelet                 kubelet
                 containerd              containerd
                 CNI / networking        CNI / networking
                 application Pods        application Pods
```

The API server is the entry point to cluster state. Controllers reconcile desired state; the scheduler assigns unscheduled Pods; kubelets run assigned Pods through the container runtime. etcd persists Kubernetes API state.

**Critical distinction:** An unavailable control plane can prevent new scheduling, API-driven changes, and some recovery operations, while already-running containers may continue serving traffic for a time. An unavailable worker node affects workloads on that node; recovery depends on replicas, topology, storage, node monitoring, and available capacity. Neither behavior guarantees application availability.

## 3. Control-plane components

| Component | Function | Failure signals | Operator focus |
|---|---|---|---|
| kube-apiserver | Authenticates, authorizes, validates and serves API requests | API errors, high latency, readiness failure | Endpoint reachability, audit/errors, etcd dependency |
| etcd | Strongly consistent API-state store | Quorum loss, latency, disk pressure, failed proposals | Member health, storage, snapshots, tested restore |
| kube-scheduler | Chooses nodes for eligible Pods | Pending Pods, scheduling latency, FailedScheduling events | Resource requests, placement constraints |
| kube-controller-manager | Runs reconciliation loops | Delayed reconciliation, missing replacements | Controller health, API connectivity, work queues |
| cloud-controller-manager | Cloud-specific node and load balancer integrations | Cloud resource reconciliation failures | Provider permissions, API quotas, controller logs |

Control-plane processes are often static Pods in kubeadm/kind. Managed platforms hide or abstract much of this infrastructure.

## 4. Worker-node components

- **kubelet:** receives assigned Pod specifications and reports node/Pod status.
- **Container runtime:** containerd or CRI-O handles images, sandboxes, and containers through CRI.
- **CNI:** provisions Pod networking, with implementation depending on the cluster.
- **Service dataplane:** commonly kube-proxy, or an alternative eBPF-based implementation.
- **CSI node plugin:** where installed, supports volume attachment/mount operations.

### Node status and conditions

`Ready` indicates whether the node can accept and run Pods according to kubelet/node-health signals. `MemoryPressure`, `DiskPressure`, and `PIDPressure` provide additional resource-pressure signals. A `Ready` node can still have an application-level outage; use workload and service SLIs as well.

### Control-plane nodes can run Pods

A Kubernetes node with the control-plane role still has kubelet and a runtime. It may be tainted to discourage regular workloads, but this is a scheduling policy, not a hard architectural separation. This chapter uses a two-node kind cluster: one control-plane node and one worker.

## 5. etcd fundamentals

### 5.1 What etcd stores

etcd stores Kubernetes cluster API objects and metadata, not application database files or container image layers. Kubernetes resource objects may include Secrets, so access to etcd data and snapshots must be tightly controlled and encrypted at rest according to policy.

### 5.2 Consensus and quorum

etcd uses Raft consensus. A cluster of **N voting members** generally requires a majority: `floor(N/2)+1`.

| Voting members | Quorum | Tolerated voting-member failures |
|---:|---:|---:|
| 1 | 1 | 0 |
| 2 | 2 | 0 |
| 3 | 2 | 1 |
| 5 | 3 | 2 |

A three-member etcd cluster tolerates one member failure, assuming remaining members can communicate and are healthy. More members do not automatically improve performance; network latency and disk fsync performance matter.

### 5.3 Operational risks

- Slow disks and fsync latency can increase API write latency.
- Quorum loss can prevent API state changes.
- Defragmentation, compaction, membership changes, and restore operations require version-specific procedures and maintenance controls.
- Snapshot creation and **restoration** are separate competencies. A snapshot that has never been restored in a test environment is not a proven recovery strategy.
- A restored etcd snapshot represents a **point-in-time** API state. It does not automatically restore application data stored in external databases or persistent volumes.

**Production warning:** Never experiment with `etcdctl member remove`, direct key writes, snapshot restoration, or stopping etcd members on a live cluster. The hands-on lab below is deliberately read-only with respect to etcd.

## 6. Prerequisites and environment

Use Windows PowerShell with:
- Docker Desktop (or compatible container engine)
- `kind` and `kubectl`
- Approximately 4 CPUs and 6 GiB available RAM recommended for the two-node lab; requirements vary
- Internet access to pull the kind node image and NGINX image, unless cached

Check:

```powershell
docker version
kind version
kubectl version --client
```

This is a disposable local exercise. Do not reuse an EKS, AKS, GKE, staging, or production context.

## 7. Lab A — Build a control-plane + worker cluster

### Step A1 — Write the cluster configuration

In an empty working directory:

```powershell
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-ch004.yaml
```

### Step A2 — Create and inspect

```powershell
kind create cluster --name k8s-admin-ch004 --config .\kind-ch004.yaml --wait 180s
kubectl config current-context
kubectl get nodes -o wide
kubectl get nodes --show-labels
```

**Expected:** context `kind-k8s-admin-ch004`, one control-plane node and one worker node, both eventually `Ready`. Exact node versions and addresses vary.

**Safety gate:** Do not proceed unless the active context is exactly `kind-k8s-admin-ch004`.

### Step A3 — Identify node components

```powershell
kubectl describe node k8s-admin-ch004-worker
kubectl get nodes -o custom-columns='NAME:.metadata.name,RUNTIME:.status.nodeInfo.containerRuntimeVersion,KUBELET:.status.nodeInfo.kubeletVersion'
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get daemonsets
```

**Expected:** runtime and kubelet versions, node capacity and conditions, control-plane static Pods, and cluster add-ons. The exact DaemonSet list depends on the kind/Kubernetes release.

## 8. Lab B — Inspect control-plane health and etcd safely

### Step B1 — API health and component visibility

```powershell
kubectl cluster-info
kubectl get --raw /livez
kubectl get --raw /readyz
kubectl -n kube-system get pods -l component=kube-apiserver
kubectl -n kube-system get pods -l component=kube-scheduler
kubectl -n kube-system get pods -l component=kube-controller-manager
kubectl -n kube-system get pods -l component=etcd
```

**Expected:** healthy API endpoints return `ok`; control-plane Pods appear in kube-system on a typical kind installation. Some distributions restrict health endpoints or use different Pod labels.

### Step B2 — Inspect etcd Pod and logs (read-only)

```powershell
kubectl -n kube-system get pod -l component=etcd -o wide
kubectl -n kube-system logs -l component=etcd --tail=40 --prefix=true
kubectl -n kube-system describe pod -l component=etcd
```

**Expected:** one etcd static Pod in this single-control-plane kind cluster. Logs show startup, leader, and request activity. Log lines vary by release and may include benign warnings; interpret them in context.

### Step B3 — Optional local-only etcd endpoint status

This optional exercise reads etcd status **inside the disposable kind control-plane container**. Paths and image tooling can vary by kind version.

```powershell
docker exec k8s-admin-ch004-control-plane sh -c 'command -v etcdctl || true'
docker exec k8s-admin-ch004-control-plane sh -c 'ls -l /etc/kubernetes/pki/etcd/ca.crt /etc/kubernetes/pki/etcd/healthcheck-client.crt /etc/kubernetes/pki/etcd/healthcheck-client.key'
```

If `etcdctl` is available and those files exist:

```powershell
docker exec k8s-admin-ch004-control-plane sh -c 'ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt --key=/etc/kubernetes/pki/etcd/healthcheck-client.key endpoint health'
```

**Expected:** the endpoint reports healthy. If `etcdctl` is not installed, **skip this optional step**; do not download unverified binaries or change control-plane configuration to force it. The command is read-only and targets only the local disposable cluster.

## 9. Lab C — Pod placement and worker-node disruption

### Step C1 — Deploy an application on the worker

```powershell
kubectl create namespace ch004
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-web
  namespace: ch004
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker-web
  template:
    metadata:
      labels:
        app: worker-web
    spec:
      nodeSelector:
        kubernetes.io/hostname: k8s-admin-ch004-worker
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
            limits:
              cpu: 250m
              memory: 128Mi
'@ | Set-Content -Encoding ascii .\ch004-worker-web.yaml

kubectl apply -f .\ch004-worker-web.yaml
kubectl -n ch004 rollout status deployment/worker-web --timeout=180s
kubectl -n ch004 get pods -o wide
```

**Expected:** two Pods are Ready on `k8s-admin-ch004-worker`. If Pods remain Pending, inspect `kubectl -n ch004 describe pod <name>` and verify the node hostname label. Node labels are implementation-specific, so confirm the actual value rather than guessing in other environments.

### Step C2 — Simulate a worker outage (disposable cluster only)

Record baseline:

```powershell
kubectl get nodes
kubectl -n ch004 get pods -o wide
```

Stop the kind worker's Docker container:

```powershell
docker stop k8s-admin-ch004-worker
```

Wait for node health detection (this can take several minutes), then inspect:

```powershell
kubectl get nodes
kubectl -n ch004 get pods -o wide
kubectl -n ch004 get events --sort-by=.lastTimestamp
kubectl describe node k8s-admin-ch004-worker
```

**Expected:** the worker may transition to `NotReady` or `Unknown` after node monitoring timeouts. The Pods cannot serve from a stopped node. Their API status may lag actual availability, and replacement may be delayed by tolerations/eviction settings. Since this Deployment requires the stopped worker by nodeSelector, its replicas **cannot relocate to the control-plane node** while the worker is unavailable.

This is an intentional demonstration of a placement constraint becoming an availability risk. Do not interpret a temporary `Running` API phase as proof of reachable traffic.

### Step C3 — Recover the worker

```powershell
docker start k8s-admin-ch004-worker
kubectl get nodes -w
```

Wait until the worker returns `Ready`, then press Ctrl+C to stop watching:

```powershell
kubectl -n ch004 rollout status deployment/worker-web --timeout=240s
kubectl -n ch004 get pods -o wide
kubectl -n ch004 get events --sort-by=.lastTimestamp
```

**Expected:** worker recovers and Deployment eventually returns to two Ready replicas. Recovery time varies. If recovery fails, inspect kubelet/container runtime/node conditions before deleting resources.

### Step C4 — Compare with a scheduler-friendly placement policy

**Discussion exercise:** In a real multi-worker cluster, replacing the hard `nodeSelector` with a topology-aware preference and sufficient spare capacity can allow relocation. Do not remove node constraints blindly: workload data locality, storage, security, GPU requirements, and compliance may require explicit placement.

## 10. etcd and control-plane troubleshooting runbook

### Symptom: API requests fail or time out

1. Confirm scope: one operator client or all API clients? Check DNS, network, authentication, and control-plane endpoint.
2. Capture timestamp, exact errors, `kubectl cluster-info`, and provider health signals.
3. On self-managed clusters, inspect API server and etcd logs and readiness.
4. Check etcd disk space, fsync latency, leader stability, member reachability, and quorum using **approved read-only** diagnostics.
5. Avoid restart loops and member removal. Escalate quorum loss or data corruption to a tested disaster-recovery procedure.

### Symptom: Node is NotReady

1. `kubectl describe node <node>`: examine conditions, taints, events, and last heartbeat.
2. Inspect node host reachability, kubelet, runtime, disk, memory, and CNI.
3. Assess affected Pods, PodDisruptionBudgets, volumes, and alternative capacity.
4. If a drain/replacement is necessary, follow change control and workload-specific recovery steps.

### Symptom: Pods remain Pending

1. `kubectl describe pod <pod>` and inspect `FailedScheduling` events.
2. Verify resource requests, nodeSelector, affinity, taints, topology constraints, and PVC bindings.
3. Check actual node allocatable capacity and cluster-autoscaler behavior.
4. Fix the constraint or capacity issue rather than repeatedly deleting Pods.

### Quick reference

| Signal | Possible cause | Evidence |
|---|---|---|
| API readiness failure | etcd dependency, admission issues, control-plane faults | API readiness details, API logs |
| etcd no leader/quorum | member or network failures | Approved endpoint/member status checks |
| High etcd fsync latency | Storage I/O bottleneck | etcd metrics and disk telemetry |
| Worker NotReady | kubelet, runtime, CNI, resource pressure | Node conditions and host diagnostics |
| Pods Pending | Scheduling constraints or capacity | Pod events, scheduler diagnostics |
| Pods Running but unavailable | Network or application readiness | Service endpoints, probes, application SLIs |

## 11. Managed platform operational boundaries

| Concern | kubeadm/self-managed | Amazon EKS | Azure AKS | Google GKE |
|---|---|---|---|---|
| API server/etcd operation | Your team | AWS | Azure | Google |
| Control-plane upgrade | Your team | Provider-managed workflow, user-initiated/version controls | Provider-managed workflow, user-initiated/version controls | Provider-managed workflow with release channels and upgrade policies |
| Worker lifecycle | Your team | Depends on managed node groups, self-managed nodes, Fargate, etc. | Depends on node pools/mode | Depends on Standard/Autopilot |
| Workload readiness, security, backups | Your team | Shared responsibility | Shared responsibility | Shared responsibility |
| etcd direct access | Possible with strict controls | Typically unavailable | Typically unavailable | Typically unavailable |

Managed control-plane availability does not eliminate node, application, network, IAM, cost, or data-recovery responsibilities. Use provider-native metrics, events, and support escalation for inaccessible control-plane internals.

## 12. Production reliability and security practices

- Design control-plane and etcd quorum across independent failure domains where supported; avoid even-sized etcd membership without a specific reason.
- Use fast, reliable etcd storage; monitor WAL/fsync latency, leader changes, disk capacity, and request failures.
- Encrypt and access-control etcd snapshots. Test restore in isolated environments; maintain version-compatible recovery instructions.
- Maintain multiple workers across availability zones for critical workloads, with capacity headroom and topology spread.
- Use workload probes, disruption budgets, resource requests, and realistic node failure simulations.
- Separate read-only diagnosis from disruptive actions. Do not stop nodes or etcd members in production without approved maintenance or incident procedures.
- Understand that Kubernetes API-state backups are not substitutes for application data backups.

## 13. Acceptance checklist

- [ ] Verified Docker, kind, kubectl and current context.
- [ ] Created a disposable two-node cluster.
- [ ] Inspected API health and control-plane Pods.
- [ ] Inspected worker conditions, kubelet and runtime versions.
- [ ] Inspected etcd logs without modifying cluster state.
- [ ] Deployed two Pods constrained to the worker.
- [ ] Stopped the disposable worker and observed node/workload effects.
- [ ] Restarted worker and verified recovery.
- [ ] Documented differences between self-managed and managed control planes.
- [ ] Cleaned up local resources.

## 14. Cleanup and rollback

Before cleanup, check context:

```powershell
kubectl config current-context
```

Proceed **only** if the output is `kind-k8s-admin-ch004`:

```powershell
kubectl delete namespace ch004
kind delete cluster --name k8s-admin-ch004
kind get clusters
```

If the worker remains stopped, `kind delete cluster` should still remove the disposable cluster containers; inspect `docker ps -a --filter name=k8s-admin-ch004` if cleanup reports a failure.

Remove locally created manifests if desired:

```powershell
Remove-Item .\kind-ch004.yaml, .\ch004-worker-web.yaml
```

**Warning:** Cluster deletion permanently removes local workloads and data. Do not delete a cluster you intend to keep.

## 15. Knowledge check

1. Why can running Pods continue briefly during an API-server outage?
2. Why does a two-member etcd cluster tolerate zero voting-member failures?
3. Which components make scheduling decisions and start containers?
4. What does `Ready` mean for a worker node, and what does it not guarantee?
5. Why did the Deployment in Lab C fail to relocate when the worker stopped?
6. Why is an etcd snapshot not a complete application backup?
7. How does operational ownership differ between kubeadm, EKS, AKS, and GKE?

## 16. Chapter status

**Draft complete; lab execution has not been independently verified.** Promote to **Lab Validated** after executing the acceptance checklist and to **Complete** after review.

**Next:** Chapter 005 — Kubernetes Objects, YAML and Declarative Management.
