# Chapter 007 — Kubernetes Local Lab with kind and Minikube

**Track:** Kubernetes Administration · **Part:** 02 — Cluster Installation and Setup · **Level:** Beginner–Intermediate · **Status:** Draft — hands-on validation pending

## 1. Learning objectives

By the end of this chapter, you will be able to:

1. Explain how kind and Minikube differ in architecture, use cases, and operational tradeoffs.
2. Install and validate both tools in a Windows PowerShell environment.
3. Provision isolated Kubernetes clusters using each tool.
4. Inspect contexts, nodes, system Pods, runtime and networking components.
5. Deploy and verify an application through a Service and local access.
6. Simulate a workload failure and demonstrate Kubernetes reconciliation.
7. Safely switch contexts, clean up resources, and troubleshoot local-cluster problems.

## 2. Local Kubernetes architecture

### kind (Kubernetes IN Docker)

```text
Windows + Docker Desktop
          |
          v
      Docker Engine
          |
     +----+------------------+
     |                       |
kind control-plane      kind worker
(container)             (container)
     |                       |
API server / etcd       kubelet / runtime
scheduler/controllers   application Pods
     |                       |
     +---- cluster CNI ------+
```

kind creates Kubernetes nodes as containers. It is well suited to CI tests, reproducible labs, multi-node experiments, and disposable environments. Each node container runs the services required for its Kubernetes role; the control-plane node also runs kubelet and a container runtime.

### Minikube

```text
Windows host
    |
Minikube CLI
    |
Driver (Docker, Hyper-V, etc.)
    |
Minikube node(s)
    |
Kubernetes components + workloads
```

Minikube is a local Kubernetes development environment supporting multiple drivers and configurable add-ons. Its exact node topology, IP reachability, storage behavior, and service-access workflow depend on the selected driver and operating system.

### Comparison

| Area | kind | Minikube |
|---|---|---|
| Primary focus | Kubernetes testing and reproducible clusters | Local development and learning |
| Node model | Containerized Kubernetes nodes | Driver-backed nodes |
| Multi-node support | Yes, via cluster config | Yes, via node configuration |
| Local image workflow | `kind load docker-image` | `minikube image load` |
| Add-on management | Kubernetes manifests/Helm | `minikube addons` for supported add-ons |
| Common access workflow | `kubectl port-forward` | `minikube service` or `kubectl port-forward` |
| Cleanup | `kind delete cluster` | `minikube delete -p <profile>` |

Neither is a substitute for production EKS, AKS, GKE, or a properly managed self-hosted cluster. Both are appropriate for practicing administration without cloud costs.

## 3. Prerequisites

This chapter targets **Windows PowerShell**. You need:

- Docker Desktop with a functioning Linux-container engine.
- `kubectl` compatible with your Kubernetes server.
- `kind` and `minikube` executables.
- Sufficient local CPU, memory, and disk. For running both clusters sequentially, start with approximately 4 available CPUs, 8 GiB free RAM, and 15–20 GiB free disk; actual needs vary.
- Internet access for node and application images, unless cached.

Check:

```powershell
docker version
docker info --format '{{.OSType}}'
kubectl version --client
kind version
minikube version
```

**Expected:** Docker reports `linux` as its OS type; CLI version commands succeed.

### Install kind and Minikube (if missing)

With Windows Package Manager, inspect the packages first:

```powershell
winget search kind
winget search minikube
```

Install using the exact package identifiers returned by your approved package source, or use the official installation instructions:

- kind: https://kind.sigs.k8s.io/docs/user/quick-start/
- Minikube: https://minikube.sigs.k8s.io/docs/start/
- kubectl: https://kubernetes.io/docs/tasks/tools/

Avoid running unverified download scripts with elevated privileges.

## 4. Lab safety rules

**All exercises must run in disposable local clusters.** Before every write or delete, confirm the current context or pass an explicit `--context`. Do not reuse production, staging, EKS, AKS, or GKE contexts.

Create a working directory:

```powershell
New-Item -ItemType Directory -Force .\k8s-ch007 | Out-Null
Set-Location .\k8s-ch007
```

This chapter uses unique names:
- kind cluster: `k8s-admin-ch007`
- kind context: `kind-k8s-admin-ch007`
- Minikube profile/context: `ch007-minikube`
- Namespaces: `ch007-kind`, `ch007-mini`

## 5. Hands-on Lab A — Create a two-node kind cluster

### Step A1 — Define topology

```powershell
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-ch007.yaml
```

### Step A2 — Create and verify

```powershell
kind create cluster --name k8s-admin-ch007 --config .\kind-ch007.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch007 get nodes -o wide
kubectl --context kind-k8s-admin-ch007 -n kube-system get pods -o wide
```

**Expected:** two nodes eventually become `Ready`; the API server, etcd, scheduler, controller manager, and CoreDNS appear in `kube-system`. Image pulls and initialization may take several minutes.

**Safety gate:** Do not proceed unless `kind-k8s-admin-ch007` is a listed context and the explicit-context commands reach the intended local cluster.

