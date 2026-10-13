# Chapter 010 — Cluster Installation and Verification Project

**Track:** Kubernetes Administration · **Part:** 02 — Cluster Installation and Setup · **Level:** Intermediate · **Status:** Draft — project execution and acceptance pending

## 1. Project overview

This is the **Part 02 capstone**. Build a reproducible local Kubernetes cluster, verify its control plane, nodes, container runtime, CNI, DNS, scheduling, Service networking, and workload recovery, and produce an evidence-based acceptance report.

**Primary path:** Windows PowerShell + Docker Desktop + kind, with a **one-control-plane, two-worker** topology. This is a local functional lab, **not a highly available production control plane**.

**Optional extension:** Repeat the verification matrix against the disposable kubeadm Ubuntu VMs from Chapter 008, adapting the CNI/runtime checks to that installation. Do not run failure injection against a shared, staging, or production cluster.

## 2. Learning objectives

1. Define installation acceptance criteria before provisioning.
2. Provision a repeatable multi-node Kubernetes lab and verify cluster identity.
3. Validate control-plane readiness, node conditions, kubelet/runtime metadata, CNI, CoreDNS, Pod DNS, and Service endpoints.
4. Test scheduling, rolling updates, reconciliation, and a controlled worker drain.
5. Capture troubleshooting evidence and identify failed acceptance gates.
6. Cleanly restore cluster state and document rollback.
7. Produce a final installation handover report with pass/fail evidence.

## 3. Architecture and success criteria

```text
                  Windows PowerShell
                    kubectl + kind
                          |
                    API server / etcd
                     Control plane
                          |
              +-----------+-----------+
              |                       |
          Worker 1                  Worker 2
          containerd                containerd
          CNI / kubelet             CNI / kubelet
              |                       |
          NGINX Pod                 NGINX Pod
              +-----------+-----------+
                          |
                     ClusterIP Service
                          |
                        CoreDNS
```

### Acceptance matrix

| ID | Verification | Passing condition |
|---|---|---|
| A01 | Cluster identity | Context is exactly `kind-k8s-admin-ch010` |
| A02 | Node health | 3 nodes report Ready |
| A03 | Control plane | API readiness succeeds; static control-plane Pods healthy |
| A04 | Runtime | Each node reports compatible kubelet and container runtime |
| A05 | CNI | CNI agents healthy; Pods receive IPs |
| A06 | DNS | Internal Service FQDN resolves from a test Pod |
| A07 | Service | ClusterIP Service has ready endpoints and serves HTTP |
| A08 | Scheduling | 2 application replicas placed across 2 worker nodes |
| A09 | Reconciliation | Deleted application Pod replaced; 2/2 Ready restored |
| A10 | Rolling update | Version/image change rolls out and application remains healthy |
| A11 | Planned maintenance | Worker drain reschedules workload; 2/2 Ready restored |
| A12 | Recovery/cleanup | Worker uncordoned; resources deleted; cluster removed |

**Note:** This lab does not prove zero downtime, zone-level resilience, control-plane HA, data durability, or production readiness. Those require separate acceptance tests.

## 4. Prerequisites and safety

Use Windows PowerShell with Docker Desktop, `kind`, and `kubectl`. Recommended workstation headroom: approximately 6 CPUs, 10 GiB free RAM, and 20 GiB disk, subject to image size and Docker configuration.

```powershell
docker version
docker info --format '{{.OSType}}'
kind version
kubectl version --client
```

**Expected:** Docker reports `linux`; tools are available. Do not proceed if resources are insufficient.

**Safety:** The commands below create and delete Pods, drain a worker, and delete the disposable cluster. Use only the explicitly named kind context. Never substitute a production context or run the drain step on EKS, AKS, GKE, or shared clusters.

Create a workspace:

```powershell
New-Item -ItemType Directory -Force .\k8s-ch010 | Out-Null
Set-Location .\k8s-ch010
```

## 5. Lab A — Provision a reproducible cluster

### Step A1 — Create the kind configuration

```powershell
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-ch010.yaml
```

### Step A2 — Create and verify identity

```powershell
kind create cluster --name k8s-admin-ch010 --config .\kind-ch010.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch010 get nodes -o wide
kind get clusters
```

**Expected:** the current context is `kind-k8s-admin-ch010` and three nodes become Ready.

**Stop condition:** If the context is wrong or fewer than three nodes become Ready, capture events and resolve before continuing.

### Step A3 — Capture baseline evidence

