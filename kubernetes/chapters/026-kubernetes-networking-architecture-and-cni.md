# Chapter 026 — Kubernetes Networking Architecture and CNI

**Track:** Kubernetes Administration · **Part 06 — Kubernetes Networking**  
**Status:** Draft — hands-on validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 001–025; Windows PowerShell, Docker Desktop, kind, kubectl

## 1. Production scenario and learning objectives

Your application team reports that two Pods on different Kubernetes nodes cannot communicate reliably. A Service sometimes appears healthy, but requests time out after a node replacement. The network team asks whether the fault is in the CNI plugin, Pod routing, DNS, a NetworkPolicy, or the application itself.

Kubernetes networking is easiest to troubleshoot by separating the **data path** from the **control and configuration path**.

By the end of this chapter, you will:

1. Explain Kubernetes Pod, Service, node, and external traffic models.
2. Trace packet flow for same-node and cross-node Pod-to-Pod communication.
3. Describe CNI's role in Pod network setup, IP address management, and cleanup.
4. Distinguish container network namespaces, veth pairs, bridges, routing, encapsulation, and eBPF datapaths.
5. Explain kube-proxy versus CNI responsibilities and common exceptions.
6. Inspect Pod CIDRs, CNI configuration, node routes, and connectivity.
7. Understand NetworkPolicy enforcement dependencies and common failure modes.
8. Complete seven controlled networking labs and document troubleshooting evidence.

## 2. Kubernetes networking contracts

The conventional Kubernetes networking model aims to provide:

- Each Pod with a distinct IP address in the cluster networking domain.
- Direct Pod-to-Pod communication across nodes without application-level address translation in the normal Pod networking model.
- Node-to-Pod and Pod-to-node reachability as supported by the cluster network implementation.
- Stable Service virtual addresses and names that decouple clients from changing Pod IPs.

**Important qualification:** The implementation is not uniform. Overlay, routed, VPC-native, eBPF, service-mesh and Windows networking implementations differ. NAT may exist at network boundaries, for outbound traffic, or in specific datapaths. The practical contract should be verified against your CNI and cloud provider.

### Four traffic paths

```text
A. Same-node Pod -> Pod
   Pod A -> veth / node datapath -> Pod B

B. Cross-node Pod -> Pod
   Pod A -> node A datapath -> underlay / tunnel / route
         -> node B datapath -> Pod B

C. Pod -> Service -> Pod
   Pod -> Service VIP or DNS-resolved ClusterIP
       -> service implementation -> selected backend Pod

D. Pod -> external destination
   Pod -> node / CNI egress datapath -> cloud or on-prem network
       -> NAT / firewall / route as configured
```

Pod-to-Pod traffic can work while Service traffic fails, or vice versa. Diagnose them separately.

## 3. Networking architecture and responsibility boundaries

| Component | Responsibility | What it usually does not own |
|---|---|---|
| CNI plugin | Configure Pod interfaces, IP allocation and connectivity | Kubernetes API admission and application DNS records |
| Container runtime + kubelet | Create sandbox and invoke network setup via runtime integration | Choose Service backends |
| CoreDNS | Resolve Kubernetes Service and Pod-related DNS names | Forward packets to backend Pods |
| Service controller / EndpointSlice controllers | Maintain desired Service and endpoint objects | Configure the CNI for every Pod directly |
| kube-proxy | Implement Service routing in clusters using kube-proxy | Pod IP allocation |
| eBPF Service datapath | May replace kube-proxy's Service forwarding | Automatically replace every CNI or DNS function |
| NetworkPolicy controller/datapath | Enforce supported ingress/egress policy | Guarantee enforcement when CNI lacks policy support |
| Cloud network | Underlay, VPC/VNet, security groups, routes and load balancers | Application readiness |

**Do not assume kube-proxy is installed.** Some managed and self-managed distributions implement Services with an alternative datapath. Identify the actual network stack before troubleshooting iptables or IPVS.

## 4. Pod network namespaces, veth and routing

On Linux, a Pod normally has a network namespace shared by its containers. Containers in that Pod communicate over `localhost` and share the Pod IP, while distinct Pods have distinct network namespaces.

A common CNI implementation creates a **virtual Ethernet (veth) pair**:

