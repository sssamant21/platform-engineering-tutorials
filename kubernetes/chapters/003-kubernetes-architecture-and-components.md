# Chapter 003 — Kubernetes Architecture and Components

**Track:** Kubernetes Administration · **Part:** 01 — Kubernetes Fundamentals · **Level:** Beginner–Intermediate · **Status:** Draft (lab validation pending)

## 1. Learning objectives

After completing this chapter you should be able to:

1. Explain the separation of Kubernetes control plane and worker-node responsibilities.
2. Describe the API server, etcd, scheduler, controller manager, kubelet, container runtime, kube-proxy, CNI, and CoreDNS.
3. Trace the lifecycle of a Deployment from API submission to a running Pod.
4. Inspect architecture and component health using `kubectl` and a disposable kind cluster.
5. Diagnose a scheduling failure using Pod conditions, events, and node state.
6. Distinguish self-managed cluster components from managed EKS, AKS, and GKE responsibilities.

## 2. Architecture overview

```text
                       Operators / CI/CD / GitOps
                                  |
                              kubectl / API
                                  |
                         +-------------------+
                         | Kubernetes API    |
                         | server            |
                         +-------------------+
                            |      |      |
                      +-----+      |      +------------------+
                      |            |                         |
                   +------+   +-----------+          +----------------+
                   | etcd |   | Scheduler |          | Controller     |
                   |      |   |           |          | manager        |
                   +------+   +-----------+          +----------------+
                                  |
                      API objects / assignments
                                  |
               +------------------+-------------------+
               |                                      |
        +--------------+                       +--------------+
        | Worker node A|                       | Worker node B|
        | kubelet      |                       | kubelet      |
        | CRI runtime  |                       | CRI runtime  |
        | CNI / proxy  |                       | CNI / proxy  |
        | Pods         |                       | Pods         |
        +--------------+                       +--------------+
```

The **control plane** manages the cluster's desired state and placement decisions. **Nodes** provide compute resources and run Pods. Almost all administrative interactions flow through the Kubernetes API rather than directly modifying component state.

The diagram is conceptual. In a highly available cluster, control-plane services may run on multiple machines and etcd may have multiple voting members. A kind lab often uses a single control-plane node and is not itself highly available.

## 3. Control-plane components

### 3.1 kube-apiserver

The API server is the front door to Kubernetes. It authenticates and authorizes requests, validates API objects, runs applicable admission control, and persists supported cluster state. Controllers and clients watch API resources to react to changes.

```powershell
kubectl cluster-info
kubectl api-resources
kubectl get --raw /readyz
```

**Expected:** cluster endpoints, discoverable resource types, and (when authorized and healthy) `ok` for the readiness endpoint. A managed cluster may restrict health endpoints.

### 3.2 etcd

etcd is a strongly consistent distributed key-value store used to persist Kubernetes API state. Protect etcd access, monitor latency and quorum, and test backup/restore procedures. **Never directly modify etcd keys** to repair an ordinary workload problem.

In kind and kubeadm clusters, etcd commonly runs as a static Pod. In EKS, AKS, and GKE, etcd is normally provider-managed and not exposed for direct administration.

### 3.3 kube-scheduler

The scheduler watches for Pods without a node assignment, filters eligible nodes using constraints and available resources, scores feasible placements, and binds Pods to selected nodes.

Scheduling constraints include resource requests, taints and tolerations, affinity, topology, volume requirements, and other policies. The scheduler does not run containers itself.

### 3.4 kube-controller-manager

Controllers continuously reconcile actual state toward desired state. Examples include Deployment, ReplicaSet, Node, Job, EndpointSlice, and namespace controllers. The controller manager is not a single monolithic controller; it hosts multiple control loops.

**Example:** If a Deployment requests three replicas but only two exist, its controllers arrange for another Pod. The scheduler chooses a node, and kubelet starts its containers.

### 3.5 cloud-controller-manager

On supported cloud integrations, cloud-controller-manager connects Kubernetes objects and nodes to provider services such as cloud load balancers and node lifecycle information. Its availability and implementation vary by platform; local kind clusters generally do not require a cloud controller manager.

