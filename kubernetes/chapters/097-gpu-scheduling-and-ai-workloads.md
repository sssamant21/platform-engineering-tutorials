# Chapter 097 — GPU Scheduling and AI Workloads

**Track:** Kubernetes Administration · **Part 20 — Advanced Platform Engineering and Production Operations**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, AI platform engineers, ML engineers  
**Prerequisites:** Chapters 021–025, 046–050, 076–090, 096; kubectl, Helm, PowerShell, approved NVIDIA-compatible GPU nodes, provider GPU quota, and access to a disposable staging cluster.

## Learning outcomes

Explain GPU device discovery and scheduling; distinguish NVIDIA drivers, runtime and device plugins; configure GPU pools and placement; validate CUDA access; deploy and observe inference workloads; troubleshoot GPU failures; understand MIG/time-slicing tradeoffs; control accelerator spend; and build a safe operational runbook.

## 1. GPU workload architecture

```text
AI request → Ingress/Gateway → model-serving Pod (vLLM/Triton/etc.)
                                        |
                                  Kubernetes scheduler
                                        |
                              GPU allocatable resource
                                        |
                         NVIDIA device plugin / DRA driver
                                        |
                            Container runtime integration
                                        |
                           Host GPU driver + GPU hardware
                                        |
                              CUDA userspace in image
```

A GPU-capable node must have compatible hardware, kernel driver, container-runtime integration and a resource discovery mechanism. The NVIDIA device plugin traditionally advertises `nvidia.com/gpu` as an extended resource. Newer Kubernetes Dynamic Resource Allocation (DRA) mechanisms may be available, but support depends on cluster version, driver and vendor implementation; validate before adoption.

**Critical:** Kubernetes `Ready` describes node health, not end-to-end GPU readiness.

## 2. Lab 01 — Preflight inventory and safety

Use a disposable or explicitly approved GPU staging node pool. GPU instances can be expensive and may require cloud quotas and image pull access.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl get nodes -L node-pool,gpu,gpu_type
kubectl describe nodes
kubectl get pods -A -o wide
```

Record Kubernetes version, OS/architecture, GPU model, driver version, runtime, device-plugin/operator version, node image, kernel and cloud provider. Do not assume labels such as `node-pool=gpu-reserved` or `gpu_type=A10G` exist until verified.

## 3. Lab 02 — GPU node hardware and drivers

On an authorized GPU node, check the host NVIDIA driver:

```bash
nvidia-smi
nvidia-smi -L
cat /proc/driver/nvidia/version
```

Run these via approved node access/diagnostic tooling; they are **host shell commands**, not PowerShell commands to run on your Windows workstation. `nvidia-smi` failure suggests missing hardware visibility, driver or kernel module issues. Successful host `nvidia-smi` does not prove container GPU access.

Check OS image, secure boot, kernel-driver compatibility and provider-specific GPU enablement. For managed services, prefer supported GPU node images and driver installation methods.

## 4. Lab 03 — NVIDIA runtime and device plugin

GPU workloads typically require the NVIDIA Container Toolkit/runtime integration and a compatible device plugin or GPU Operator deployment. Installation methods differ by provider and Kubernetes distribution; pin supported versions and follow the vendor/provider support matrix.

```powershell
kubectl get daemonsets -A
kubectl get pods -A | Select-String -Pattern 'nvidia|gpu'
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU_CAPACITY:.status.capacity.nvidia\.com/gpu,GPU_ALLOCATABLE:.status.allocatable.nvidia\.com/gpu
```

If the custom-column escaping is incompatible with your kubectl version, inspect `kubectl get node <name> -o yaml` under `status.capacity` and `status.allocatable`. Confirm plugin Pods run on intended GPU nodes and inspect their logs/events.

**Acceptance:** GPU resources appear in allocatable capacity and the plugin is healthy. Do not install two competing device-plugin stacks on the same nodes.

## 5. Lab 04 — GPU requests, limits and scheduling

For traditional `nvidia.com/gpu` resources, a container commonly declares the GPU in `limits`; Kubernetes uses the same value as its request if only a limit is specified. If both are specified, values must match. GPU resources are typically integer quantities unless vendor-specific partitioning/sharing resources are configured.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-smoke-test
  namespace: default
spec:
  restartPolicy: Never
  nodeSelector:
    node-pool: gpu-reserved
  containers:
  - name: cuda-test
    image: nvidia/cuda:12.4.1-base-ubuntu22.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Important:** this image tag is illustrative and must be checked for availability, provenance and compatibility with the host driver before use. Replace `node-pool: gpu-reserved` with a verified label, or remove the selector in a dedicated disposable cluster. Use approved registry images and digest pinning in production.

```powershell
kubectl apply -f .\gpu-smoke-test.yaml
kubectl get pod gpu-smoke-test -o wide
kubectl describe pod gpu-smoke-test
kubectl logs gpu-smoke-test
```

**Acceptance:** Pod schedules on an intended GPU node, `nvidia-smi` succeeds inside the container and the Pod completes successfully.

## 6. Lab 05 — GPU affinity, taints and tolerations

Dedicate expensive GPU nodes with labels and taints, then require explicit opt-in from workloads:

```powershell
kubectl get nodes --show-labels
kubectl describe node <gpu-node-name>
```

Example placement fragment:

```yaml
nodeSelector:
  node-pool: gpu-reserved