### Step A3 — Inspect runtime and node topology

```powershell
kubectl --context kind-k8s-admin-ch007 get nodes --show-labels
kubectl --context kind-k8s-admin-ch007 get nodes -o custom-columns='NAME:.metadata.name,ROLE:.metadata.labels.node-role\.kubernetes\.io/control-plane,RUNTIME:.status.nodeInfo.containerRuntimeVersion'
docker ps --filter name=k8s-admin-ch007
```

**Expected:** Docker shows the kind node containers; Kubernetes shows the cluster's two nodes. The custom-column ROLE field may be empty depending on label parsing and version; inspect `--show-labels` for authoritative labels.

## 6. Hands-on Lab B — Deploy, expose, and reconcile a kind workload

### Step B1 — Create the namespace and application

```powershell
kubectl --context kind-k8s-admin-ch007 create namespace ch007-kind
kubectl --context kind-k8s-admin-ch007 -n ch007-kind create deployment web --image=nginx:stable --replicas=2
kubectl --context kind-k8s-admin-ch007 -n ch007-kind rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch007 -n ch007-kind expose deployment web --port=80 --target-port=80 --type=ClusterIP
kubectl --context kind-k8s-admin-ch007 -n ch007-kind get deployment,replicaset,pods,service -o wide
```

**Expected:** two Ready replicas and a ClusterIP Service. Pod names and IPs vary.

### Step B2 — Verify HTTP traffic

In **PowerShell terminal 1**:

```powershell
kubectl --context kind-k8s-admin-ch007 -n ch007-kind port-forward service/web 18087:80
```

In **PowerShell terminal 2**:

```powershell
(Invoke-WebRequest http://localhost:18087 -UseBasicParsing).StatusCode
```

**Expected:** `200`. Stop port-forward with Ctrl+C in terminal 1.

### Step B3 — Observe reconciliation

```powershell
$pod = kubectl --context kind-k8s-admin-ch007 -n ch007-kind get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl --context kind-k8s-admin-ch007 -n ch007-kind delete pod $pod
kubectl --context kind-k8s-admin-ch007 -n ch007-kind rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch007 -n ch007-kind get pods -o wide
```

**Expected:** the ReplicaSet creates a replacement Pod and the Deployment returns to two Ready replicas. Deleting a managed Pod is safe for this lab but can cause disruption when production replicas or capacity are insufficient.

## 7. Hands-on Lab C — Create a Minikube cluster

Run Minikube after or alongside kind **only if your machine has sufficient resources**. To conserve resources, you may complete kind Labs A/B, clean up kind, and then start Minikube. Do not delete kind until its acceptance checks are recorded.

### Step C1 — Start Minikube using the Docker driver

```powershell
minikube start -p ch007-minikube --driver=docker --cpus=2 --memory=3072
minikube profile list
kubectl config get-contexts
kubectl --context ch007-minikube get nodes -o wide
kubectl --context ch007-minikube -n kube-system get pods
```

**Expected:** one Ready Minikube node and healthy system Pods. Startup may fail if Docker Desktop has insufficient resources; adjust within your available capacity and retry.

**Context note:** Minikube typically creates a context named after the profile. Confirm with `kubectl config get-contexts` rather than assuming.

### Step C2 — Inspect add-ons

```powershell
minikube addons list -p ch007-minikube
minikube status -p ch007-minikube
```

**Expected:** supported add-ons and cluster component status. Do not enable unrelated add-ons merely to complete this lab.

### Step C3 — Deploy an application

```powershell
kubectl --context ch007-minikube create namespace ch007-mini
kubectl --context ch007-minikube -n ch007-mini create deployment web --image=nginx:stable --replicas=2
kubectl --context ch007-minikube -n ch007-mini rollout status deployment/web --timeout=180s
kubectl --context ch007-minikube -n ch007-mini expose deployment web --port=80 --target-port=80 --type=ClusterIP
kubectl --context ch007-minikube -n ch007-mini get deployment,pods,service
```

**Expected:** two Ready Pods and a ClusterIP Service.

### Step C4 — Access the Minikube application

In **PowerShell terminal 1**:

```powershell
kubectl --context ch007-minikube -n ch007-mini port-forward service/web 18088:80
```

In **PowerShell terminal 2**:

```powershell
(Invoke-WebRequest http://localhost:18088 -UseBasicParsing).StatusCode
```

**Expected:** HTTP `200`. Stop port-forward with Ctrl+C.

For Minikube-specific Service access, `minikube service` is also available, but behavior differs by Service type and driver; port-forward is the portable approach used here.

## 8. Hands-on Lab D — Context isolation and comparison

### Step D1 — Confirm both clusters

If both are running:

```powershell
kubectl config get-contexts
kubectl --context kind-k8s-admin-ch007 get nodes
kubectl --context ch007-minikube get nodes
```

**Expected:** kind reports two nodes and Minikube reports one node.

### Step D2 — Demonstrate namespace isolation

