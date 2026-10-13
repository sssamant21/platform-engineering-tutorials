# Chapter 002 — Containers, Images and Container Runtimes

**Track:** Kubernetes Administration · **Part:** 01 — Kubernetes Fundamentals · **Level:** Beginner–Intermediate · **Status:** Draft (hands-on validation pending)

## 1. Objectives and outcomes

After this chapter, you should be able to:
1. Explain the relationship between an application process, container, image, registry, container runtime, and Kubernetes Pod.
2. Understand OCI image layers, tags, digests, namespaces, cgroups, and the container lifecycle.
3. Distinguish Docker Engine, containerd, CRI-O, OCI runtimes (such as runc), and the Kubernetes Container Runtime Interface (CRI).
4. Build and inspect a small container image and run it locally.
5. Load an image into a disposable kind cluster, deploy it using Kubernetes, and investigate runtime/image errors.
6. Apply safe image-pinning, supply-chain, resource, and cleanup practices.

## 2. Mental model: from source code to running workload

```text
Source + Dockerfile
       |
       v
Image build (layers, metadata, config)
       |
       v
OCI-compatible image (tag and/or immutable digest)
       |
       v
Registry (optional; stores manifests and layers)
       |
       v
Kubernetes Pod specification (image reference)
       |
       v
kubelet -> CRI -> containerd/CRI-O -> OCI runtime -> process
       |
       v
Linux kernel: namespaces, cgroups, filesystems, networking
```

An **image** is a packaged, immutable-by-digest set of filesystem layers and metadata. A **container** is an isolated execution instance created from an image. A **Pod** is Kubernetes' smallest schedulable unit: one or more tightly coupled containers sharing a network namespace and selected storage resources.

**Important:** A container is not a virtual machine. Containers typically share the host kernel, while VMs have guest operating systems and a hypervisor boundary. Containers offer process isolation, not a universal security boundary.

## 3. Image internals

### 3.1 Image layers and copy-on-write

Image builds generally produce reusable read-only layers. A running container adds a writable layer for ephemeral changes. Recreating a container does not preserve that writable layer; persist required data through appropriate volumes or external services.

### 3.2 Image reference anatomy

```text
registry.example.com/team/web:1.2.3
registry.example.com/team/web@sha256:<digest>
```

- **Registry** hosts images and manifests.
- **Repository** identifies the image.
- **Tag** is a mutable name; a registry operator may move it.
- **Digest** is a content-addressed reference to an image manifest or index; use a verified digest when reproducibility is required.
- **Multi-platform images** may use an image index that selects an architecture-specific manifest. The image index digest and selected platform manifest digest may differ.

Avoid assuming `latest` means newest, secure, or stable. Pin to a tested version or digest, and update intentionally.

### 3.3 OCI standards

The Open Container Initiative specifies formats and interfaces for images, runtimes, and distribution. OCI compliance improves interoperability but does not mean every runtime exposes identical features.

## 4. Runtime architecture: Docker vs containerd vs CRI-O

| Component | Responsibility | Kubernetes relationship |
|---|---|---|
| Docker CLI | Developer-facing commands to build/run/manage containers | Not the Kubernetes node runtime API |
| Docker Engine | Developer/host container management stack, commonly using containerd | Kubernetes no longer directly uses the legacy built-in dockershim |
| containerd | Container lifecycle, image management, snapshots and runtime integration | Common CRI implementation on Kubernetes nodes |
| CRI-O | Kubernetes-focused CRI implementation | Alternative to containerd |
| CRI | gRPC interface between kubelet and a runtime implementation | Enables kubelet/runtime interoperability |
| runc | Low-level OCI runtime that creates container processes | Often used beneath containerd or CRI-O |
| kubelet | Node agent that manages Pod lifecycle | Calls CRI to realize Pod containers |

**Version note:** Kubernetes removed the in-tree dockershim in v1.24. Docker Engine can still be used for local image builds and kind's node containers; that does **not** imply kubelet is speaking directly to Docker Engine. Special CRI adapters exist, but they are outside this introductory lab.