tolerations:
- key: dedicated
  operator: Equal
  value: gpu
  effect: NoSchedule
```

A toleration **allows** scheduling onto a tainted node; it does not force placement there. Pair with affinity or selectors. Apply taints only under an approved change because existing workloads may be affected. Review topology spread, GPU availability zones and failure domains.

## 7. Lab 06 — Diagnose Pending GPU Pods

```powershell
kubectl describe pod gpu-smoke-test
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe nodes
kubectl get pods -A -o wide
```

Common reasons:
- `Insufficient nvidia.com/gpu`: allocatable GPUs exhausted or plugin not reporting.
- Node selector/affinity mismatch: labels differ from Pod requirements.
- Untolerated taint: Pod lacks matching toleration.
- CPU/memory shortage: GPU capacity exists but other requested resources do not fit.
- PVC topology mismatch: storage and GPU placement constraints conflict.
- Autoscaler limits or cloud GPU quota: nodes cannot provision.

Do not solve GPU scheduling failures by adding broad tolerations or removing resource requests without reviewing isolation and capacity.

## 8. Lab 07 — CUDA runtime verification

A successful `nvidia-smi` demonstrates device/driver visibility but not necessarily a working CUDA application. Run a compatible, approved CUDA sample or a framework diagnostic inside a GPU-enabled container.

For a PyTorch image with GPU support installed:

```python
import torch
print("CUDA available:", torch.cuda.is_available())
print("GPU count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

A CPU-only PyTorch build reports CUDA unavailable even when the host GPU is healthy. Match CUDA runtime/framework wheels to the supported driver capability. For `No CUDA runtime is found` or `Failed to infer device type`, check device-plugin allocation, container toolkit, image framework build and scheduling first.

## 9. Lab 08 — GPU isolation and sharing modes

Compare:
- **Exclusive GPU allocation:** simpler isolation and predictable resource accounting.
- **MIG (Multi-Instance GPU):** supported NVIDIA models partition hardware into defined profiles; availability depends on GPU model and configuration.
- **Time-slicing:** multiple workloads share a GPU but generally do not gain strong memory or fault isolation from sharing alone.
- **MPS:** supported CUDA multi-process sharing with distinct operational constraints.
- **DRA:** emerging/available-by-version API-driven device allocation; verify feature maturity and vendor driver support.

Never assume an A10G or other specific model supports MIG. Check vendor documentation and actual hardware capabilities. Define security and noisy-neighbor requirements before enabling sharing.

## 10. Lab 09 — Deploy a model-serving workload

Use a supported vLLM, NVIDIA Triton or another approved inference server image with a compatible model and GPU type. Model weights, tokenizers and images can be large; plan network, storage and startup time.

Representative Deployment fragment (adapt to the selected server and image):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: model-server
  namespace: ai-staging
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: model-server
  template:
    metadata:
      labels:
        app: model-server
    spec:
      nodeSelector:
        node-pool: gpu-reserved
      containers:
      - name: server
        image: YOUR_APPROVED_MODEL_SERVER_IMAGE@sha256:REPLACE_WITH_REAL_DIGEST
        resources:
          requests:
            cpu: "2"
            memory: 8Gi
          limits:
            memory: 16Gi
            nvidia.com/gpu: 1
        ports:
        - containerPort: 8000
```

This is a **template**, not a directly runnable manifest: set a real digest, server command, model reference, readiness/startup probes, secret delivery and namespace first. Large models may need much more CPU, RAM and VRAM. Do not embed model-registry tokens in manifests.

## 11. Lab 10 — Model-serving health and performance

```powershell
kubectl get deployments,pods,svc -n ai-staging -o wide
kubectl describe deployment model-server -n ai-staging
kubectl logs deployment/model-server -n ai-staging --since=20m
kubectl top pods -n ai-staging --containers
```

Track time to first token, output tokens/second, p50/p95 latency, request queue depth, concurrent requests, model load time, GPU memory, GPU utilization, CPU, RAM, errors and OOMs. GPU utilization alone does not capture inference quality or service performance.

Configure startup probes to accommodate model loading and readiness probes to reflect actual serving readiness. Validate the API contract and load-test with representative request sizes.

## 12. Lab 11 — GPU observability

A common NVIDIA telemetry path is DCGM Exporter plus Prometheus/Grafana, deployed using a vendor-supported version. Typical metrics cover GPU utilization, framebuffer memory, temperature, power, ECC errors and device health; metric names vary by exporter release.

```powershell
kubectl get daemonsets -A
kubectl get servicemonitors -A
kubectl get pods -A | Select-String -Pattern 'dcgm|gpu|nvidia'
```

ServiceMonitor is a Prometheus Operator CRD and may be absent. Validate metrics freshness, GPU-to-Pod attribution and dashboard labels. Alert on sustained errors, memory exhaustion and unavailable GPUs; distinguish short bursts from incidents.

## 13. Lab 12 — Scaling and cost controls

GPU nodes often have high hourly cost and slower provisioning. Compare:
- Dedicated always-on inference pools for predictable latency.
- Queue-based autoscaling for asynchronous inference/batch jobs.
- HPA/KEDA where supported by relevant workload metrics.
- Model consolidation, batching and quantization after quality testing.
- Scale-to-zero only when cold-start latency is acceptable.
- Spot/preemptible GPUs only with tested interruption handling.

```powershell
kubectl get hpa -A
kubectl get nodes -L node-pool,gpu_type
kubectl get pods -A -o wide
```

Cost per 1,000 successful requests or per million tokens can be more meaningful than raw GPU utilization, but define the workload, latency/quality targets, pricing assumptions and denominator consistently. Request reductions do not equal savings unless actual billed capacity changes.

## 14. Lab 13 — GPU workload security

Use approved images, scan dependencies, pin digests, restrict model and artifact sources, protect tokens via workload identity/secrets management and constrain egress. Device access may require security-policy exceptions; scope them narrowly and review with platform security. Treat user prompts, retrieved documents and model artifacts as potentially sensitive data.

Multi-tenant GPU sharing introduces memory isolation, model-data exposure and noisy-neighbor risks. Strong tenant boundaries may require dedicated GPU nodes or clusters.

## 15. Lab 14 — Failure simulation and recovery

In disposable staging, deliberately schedule a test Pod with a nonexistent GPU node label. Capture Pending reason, events and time to detect. Fix the selector through GitOps and verify successful scheduling. This tests scheduling recovery **without disrupting drivers or production devices**.

Second exercise: use a known CPU-only framework image with a GPU request to demonstrate the difference between successful device allocation and unavailable CUDA support. Record framework version, image digest, host driver, runtime, plugin and observed failure. Do not deliberately break the host GPU driver on a shared node.

## 16. Production troubleshooting runbook

| Symptom | Inspect | Likely cause | Safe action |
|---|---|---|---|
| Node Ready but GPU allocatable missing | Device plugin logs, driver, runtime | Discovery/plugin failure | Repair supported stack |
| Pod Pending | Events, taints, selectors, quota | Scheduling mismatch or GPU exhausted | Fix constraints/capacity |
| `nvidia-smi` fails in container | Host driver, runtime toolkit, allocation | Device exposure failure | Validate runtime integration |
| CUDA unavailable in framework | Image build, CUDA libs, driver | CPU-only image or incompatibility | Use supported image |
| vLLM cannot infer device | CUDA availability, plugin, image | Runtime/framework mismatch | Verify end-to-end CUDA |
| Model Pod OOMKilled | Pod memory, GPU VRAM, batch/model size | RAM or VRAM exhaustion | Right-size or optimize workload |
| GPU idle but high bill | Node-hours, autoscaling floor | Overprovisioned dedicated pool | Consolidate with SLO review |
| Slow first request | Model download/load, cache | Cold start | Warm pool or optimize startup |
| High GPU utilization, poor throughput | Batching, queue, CPU, network | Bottleneck outside raw GPU | Profile end-to-end |

## 17. Lab 15 — Operational acceptance

- [ ] GPU hardware, driver, runtime, plugin and Kubernetes versions inventoried.
- [ ] `nvidia.com/gpu` allocatable confirmed on intended nodes.
- [ ] GPU smoke-test Pod schedules and executes `nvidia-smi`.
- [ ] CUDA framework detects the GPU in a supported image.
- [ ] Taints, selectors, affinity and quotas tested with negative controls.
- [ ] Model server starts, becomes ready and serves a representative request.
- [ ] p95 latency, throughput, queue depth and GPU memory baselined.
- [ ] Metrics, alerts and GPU-to-workload attribution verified.
- [ ] Sharing/isolation mode documented and reviewed.
- [ ] Cost per unit of work and scale-up behavior measured.
- [ ] Incident recovery demonstrated in staging.
- [ ] Independent technical review and runtime evidence recorded.

## 18. Cleanup and cost hygiene

Delete only disposable test workloads:

```powershell
kubectl config current-context
kubectl delete pod gpu-smoke-test --ignore-not-found
kubectl get pods -A -o wide
```

If the model-serving test was created, remove it through the owning GitOps repository and verify reconciliation. Decommission temporary GPU node pools only after confirming they are not shared, and verify that cloud GPU instances, disks and load balancers are no longer billed. Never delete production GPU pools to complete a lab.

## Production takeaways

GPU platform readiness is a chain: hardware → driver → container runtime → device discovery → scheduler → image/framework → model server. Test every link. Build GPU node pools around reliability, isolation and actual inference performance, not just utilization. Treat accelerator cost as a first-class SRE metric.

**Draft status:** the labs and commands have not been executed or independently reviewed in this publication workflow.

**Next:** Chapter 098 — Multi-Cluster Administration and Fleet Management.
