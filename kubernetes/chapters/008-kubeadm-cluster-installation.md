# Chapter 008 — kubeadm Cluster Installation

**Track:** Kubernetes Administration · **Part:** 02 — Cluster Installation and Setup · **Level:** Intermediate–Advanced · **Status:** Draft — lab execution pending

## 1. Learning objectives

By the end of this chapter, you should be able to:

1. Describe what `kubeadm` installs and what it deliberately does not manage.
2. Plan a Linux-based control-plane and worker-node installation, including version, networking, security, and host prerequisites.
3. Configure containerd, the kubelet, and Linux kernel networking requirements.
4. Bootstrap a single-control-plane cluster with `kubeadm init` and join a worker with `kubeadm join`.
5. Install and verify a compatible CNI plugin.
6. Diagnose common installation failures using `kubeadm`, `kubectl`, `journalctl`, and CRI tools.
7. Understand the limitations of a single-control-plane lab and the additional requirements for HA production design.

## 2. Architecture and installation flow

```text
             Linux control-plane VM
     +-----------------------------------+
     | kubeadm init                      |
     |   -> PKI + kubeconfig             |
     |   -> static Pod manifests         |
     |   -> kube-apiserver               |
     |   -> kube-controller-manager      |
     |   -> kube-scheduler               |
     |   -> etcd                         |
     | kubelet -> containerd             |
     +------------------+----------------+
                        |
               API server :6443
                        |
             Linux worker VM
     +-----------------------------------+
     | kubeadm join                      |
     | kubelet -> containerd             |
     | CNI agent / Pod networking        |
     | application Pods                  |
     +-----------------------------------+
```

`kubeadm` bootstraps a Kubernetes cluster using upstream conventions. It does **not** provision virtual machines, operating systems, a production load balancer, storage classes, a CNI implementation, application ingress, or an observability stack.

A typical kubeadm control plane uses static Pods under `/etc/kubernetes/manifests`, with kubelet supervising them. The local etcd data directory is commonly `/var/lib/etcd`.

## 3. Lab design and prerequisites

### 3.1 Lab topology

This is a **disposable two-VM Linux lab**, not a kind cluster. Windows PowerShell can be your operator terminal, but the installation commands below run **inside Ubuntu Linux VMs** using Bash.

| Host | Role | Example IP | Minimum suggested lab resources |
|---|---|---|---|
| `k8s-cp01` | Control plane | `192.168.56.10` | 2 vCPU, 4 GiB RAM |
| `k8s-worker01` | Worker | `192.168.56.11` | 2 vCPU, 4 GiB RAM |

**Addresses are illustrative.** Replace them with reachable addresses on your actual isolated VM network. Allow additional resources for workloads and image pulls. Both nodes need stable IP connectivity and correct DNS/time configuration.

### 3.2 Supported environment

Use an Ubuntu LTS release supported by the selected Kubernetes packages, a compatible Linux kernel, and a supported containerd release. Package and CNI compatibility must be checked against the **specific Kubernetes minor version you select**. This tutorial uses the placeholder `v1.34` as an **example**, not a claim that it is the newest or the only supported version.

Set your chosen minor version on **each VM**:

```bash
K8S_MINOR="v1.34"   # Replace with your approved supported Kubernetes minor
```

Choose a version for which the Kubernetes package repository, kubeadm, kubelet, kubectl, runtime, and CNI are compatible. For production, follow the official release and version-skew policy.

### 3.3 Required network connectivity

At minimum, confirm the required control-plane and node traffic for your deployment, including API server TCP 6443, kubelet TCP 10250, and CNI-specific inter-node traffic. etcd ports 2379–2380 are relevant for control-plane members but should **not** be exposed publicly. Other ports depend on NodePort, control-plane architecture, and your CNI.

See the official port reference: https://kubernetes.io/docs/reference/networking/ports-and-protocols/

**Security:** Restrict management and control-plane access to trusted networks. Do not disable firewalls globally as a troubleshooting shortcut.

## 4. Preflight checks on both Linux VMs

Run the following on **each VM**:

```bash
hostnamectl
ip -brief address
ip route
free -h
df -h /
uname -r
timedatectl status
getent hosts k8s-cp01
getent hosts k8s-worker01
```

**Expected:** distinct hostnames, correct IP routing, sufficient CPU/RAM/disk, synchronized clocks, and resolvable peer hostnames. If internal DNS is unavailable, use approved host records on both VMs.

Check connectivity:

```bash
ping -c 2 192.168.56.10
ping -c 2 192.168.56.11
```

ICMP may be blocked; use approved TCP checks if needed. Ensure each VM can access approved package repositories and image registries, or use an approved offline mirror.

## 5. Lab A — Configure Linux networking and containerd