```text
+-------------------------+       +------------------------------+
| Pod network namespace   |       | Host network namespace       |
| eth0 <------------------+-------+--> veth peer -> bridge/route  |
| 10.x.y.z                |       |             -> other Pods     |
+-------------------------+       +------------------------------+
```

This is a useful mental model, **not a universal topology**. Some CNIs use different device types or datapath architectures. A `hostNetwork: true` Pod uses the host network namespace and does not behave like an ordinary isolated Pod.

### Node and Pod IP concepts

- **Node IP:** Address used for node-to-node and control-plane connectivity.
- **Pod IP:** Address assigned to an individual Pod, usually from a node Pod CIDR or another IPAM pool.
- **Service ClusterIP:** Virtual address representing a Service, not generally bound to a normal Pod interface.
- **External IP / LoadBalancer IP:** Address exposed outside the cluster by an implementation-specific network path.

`spec.podCIDR` may be populated by cluster networking configuration, but **not every CNI allocates from or depends on this field**. Inspect CNI-specific IPAM data before concluding that a missing Pod CIDR is an error.

## 5. What CNI actually does

CNI is a specification and plugin ecosystem used by container runtimes to set up and tear down container networking.

A typical flow:

1. Kubelet requests creation of a Pod sandbox from the container runtime.
2. The runtime prepares the sandbox/network namespace.
3. The runtime invokes configured CNI plugin(s) for network setup.
4. IPAM assigns an IP or delegates allocation to a provider-specific mechanism.
5. The plugin configures interfaces, addresses, routes and optional datapath state.
6. The runtime reports the sandbox network result and Pod IP to kubelet.
7. On teardown, the runtime invokes network cleanup.

A failure can surface as `ContainerCreating` or `FailedCreatePodSandBox`, with events referring to CNI setup, IPAM exhaustion, missing plugin binaries, or network agent health.

### Configuration and installation paths

On Linux nodes, common paths include:

```text
/etc/cni/net.d/           CNI configuration
/opt/cni/bin/             CNI plugin executables
/var/lib/cni/             Some CNI/IPAM state
/run/netns/               Network namespace handles in some setups
```

Paths are distribution-dependent. Managed services may package CNI components differently. Inspect the actual runtime configuration rather than assuming these paths always exist.

## 6. CNI implementation models

| Model | General behavior | Operational tradeoffs |
|---|---|---|
| Overlay (VXLAN, Geneve, etc.) | Encapsulates Pod traffic over node underlay | Additional headers/MTU overhead; simpler underlay requirements |
| Routed/BGP | Advertises Pod reachability via routes | Routing integration and policy complexity |
| VPC/VNet-native | Uses cloud-network-addressing primitives | Cloud IP quotas, subnet capacity and ENI/NIC limits |
| eBPF datapath | Programs kernel hooks/maps for forwarding and policy | Kernel compatibility and specialized observability |
| Hybrid | Combines multiple approaches | Requires component-specific packet-path knowledge |

Representative implementations include **Calico**, **Cilium**, **Flannel**, **AWS VPC CNI**, and **Azure CNI**. These are not interchangeable merely by changing a DaemonSet; migration can affect Pod addressing, NetworkPolicy, Services, routing and downtime.

### Platform differences

- **Amazon EKS:** Often uses Amazon VPC CNI for Pod networking; Pod IP and ENI allocation can become scheduling constraints.
- **Azure AKS:** Network behavior varies by Azure CNI mode and network datapath; overlay and VNet-native models have different IP and routing considerations.
- **Google GKE:** VPC-native alias IPs and Dataplane V2 change the relevant control and packet paths.
- **Self-managed kind/kubeadm:** Inspect the actual CNI and kube-proxy configuration installed in that cluster.

Use vendor-specific runbooks for managed environments; never apply kind-specific remediation directly to EKS, AKS or GKE.

## 7. Same-node versus cross-node packet flow

### Same-node Pod-to-Pod

1. Source application resolves or already knows destination Pod IP.
2. Source kernel selects route and emits packet from Pod interface.
3. Node datapath forwards toward the destination Pod interface.
4. Destination Pod receives traffic if its process is listening and policy permits it.

### Cross-node Pod-to-Pod

1. Source Pod sends to destination Pod IP.
2. Node datapath determines destination node or next hop.
3. Depending on CNI, traffic is encapsulated, routed, or sent using cloud-native addressability.
4. Underlay network carries traffic between nodes.
5. Destination node decapsulates/routes as necessary and delivers to the Pod.