### 4.1 Node-level troubleshooting tools

- `kubectl`: API-level Pod status, events and logs.
- `crictl`: CRI-level images, containers, pods and logs; must be configured for the intended runtime endpoint.
- `ctr`: containerd debugging utility; low-level namespaces differ from Kubernetes concepts.
- `nerdctl`: Docker-like CLI for containerd.

Do **not** assume `docker ps` on a Kubernetes node lists all Kubernetes-managed containers. In kind, Docker shows the kind **node container**, while containerd runs the Pod containers *inside* that node.

## 5. Prerequisites and guardrails

This lab targets **Windows PowerShell** with Docker Desktop, `kind`, and `kubectl`. Use an isolated local machine with available CPU, memory, and disk. Internet access is required for the base image unless it is cached. Commands are not intended for production clusters.

Check tools:

```powershell
docker version
docker info --format '{{.ServerVersion}}'
kind version
kubectl version --client
```

**Expected:** Versions display without daemon or authentication errors. If Docker is unavailable, start Docker Desktop. If a registry is blocked, follow your organization's approved mirror policy rather than bypassing it.

Create a working directory:

```powershell
New-Item -ItemType Directory -Force .\k8s-ch002 | Out-Null
Set-Location .\k8s-ch002
```

## 6. Hands-on Lab A — Build and inspect an image

### Step A1 — Write a tiny HTTP application

Create `index.html`:

```powershell
@'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Kubernetes Chapter 002</title></head>
<body><h1>Chapter 002: Containers and Images</h1></body>
</html>
'@ | Set-Content -Encoding utf8 .\index.html
```

Create a `Dockerfile`:

```powershell
@'
FROM nginx:stable-alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
'@ | Set-Content -Encoding ascii .\Dockerfile
```

This lab uses a floating base-image tag for accessibility. In production, use an approved, scanned, digest-pinned base image and a documented update process.

### Step A2 — Build and inspect

```powershell
docker build --tag k8s-ch002-web:v1 .
docker image inspect k8s-ch002-web:v1 --format '{{.Id}}'
docker image history k8s-ch002-web:v1
docker image ls k8s-ch002-web
```

**Expected:** A successful build, a `sha256:` image ID, image-history entries, and a local image listing. The image ID is not necessarily the same digest used to identify a pushed registry manifest.

### Step A3 — Run locally

```powershell
docker run --detach --name k8s-ch002-local --publish 18080:80 k8s-ch002-web:v1
(Invoke-WebRequest http://localhost:18080 -UseBasicParsing).StatusCode
docker logs k8s-ch002-local --tail 20
docker inspect k8s-ch002-local --format '{{.State.Status}}'
```

**Expected:** HTTP `200` and status `running`. Open `http://localhost:18080` to view the page.

### Step A4 — Demonstrate container ephemerality

```powershell
docker exec k8s-ch002-local sh -c 'echo temporary > /tmp/lab-note'
docker exec k8s-ch002-local cat /tmp/lab-note
docker rm --force k8s-ch002-local
docker run --detach --name k8s-ch002-local --publish 18080:80 k8s-ch002-web:v1
docker exec k8s-ch002-local sh -c 'test ! -e /tmp/lab-note && echo ephemeral-file-absent'
```

**Expected:** `ephemeral-file-absent`. The newly created container has a new writable layer; data not persisted externally is gone. This example is deliberately about container-local data, not Kubernetes persistent volumes.

## 7. Hands-on Lab B — Use the image in Kubernetes

### Step B1 — Create and verify a disposable cluster

```powershell
kind create cluster --name k8s-admin-ch002 --wait 120s
kubectl config current-context
kubectl get nodes
```

**Stop if the context is not `kind-k8s-admin-ch002`.** Do not continue on a production or unrelated cluster.

### Step B2 — Load the locally built image

```powershell
kind load docker-image k8s-ch002-web:v1 --name k8s-admin-ch002
kubectl create namespace ch002
```

