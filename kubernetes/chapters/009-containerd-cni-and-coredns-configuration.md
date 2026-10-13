# Chapter 009 — Containerd, CNI and CoreDNS Configuration

**Track:** Kubernetes Administration · **Part:** 02 — Cluster Installation and Setup · **Level:** Intermediate–Advanced · **Status:** Draft — lab execution pending

## 1. Learning objectives

After completing this chapter, you will be able to:

1. Explain how kubelet, the Container Runtime Interface (CRI), containerd, the Container Network Interface (CNI), and CoreDNS work together.
2. Inspect containerd runtime configuration, cgroup drivers, CRI sockets, images, and Pod sandboxes.
3. Describe Pod CIDRs, Service CIDRs, node routing, CNI plugins, and Kubernetes DNS resolution.
4. Diagnose `ContainerCreating`, `FailedCreatePodSandBox`, `ImagePullBackOff`, and DNS failures.
5. Perform read-only runtime and networking checks in a disposable kind cluster.
6. Simulate and recover from a DNS configuration error without changing cluster-wide CoreDNS settings.
7. Apply production change-control and rollback practices to runtime, CNI, and DNS configuration.

## 2. Architecture: from Pod specification to networked container

```text
kubectl / GitOps
      |
      v
Kubernetes API server
      |
      v
Scheduler assigns Pod to node
      |
      v
kubelet on node
      |
      +--> CRI gRPC --> containerd --> OCI runtime (runc) --> processes
      |                   |
      |                   +--> image store / snapshots
      |
      +--> Pod sandbox creation
                         |
                         +--> CNI plugin / node networking --> Pod IP
                         |
                         +--> kube-proxy or alternate Service dataplane
      |
      +--> Pod DNS policy + resolv.conf
                              |
                              v
                           CoreDNS
                              |
                         Service records / upstream DNS
```

**Separation of concerns:** Containerd manages containers and images, CNI establishes Pod networking, and CoreDNS provides DNS resolution. Kubernetes Service forwarding is generally implemented by kube-proxy or a replacement dataplane, not by CoreDNS. A DNS record resolving correctly does not prove network connectivity or application readiness.

## 3. Containerd and CRI fundamentals

### 3.1 Responsibilities

| Component | Responsibility | Typical diagnostic tool |
|---|---|---|
| kubelet | Reconcile assigned Pods and report node/container status | `kubectl describe node`, kubelet logs |
| CRI | Standard runtime API for Kubernetes | `crictl` |
| containerd | Image lifecycle, sandboxes, containers, snapshots | `crictl`, `ctr` |
| runc | Low-level OCI container execution | Runtime logs, containerd diagnostics |
| CNI | Attach Pod networking and configure routes/interfaces | CNI agent logs, node network tools |
| CoreDNS | Cluster DNS service discovery and forwarding | `kubectl logs`, DNS query tools |

### 3.2 CRI sockets and cgroup drivers

A common containerd socket is `unix:///run/containerd/containerd.sock`. Paths can differ by distribution. On systemd-based Linux nodes, the recommended configuration is for kubelet and containerd's OCI runtime to use compatible systemd cgroup handling.

Containerd **1.x and 2.x configuration schemas differ**. Do not copy a `SystemdCgroup` TOML snippet from one major version to another without checking the generated configuration and vendor guidance.

### 3.3 Containerd namespaces are not Kubernetes namespaces

Kubernetes CRI workloads commonly appear in containerd's `k8s.io` namespace. This is an internal containerd namespace, unrelated to the Kubernetes `metadata.namespace` field. `ctr -n k8s.io` is a low-level debugging command and not a substitute for the CRI API.

## 4. CNI and Pod networking fundamentals

Kubernetes networking expects each Pod to have a routable IP within the cluster's network model. The CNI implementation configures network interfaces, addresses, routes, policies, and potentially overlay or eBPF dataplanes.

### 4.1 Address spaces

- **Node subnet:** host VM or cloud VPC/VNet addresses.
- **Pod CIDR:** address range allocated to Pods; implementation and assignment vary.
- **Service CIDR:** virtual Service IP range.
- **DNS Service IP:** the ClusterIP assigned to the cluster DNS Service.