**Common cross-node failure domains:** node firewall, security groups/NSGs, missing routes, tunnel port blocking, MTU mismatch, IPAM allocation problems, stale datapath state, and policy enforcement.

## 8. Service networking versus Pod networking

A Service selects backends through labels and EndpointSlices. A ClusterIP is usually implemented by kube-proxy or a replacement Service datapath.

```text
Client Pod
  -> DNS resolves api.namespace.svc.cluster.local to ClusterIP
  -> Service datapath selects ready endpoint
  -> destination Pod IP and port
```

An application can have:
- Working direct Pod IP connectivity but failing Service DNS.
- Working DNS resolution but no ready Service endpoints.
- Ready endpoints but broken Service forwarding.
- Working Service forwarding but application-level HTTP errors.

**Troubleshooting order:** DNS answer → Service spec → EndpointSlices → direct Pod IP → Service datapath → application.

## 9. NetworkPolicy fundamentals and caveats

NetworkPolicy is a Kubernetes API for expressing traffic isolation between Pods and IP ranges, but enforcement depends on a compatible networking implementation.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-from-client
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: client
      ports:
        - protocol: TCP
          port: 80
```

This example allows selected ingress **only when the CNI supports NetworkPolicy enforcement** and the selected Pods are otherwise isolated by the policy. It does not automatically create a universal default-deny for all Pods.

**Security warning:** The default kind networking configuration should not be assumed to enforce NetworkPolicy. Do not use a successful or failed NetworkPolicy connectivity test in kind as proof of production policy enforcement unless the actual CNI datapath supports and enables it.

NetworkPolicy also does not replace cloud firewalls, workload identity, TLS or application authorization.

## 10. Network MTU, fragmentation and performance

Overlay headers reduce effective payload MTU. A path that supports 1500-byte underlay frames may need a smaller Pod MTU when encapsulation is present. Misconfiguration can cause intermittent large-payload failures while small pings or TCP handshakes succeed.

Investigate:
- CNI configured MTU and underlying node interface MTU.
- ICMP Packet Too Big handling and PMTU discovery.
- TCP retransmissions, dropped packets and fragmentation counters.
- Cross-zone/cross-node asymmetry.
- eBPF/iptables/conntrack drops where supported.

Do not change MTU cluster-wide during an incident without a controlled rollout and rollback plan.

## 11. Lab environment and safety

Use **Windows PowerShell**, Docker Desktop and kind. The lab creates one control-plane node and two worker nodes.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch026 | Out-Null
Set-Location .\k8s-ch026
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch026 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch026 get nodes -o wide
kubectl --context kind-k8s-admin-ch026 create namespace ch026
```

**Expected:** `kind-k8s-admin-ch026` and three Ready nodes. If Docker capacity, networking, or image pulling fails, record Blocked; do not switch to a production context.

## 12. Lab A — Discover CNI, Pod CIDRs and node networking

```powershell
kubectl --context kind-k8s-admin-ch026 get nodes -o wide
kubectl --context kind-k8s-admin-ch026 get nodes -o custom-columns='NAME:.metadata.name,PODCIDR:.spec.podCIDR,INTERNALIP:.status.addresses[0].address'
kubectl --context kind-k8s-admin-ch026 -n kube-system get pods -o wide
kubectl --context kind-k8s-admin-ch026 -n kube-system get daemonsets
kubectl --context kind-k8s-admin-ch026 get pods -A -o wide
```

**Expected:** node addresses and, in typical kind setups, Pod CIDRs; system components depend on kind version. The CNI may not appear as a separately named DaemonSet in all distributions. Record the actual CNI rather than guessing from a Pod name.

For deeper inspection, `docker exec` targets the **disposable kind node container**, not a production host:

```powershell
docker exec k8s-admin-ch026-worker sh -c "ls -l /etc/cni/net.d/ 2>/dev/null || true"
docker exec k8s-admin-ch026-worker sh -c "ip -brief addr; ip route"
```

**Expected:** node interface/route information and CNI configuration where available. Exact interface names and route shapes are implementation-dependent.

## 13. Lab B — Pod network namespace and localhost

Create a two-container Pod. Both containers share the Pod network namespace.

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: shared-network
  namespace: ch026
