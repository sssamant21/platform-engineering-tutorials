# Kubernetes Administration — Master Plan

> **105 chapters · 21 parts · EKS, AKS, GKE · hands-on Kubernetes administration and SRE.**

## Learning outcomes

Install, secure, operate, observe, troubleshoot, scale, upgrade, back up and recover Kubernetes clusters across local environments and managed cloud platforms. Each chapter includes theory, a reproducible lab, validation, failure modes, production considerations, and cleanup.

## Curriculum

### Part 01 — Kubernetes Fundamentals (Chapters 001–005)

- **001** — What Is Kubernetes?
- **002** — Containers, Images and Container Runtimes
- **003** — Kubernetes Architecture and Components
- **004** — Control Plane, Worker Nodes and etcd
- **005** — Kubernetes Objects, YAML and Declarative Management

### Part 02 — Cluster Installation and Setup (Chapters 006–010)

- **006** — kubectl Installation and kubeconfig
- **007** — Kubernetes Local Lab with kind and Minikube
- **008** — kubeadm Cluster Installation
- **009** — Containerd, CNI and CoreDNS Configuration
- **010** — Cluster Installation and Verification Project

### Part 03 — Kubernetes API and Resource Administration (Chapters 011–015)

- **011** — Kubernetes API and API Resources
- **012** — Namespaces, Labels and Annotations
- **013** — kubectl Advanced Administration
- **014** — Resource Lifecycle, Finalizers and Garbage Collection
- **015** — Resource Management and Administration Lab

### Part 04 — Pods and Workload Controllers (Chapters 016–020)

- **016** — Pod Architecture and Lifecycle
- **017** — Init Containers, Sidecars and Probes
- **018** — Deployments, ReplicaSets and Rollouts
- **019** — StatefulSets, DaemonSets, Jobs and CronJobs
- **020** — Workload Administration and Recovery Lab

### Part 05 — Scheduling and Resource Management (Chapters 021–025)

- **021** — Kubernetes Scheduler Internals
- **022** — Node Selectors and Affinity Rules
- **023** — Taints, Tolerations and Topology Spread
- **024** — Resource Requests, Limits, QoS and Quotas
- **025** — Scheduling and Resource Pressure Troubleshooting Lab

### Part 06 — Kubernetes Networking (Chapters 026–030)

- **026** — Kubernetes Networking Architecture and CNI
- **027** — Services and Load Balancing
- **028** — CoreDNS and Service Discovery
- **029** — Ingress Controllers and Gateway API
- **030** — Networking and DNS Troubleshooting Lab

### Part 07 — Storage Administration (Chapters 031–035)

- **031** — Kubernetes Volumes, PVs and PVCs
- **032** — StorageClasses and CSI Drivers
- **033** — Dynamic Provisioning and Volume Access Modes
- **034** — Volume Expansion, Snapshots and Storage Lifecycle
- **035** — Storage Failure and Recovery Lab

### Part 08 — Configuration and Application Packaging (Chapters 036–040)

- **036** — ConfigMaps and Secrets
- **037** — Secret Management and Rotation
- **038** — Helm Installation, Charts and Releases
- **039** — Kustomize and Environment Overlays
- **040** — Configuration Management and Rollback Lab

### Part 09 — Security Administration (Chapters 041–045)

- **041** — Kubernetes Authentication and RBAC
- **042** — ServiceAccounts and Workload Identity
- **043** — Pod Security Standards and Security Contexts
- **044** — Admission Policies and Image Security
- **045** — Kubernetes Security Hardening Project

### Part 10 — Node and Cluster Lifecycle (Chapters 046–050)

- **046** — Node Architecture, Kubelet and Node Conditions
- **047** — Cordon, Drain and Node Maintenance
- **048** — Kubernetes Version Upgrades
- **049** — Certificate Management and Rotation
- **050** — Cluster Upgrade and Maintenance Project

### Part 11 — High Availability and Resilience (Chapters 051–055)

- **051** — High Availability Control Plane Design
- **052** — etcd Operations, Quorum and Recovery
- **053** — PodDisruptionBudgets and Graceful Shutdown
- **054** — Multi-Zone Availability and Failure Domains
- **055** — High Availability Failure Simulation Project