These ranges must be planned to avoid unintended overlaps with each other and connected networks. A CNI's routing or encapsulation strategy determines how Pod traffic crosses nodes.

### 4.2 Common CNI implementations

| CNI | Common design characteristics | Operational focus |
|---|---|---|
| Flannel | Simple Pod networking, often VXLAN | Pod CIDR, encapsulation, host firewall |
| Calico | Routing and network policy capabilities | BGP/VXLAN/IPIP modes, policy |
| Cilium | eBPF-based networking and observability | Kernel support, agent health, policy |
| AWS VPC CNI | AWS VPC-integrated Pod addressing | IP capacity, ENIs, IAM, subnet sizing |
| Azure CNI options | Azure-integrated Pod networking | VNet/subnet design, dataplane mode |
| GKE networking | Provider-managed GKE networking | VPC-native ranges, policies, dataplane |

Do not assume every implementation uses an overlay or requires kube-proxy. Consult the exact version and installation mode.

## 5. CoreDNS and service discovery

CoreDNS commonly runs as a Deployment in `kube-system` and is reached through the `kube-dns` Service (the historical Service name is not the name of the implementation).

Typical DNS names:

```text
web.ch009.svc.cluster.local
web.ch009.svc
web
```

Short names depend on the querying Pod's namespace and search domains. The cluster DNS suffix is often `cluster.local` but can be customized.

### DNS request flow

```text
Pod resolver -> nameserver from /etc/resolv.conf
             -> kube-dns ClusterIP
             -> CoreDNS
             -> Kubernetes Service records OR configured upstream resolver
```

CoreDNS watches Kubernetes API resources to provide records for Services and, depending on configuration, Pods and EndpointSlices. DNS resolution for a Service does **not** guarantee that healthy backends exist.

### DNS policies

- `ClusterFirst`: usual default for Pods.
- `Default`: inherit node resolver configuration.
- `None`: use explicitly supplied `dnsConfig`.
- `ClusterFirstWithHostNet`: often needed for Pods using host networking.

An incorrect `dnsPolicy` or `dnsConfig` can break application DNS even when CoreDNS is healthy.

## 6. Prerequisites and safety

Use **Windows PowerShell**, Docker Desktop, `kind`, and `kubectl`. This chapter uses a disposable **two-node kind cluster** to inspect containerd, CNI, and CoreDNS without modifying a production node.

```powershell
docker version
kind version
kubectl version --client
```

**Guardrails:** Never restart production containerd, modify a CNI DaemonSet, or edit the CoreDNS ConfigMap solely to follow this tutorial. Such actions can disrupt workloads across a node or cluster. All failure simulation is scoped to a disposable namespace and Pod.

Create a working directory:

```powershell
New-Item -ItemType Directory -Force .\k8s-ch009 | Out-Null
Set-Location .\k8s-ch009
```

## 7. Lab A — Create and inspect a two-node kind cluster

### Step A1 — Define the topology

```powershell
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-ch009.yaml

kind create cluster --name k8s-admin-ch009 --config .\kind-ch009.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch009 get nodes -o wide
```

**Expected:** context `kind-k8s-admin-ch009`, with control-plane and worker nodes reporting Ready.

**Safety gate:** Stop if the current context does not match `kind-k8s-admin-ch009`.

### Step A2 — Inspect system components

```powershell
kubectl --context kind-k8s-admin-ch009 -n kube-system get pods -o wide
kubectl --context kind-k8s-admin-ch009 -n kube-system get daemonsets
kubectl --context kind-k8s-admin-ch009 -n kube-system get deployment coredns
kubectl --context kind-k8s-admin-ch009 -n kube-system get service kube-dns
kubectl --context kind-k8s-admin-ch009 get nodes -o custom-columns='NAME:.metadata.name,RUNTIME:.status.nodeInfo.containerRuntimeVersion,KUBELET:.status.nodeInfo.kubeletVersion'
```

**Expected:** CoreDNS Deployment and kube-dns Service exist, and nodes show a CRI runtime. In typical kind clusters, kindnet and kube-proxy run as DaemonSets, but names and implementations vary by version/configuration.