kind imports the local image into the node runtime, so no registry push is required. In a multi-node cluster, kind normally loads to the cluster's nodes. This local-only technique is not a production image-distribution strategy.

### Step B3 — Create declarative Deployment and Service manifests

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ch002-web
  namespace: ch002
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ch002-web
  template:
    metadata:
      labels:
        app: ch002-web
    spec:
      containers:
        - name: web
          image: k8s-ch002-web:v1
          imagePullPolicy: Never
          ports:
            - name: http
              containerPort: 80
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
            limits:
              cpu: 250m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: ch002-web
  namespace: ch002
spec:
  selector:
    app: ch002-web
  ports:
    - name: http
      port: 80
      targetPort: http
  type: ClusterIP
'@ | Set-Content -Encoding ascii .\ch002-web.yaml

kubectl apply -f .\ch002-web.yaml
kubectl -n ch002 rollout status deployment/ch002-web --timeout=180s
kubectl -n ch002 get pods -o wide
kubectl -n ch002 get deployment,service
```

**Expected:** Deployment reports **2/2** ready replicas and the Service exists. `imagePullPolicy: Never` is intentional for a preloaded, locally built image. **Do not copy that setting into a normal production Deployment** unless you explicitly manage node-local images.

### Step B4 — Verify traffic and image identity

Run port-forward in terminal 1:

```powershell
kubectl -n ch002 port-forward service/ch002-web 18081:80
```

In terminal 2:

```powershell
(Invoke-WebRequest http://localhost:18081 -UseBasicParsing).StatusCode
kubectl -n ch002 get pods -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.status.containerStatuses[0].imageID}{"\n"}{end}'
kubectl -n ch002 describe deployment ch002-web
```

**Expected:** HTTP `200` and each Pod has an `imageID` identifying the resolved image. Press Ctrl+C in terminal 1 when done.

### Step B5 — Inspect containerd inside the kind node

```powershell
docker exec k8s-admin-ch002-control-plane crictl images
docker exec k8s-admin-ch002-control-plane crictl ps
docker exec k8s-admin-ch002-control-plane ctr -n k8s.io images ls
```

**Expected:** Runtime-level image and container listings. Some kind node images may require an explicit `crictl --runtime-endpoint` or `--image-endpoint`; if so, inspect the node's runtime configuration before retrying. The `k8s.io` containerd namespace is a containerd concept, not a Kubernetes namespace.

Compare with:

```powershell
docker ps --filter name=k8s-admin-ch002
kubectl -n ch002 get pods
```

**Interpretation:** Docker lists the kind node container; Kubernetes lists Pods scheduled *within* that node.

## 8. Failure injection — ImageNeverPull and recovery

Use a **separate** failing Pod so the working Deployment stays healthy.

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: missing-image
  namespace: ch002
spec:
  containers:
    - name: web
      image: example.invalid/does-not-exist:ch002
      imagePullPolicy: Never
'@ | Set-Content -Encoding ascii .\missing-image.yaml

kubectl apply -f .\missing-image.yaml
kubectl -n ch002 get pod missing-image
kubectl -n ch002 describe pod missing-image
kubectl -n ch002 get events --sort-by=.lastTimestamp
```

**Expected:** The Pod cannot start because the specified image is absent from the node; a status such as `ErrImageNeverPull` or `ImagePullBackOff` may appear depending on runtime and Kubernetes behavior. The decisive evidence is the Pod event indicating the image is not present and pull policy prevents fetching it.

**Recover:** Remove the intentionally failing Pod; verify the original Deployment remains healthy.

```powershell
kubectl -n ch002 delete pod missing-image
kubectl -n ch002 rollout status deployment/ch002-web --timeout=180s
```

## 9. Troubleshooting decision table