```powershell
kubectl --context kind-k8s-admin-ch007 get namespace ch007-kind
kubectl --context ch007-minikube get namespace ch007-mini
kubectl --context kind-k8s-admin-ch007 get namespace ch007-mini
```

**Expected:** the third command reports `NotFound`, showing that resources in separate clusters are isolated. A `NotFound` result is expected here, not a lab failure.

### Step D3 — Capture runtime versions and cluster info

```powershell
kubectl --context kind-k8s-admin-ch007 get nodes -o wide
kubectl --context ch007-minikube get nodes -o wide
kubectl --context kind-k8s-admin-ch007 cluster-info
kubectl --context ch007-minikube cluster-info
```

Record differences in node count, container runtime, IP addresses, system Pods, and access patterns.

## 9. Troubleshooting runbook

| Symptom | First check | Likely remediation |
|---|---|---|
| kind cluster creation fails | `docker info`, `kind version` | Start Docker Desktop, free resources, inspect kind logs |
| Minikube driver failure | `minikube logs -p ch007-minikube` | Verify Docker driver and available resources |
| Node NotReady | `kubectl describe node` | Check runtime, kubelet, CNI, disk and memory |
| CoreDNS Pending | `kubectl -n kube-system describe pod` | Inspect node capacity and networking |
| `ImagePullBackOff` | Pod events | Check registry access, DNS, image reference |
| Service not reachable | Pod readiness, endpoints, port-forward | Check selectors, targetPort and local port |
| Wrong cluster | `kubectl config current-context` | Use explicit `--context` |
| Insufficient resources | Docker Desktop CPU/memory and disk | Stop other clusters, increase resources cautiously |
| Port-forward bind failure | Local port already used | Choose another local port |

### Diagnostic commands

```powershell
kind get clusters
minikube profile list
kubectl config get-contexts
kubectl --context kind-k8s-admin-ch007 get events -A --sort-by=.lastTimestamp
kubectl --context ch007-minikube get events -A --sort-by=.lastTimestamp
minikube logs -p ch007-minikube
```

For kind cluster creation failures, rerun with increased verbosity or export logs using `kind export logs --name k8s-admin-ch007 <directory>`. Avoid collecting sensitive kubeconfig data in public logs.

## 10. Production SRE perspective

- **Local clusters:** excellent for validating YAML, controllers, scheduling, network basics, and controlled failure experiments.
- **Not production-equivalent:** local networking, storage, load balancers, HA, IAM, managed upgrades, node autoscaling, and failure domains differ materially from cloud platforms.
- **Version alignment:** reproduce the relevant Kubernetes and add-on versions when testing production behavior.
- **Change validation:** use local labs for early testing, then staging for platform-specific acceptance.
- **Security:** never import production credentials or real patient/customer data into a local lab.
- **Cost:** kind and Minikube avoid cloud compute charges, but still consume workstation resources.

## 11. Cleanup and rollback

Stop any port-forward sessions first. Delete resources only with explicit contexts:

```powershell
kubectl --context kind-k8s-admin-ch007 delete namespace ch007-kind
kubectl --context ch007-minikube delete namespace ch007-mini
```

Then delete the **disposable** clusters:

```powershell
kind delete cluster --name k8s-admin-ch007
minikube delete -p ch007-minikube
kind get clusters
minikube profile list
```

If one cluster was already deleted or never created, skip its corresponding cleanup commands. Remove the generated config if no longer needed:

```powershell
Remove-Item .\kind-ch007.yaml
```

**Warning:** Cluster deletion removes local workloads and cluster-local data. Do not delete unrelated profiles or clusters. Confirm the exact names before executing cleanup.

## 12. Acceptance checklist

- [ ] Verified Docker Desktop, kubectl, kind and Minikube.
- [ ] Created two-node kind cluster and inspected system components.
- [ ] Deployed two-replica kind application and received HTTP 200.
- [ ] Deleted a managed Pod and observed successful reconciliation.
- [ ] Created one-node Minikube cluster with Docker driver.
- [ ] Deployed Minikube application and received HTTP 200.
- [ ] Used explicit contexts to inspect both clusters.
- [ ] Verified cross-cluster namespace isolation.
- [ ] Recorded node/runtime and network differences.
- [ ] Cleaned up both disposable clusters.

## 13. Knowledge check

1. Why does kind use Docker containers to represent Kubernetes nodes?
2. How does Minikube's driver selection affect networking and service access?
3. Why should you pass `--context` when operating multiple clusters?
4. Why does deleting a Deployment-managed Pod usually result in a replacement?
5. Why might a local Service work with port-forward but not be reachable by ClusterIP from Windows?
6. What production behaviors cannot be reliably reproduced with a single-machine local cluster?
7. What are the tradeoffs between running both labs simultaneously versus sequentially?

## 14. Chapter status and next chapter

**Draft written; lab execution has not been independently verified.** Promote to **Lab Validated** only after completing the acceptance checklist, and to **Complete** after review.

**Next:** Chapter 008 — kubeadm Cluster Installation.