## 4. Node components

### 4.1 kubelet

kubelet runs on nodes, watches Pod assignments, coordinates container creation through CRI, executes probes, mounts volumes through relevant integrations, and reports Pod/node status.

### 4.2 Container runtime and CRI

A CRI implementation such as containerd or CRI-O manages images and containers. The kubelet requests operations via CRI; a low-level OCI runtime such as runc may create the processes.

### 4.3 kube-proxy and service dataplane

kube-proxy commonly programs node networking rules to implement Kubernetes Service forwarding. Some CNI/eBPF solutions replace kube-proxy's dataplane functionality, so do not assume kube-proxy is present in every cluster.

### 4.4 CNI networking

The Container Network Interface ecosystem supplies Pod networking through plugins such as Calico, Cilium, or cloud-provider implementations. Kubernetes specifies networking requirements but does not prescribe one universal CNI implementation.

### 4.5 CoreDNS

CoreDNS typically runs as a cluster add-on and provides DNS-based service discovery, such as `my-service.my-namespace.svc.cluster.local`. It is not a built-in binary of the API server.

## 5. Add-ons versus core components

| Component | Responsibility | Common location |
|---|---|---|
| API server | Kubernetes API and admission | Control plane |
| etcd | Durable API state | Control plane |
| Scheduler | Pod placement | Control plane |
| Controller manager | Reconciliation | Control plane |
| kubelet | Node-level Pod lifecycle | Each node |
| containerd / CRI-O | Container lifecycle | Each node |
| kube-proxy or replacement | Service forwarding | Node dataplane |
| CNI plugin | Pod networking | Node add-on |
| CoreDNS | Cluster DNS | System add-on |
| Metrics Server | Resource metrics API | Optional add-on |
| Ingress controller | HTTP routing | Optional add-on |
| CSI driver | Persistent volume integration | Optional add-on |

**Operational principle:** Not every cluster uses the same implementation or placement. Inspect the actual distribution and managed-service documentation before making assumptions.

## 6. Request flow: Deployment to running Pod

1. Operator applies a Deployment manifest.
2. API server authenticates, authorizes, validates, admits and stores the object.
3. Deployment controller reconciles the Deployment and creates or updates a ReplicaSet.
4. ReplicaSet controller creates Pods.
5. Scheduler selects a node for each eligible unscheduled Pod.
6. Kubelet on the selected node observes its assignment and asks the runtime to start containers.
7. CNI integration establishes Pod networking; storage and secrets are mounted as needed.
8. Kubelet reports container and Pod status.
9. Controllers keep reconciling as failures or updates occur.

**Important distinction:** A Pod's `Running` phase does not guarantee application readiness. Inspect readiness conditions and the Service's endpoints before claiming the application is serving traffic.

## 7. Prerequisites and lab safety

This chapter uses **Windows PowerShell**, Docker Desktop, `kind`, and `kubectl`. A local kind cluster is disposable and does not represent a production HA architecture.

```powershell
docker version
kind version
kubectl version --client
```

You need a working container engine and sufficient local resources (approximately 2 CPU cores and 4 GiB of free memory is a reasonable starting point; requirements vary). Never run destructive lab steps against EKS, AKS, GKE or production.

## 8. Hands-on lab A — Inspect the control plane

### Step A1 — Create a disposable cluster

```powershell
kind create cluster --name k8s-admin-ch003 --wait 120s
kubectl config current-context
kubectl get nodes -o wide
```

**Expected:** context `kind-k8s-admin-ch003` and a node eventually reporting `Ready`.

**Safety gate:** Stop unless the current context is exactly `kind-k8s-admin-ch003`.

### Step A2 — Inspect cluster endpoints and API discovery

```powershell
kubectl cluster-info
kubectl get --raw /readyz
kubectl api-versions
kubectl api-resources --namespaced=true
```

**Expected:** cluster information, readiness response `ok`, and lists of API groups and namespaced resources. API discovery output varies by version and installed add-ons.

### Step A3 — Inspect control-plane Pods