| Symptom | First evidence | Next action |
|---|---|---|
| `ImagePullBackOff` | `kubectl describe pod` events | Verify registry DNS, network, image reference, credentials and rate limits |
| `ErrImageNeverPull` | Pull policy + node-local image inventory | Load image to node or use a reachable registry and appropriate policy |
| `CrashLoopBackOff` | `kubectl logs --previous` and events | Check application exit, config, permissions and probes |
| `OOMKilled` | Container `lastState`, memory limits | Investigate usage, limits and application memory behavior |
| Architecture mismatch | Runtime errors, image platform metadata | Build/pull image for the node architecture |
| `kubectl` healthy, node containers fail | Node conditions, kubelet logs, CRI endpoint | Investigate containerd/CRI-O, filesystem and resource pressure |
| Image build fails | Dockerfile/build output | Validate base image, syntax, registry access and disk capacity |

Commands:

```powershell
kubectl -n ch002 describe pod <pod-name>
kubectl -n ch002 logs <pod-name> -c web --previous
kubectl -n ch002 get events --sort-by=.lastTimestamp
kubectl describe node k8s-admin-ch002-control-plane
```

Replace `<pod-name>` with a real name before execution.

## 10. Production practices and SRE runbook

### Image provenance and security

1. Build images in CI from reviewed Dockerfiles and controlled dependencies.
2. Use minimal, maintained base images and scan for known vulnerabilities.
3. Record provenance/SBOM where supported; sign and verify artifacts through your organization's policy.
4. Pin approved production images by digest when reproducibility is critical.
5. Run workloads as non-root where feasible; avoid privileged containers and unnecessary capabilities.
6. Keep secrets out of image layers, build arguments, logs and committed Dockerfiles.
7. Separate build permissions, registry-push permissions and runtime image-pull permissions.

### Runtime operational checks

On an incident, capture the exact cluster, namespace, Pod UID, node, image reference, image ID, timestamps and recent events. Determine whether the problem is image distribution, runtime creation, application startup or health checking **before** restarting components. Restarting containerd or kubelet on a production node may disrupt workloads and requires approved operational procedure.

### Resource and capacity considerations

Image pulls consume network bandwidth, disk and I/O; large images slow cold starts and autoscaling. Configure node image garbage collection, ephemeral storage alerts, registry availability monitoring and reasonable rollout surge parameters. Requests/limits must reflect measured workload behavior rather than arbitrary defaults.

## 11. Cleanup and rollback

Stop any port-forward processes. Verify the intended context:

```powershell
kubectl config current-context
```

Only if it shows `kind-k8s-admin-ch002`:

```powershell
kubectl delete namespace ch002
kind delete cluster --name k8s-admin-ch002
```

Clean up the local container and image:

```powershell
docker rm --force k8s-ch002-local
docker image rm k8s-ch002-web:v1
```

**Caution:** Deleting the kind cluster permanently removes its local workloads and data. The local image removal may fail if another container still references the image; inspect dependencies rather than using broad prune commands.

## 12. Acceptance checklist

- [ ] Docker, kind and kubectl versions checked.
- [ ] Local image built and inspected.
- [ ] Local container served HTTP 200.
- [ ] Container writable-layer ephemerality observed.
- [ ] Disposable kind cluster created and context verified.
- [ ] Image loaded into the node runtime.
- [ ] Two-replica Deployment reached 2/2 ready.
- [ ] Kubernetes Service returned HTTP 200 through port-forward.
- [ ] CRI/containerd inspection performed.
- [ ] Missing-image failure diagnosed from events.
- [ ] Local cluster and containers cleaned up.

## 13. Knowledge check

1. Why is an image not the same thing as a running container?
2. What is the difference between an image tag, image ID and registry digest?
3. How does kubelet communicate with a runtime on a Kubernetes node?
4. Why does `docker ps` on the host show a kind node rather than all Pods?
5. Why is `imagePullPolicy: Never` useful here but risky for general deployments?
6. How would you distinguish an image-pull problem from an application crash?

## 14. Chapter status and next step

**Draft written; lab execution and acceptance are not independently verified.** Update tracker to **Lab Validated** only after running the lab, and **Complete** after content review.

**Next:** Chapter 003 — Kubernetes Architecture and Components.