### Part 12 — Monitoring and Observability (Chapters 056–060)

- **056** — Kubernetes Metrics, Logs and Events
- **057** — Metrics Server and Prometheus
- **058** — Grafana Dashboards and Alertmanager
- **059** — OpenTelemetry and Distributed Tracing
- **060** — Production Observability and Alerting Project

### Part 13 — Troubleshooting and Incident Response (Chapters 061–065)

- **061** — Kubernetes Troubleshooting Methodology
- **062** — Container Startup and Image Pull Failures
- **063** — Pending, Evicted, OOMKilled and CrashLoopBackOff Pods
- **064** — Node, Network, DNS and Control Plane Failures
- **065** — Production Incident Investigation Project

### Part 14 — Performance and Autoscaling (Chapters 066–070)

- **066** — Horizontal Pod Autoscaler
- **067** — Vertical Pod Autoscaler
- **068** — Cluster Autoscaler and Karpenter
- **069** — CPU, Memory, Network and Storage Capacity Planning
- **070** — Kubernetes Performance and Scaling Project

### Part 15 — Backup and Disaster Recovery (Chapters 071–075)

- **071** — Kubernetes Backup Strategy and RPO/RTO
- **072** — etcd Backup and Restore
- **073** — Velero and Persistent Volume Backups
- **074** — Cross-Cluster Restore and Disaster Recovery
- **075** — Disaster Recovery Simulation Project

### Part 16 — Amazon EKS Administration (Chapters 076–080)

- **076** — Amazon EKS Architecture and Provisioning
- **077** — EKS Node Groups and Karpenter
- **078** — EKS Networking, Load Balancers and Storage
- **079** — EKS Security, Identity, Monitoring and Upgrades
- **080** — EKS Production Operations Project

### Part 17 — Azure AKS Administration (Chapters 081–085)

- **081** — Azure AKS Architecture and Provisioning
- **082** — AKS Node Pools and Autoscaling
- **083** — AKS Networking, Load Balancing and Storage
- **084** — AKS Identity, Security, Monitoring and Upgrades
- **085** — AKS Production Operations Project

### Part 18 — Google GKE Administration (Chapters 086–090)

- **086** — Google GKE Architecture, Control Plane and Cluster Provisioning
- **087** — GKE Standard vs Autopilot, Node Pools and Autoscaling
- **088** — GKE Networking, VPC-Native Clusters, Load Balancing and Storage
- **089** — GKE Security, Workload Identity Federation, IAM, Monitoring and Upgrades
- **090** — GKE Production Administration, Troubleshooting and Recovery Project

### Part 19 — GitOps, Governance and FinOps (Chapters 091–095)

- **091** — GitOps with Argo CD and Flux
- **092** — Policy as Code with Kyverno and Gatekeeper
- **093** — Multi-Tenancy and Namespace Governance
- **094** — Kubernetes Cost Management and FinOps
- **095** — GitOps and Governance Project

### Part 20 — Advanced Platform Engineering (Chapters 096–100)

- **096** — CRDs, Operators and Custom Controllers
- **097** — GPU Scheduling and AI Workloads
- **098** — Multi-Cluster Administration and Fleet Management
- **099** — Production Change Management and SRE Runbooks
- **100** — Advanced Production Recovery Project

### Part 21 — Final Production Capstone Projects (Chapters 101–105)

- **101** — Build a Production-Ready Kubernetes Cluster
- **102** — Deploy a Highly Available Stateful Application
- **103** — Simulate Complex Kubernetes Failures
- **104** — Upgrade, Recover and Validate a Production Cluster
- **105** — Kubernetes Administrator and SRE Final Assessment

## Chapter acceptance standard

1. Explain objectives, prerequisites and architecture.
2. Provide tested, copyable commands and version/platform assumptions.
3. Include hands-on lab, expected observations, validation and failure diagnosis.
4. Document safety boundaries, production practices, rollback and cleanup.
5. Mark complete only after content and lab review; do not claim production validation based only on a local simulation.

## Lab safety

Use disposable kind clusters for destructive exercises. Treat EKS, AKS and GKE examples as potentially billable. Never run disruptive commands against production without approved change control and tested backups.