```powershell
kubectl --context kind-k8s-admin-ch010 cluster-info
kubectl --context kind-k8s-admin-ch010 get --raw /readyz
kubectl --context kind-k8s-admin-ch010 get nodes -o wide
kubectl --context kind-k8s-admin-ch010 -n kube-system get pods -o wide
kubectl --context kind-k8s-admin-ch010 -n kube-system get daemonsets
kubectl --context kind-k8s-admin-ch010 get nodes -o custom-columns='NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion'
```

**Expected:** API readiness returns `ok`, core components are healthy, and all nodes report a runtime and kubelet version.

For evidence, redirect **non-sensitive** command output to local files as needed. Do not publish kubeconfig credentials or tokens.

## 6. Lab B — Deploy a topology-aware workload

### Step B1 — Create Namespace, Deployment and Service

The Deployment uses required Pod anti-affinity to place its two replicas on **different worker nodes**. A node affinity rule prevents application scheduling on the control-plane node.

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch010
  labels:
    training: kubernetes-admin
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch010
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: node-role.kubernetes.io/control-plane
                    operator: DoesNotExist
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: web
              topologyKey: kubernetes.io/hostname
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - name: http
              containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 2
            periodSeconds: 5
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch010
spec:
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: http
  type: ClusterIP
'@ | Set-Content -Encoding ascii .\ch010-workload.yaml

kubectl --context kind-k8s-admin-ch010 apply --dry-run=server -f .\ch010-workload.yaml
kubectl --context kind-k8s-admin-ch010 apply -f .\ch010-workload.yaml
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout status deployment/web --timeout=240s
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -o wide
```

**Expected:** two Ready NGINX Pods on separate worker nodes. If a Pod remains Pending, inspect `FailedScheduling` events and confirm the expected node labels and worker capacity.

### Step B2 — Inspect scheduling and endpoints

```powershell
kubectl --context kind-k8s-admin-ch010 -n ch010 describe deployment web
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -l app=web -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,IP:.status.podIP'
kubectl --context kind-k8s-admin-ch010 -n ch010 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** Pod placement spans the two workers, and the Service has two ready endpoints.

## 7. Lab C — Verify CoreDNS, CNI, and Service connectivity

### Step C1 — Inspect cluster networking

```powershell
kubectl --context kind-k8s-admin-ch010 -n kube-system get service kube-dns -o wide
kubectl --context kind-k8s-admin-ch010 -n kube-system get deployment coredns
kubectl --context kind-k8s-admin-ch010 -n kube-system get daemonsets
kubectl --context kind-k8s-admin-ch010 get nodes -o jsonpath='{range .items[*]}{.metadata.name}{" podCIDR="}{.spec.podCIDR}{"\n"}{end}'
```

**Expected:** CoreDNS is healthy, kube-dns has a ClusterIP, and node Pod CIDRs are visible. CNI implementation details vary by kind version.

### Step C2 — Create a test client

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: ch010
spec:
  containers:
    - name: busybox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\ch010-client.yaml

kubectl --context kind-k8s-admin-ch010 apply -f .\ch010-client.yaml
kubectl --context kind-k8s-admin-ch010 -n ch010 wait --for=condition=Ready pod/client --timeout=180s
```

### Step C3 — Verify DNS and HTTP

```powershell
kubectl --context kind-k8s-admin-ch010 -n ch010 exec client -- cat /etc/resolv.conf
kubectl --context kind-k8s-admin-ch010 -n ch010 exec client -- nslookup web.ch010.svc.cluster.local
kubectl --context kind-k8s-admin-ch010 -n ch010 exec client -- wget -qO- http://web.ch010.svc.cluster.local
```

**Expected:** DNS resolves the Service, and HTTP returns the NGINX welcome page. If DNS succeeds but HTTP fails, inspect Service selectors, EndpointSlices, readiness and network dataplane separately.

## 8. Lab D — Test reconciliation

Delete one Deployment-managed Pod:

```powershell
$pod = kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl --context kind-k8s-admin-ch010 -n ch010 delete pod $pod
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -o wide
```

**Expected:** ReplicaSet creates a replacement and returns to two Ready Pods on separate workers. A short period of reduced redundancy is possible; do not claim zero interruption solely from Deployment readiness.

## 9. Lab E — Controlled rolling update and rollback

### Step E1 — Record current image

```powershell
kubectl --context kind-k8s-admin-ch010 -n ch010 get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Step E2 — Trigger a safe rollout

Rather than changing to an unverified image tag, update a Pod-template annotation to trigger a rolling replacement:

```powershell
kubectl --context kind-k8s-admin-ch010 -n ch010 patch deployment web --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"training.example.com/revision":"2"}}}}}'
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout status deployment/web --timeout=240s
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout history deployment/web
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -o wide
```

