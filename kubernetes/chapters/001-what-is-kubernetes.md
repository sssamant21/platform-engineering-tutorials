# Chapter 001 — What Is Kubernetes? Architecture and Use Cases

**Track:** Kubernetes Administration · **Part:** 01 — Kubernetes Fundamentals · **Level:** Beginner · **Status:** Draft — lab execution pending

## 1. Learning objectives

By the end of this chapter you should be able to:
- Explain why container orchestration exists and when Kubernetes is appropriate.
- Distinguish a cluster, node, Pod, Deployment and Service.
- Describe declarative desired state and the reconciliation loop.
- Start a disposable Kubernetes cluster, deploy an application, scale it, expose it locally and clean up safely.
- Identify common startup and scheduling failures using `kubectl`.

## 2. What is Kubernetes?

Kubernetes (often abbreviated K8s) is an open-source platform for orchestrating containerized workloads. It schedules application Pods onto cluster nodes and continuously works to reconcile observed state with the desired state declared through the Kubernetes API.

Kubernetes provides workload scheduling, health-based restart/replacement, service discovery, rollout/rollback controls, resource management and extensible APIs. It does **not** automatically make an application highly available, back up its data, secure an insecure image, or fix application defects.

### Why orchestration?

Running one container with a container engine is straightforward. Operating hundreds of containers across hosts requires repeatable placement, health checks, updates, recovery, configuration and networking. Kubernetes provides common primitives to manage these tasks.

### When to use it

Kubernetes fits teams running multiple services, requiring automated scheduling, standardized deployment controls and consistent operations. A simple application may be better served by a managed application platform or a smaller deployment model: Kubernetes introduces real operational complexity.

## 3. Architecture and terminology

| Term | Meaning | Operational note |
|---|---|---|
| Cluster | Control plane plus worker nodes | The administrative boundary |
| API server | Front door for Kubernetes API operations | `kubectl` talks to this endpoint |
| etcd | Persistent key-value store for cluster state | Protect access and backups |
| Scheduler | Selects nodes for unscheduled Pods | Uses resource and scheduling constraints |
| Controller manager | Runs reconciliation controllers | Works toward desired state |
| Kubelet | Node agent that manages Pods | Reports node and Pod status |
| Container runtime | Runs containers through CRI | Commonly containerd |
| Pod | Smallest schedulable workload unit | Can contain multiple containers |
| Deployment | Manages replicated stateless Pods | Supports rolling updates |
| Service | Stable network endpoint for a group of Pods | Usually selects Pods by labels |

**Flow:** Operator applies YAML → API server stores desired state → controllers create/update objects → scheduler assigns Pods → kubelet starts containers → status is reported back to API server.

## 4. Prerequisites and safety

Use a **non-production local machine** with Docker Desktop or another supported container engine, `kubectl` and `kind`. Allocate enough resources for a local cluster (approximately 2 CPUs and 4 GiB of available RAM is a practical starting point; requirements vary).

Commands below use PowerShell syntax on Windows, but most `kubectl` commands are cross-platform. Install `kind` and `kubectl` from their official documentation and ensure your container engine is running. Do not execute cleanup commands against an unrelated cluster.

Verify tooling:

```powershell
docker version
kind version
kubectl version --client
```

Expected: each command returns version information. If Docker cannot reach its daemon, start Docker Desktop before proceeding.

## 5. Hands-on lab — Your first Kubernetes cluster

### Lab 5.1 — Create a disposable kind cluster

```powershell
kind create cluster --name k8s-admin-ch001 --wait 120s
kind get clusters
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A
```

Expected: `k8s-admin-ch001` appears in the kind cluster list; context is `kind-k8s-admin-ch001`; the control-plane node eventually reports `Ready`; core system Pods become ready. Exact Kubernetes versions, IP addresses and Pod names will vary.

**Safety check before the next commands:**

```powershell
kubectl config current-context
```

Proceed only when the output is `kind-k8s-admin-ch001`.

### Lab 5.2 — Create an isolated namespace and Deployment

```powershell
kubectl create namespace ch001
kubectl -n ch001 create deployment web --image=nginx:stable --replicas=2
kubectl -n ch001 rollout status deployment/web --timeout=180s
kubectl -n ch001 get deployments,replicasets,pods -o wide
```

Expected: the Deployment shows **2/2** ready replicas and two running Pods. The first image pull may take time depending on network access.

Inspect desired versus observed state:

```powershell
kubectl -n ch001 describe deployment web
kubectl -n ch001 get deployment web -o yaml
kubectl -n ch001 get pods -l app=web
```