spec:
  containers:
    - name: web
      image: nginx:stable
      ports:
        - containerPort: 80
      resources:
        requests:
          cpu: 20m
          memory: 32Mi
    - name: client
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\shared-network.yaml

kubectl --context kind-k8s-admin-ch026 apply -f .\shared-network.yaml
kubectl --context kind-k8s-admin-ch026 -n ch026 wait --for=condition=Ready pod/shared-network --timeout=180s
kubectl --context kind-k8s-admin-ch026 -n ch026 get pod shared-network -o wide
kubectl --context kind-k8s-admin-ch026 -n ch026 exec shared-network -c client -- wget -qO- http://127.0.0.1/
```

**Expected:** NGINX default HTML is returned over `localhost` from the second container. This demonstrates network namespace sharing, not cross-Pod routing.

## 14. Lab C — Same-node and cross-node Pod connectivity

Discover the worker names and create two web Pods pinned to different workers:

```powershell
$workers = @((kubectl --context kind-k8s-admin-ch026 get nodes -l '!node-role.kubernetes.io/control-plane' -o json | ConvertFrom-Json).items | ForEach-Object { $_.metadata.name })
if ($workers.Count -ne 2) { throw "Expected exactly two workers" }
@'
apiVersion: v1
kind: Pod
metadata:
  name: web-a
  namespace: ch026
  labels:
    app: crossnode-web
spec:
  nodeSelector:
    kubernetes.io/hostname: NODE_A
  containers:
    - name: web
      image: nginx:stable
      ports:
        - containerPort: 80
      resources:
        requests:
          cpu: 20m
          memory: 32Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: web-b
  namespace: ch026
  labels:
    app: crossnode-web
spec:
  nodeSelector:
    kubernetes.io/hostname: NODE_B
  containers:
    - name: web
      image: nginx:stable
      ports:
        - containerPort: 80
      resources:
        requests:
          cpu: 20m
          memory: 32Mi
'@.Replace('NODE_A', $workers[0]).Replace('NODE_B', $workers[1]) | Set-Content -Encoding ascii .\web-pods.yaml

kubectl --context kind-k8s-admin-ch026 apply -f .\web-pods.yaml
kubectl --context kind-k8s-admin-ch026 -n ch026 wait --for=condition=Ready pod/web-a --timeout=180s
kubectl --context kind-k8s-admin-ch026 -n ch026 wait --for=condition=Ready pod/web-b --timeout=180s
kubectl --context kind-k8s-admin-ch026 -n ch026 get pods -l app=crossnode-web -o wide
```

Create a disposable client Pod pinned to the same worker as web-a:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: net-client
  namespace: ch026
spec:
  nodeSelector:
    kubernetes.io/hostname: NODE_A
  containers:
    - name: client
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@.Replace('NODE_A', $workers[0]) | Set-Content -Encoding ascii .\net-client.yaml

kubectl --context kind-k8s-admin-ch026 apply -f .\net-client.yaml
kubectl --context kind-k8s-admin-ch026 -n ch026 wait --for=condition=Ready pod/net-client --timeout=180s
$ipA = kubectl --context kind-k8s-admin-ch026 -n ch026 get pod web-a -o jsonpath='{.status.podIP}'
$ipB = kubectl --context kind-k8s-admin-ch026 -n ch026 get pod web-b -o jsonpath='{.status.podIP}'
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -qO- "http://$ipA/"
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -qO- "http://$ipB/"
```

**Expected:** HTTP succeeds to both Pod IPs; `web-a` tests same-node reachability and `web-b` cross-node reachability. Verify actual node assignments before interpreting results.

## 15. Lab D — Service and EndpointSlice routing

Create a ClusterIP Service selecting both web Pods:

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch026
spec:
  selector:
    app: crossnode-web
  ports:
    - name: http
      port: 80
      targetPort: 80
'@ | Set-Content -Encoding ascii .\web-service.yaml