### Step A1 — Disable swap for this lab

Kubelet's swap behavior depends on configuration and version. This lab uses the simpler, broadly compatible no-swap setup.

```bash
sudo swapoff -a
swapon --show
```

**Expected:** no active swap. For persistence across reboot, review `/etc/fstab` and disable only the VM's swap entry using your image-management process. Do **not** blindly edit or delete unrelated fstab entries.

### Step A2 — Enable kernel modules and sysctl settings

```bash
cat <<'EOF' | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

cat <<'EOF' | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system
lsmod | grep -E 'overlay|br_netfilter'
sysctl net.ipv4.ip_forward
```

**Expected:** required modules loaded and IPv4 forwarding enabled. CNI implementations may have additional requirements; do not assume these settings are sufficient for every dataplane.

### Step A3 — Install containerd

On Ubuntu, install containerd from an approved compatible package source:

```bash
sudo apt-get update
sudo apt-get install -y containerd
containerd --version
```

If your distribution's `containerd` package is incompatible with the selected Kubernetes release, stop and use the vendor-approved repository/package rather than mixing arbitrary packages.

Create a baseline config:

```bash
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
```

Set `SystemdCgroup = true` in the **runc runtime configuration section** of `/etc/containerd/config.toml`. The section path differs between containerd 1.x and 2.x; inspect the generated config and use the documentation for your installed version rather than blindly replacing strings.

```bash
sudo grep -n 'SystemdCgroup\|disabled_plugins' /etc/containerd/config.toml
sudo systemctl enable --now containerd
sudo systemctl restart containerd
sudo systemctl status containerd --no-pager
```

**Expected:** containerd is active. Ensure the CRI plugin is enabled and the kubelet/containerd cgroup drivers agree. On systemd-based Ubuntu, `systemd` cgroups are the recommended choice.

### Step A4 — Validate CRI availability

Install a compatible `crictl` if your image does not include it, using the official cri-tools release or an approved package source. Configure it for the containerd socket:

```bash
sudo crictl --runtime-endpoint unix:///run/containerd/containerd.sock info
```

**Expected:** runtime information. If `crictl` is not installed, record this as a prerequisite gap rather than attempting to diagnose CRI using Docker commands.

## 6. Lab B — Install kubeadm, kubelet, and kubectl

The upstream Debian/Ubuntu package repositories are scoped by Kubernetes minor version. On **both nodes**, replace `v1.34` with the approved minor you selected.

```bash
K8S_MINOR="v1.34"
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/$K8S_MINOR/deb/Release.key" \
  | gpg --dearmor \
  | sudo tee /etc/apt/keyrings/kubernetes-apt-keyring.gpg >/dev/null

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_MINOR/deb/ /" \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
sudo systemctl enable --now kubelet
kubeadm version
kubelet --version
kubectl version --client
```

**Expected:** tools install from the selected minor repository. The kubelet may restart repeatedly **before** cluster initialization; that is expected because it does not yet have its full cluster configuration.

**Security note:** Use a trusted package repository and validate the repository signing key through an approved supply-chain process. A network fetch piped to `gpg` is not a substitute for out-of-band key verification in regulated environments.

## 7. Lab C — Initialize the control plane

**Run only on `k8s-cp01`.**

### Step C1 — Choose Pod CIDR and advertise address

Use a Pod network CIDR that does not overlap with host, VPN, VPC, or Service CIDRs. This lab uses `10.244.0.0/16` as an example. The CNI you install **must** support the selected CIDR and configuration.

```bash
sudo kubeadm init \
  --apiserver-advertise-address=192.168.56.10 \
  --pod-network-cidr=10.244.0.0/16 \
  --cri-socket=unix:///run/containerd/containerd.sock
```

**Expected:** successful control-plane initialization and a generated `kubeadm join` command. **Treat the join token as sensitive and time-limited.** Do not paste it into public tickets or Git.

### Step C2 — Configure kubectl for the Linux admin account

```bash
mkdir -p "$HOME/.kube"
sudo cp -i /etc/kubernetes/admin.conf "$HOME/.kube/config"
sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
chmod 600 "$HOME/.kube/config"

kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
```

**Expected:** the control-plane node appears, potentially `NotReady` until a CNI is installed. The `admin.conf` file is highly privileged and must not be shared or committed.

### Step C3 — Inspect static Pod manifests

```bash
sudo ls -l /etc/kubernetes/manifests/
kubectl -n kube-system get pods -o wide
sudo journalctl -u kubelet -n 60 --no-pager
```

**Expected:** manifests for kube-apiserver, kube-controller-manager, kube-scheduler, and etcd in a typical single-control-plane kubeadm setup.

## 8. Lab D — Install a compatible CNI

