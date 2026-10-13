# Kubernetes Administration

**105 chapters / 21 parts** — from Kubernetes fundamentals to production SRE capstones, with dedicated Amazon EKS, Azure AKS and Google GKE modules.

- [Complete chapter roadmap](MASTER-PLAN.md)
- [Chapter progress tracker](PROGRESS-TRACKER.md)
- [Chapter 001 — What Is Kubernetes?](chapters/001-what-is-kubernetes.md)
- [Chapter 002 — Containers, Images and Container Runtimes](chapters/002-containers-images-and-container-runtimes.md)
- [Chapter 003 — Kubernetes Architecture and Components](chapters/003-kubernetes-architecture-and-components.md)
- [Chapter 004 — Control Plane, Worker Nodes and etcd](chapters/004-control-plane-worker-nodes-and-etcd.md)
- [Chapter 005 — Kubernetes Objects, YAML and Declarative Management](chapters/005-kubernetes-objects-yaml-and-declarative-management.md)
- [Chapter 006 — kubectl Installation and kubeconfig](chapters/006-kubectl-installation-and-kubeconfig.md)
- [Chapter 007 — Kubernetes Local Lab with kind and Minikube](chapters/007-kubernetes-local-lab-with-kind-and-minikube.md)
- [Chapter 008 — kubeadm Cluster Installation](chapters/008-kubeadm-cluster-installation.md)
- [Chapter 009 — Containerd, CNI and CoreDNS Configuration](chapters/009-containerd-cni-and-coredns-configuration.md)
- [Chapter 010 — Cluster Installation and Verification Project](chapters/010-cluster-installation-and-verification-project.md)
- [Chapter 011 — Kubernetes API and API Resources](chapters/011-kubernetes-api-and-api-resources.md)
- [Chapter 012 — Namespaces, Labels and Annotations](chapters/012-namespaces-labels-and-annotations.md)
- [Chapter 013 — kubectl Advanced Administration](chapters/013-kubectl-advanced-administration.md)
- [Chapter 014 — Resource Lifecycle, Finalizers and Garbage Collection](chapters/014-resource-lifecycle-finalizers-and-garbage-collection.md)
- [Chapter 015 — Resource Management and Administration Lab](chapters/015-resource-management-and-administration-lab.md)
- [Chapter 016 — Pod Architecture and Lifecycle](chapters/016-pod-architecture-and-lifecycle.md)
- [Chapter 017 — Init Containers, Sidecars and Probes](chapters/017-init-containers-sidecars-and-probes.md)
- [Chapter 018 — Deployments, ReplicaSets and Rollouts](chapters/018-deployments-replicasets-and-rollouts.md)
- [Chapter 019 — StatefulSets, DaemonSets, Jobs and CronJobs](chapters/019-statefulsets-daemonsets-jobs-and-cronjobs.md)
- [Chapter 020 — Workload Administration and Recovery Lab](chapters/020-workload-administration-and-recovery-lab.md)
- [Chapter 021 — Kubernetes Scheduler Internals](chapters/021-kubernetes-scheduler-internals.md)
- [Chapter 022 — Node Selectors and Affinity Rules](chapters/022-node-selectors-and-affinity-rules.md)
- [Chapter 023 — Taints, Tolerations and Topology Spread](chapters/023-taints-tolerations-and-topology-spread.md)
- [Chapter 024 — Resource Requests, Limits, QoS and Quotas](chapters/024-resource-requests-limits-qos-and-quotas.md)
- [Chapter 025 — Scheduling and Resource Pressure Troubleshooting Lab](chapters/025-scheduling-and-resource-pressure-troubleshooting-lab.md)
- [Chapter 026 — Kubernetes Networking Architecture and CNI](chapters/026-kubernetes-networking-architecture-and-cni.md)
- [Chapter 027 — Services and Load Balancing](chapters/027-services-and-load-balancing.md)
- [Chapter 028 — CoreDNS and Service Discovery](chapters/028-coredns-and-service-discovery.md)
- [Chapter 029 — Ingress Controllers and Gateway API](chapters/029-ingress-controllers-and-gateway-api.md)
- [Chapter 030 — Kubernetes NetworkPolicies and Network Security](chapters/030-kubernetes-networkpolicies-and-network-security.md)
- [Chapter 031 — Kubernetes Volumes, PersistentVolumes and PersistentVolumeClaims](chapters/031-kubernetes-volumes-pvs-and-pvcs.md)
- [Chapter 032 — StorageClasses and CSI Drivers](chapters/032-storageclasses-and-csi-drivers.md)
- [Chapter 033 — Dynamic Provisioning and Volume Access Modes](chapters/033-dynamic-provisioning-and-volume-access-modes.md)
- [Chapter 034 — Volume Expansion, Snapshots and Storage Lifecycle](chapters/034-volume-expansion-snapshots-and-storage-lifecycle.md)
- [Chapter 035 — Storage Failure and Recovery Lab](chapters/035-storage-failure-and-recovery-lab.md)
- [Chapter 036 — ConfigMaps and Secrets](chapters/036-configmaps-and-secrets.md)
- [Chapter 037 — Secret Management and Rotation](chapters/037-secret-management-and-rotation.md)

## Repository conventions

- `chapters/`: canonical numbered tutorials
- `labs/`: reusable exercises and instructions
- `manifests/`: Kubernetes YAML used in labs
- `scripts/`: setup and verification helpers
- `runbooks/`: operational troubleshooting and recovery guides
- `projects/`: multi-chapter capstones

Do not mark a chapter complete until its lab is executed and verified. Lab examples are for disposable environments unless explicitly stated otherwise.