```powershell
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get pods -l component=kube-apiserver
kubectl -n kube-system get pods -l component=kube-scheduler
kubectl -n kube-system get pods -l component=kube-controller-manager
kubectl -n kube-system get pods -l component=etcd
```

**Expected:** In a typical kind cluster, static Pods for the API server, scheduler, controller manager and etcd appear. Label selectors are common in kind/kubeadm but may differ elsewhere.

Inspect a component's logs:

```powershell
kubectl -n kube-system logs -l component=kube-scheduler --tail=30 --prefix=true
```

If the selector matches nothing, list Pods and use the actual Pod name instead.

### Step A4 — Inspect node details

```powershell
kubectl describe node k8s-admin-ch003-control-plane
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.status.nodeInfo.containerRuntimeVersion}{"  "}{.status.nodeInfo.kubeletVersion}{"\n"}{end}'
kubectl -n kube-system get daemonsets
```

**Expected:** kubelet version, runtime version, node capacity/allocatable resources and node conditions. The kube-proxy DaemonSet may be present; do not assume all cluster distributions use it.

## 9. Hands-on lab B — Trace workload reconciliation

### Step B1 — Create a namespace and Deployment

```powershell
kubectl create namespace ch003
kubectl -n ch003 create deployment architecture-web --image=nginx:stable --replicas=2
kubectl -n ch003 rollout status deployment/architecture-web --timeout=180s
kubectl -n ch003 get deployments,replicasets,pods -o wide
```

**Expected:** Deployment `2/2` ready and two running Pods after image pull.

### Step B2 — Trace owner references

```powershell
kubectl -n ch003 get replicasets -o wide
kubectl -n ch003 get pods -l app=architecture-web -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,OWNER:.metadata.ownerReferences[0].name,PHASE:.status.phase'
kubectl -n ch003 describe deployment architecture-web
```

**Expected:** Pods reference a ReplicaSet as their owner; ReplicaSet is owned by the Deployment. This illustrates controller reconciliation and node scheduling.

### Step B3 — Observe scheduling and readiness

```powershell
kubectl -n ch003 get events --sort-by=.lastTimestamp
kubectl -n ch003 get pods -l app=architecture-web -o wide
kubectl -n ch003 get pods -l app=architecture-web -o jsonpath='{range .items[*]}{.metadata.name}{" node="}{.spec.nodeName}{" ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'
```

**Expected:** Scheduled events and Pods assigned to the kind node, with `ready=true` when containers are healthy.

## 10. Hands-on lab C — Safe scheduler failure simulation

Create a Pod that requests a deliberately nonexistent node label:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: unschedulable-demo
  namespace: ch003
spec:
  nodeSelector:
    training.example.com/nonexistent: "true"
  containers:
    - name: nginx
      image: nginx:stable
      resources:
        requests:
          cpu: 25m
          memory: 32Mi
'@ | Set-Content -Encoding ascii .\ch003-unschedulable.yaml