Notice the Deployment's `spec.replicas` (desired) and `status.readyReplicas` (observed).

### Lab 5.3 — Expose the application locally

```powershell
kubectl -n ch001 expose deployment web --port=80 --target-port=80 --name=web-service
kubectl -n ch001 get service web-service
kubectl -n ch001 port-forward service/web-service 8080:80
```

Leave port-forward running in that terminal. In **another** PowerShell terminal:

```powershell
Invoke-WebRequest http://localhost:8080 -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

Expected: HTTP status **200** and the default NGINX page. Stop port-forward with Ctrl+C. The Service is ClusterIP by default; port-forward creates a local development tunnel, not a production ingress.

### Lab 5.4 — Scale and observe reconciliation

```powershell
kubectl -n ch001 scale deployment/web --replicas=3
kubectl -n ch001 rollout status deployment/web --timeout=180s
kubectl -n ch001 get deployment web
kubectl -n ch001 get pods -l app=web -o wide
```

Expected: **3/3** ready replicas. Observe the desired replica count and actual Pods.

Simulate a non-destructive Pod replacement:

```powershell
$pod = kubectl -n ch001 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl -n ch001 delete pod $pod
kubectl -n ch001 get pods -l app=web -w
```

Expected: the Deployment's ReplicaSet creates a replacement Pod to restore the replica count. Press Ctrl+C to stop watching.

### Lab 5.5 — View events and logs

```powershell
kubectl -n ch001 get events --sort-by=.lastTimestamp
kubectl -n ch001 logs deployment/web --tail=30
kubectl -n ch001 describe pods -l app=web
```

Expected: scheduling/startup events and NGINX logs. A freshly started NGINX Pod may have little or no access-log output until it receives a request.

## 6. Troubleshooting practice

| Symptom | Investigate | Likely remediation |
|---|---|---|
| `kind create cluster` fails | `docker info`, Docker Desktop status | Start the container engine, check available memory |
| `kubectl` cannot connect | `kubectl config current-context` | Select the intended kind context |
| Pod is `Pending` | `kubectl describe pod <name> -n ch001` | Check scheduling events and node resources |
| Pod is `ImagePullBackOff` | Pod events, image name, registry reachability | Fix image reference or registry access |
| Port 8080 is in use | Port-forward error | Use `8081:80` and test port 8081 |
| Ready replicas below desired | `kubectl get pods`, `describe`, `logs` | Diagnose readiness, startup or scheduling |

**Incident drill:** Explain why deleting one Deployment-managed Pod is usually recoverable but deleting the Deployment itself removes the controller's desired state. Do not try this in production.

## 7. Production operations perspective

- Treat Kubernetes YAML and access policies as version-controlled infrastructure.
- Set resource requests/limits and health probes deliberately; defaults alone are not a production standard.
- Use least-privilege RBAC, approved images, secret management and network segmentation.
- Monitor control-plane health, node conditions, workload readiness, restarts and service-level indicators.
- Use PodDisruptionBudgets and topology spread for suitable highly available workloads; replica count alone is not enough.
- Establish backup, recovery, upgrade and rollback procedures before critical workloads go live.

## 8. Validation and acceptance checklist

- [ ] Cluster created and intended context verified.
- [ ] Node reported Ready and system Pods were inspected.
- [ ] Deployment reached 2/2 replicas.
- [ ] Service returned HTTP 200 through port-forward.
- [ ] Deployment scaled to 3/3 replicas.
- [ ] Deleting a managed Pod caused a replacement.
- [ ] Events, describe output and logs were inspected.
- [ ] Cleanup completed.

## 9. Cleanup

First verify the active context is **kind-k8s-admin-ch001**.

```powershell
kubectl config current-context
kubectl delete namespace ch001
kind delete cluster --name k8s-admin-ch001
kind get clusters
```

Expected: the disposable cluster no longer appears in `kind get clusters`. **Warning:** `kind delete cluster` permanently removes that local cluster and its contents; do not use it for any cluster you want to preserve.

## 10. Knowledge check

1. What is the difference between a Pod and a Deployment?
2. Which components schedule Pods and run containers on nodes?
3. Why does Kubernetes replace a deleted Deployment-managed Pod?
4. What is the purpose of a ClusterIP Service?
5. Why is a successful local NGINX deployment not proof of production readiness?

## 11. Chapter completion status

**Draft complete; hands-on execution not independently verified.** Run the acceptance checklist in your local lab before updating the tracker to **Lab Validated** or **Complete**.

**Next:** Chapter 002 — Containers, Images and Container Runtimes.