**Expected:** a new ReplicaSet revision and two Ready Pods. This is a rolling **configuration** update, not an image-version upgrade. With strict anti-affinity and exactly two workers, an update may stall because an extra surge Pod cannot schedule while both nodes are occupied. If so, inspect events and use the safe rollback below; do not relax production placement rules without a review.

### Step E3 — Roll back if needed

```powershell
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout undo deployment/web
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout status deployment/web --timeout=240s
```

**Expected:** previous Pod template is restored. `rollout undo` is intended for reverting the Deployment revision; validate the resulting image/annotation and application readiness.

### Important scheduling nuance

For this specific two-worker lab, `maxSurge: 1` plus required anti-affinity can prevent creating a third Pod, while `maxUnavailable: 0` prevents removing a healthy Pod. Kubernetes' default rolling strategy generally allows one unavailable replica for a two-replica Deployment due to percentage rounding, but never rely on default rounding without checking the actual Deployment strategy. If a rollout stalls, inspect `kubectl describe deployment` and Pod events before changing rollout parameters. A deliberate `maxSurge: 0, maxUnavailable: 1` strategy can make progress but accepts reduced availability during the rollout.

## 10. Lab F — Controlled worker drain and recovery

### Step F1 — Confirm placement and node names

```powershell
kubectl --context kind-k8s-admin-ch010 get nodes
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -o wide
```

**Safety gate:** Verify the context is `kind-k8s-admin-ch010` and the target node is one of its disposable worker nodes.

### Step F2 — Understand the expected disruption

The two NGINX replicas are required to run on **different workers**. Draining one worker while the other already hosts one replica leaves no eligible node for the evicted replica. **Therefore, 2/2 readiness is not expected during the drain**. This is an intentional demonstration of a topology constraint and insufficient spare capacity.

Create a third worker **before** the drain to provide eligible capacity:

```powershell
# kind does not support adding nodes to an existing cluster with a simple kubectl command.
# For this fixed three-node lab, proceed with the drain as a capacity-failure exercise,
# then recover by uncordoning the original worker.
```

### Step F3 — Drain one disposable worker

```powershell
kubectl --context kind-k8s-admin-ch010 drain k8s-admin-ch010-worker --ignore-daemonsets --delete-emptydir-data --timeout=180s
kubectl --context kind-k8s-admin-ch010 get nodes
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -o wide
kubectl --context kind-k8s-admin-ch010 -n ch010 get events --sort-by=.lastTimestamp
```

**Expected:** target worker is cordoned, one NGINX replica remains Ready on the other worker, and the replacement replica remains Pending due to required anti-affinity. Drain itself may complete once evictions are accepted; this does not mean the workload is fully recovered.

If drain is blocked by a PodDisruptionBudget, **do not force it**. Record the PDB condition as a safety success. The default lab has no PDB.

### Step F4 — Restore scheduling

```powershell
kubectl --context kind-k8s-admin-ch010 uncordon k8s-admin-ch010-worker
kubectl --context kind-k8s-admin-ch010 -n ch010 rollout status deployment/web --timeout=240s
kubectl --context kind-k8s-admin-ch010 -n ch010 get pods -o wide
kubectl --context kind-k8s-admin-ch010 get nodes
```

**Expected:** the worker becomes schedulable and the Deployment eventually returns to 2/2 Ready, with Pods on separate workers.

**Operational lesson:** A PDB, required anti-affinity, and available capacity must be evaluated together. A drain that is technically successful can still reduce application redundancy.

## 11. Troubleshooting decision tree

```text
Cluster unhealthy?
  |
  +-- API unreachable --> verify context, endpoint, control-plane Pods, etcd
  |
  +-- Node NotReady --> kubelet, runtime, CNI, disk/memory conditions
  |
  +-- Pod Pending --> scheduler events, node selectors, affinity, capacity
  |
  +-- ContainerCreating --> image pulls, CRI, CNI, volumes
  |
  +-- DNS fails --> Pod resolv.conf, kube-dns Service, CoreDNS, CNI
  |
  +-- DNS works / HTTP fails --> Service endpoints, readiness, network path
  |
  +-- Drain blocks --> PDB, DaemonSets, unmanaged Pods, volume constraints
```

Useful commands:

```powershell
kubectl --context kind-k8s-admin-ch010 get nodes -o wide
kubectl --context kind-k8s-admin-ch010 get pods -A -o wide
kubectl --context kind-k8s-admin-ch010 get events -A --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch010 -n ch010 describe deployment web
kubectl --context kind-k8s-admin-ch010 -n ch010 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch010 -n kube-system logs deployment/coredns --tail=100
```