kubectl apply -f .\ch003-unschedulable.yaml
kubectl -n ch003 get pod unschedulable-demo
kubectl -n ch003 describe pod unschedulable-demo
kubectl -n ch003 get events --sort-by=.lastTimestamp
```

**Expected:** Pod remains `Pending` because no node matches the selector. Scheduler events should describe a node-selector or affinity mismatch. The exact wording varies by version.

### Recover safely

Remove the unsatisfiable selector from the Pod by deleting the demonstration Pod and creating a normal one:

```powershell
kubectl -n ch003 delete pod unschedulable-demo
kubectl -n ch003 run schedulable-demo --image=nginx:stable --restart=Never
kubectl -n ch003 wait --for=condition=Ready pod/schedulable-demo --timeout=180s
kubectl -n ch003 get pod schedulable-demo -o wide
```

**Expected:** New Pod schedules and becomes Ready. No node labels or production scheduling policies were changed.

## 11. Troubleshooting playbook

| Symptom | First check | Likely next investigation |
|---|---|---|
| `kubectl` cannot connect | Current context and API endpoint | API server reachability, certificates, network |
| API server returns errors | `kubectl get --raw /readyz?verbose` where authorized | API server dependencies and etcd health |
| Pod stays Pending | `kubectl describe pod` and events | Requests, taints, selectors, topology, PVCs |
| Pod assigned but not running | `kubectl describe pod`, container status | Image pull, CRI, volume mount, CNI |
| Pod Running but not Ready | Readiness conditions and application logs | Probe failures, application dependencies |
| Service has no healthy backends | `kubectl get endpointslices` | Selectors, Pod readiness, ports |
| Node NotReady | `kubectl describe node` | kubelet, runtime, disk, memory, CNI |

**Incident workflow:** Record cluster/context, namespace, timestamps, affected workloads, events and node conditions before changing anything. Identify whether failure is in API/control plane, scheduling, node runtime, networking, storage or application readiness. Prefer narrowly scoped remediation with an explicit rollback.

### Useful commands

```powershell
kubectl get nodes
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl -n ch003 describe pod <pod-name>
kubectl -n ch003 logs <pod-name> --previous
```

Replace `<pod-name>` with an actual Pod name. `--previous` is useful only when a prior container instance exists.

## 12. Managed Kubernetes: EKS, AKS, GKE

| Area | Self-managed/kubeadm | EKS | AKS | GKE |
|---|---|---|---|---|
| Control-plane lifecycle | Operator responsibility | AWS-managed | Azure-managed | Google-managed |
| etcd operations | Operator responsibility | Provider-managed | Provider-managed | Provider-managed |
| Node operations | Operator responsibility | Shared responsibility, depends on compute mode | Shared responsibility, depends on node mode | Shared responsibility, Standard vs Autopilot |
| CNI/network integration | Operator-selected | AWS VPC CNI or supported alternatives | Azure networking options | GKE-managed networking choices |
| Application reliability | Workload owner | Workload owner | Workload owner | Workload owner |

**Do not infer** that managed control planes eliminate responsibility for RBAC, workload identity, networking policy, resource sizing, observability, backup strategy, or application recovery.

## 13. Production SRE practices

- Use at least the provider-supported HA design for critical workloads; a single-control-plane kind cluster is a learning tool.
- Protect Kubernetes API access with least privilege, audit logging, secure authentication, and approved network controls.
- Monitor API request latency/error rates, node readiness, scheduling latency, Pod restarts, DNS availability and Service-level indicators.
- Distinguish control-plane incidents from workload/node failures; they have different recovery owners.
- Maintain version compatibility across control plane, kubelet, CNI, CSI and add-ons.
- Never directly alter etcd state or restart control-plane services in production without an approved, tested recovery plan.

## 14. Acceptance checklist

- [ ] Tooling verified and disposable cluster created.
- [ ] Current context confirmed before modifying resources.
- [ ] Control-plane components and API discovery inspected.
- [ ] Node runtime and kubelet versions recorded.
- [ ] Deployment, ReplicaSet and Pod ownership traced.
- [ ] Scheduler-assigned node and Pod readiness verified.
- [ ] Unschedulable Pod failure identified from events.
- [ ] Replacement Pod successfully scheduled and became Ready.
- [ ] Cleanup performed.

## 15. Cleanup

Confirm the active context is `kind-k8s-admin-ch003` before deletion:

```powershell
kubectl config current-context
kubectl delete namespace ch003
kind delete cluster --name k8s-admin-ch003
kind get clusters
```

**Warning:** Deleting the kind cluster removes its workloads and local data permanently. Do not delete clusters that are not disposable.

Optionally remove the locally created manifest:

```powershell
Remove-Item .\ch003-unschedulable.yaml
```

## 16. Knowledge check

1. Why does the scheduler not directly launch containers?
2. Which component persists Kubernetes API state?
3. What is the relationship between Deployment, ReplicaSet and Pod?
4. What does kubelet do after a Pod is assigned to its node?
5. Why can a Pod be Running but not Ready?
6. Which control-plane responsibilities are typically managed by EKS, AKS and GKE?
7. Why is `kubectl describe pod` often more useful than restarting a Pending Pod?

## 17. Status and next chapter

**Draft complete; lab execution has not been independently verified.** Mark Lab Validated only after executing the lab, and Complete after review.

**Next:** Chapter 004 — Control Plane, Worker Nodes and etcd.