kubectl --context kind-k8s-admin-ch026 apply -f .\web-service.yaml
kubectl --context kind-k8s-admin-ch026 -n ch026 get service web -o wide
kubectl --context kind-k8s-admin-ch026 -n ch026 get endpointslices -l kubernetes.io/service-name=web -o wide
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -qO- http://web.ch026.svc.cluster.local/
```

**Expected:** Service resolves and HTTP succeeds. EndpointSlices contain ready endpoints for the web Pods.

### Negative test: wrong Service selector

Temporarily change the selector to a label that matches no Pods:

```powershell
kubectl --context kind-k8s-admin-ch026 -n ch026 patch service web --type=merge -p '{"spec":{"selector":{"app":"no-such-app"}}}'
kubectl --context kind-k8s-admin-ch026 -n ch026 get endpointslices -l kubernetes.io/service-name=web -o yaml
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -T 3 -qO- http://web.ch026.svc.cluster.local/
```

**Expected:** Service has no usable ready endpoints and the HTTP request fails. Exact error may be timeout or connection refusal depending on datapath. This is a **Service selector/endpoint failure**, not necessarily a CNI routing failure.

Restore the selector:

```powershell
kubectl --context kind-k8s-admin-ch026 -n ch026 patch service web --type=merge -p '{"spec":{"selector":{"app":"crossnode-web"}}}'
kubectl --context kind-k8s-admin-ch026 -n ch026 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -qO- http://web.ch026.svc.cluster.local/
```

## 16. Lab E — DNS diagnosis: name versus IP

```powershell
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- cat /etc/resolv.conf
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- nslookup web.ch026.svc.cluster.local
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- nslookup kubernetes.default.svc.cluster.local
kubectl --context kind-k8s-admin-ch026 -n kube-system get pods -l k8s-app=kube-dns -o wide
```

**Expected:** DNS resolves Service names to ClusterIPs. Compare the Service ClusterIP with the DNS answer.

**Diagnostic interpretation:**
- Pod IP HTTP succeeds, Service DNS lookup fails: inspect CoreDNS and Pod DNS configuration.
- DNS succeeds, Service HTTP fails, direct Pod IP succeeds: inspect Service selector, EndpointSlices and Service datapath.
- Direct cross-node Pod IP fails: inspect CNI routing, node firewall and network policies.
- All network checks pass, but application returns HTTP 500: investigate the application.

Do not delete CoreDNS or restart networking agents in a shared cluster as a first diagnostic step.

## 17. Lab F — Inspect CNI config, routes and network state

Use read-only inspection against the disposable kind worker containers:

```powershell
docker exec k8s-admin-ch026-worker sh -c "ip -brief addr; ip route"
docker exec k8s-admin-ch026-worker2 sh -c "ip -brief addr; ip route"
docker exec k8s-admin-ch026-worker sh -c "ls -la /etc/cni/net.d/ 2>/dev/null || true"
docker exec k8s-admin-ch026-worker2 sh -c "ls -la /etc/cni/net.d/ 2>/dev/null || true"
kubectl --context kind-k8s-admin-ch026 -n kube-system get pods -o wide
```

**Expected:** network interfaces, routes and available CNI configuration. Compare node-to-node routes and Pod subnet reachability.

If the kind node image provides `ip` and CNI files, record:
- Node interface names and IP addresses.
- Pod CIDR routes.
- Bridge or tunnel interfaces where present.
- CNI configuration plugin type(s).

**Do not edit CNI configuration** in this lab. CNI changes can disrupt all Pods on a node.

## 18. Lab G — NetworkPolicy enforcement capability check

This lab is deliberately **observational**: determine whether your CNI enforces NetworkPolicy rather than assuming enforcement.

First record the current CNI implementation and cluster version. Then apply a policy selecting the web Pods:

```powershell
@'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-deny-ingress
  namespace: ch026
spec:
  podSelector:
    matchLabels:
      app: crossnode-web
  policyTypes:
    - Ingress
'@ | Set-Content -Encoding ascii .\web-deny.yaml