**Do not install an arbitrary “latest” CNI manifest.** Choose a version explicitly compatible with your Kubernetes release, kernel, containerd, and selected Pod CIDR.

For this lab, use a **reviewed, version-pinned Flannel manifest** from the official project release, after confirming its expected Pod CIDR is `10.244.0.0/16` and required inter-node UDP/VXLAN traffic is allowed.

Official project: https://github.com/flannel-io/flannel

Example workflow (replace the placeholder with an approved exact release asset URL):

```bash
# Download and review the exact pinned manifest through your approved process.
# Save it locally as flannel-reviewed.yaml.
grep -n 'Network\|10.244.0.0/16\|image:' flannel-reviewed.yaml
kubectl apply -f flannel-reviewed.yaml
kubectl -n kube-flannel get pods -o wide
kubectl get nodes -o wide
```

**Expected:** Flannel components become healthy and the control-plane node transitions to `Ready`. The CNI's namespace and workload names can differ by release; inspect the manifest and cluster instead of assuming names.

**Why no unpinned download command?** A CNI manifest is a privileged cluster-wide component. Pinning and reviewing it is an essential operational practice, especially when teaching production administration.

## 9. Lab E — Join the worker

**Run on `k8s-worker01` only after the control plane and CNI are healthy.**

On the control-plane VM, create a fresh join command:

```bash
sudo kubeadm token create --print-join-command
```

Copy the generated command to the worker through an approved secure channel. It will resemble:

```bash
sudo kubeadm join 192.168.56.10:6443 \
  --token <generated-token> \
  --discovery-token-ca-cert-hash sha256:<actual-hash> \
  --cri-socket=unix:///run/containerd/containerd.sock
```

**Do not run the placeholder values literally.** Verify the API endpoint and CA hash against your intended cluster. Join tokens grant cluster bootstrap access; keep them confidential and allow them to expire or revoke them when no longer needed.

On the control plane:

```bash
kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
kubectl describe node k8s-worker01
```

**Expected:** both nodes eventually `Ready`. If the worker is `NotReady`, inspect CNI Pods, kubelet logs, and runtime status on that node.

## 10. Lab F — Validate application scheduling and networking

On the control-plane VM:

```bash
kubectl create namespace ch008
kubectl -n ch008 create deployment web --image=nginx:stable --replicas=2
kubectl -n ch008 rollout status deployment/web --timeout=180s
kubectl -n ch008 expose deployment web --port=80 --target-port=80 --type=ClusterIP
kubectl -n ch008 get pods -o wide
kubectl -n ch008 get svc,endpointslices
```

**Expected:** two Ready replicas, usually scheduled to the worker because the control-plane node commonly has a NoSchedule taint. A Service and EndpointSlice objects should be present.

### Validate Service access from inside the cluster

```bash
kubectl -n ch008 run client --image=curlimages/curl:8.12.1 --restart=Never --command -- sleep 3600
kubectl -n ch008 wait --for=condition=Ready pod/client --timeout=180s
kubectl -n ch008 exec client -- curl -fsSI http://web.ch008.svc.cluster.local
```

**Expected:** HTTP response headers from NGINX, typically status `200`. If the curl image tag is unavailable in your approved registry, use a reviewed replacement. Check DNS, Pod readiness, Service selector, and CNI connectivity if the request fails.

### Validate DNS

```bash
kubectl -n ch008 exec client -- nslookup web.ch008.svc.cluster.local
```

**Expected:** DNS resolves the Service name. The image must include `nslookup`; if absent, use a separate approved diagnostic image with DNS utilities instead of modifying production Pods.

## 11. Troubleshooting runbook

| Failure | First evidence | Next checks |
|---|---|---|
| `kubeadm init` preflight failure | Exact preflight output | Swap, CPU/memory, port conflicts, kernel modules, CRI |
| CRI endpoint unavailable | `crictl info`, containerd status | Socket path, CRI plugin, cgroup driver |
| Kubelet repeatedly restarts before init | `journalctl -u kubelet` | Expected until kubeadm config exists |
| Control plane never becomes healthy | Static Pod status, kubelet logs | Image pulls, certificates, API advertise address, etcd |
| Node stays NotReady | Node conditions, CNI Pods | CNI installation, Pod CIDR, host networking |
| Worker join fails | `kubeadm join` output | Token expiry, CA hash, API TCP 6443, hostname conflict |
| CoreDNS Pending | Pod events | CNI availability, scheduling and resource constraints |
| Pod image pull fails | Pod events | Registry access, DNS, image reference, credentials |
| Service traffic fails | EndpointSlices, CoreDNS, CNI logs | Pod readiness, selector, network policy, firewall |

### Read-only diagnostic commands