## 8. Lab B — Inspect containerd and CRI

kind nodes are Docker containers with their own containerd runtime.

### Step B1 — Read-only runtime inspection

```powershell
docker exec k8s-admin-ch009-worker sh -c 'containerd --version'
docker exec k8s-admin-ch009-worker sh -c 'ls -l /run/containerd/containerd.sock'
docker exec k8s-admin-ch009-worker sh -c 'grep -n SystemdCgroup /etc/containerd/config.toml || true'
docker exec k8s-admin-ch009-worker crictl --runtime-endpoint unix:///run/containerd/containerd.sock info
```

**Expected:** runtime version, CRI socket, and CRI information. Some kind node images may store runtime configuration in a different location; inspect the installed version before interpreting a missing config file.

### Step B2 — Compare CRI and containerd views

```powershell
docker exec k8s-admin-ch009-worker crictl --runtime-endpoint unix:///run/containerd/containerd.sock images
docker exec k8s-admin-ch009-worker crictl --runtime-endpoint unix:///run/containerd/containerd.sock pods
docker exec k8s-admin-ch009-worker ctr -n k8s.io images ls
```

**Expected:** image and Pod sandbox inventories. `crictl` output is CRI-oriented; `ctr` shows lower-level containerd objects.

**Production note:** Use `ctr` for diagnostics only unless you understand its runtime namespace and object lifecycle. Avoid deleting images or containers directly under kubelet management.

## 9. Lab C — Deploy workloads and inspect Pod IP routing

### Step C1 — Create a namespace and application

```powershell
kubectl --context kind-k8s-admin-ch009 create namespace ch009
kubectl --context kind-k8s-admin-ch009 -n ch009 create deployment web --image=nginx:stable --replicas=2
kubectl --context kind-k8s-admin-ch009 -n ch009 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch009 -n ch009 expose deployment web --port=80 --target-port=80 --type=ClusterIP
kubectl --context kind-k8s-admin-ch009 -n ch009 get pods -o wide
kubectl --context kind-k8s-admin-ch009 -n ch009 get service web -o wide
kubectl --context kind-k8s-admin-ch009 -n ch009 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** two Ready NGINX Pods, Pod IPs, a ClusterIP Service, and an EndpointSlice for the Service.

### Step C2 — Inspect Pod CIDRs and node networking

```powershell
kubectl --context kind-k8s-admin-ch009 get nodes -o jsonpath='{range .items[*]}{.metadata.name}{" podCIDR="}{.spec.podCIDR}{"\n"}{end}'
docker exec k8s-admin-ch009-worker sh -c 'ip -brief address'
docker exec k8s-admin-ch009-worker sh -c 'ip route'
```

**Expected:** node Pod CIDRs and Linux interface/route information. The specific routes depend on kind's networking setup.

### Step C3 — Inspect Service endpoints

```powershell
kubectl --context kind-k8s-admin-ch009 -n ch009 describe service web
kubectl --context kind-k8s-admin-ch009 -n ch009 get endpointslices -l kubernetes.io/service-name=web -o yaml
```

**Expected:** Service selector matches Pod labels and ready endpoints exist. EndpointSlice addresses correspond to application Pods.

## 10. Lab D — Validate CoreDNS and cluster DNS

### Step D1 — Inspect DNS Service and CoreDNS configuration

```powershell
kubectl --context kind-k8s-admin-ch009 -n kube-system get service kube-dns -o wide
kubectl --context kind-k8s-admin-ch009 -n kube-system get configmap coredns -o yaml
kubectl --context kind-k8s-admin-ch009 -n kube-system logs deployment/coredns --tail=50
```

**Expected:** kube-dns has a ClusterIP and CoreDNS configuration contains a Kubernetes plugin and forwarding configuration. **Do not modify this ConfigMap in the lab.**

### Step D2 — Create a DNS client Pod

Use a versioned BusyBox image with `nslookup`:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: dns-client
  namespace: ch009
spec:
  containers:
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          memory: 64Mi
'@ | Set-Content -Encoding ascii .\dns-client.yaml

kubectl --context kind-k8s-admin-ch009 apply -f .\dns-client.yaml
kubectl --context kind-k8s-admin-ch009 -n ch009 wait --for=condition=Ready pod/dns-client --timeout=180s
```