kubectl --context kind-k8s-admin-ch026 apply -f .\web-deny.yaml
kubectl --context kind-k8s-admin-ch026 -n ch026 get networkpolicy
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -T 3 -qO- http://web.ch026.svc.cluster.local/
```

**Expected:** If the installed CNI enforces NetworkPolicy, ingress to selected web Pods is denied. If the kind networking implementation does not enforce policies, HTTP may still succeed. **A NetworkPolicy object being accepted by the API is not proof of enforcement.**

Remove the policy and retest:

```powershell
kubectl --context kind-k8s-admin-ch026 -n ch026 delete networkpolicy web-deny-ingress
kubectl --context kind-k8s-admin-ch026 -n ch026 exec net-client -- wget -qO- http://web.ch026.svc.cluster.local/
```

**Expected:** connectivity is restored or remains available, depending on enforcement capability. Mark this lab **Capability Observed**, not Pass for enforcement, unless you have independently confirmed a policy-capable CNI.

## 19. Production troubleshooting decision tree

```text
Connectivity problem
  |
  +-- Pod Ready and application listening?
  |     No -> application/container/probe
  |
  +-- DNS resolves target Service?
  |     No -> resolv.conf, CoreDNS, DNS policy
  |
  +-- Service has ready EndpointSlices?
  |     No -> selector, labels, readiness, target port
  |
  +-- Direct destination Pod IP reachable?
  |     No -> CNI, NetworkPolicy, node route, firewall, MTU
  |
  +-- Direct Pod IP works, Service IP fails?
  |     Yes -> kube-proxy/eBPF Service datapath, conntrack
  |
  +-- Only cross-node fails?
  |     Yes -> underlay, tunnel, route, cloud security, MTU
  |
  +-- Only external egress fails?
        Yes -> NAT, routing, firewall, DNS, egress policy
```

## 20. Incident symptom matrix

| Symptom | Evidence | Likely failure domain | Safe next step |
|---|---|---|---|
| `FailedCreatePodSandBox` | Pod events, CNI agent logs | CNI plugin/IPAM/runtime | Inspect node CNI health and capacity |
| Pod IP missing | Pod status and events | Sandbox/network setup | Check runtime/CNI failures |
| Same-node works, cross-node fails | Direct Pod IP tests | Routes, overlay, firewall, MTU | Compare node routes and datapath |
| Pod IP works, Service IP fails | EndpointSlices, kube-proxy/eBPF | Service forwarding | Inspect actual Service datapath |
| DNS fails, IP works | CoreDNS, resolv.conf | DNS | Check CoreDNS and policies |
| Service has zero endpoints | EndpointSlices, labels, readiness | Application/selector | Correct selector or readiness |
| Intermittent large-payload failures | MTU, retransmissions | PMTU/encapsulation | Test MTU safely and review CNI config |
| NetworkPolicy ignored | Policy API accepted, traffic still works | Unsupported/disabled enforcement | Confirm CNI capability |
| EKS Pod allocation fails | VPC CNI logs, ENI/IP metrics | Subnet/ENI/IP exhaustion | Review cloud IP capacity |
| AKS cross-node failures | CNI logs, VNet/NSG routes | Azure network mode/underlay | Review mode-specific network paths |

## 21. SRE/DBRE networking incident runbook

### Phase A — Scope and impact

1. Confirm context, namespace, affected applications and time window.
2. Classify source/destination: same Pod, same node, cross-node, Service, external.
3. Check whether failure is intermittent, size-dependent or isolated to a node/zone.
4. Capture application error rates, latency and dependency impact.

### Phase B — Read-only evidence

```powershell
kubectl --context kind-k8s-admin-ch026 get nodes -o wide
kubectl --context kind-k8s-admin-ch026 -n ch026 get pods -o wide
kubectl --context kind-k8s-admin-ch026 -n ch026 get services
kubectl --context kind-k8s-admin-ch026 -n ch026 get endpointslices
kubectl --context kind-k8s-admin-ch026 -n ch026 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch026 -n kube-system get pods -o wide
kubectl --context kind-k8s-admin-ch026 -n ch026 get networkpolicies
```

For production, prefer explicit context and namespace and use your approved access workflow. Avoid dumping Secrets or unrelated workloads.

### Phase C — Fault isolation

1. Test destination Pod IP directly, then Service IP and DNS.
2. Compare same-node and cross-node paths.
3. Inspect EndpointSlice readiness and target ports.
4. Identify CNI, Service datapath and policy engine.
5. Check routes, tunnel health, cloud firewalls, IPAM pool and node conditions.
6. Check MTU and conntrack only when evidence points there.

### Phase D — Recovery and prevention

1. Fix the smallest verified issue first (e.g., wrong Service selector).
2. If CNI agents or node routes are implicated, follow platform-specific change controls.
3. Validate Pod-to-Pod, Service, DNS and application-level transactions.
4. Check all affected nodes/zones and monitor error rate, latency and packet drops.
5. Record rollback, root cause, contributing factors and preventive alerts.

## 22. Evidence collection and acceptance

```powershell
New-Item -ItemType Directory -Force .\evidence | Out-Null
(Get-Date).ToUniversalTime().ToString("o") | Set-Content .\evidence\capture-time-utc.txt
kubectl --context kind-k8s-admin-ch026 get nodes -o wide > .\evidence\nodes.txt
kubectl --context kind-k8s-admin-ch026 -n ch026 get pods -o wide > .\evidence\pods.txt
kubectl --context kind-k8s-admin-ch026 -n ch026 get services,endpointslices > .\evidence\services-endpoints.txt
kubectl --context kind-k8s-admin-ch026 -n ch026 get events --sort-by=.lastTimestamp > .\evidence\events.txt
kubectl --context kind-k8s-admin-ch026 -n ch026 get networkpolicies > .\evidence\networkpolicies.txt
```

Review files for sensitive addresses and metadata before sharing. Do not export Secrets.

### Acceptance checklist

- [ ] A01 — Correct disposable context and three Ready nodes.
- [ ] A02 — CNI, node IPs and Pod CIDR behavior inspected.
- [ ] A03 — Shared-Pod localhost communication confirmed.
- [ ] A04 — Same-node Pod IP HTTP confirmed.
- [ ] A05 — Cross-node Pod IP HTTP confirmed.
- [ ] A06 — Service ClusterIP/DNS and EndpointSlices confirmed.
- [ ] A07 — Wrong Service selector failure reproduced and recovered.
- [ ] A08 — CoreDNS resolution and resolv.conf inspected.
- [ ] A09 — CNI configuration and node routes inspected read-only.
- [ ] A10 — NetworkPolicy enforcement capability observed and documented.
- [ ] A11 — Application connectivity restored and verified.
- [ ] A12 — Evidence sanitized and disposable resources cleaned up.

**Full lab validation** requires observed results for A01–A09, A11–A12. A10 is a capability assessment; do not claim NetworkPolicy enforcement if the CNI lacks it.

### Acceptance report template

```markdown
# Chapter 026 Networking Acceptance Report
Operator:
Reviewer:
Date:
Cluster context:
Kubernetes version:
CNI plugin/version:
Service datapath:
NetworkPolicy enforcement confirmed? Yes / No / Unknown