```bash
sudo systemctl status containerd --no-pager
sudo systemctl status kubelet --no-pager
sudo journalctl -u kubelet -n 100 --no-pager
sudo crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps -a
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl -n kube-system get pods
```

On a broken control plane, `kubectl` may be unavailable; rely on host logs, static manifests, and CRI tools. Capture evidence before restarting services.

## 12. Common installation mistakes

- Selecting a Pod CIDR overlapping the VM subnet or VPN.
- Using a CNI version incompatible with the Kubernetes version.
- Forgetting to enable IP forwarding or required kernel modules.
- Running containerd with a cgroup driver inconsistent with kubelet.
- Treating the kubelet's pre-init restart loop as a cluster failure.
- Running `kubeadm init` on both nodes instead of using `kubeadm join` on the worker.
- Copying `admin.conf` broadly rather than using least-privilege user credentials.
- Exposing API server or etcd ports to the public internet.
- Assuming a two-node, single-control-plane lab is production highly available.

## 13. Production design considerations

A production kubeadm design needs substantially more than a successful `kubeadm init`:

1. **HA control plane:** multiple control-plane nodes, a stable API endpoint/load balancer, and a supported etcd topology.
2. **Quorum:** etcd voting-member placement across independent failure domains, with tested backup and restore.
3. **Node lifecycle:** OS patching, Kubernetes upgrades, cordon/drain, certificate rotation, and capacity planning.
4. **Security:** RBAC, least privilege, network policies, image provenance, secrets encryption, and audit logging.
5. **Networking:** supported CNI, DNS, ingress/load balancing, egress controls, and validated firewall rules.
6. **Storage:** CSI driver, storage classes, snapshot and backup policy, and recovery testing.
7. **Observability:** API server and etcd metrics, kubelet/runtime health, events, alerts, and application SLIs.
8. **Disaster recovery:** documented RPO/RTO and rehearsed cluster/API-state plus application-data recovery.

Do not convert this single-control-plane exercise into production simply by adding workers. Chapter 051 and Chapter 052 cover HA and etcd recovery in detail.

## 14. Rollback and cleanup — disposable VMs only

**Warning:** `kubeadm reset` removes Kubernetes configuration from a node but does not fully clean CNI configuration, firewall rules, network interfaces, user kubeconfig, or all runtime state. It does not erase all application data and is **not** a reliable full-cluster rollback strategy.

For this lab, the **preferred cleanup is deleting/reverting the two disposable VMs using your hypervisor snapshots or VM management tooling** after recording acceptance evidence. This returns the entire machine state, including CNI and runtime changes.

If you need to reset a disposable node for troubleshooting:

```bash
sudo kubeadm reset --force
```

Run only on VMs explicitly dedicated to this exercise, and consult the official reset documentation for any additional cleanup required by your selected CNI. Do not remove CNI directories or iptables rules on a shared host.

Remove temporary training resources while the cluster is still healthy:

```bash
kubectl delete namespace ch008
```

Do not run `kubeadm reset` on production nodes as a casual troubleshooting step.

## 15. Acceptance checklist

- [ ] Verified VM OS, hostnames, IPs, clocks, and required network ports.
- [ ] Selected compatible Kubernetes, containerd, and CNI versions.
- [ ] Configured swap, kernel modules, IP forwarding, and containerd.
- [ ] Installed kubeadm, kubelet, and kubectl on both nodes.
- [ ] Initialized control plane on `k8s-cp01`.
- [ ] Inspected API server, scheduler, controller manager, and etcd static Pods.
- [ ] Installed reviewed version-pinned CNI and verified readiness.
- [ ] Joined worker using a valid token and CA hash.
- [ ] Verified both nodes `Ready`.
- [ ] Deployed application with two Ready replicas.
- [ ] Validated Service access and DNS inside the cluster.
- [ ] Captured logs/evidence and reverted disposable VM state.

## 16. Knowledge check

1. What does kubeadm configure, and what must an operator provide separately?
2. Why is containerd cgroup-driver alignment important?
3. Why can a kubeadm control-plane node remain NotReady before CNI installation?
4. Why is a `kubeadm join` token security-sensitive?
5. What does the CA discovery hash protect during worker bootstrap?
6. Why should Pod CIDRs not overlap existing host or VPN networks?
7. Why is a single-control-plane cluster unsuitable for critical production availability?
8. Why is `kubeadm reset` not equivalent to restoring a clean VM snapshot?
9. How would you distinguish CNI failure from container-runtime failure?
10. Which additional components are needed for a production-ready cluster?

## 17. Chapter status and next chapter

**Draft written; lab execution has not been independently verified.** Promote to **Lab Validated** after running the acceptance checklist and to **Complete** after technical review.

**Next:** Chapter 009 — Containerd, CNI and CoreDNS Configuration.