Capture evidence before deleting Pods or restarting components. Avoid unreviewed control-plane or CNI changes during diagnosis.

## 12. Evidence and handover report template

Create a local report after executing the project:

```markdown
# Chapter 010 Cluster Installation Acceptance Report

Date/time:
Operator:
Environment: Disposable kind cluster
Cluster/context: kind-k8s-admin-ch010
Kubernetes server version:
kubectl version:
Container runtime:
CNI implementation:
DNS Service IP:

| ID | Test | Pass/Fail/Blocked | Evidence / command | Notes |
|----|------|-------------------|--------------------|-------|
| A01 | Context | | | |
| A02 | Nodes | | | |
| A03 | Control plane | | | |
| A04 | Runtime | | | |
| A05 | CNI | | | |
| A06 | DNS | | | |
| A07 | Service | | | |
| A08 | Placement | | | |
| A09 | Reconciliation | | | |
| A10 | Rollout | | | |
| A11 | Drain / capacity limitation | | | |
| A12 | Recovery / cleanup | | | |

Findings:
Risks:
Remediation actions:
Rollback performed:
Final acceptance decision:
Reviewer:
```

**Acceptance decision:** The project is accepted only when all mandatory checks pass or documented deviations are explicitly approved. A11 includes an **expected temporary degradation** because this lab deliberately has no spare worker; acceptance means the operator recognizes the limitation, records it, and restores readiness.

## 13. Production readiness gaps

This capstone demonstrates installation and basic operational verification only. A production rollout additionally needs:

- Multiple control-plane nodes and a tested etcd quorum/recovery plan.
- Availability zones, topology spread, and capacity for node failures and drains.
- Proper PodDisruptionBudgets and rollout settings.
- Managed or audited PKI, RBAC, admission policies, secrets encryption, and workload identity.
- CNI policy, ingress, load balancing, persistent storage, and backup/restore.
- Monitoring, alerting, logs, tracing, SLIs/SLOs, and incident runbooks.
- Version-pinned infrastructure as code, patching, upgrade and rollback plans.
- Application and data-specific disaster recovery validation.

Do not label this local kind cluster production-ready.

## 14. Cleanup and rollback

First restore any cordoned worker:

```powershell
kubectl --context kind-k8s-admin-ch010 uncordon k8s-admin-ch010-worker
kubectl --context kind-k8s-admin-ch010 get nodes
```

Delete the training namespace and disposable cluster only after recording evidence:

```powershell
kubectl --context kind-k8s-admin-ch010 delete namespace ch010
kind delete cluster --name k8s-admin-ch010
kind get clusters
```

Optionally remove generated local manifests:

```powershell
Remove-Item .\kind-ch010.yaml, .\ch010-workload.yaml, .\ch010-client.yaml
```

**Warning:** Cluster deletion permanently removes cluster-local data. Verify the exact cluster name; never delete an unrelated environment.

## 15. Acceptance checklist

- [ ] Verified tooling and safe context.
- [ ] Created one control-plane and two worker nodes.
- [ ] Verified API readiness, control-plane Pods, kubelet/runtime and CNI.
- [ ] Deployed two replicas across separate workers.
- [ ] Verified DNS and HTTP access from an in-cluster client.
- [ ] Observed Pod reconciliation.
- [ ] Tested a Deployment rollout and understood anti-affinity/surge constraints.
- [ ] Drained one worker and documented the expected lack of spare capacity.
- [ ] Uncordoned worker and restored 2/2 Ready.
- [ ] Completed acceptance report with evidence and deviations.
- [ ] Deleted disposable lab resources.

## 16. Knowledge check

1. What proves a Kubernetes node is Ready, and what does it not prove?
2. Why can DNS succeed while a Service still has no usable endpoints?
3. Why do two workers with required anti-affinity provide no spare placement capacity during a drain?
4. How can a rolling update stall even when all current replicas are healthy?
5. Why should a drain test include both PDB and scheduling analysis?
6. What is the difference between installation verification and production readiness?
7. What evidence belongs in a cluster handover report?

## 17. Part 02 completion checkpoint

| Chapter | Title | Writing status |
|---|---|---|
| 006 | kubectl Installation and kubeconfig | Draft |
| 007 | Kubernetes Local Lab with kind and Minikube | Draft |
| 008 | kubeadm Cluster Installation | Draft |
| 009 | Containerd, CNI and CoreDNS Configuration | Draft |
| 010 | Cluster Installation and Verification Project | Draft |

**Writing milestone:** All five Part 02 chapter drafts are written. **Lab execution and editorial review remain pending**, so Part 02 is not yet marked fully validated or complete.

**Next:** Chapter 011 — Kubernetes API and API Resources.