**Expected:** Pod becomes Ready.

### Step D3 — Inspect resolver and query service records

```powershell
kubectl --context kind-k8s-admin-ch009 -n ch009 exec dns-client -- cat /etc/resolv.conf
kubectl --context kind-k8s-admin-ch009 -n ch009 exec dns-client -- nslookup kubernetes.default.svc.cluster.local
kubectl --context kind-k8s-admin-ch009 -n ch009 exec dns-client -- nslookup web.ch009.svc.cluster.local
kubectl --context kind-k8s-admin-ch009 -n ch009 exec dns-client -- nslookup web
```

**Expected:** resolver points to the cluster DNS IP; queries return Service IPs. If the cluster domain differs from `cluster.local`, use the configured domain. Short-name resolution should work inside the same namespace.

### Step D4 — Verify application access separately from DNS

```powershell
kubectl --context kind-k8s-admin-ch009 -n ch009 exec dns-client -- wget -qO- http://web.ch009.svc.cluster.local
```

**Expected:** NGINX HTML output. DNS lookup success alone does not establish that the Service routes to healthy Pods.

## 11. Lab E — Simulate DNS misconfiguration safely

This exercise creates **one misconfigured Pod**; it does not change cluster-wide DNS.

### Step E1 — Create a Pod with an intentionally invalid DNS server

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: bad-dns-client
  namespace: ch009
spec:
  dnsPolicy: None
  dnsConfig:
    nameservers:
      - 127.0.0.1
    searches:
      - ch009.svc.cluster.local
  containers:
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
'@ | Set-Content -Encoding ascii .\bad-dns-client.yaml

kubectl --context kind-k8s-admin-ch009 apply -f .\bad-dns-client.yaml
kubectl --context kind-k8s-admin-ch009 -n ch009 wait --for=condition=Ready pod/bad-dns-client --timeout=180s
kubectl --context kind-k8s-admin-ch009 -n ch009 exec bad-dns-client -- cat /etc/resolv.conf
kubectl --context kind-k8s-admin-ch009 -n ch009 exec bad-dns-client -- nslookup web.ch009.svc.cluster.local
```

**Expected:** Pod is running but DNS query fails or times out because `127.0.0.1` is the Pod's loopback interface and no DNS resolver is listening there. Depending on BusyBox, error wording varies.

### Step E2 — Recover without touching CoreDNS

```powershell
kubectl --context kind-k8s-admin-ch009 -n ch009 delete pod bad-dns-client
kubectl --context kind-k8s-admin-ch009 -n ch009 exec dns-client -- nslookup web.ch009.svc.cluster.local
```

**Expected:** the normal client still resolves the Service. The failure was isolated to the bad Pod's DNS configuration.

## 12. Troubleshooting runbook

| Symptom | First evidence | Investigate |
|---|---|---|
| `ContainerCreating` | `kubectl describe pod` events | CRI, CNI, volumes, sandbox creation |
| `FailedCreatePodSandBox` | Pod events, kubelet logs | Runtime socket, CNI binary/config, IP allocation |
| `ImagePullBackOff` | Pod events, runtime image inventory | Registry connectivity, credentials, DNS |
| `NetworkPluginNotReady` | Node conditions, kubelet logs | CNI DaemonSet/config and host networking |
| Pod-to-Pod traffic fails | Pod IPs, routes, policies | CNI health, firewall, encapsulation |
| Service resolves but cannot connect | EndpointSlices, Service selectors | Readiness, ports, dataplane/network policy |
| DNS lookup times out | Pod `/etc/resolv.conf`, CoreDNS logs | DNS policy, kube-dns Service, network reachability |
| External DNS fails but internal works | CoreDNS forwarding config and upstream reachability | Node DNS, upstream resolvers, egress rules |
| Runtime errors after config change | containerd/kubelet logs | CRI plugin, cgroups, version compatibility |

### Useful diagnostics

```powershell
kubectl --context kind-k8s-admin-ch009 get nodes
kubectl --context kind-k8s-admin-ch009 get pods -A -o wide
kubectl --context kind-k8s-admin-ch009 get events -A --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch009 -n kube-system logs deployment/coredns --tail=100
kubectl --context kind-k8s-admin-ch009 -n ch009 describe pod dns-client
```

For a real Linux node, use `journalctl -u kubelet`, `systemctl status containerd`, `crictl info`, and approved CNI diagnostics. Do not restart runtime or networking components without understanding disruption scope.

## 13. Production configuration and change management

### Containerd

- Use supported containerd and Kubernetes versions; verify CRI compatibility and cgroup driver settings.
- Maintain approved registry mirrors, image-pull credentials, and disk/image garbage-collection policies.
- Alert on containerd failures, image-pull latency, ephemeral disk pressure, and Pod sandbox errors.
- Drain or replace nodes in a controlled manner before disruptive runtime upgrades, respecting PodDisruptionBudgets and storage constraints.

### CNI

- Maintain a documented Pod CIDR/Service CIDR/VPC/VNet plan.
- Validate CNI version, kernel support, IP address capacity, policy enforcement, and cross-node connectivity.
- Review CNI upgrades and configuration changes in staging before production.
- Monitor IP exhaustion, routing errors, packet drops, policy denials, and CNI agent readiness.

### CoreDNS

- Monitor query latency, error rates, upstream health, DNS Pod readiness, and Service availability.
- Size DNS replicas and resources to workload query rates and failure domains.
- Avoid direct unreviewed CoreDNS ConfigMap changes; use source control and a rollback plan.
- Distinguish DNS resolution, Service dataplane, and application readiness before remediation.

### Incident evidence checklist

Record cluster/context, namespace, timestamps, Pod UID, node, runtime version, CNI implementation/version, Pod IP, DNS Service IP, relevant events, CoreDNS logs, and a reproducible query. Redact credentials and sensitive data.

## 14. Cleanup

Stop any active port-forward or watch commands. Use explicit context and verify cluster identity:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch009 get nodes
```