| Check | Pass / Fail / Blocked / Not Run | Evidence |
|---|---|---|
| A01 | | |
| A02 | | |
| A03 | | |
| A04 | | |
| A05 | | |
| A06 | | |
| A07 | | |
| A08 | | |
| A09 | | |
| A10 | | |
| A11 | | |
| A12 | | |

Incident timeline:
Root cause:
Recovery validation:
Rollback:
Observability gaps:
Cleanup confirmation:
Reviewer decision:
```

## 23. Cleanup

**Destructive operations apply only to the disposable kind cluster.**

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch026 get nodes
kubectl --context kind-k8s-admin-ch026 -n ch026 delete networkpolicy web-deny-ingress --ignore-not-found
kubectl --context kind-k8s-admin-ch026 delete namespace ch026 --ignore-not-found
kind delete cluster --name k8s-admin-ch026
kind get clusters
Remove-Item .\kind-config.yaml, .\shared-network.yaml, .\web-pods.yaml, .\net-client.yaml, .\web-service.yaml, .\web-deny.yaml -ErrorAction SilentlyContinue
```

Retain the sanitized evidence and acceptance report. Never delete production CNI DaemonSets, modify node routes, or disable NetworkPolicy enforcement to complete a lab.

## 24. Knowledge check

1. Which components own Pod IP allocation, DNS, and Service forwarding?
2. Why can same-node traffic work while cross-node traffic fails?
3. What is the purpose of a veth pair and a Pod network namespace?
4. How does an overlay CNI differ from a routed CNI?
5. Why is `spec.podCIDR` not always authoritative for IPAM?
6. How can a Service have a ClusterIP but no usable backends?
7. What evidence distinguishes DNS failure from Service datapath failure?
8. Why does an accepted NetworkPolicy not prove traffic enforcement?
9. How can MTU mismatch produce intermittent application errors?
10. Which CNI-specific constraints matter in EKS, AKS and GKE?

## 25. Status and next chapter

**Draft published.** The labs and expected outputs are instructional; no cluster execution or technical review has been performed. Keep the chapter at Draft until evidence-based validation is complete.

**Next:** Chapter 027 — Services and Load Balancing.