Only for the disposable lab cluster:

```powershell
kubectl --context kind-k8s-admin-ch009 delete namespace ch009
kind delete cluster --name k8s-admin-ch009
kind get clusters
Remove-Item .\kind-ch009.yaml, .\dns-client.yaml, .\bad-dns-client.yaml
```

**Warning:** Deleting the kind cluster permanently removes its workloads and local data. Never run equivalent deletion commands against production clusters.

## 15. Acceptance checklist

- [ ] Verified Docker, kind, kubectl and the exact lab context.
- [ ] Created two-node disposable cluster.
- [ ] Inspected containerd version, CRI socket, images, and sandboxes.
- [ ] Inspected CNI and kube-proxy components where present.
- [ ] Deployed NGINX and verified Pod IPs and EndpointSlices.
- [ ] Inspected CoreDNS configuration and kube-dns Service.
- [ ] Resolved Kubernetes and application Service DNS names.
- [ ] Verified HTTP access through the Service name.
- [ ] Reproduced a Pod-scoped DNS failure.
- [ ] Recovered without changing cluster-wide DNS.
- [ ] Cleaned up all disposable resources.

## 16. Knowledge check

1. How does kubelet communicate with containerd?
2. Why is containerd's `k8s.io` namespace different from a Kubernetes namespace?
3. What is the difference between Pod CIDR and Service CIDR?
4. Which components provide Pod networking, Service forwarding, and DNS resolution?
5. Why can a DNS lookup succeed while HTTP access still fails?
6. What does `dnsPolicy: None` change?
7. How would you distinguish a CNI problem from a container runtime problem?
8. Why can restarting containerd or changing CoreDNS be disruptive in production?

## 17. Chapter status and next chapter

**Draft written; lab execution has not been independently verified.** Mark **Lab Validated** after successful acceptance checks and **Complete** after review.

**Next:** Chapter 010 — Cluster Installation and Verification Project.
