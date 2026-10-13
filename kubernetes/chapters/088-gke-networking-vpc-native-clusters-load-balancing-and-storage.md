# Chapter 088 — GKE Networking, VPC-Native Clusters, Load Balancing and Storage

**Track:** Kubernetes Administration · **Part 18 — Google Kubernetes Engine**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, GKE platform, Google Cloud networking and storage engineers  
**Prerequisites:** Chapters 026–030, 036–040, 086–087; Google Cloud CLI, gke-gcloud-auth-plugin, kubectl, Windows PowerShell; approved staging project

## 1. Incident scenario and objectives

A GKE application reports intermittent HTTP 503 responses. New Pods cannot schedule after node pool growth because Pod secondary IP ranges are exhausted. An internal load balancer cannot be reached from an on-premises client despite successful DNS resolution. A stateful workload remains Pending after its Persistent Disk volume was provisioned in a different zone from eligible nodes.

**Mission:** inspect VPC-native networking, diagnose Pod and Service routing, review Google Cloud load balancers and Gateway/Ingress, validate CSI storage, and deliver safe production runbooks and acceptance evidence.

**Safety:** changing VPC routes, firewall policies, load balancers, IP allocations, StorageClasses or persistent volumes can cause outages or charges. Use read-only inspection by default; apply manifests only in an approved staging cluster. Never force-detach an active database disk.

### Learning outcomes

1. Explain GKE VPC-native alias IP networking.
2. Plan node, Pod and Service secondary ranges.
3. Diagnose kube-dns/CoreDNS and Service EndpointSlices.
4. Compare ClusterIP, LoadBalancer, Ingress and Gateway API.
5. Review internal/external Google Cloud load balancing and health checks.
6. Trace VPC firewall, Cloud NAT, Private Google Access and hybrid connectivity.
7. Validate NetworkPolicy or Dataplane V2 enforcement.
8. Understand Persistent Disk CSI and Filestore CSI.
9. Diagnose volume binding, topology and mount failures.
10. Produce operational network/storage readiness evidence.

## 2. Reference architecture

```text
Public clients / private corporate clients
                    |
             DNS and TLS
                    |
      Google Cloud Load Balancing
                    |
          Ingress / Gateway
                    |
         Kubernetes Service
                    |
          Ready EndpointSlices
                    |
               GKE Pods
                    |
        VPC-native alias IP ranges
                    |
        VPC / firewall / Cloud NAT
                    |
    Cloud VPN / Interconnect / DNS

Storage:
  Pod -> Persistent Disk CSI -> zonal/regional PD
  Pod -> Filestore CSI -> shared filesystem
```

VPC-native GKE clusters use alias IPs: node IPs come from the primary subnet range, while Pods and Services use configured secondary ranges. The exact range allocation and Pod density vary by GKE configuration; calculate actual capacity rather than multiplying a generic maximum.

## 3. Lab 1 — Verify project, cluster and identity

```powershell
$ErrorActionPreference = 'Stop'
$project = 'REPLACE_WITH_APPROVED_STAGING_PROJECT_ID'
$location = 'us-central1'
$cluster = 'REPLACE_WITH_APPROVED_GKE_CLUSTER'
gcloud config set project $project
gcloud auth list
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(name,location,network,subnetwork,ipAllocationPolicy,privateClusterConfig,networkPolicy,datapathProvider)'
kubectl config current-context
kubectl get nodes -o wide
```

**Stop if** project, principal or Kubernetes context is not approved. The cluster location may be a region or a zone.

**Expected:** network, subnet, Pod/Service ranges, dataplane and endpoint access captured.

## 4. Lab 2 — Inventory VPC, subnet and secondary ranges

```powershell
gcloud compute networks list --project $project
gcloud compute networks subnets list --project $project --format='table(name,region,network,ipCidrRange,secondaryIpRanges)'
gcloud compute routes list --project $project --format='table(name,network,destRange,nextHopGateway)'
gcloud compute firewall-rules list --project $project --format='table(name,network,direction,disabled)'
```

### IP capacity worksheet

```text
VPC and subnet:
Node primary range:
Pod secondary range and name:
Service secondary range and name:
Max nodes and Pods per node:
Current Pod IP allocations:
Upgrade surge and scale-out headroom:
Future clusters sharing ranges:
Hybrid VPN/Interconnect overlaps:
Private Google Access and Cloud NAT:
Firewall and route owners:
```

**Expected:** no overlap with connected networks, documented range utilization and growth thresholds. Avoid editing a shared subnet solely for a tutorial.

## 5. Lab 3 — Investigate Pod IP exhaustion

```powershell
kubectl get nodes -o wide
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(ipAllocationPolicy,defaultMaxPodsConstraint)'
gcloud container node-pools list --cluster $cluster --location $location --project $project
```

### Root-cause checklist

1. Distinguish unschedulable Pods from sandbox/CNI IP assignment failures.
2. Check actual Pod CIDR allocations and node Pod density.
3. Verify node pool autoscaler bounds and VM quotas.
4. Review secondary range fragmentation/remaining capacity.
5. Check GKE networking feature and range expansion support.
6. Consider new node pools or approved CIDR changes only after impact review.

**Expected:** capacity analysis supported by Events and GKE network configuration.

## 6. Lab 4 — Validate kube-dns, Services and EndpointSlices

```powershell
kubectl -n kube-system get services
kubectl -n kube-system get deployments
kubectl get services -A
kubectl get endpointslices -A
kubectl -n kube-system get pods -o wide
```

DNS component naming depends on the GKE configuration; inspect the cluster instead of assuming a fixed CoreDNS deployment.

### Diagnosis

- Does the Service exist with the intended selector?
- Are backing Pods Ready?
- Are EndpointSlices populated?
- Does Pod DNS resolve cluster Service names?
- Do network policies allow DNS?
- Are upstream VPC DNS and private zones reachable?
- Is the problem name resolution, TCP connectivity or application readiness?

**Expected:** clear separation between DNS and Service-routing failures.

## 7. Lab 5 — Deploy isolated ClusterIP smoke test

Save `ch088-web.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch088
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch088
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
      containers:
        - name: web
          image: nginx:stable
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 250m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch088
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
```

```powershell
kubectl apply -f .\ch088-web.yaml
kubectl -n ch088 rollout status deployment/web --timeout=180s
kubectl -n ch088 get pods,services,endpointslices -o wide
kubectl -n ch088 get events --sort-by=.lastTimestamp
```

**Expected:** two Ready Pods and a ClusterIP with ready endpoints. This test does not create a Google Cloud load balancer.

## 8. Lab 6 — Internal and external LoadBalancer Services

A `Service type=LoadBalancer` can cause Google Cloud to provision load-balancing resources. GKE-specific annotations and service configuration control internal versus external behavior and backend design.

### Internal LoadBalancer example — review only

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-internal
  namespace: ch088
  annotations:
    networking.gke.io/load-balancer-type: "Internal"
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
```

**Do not apply without approval.** Review supported annotations, subnet, regional IP, health check, firewall, backend service/instance group design, and billing.

### Load balancer review gates

- Public versus internal access.
- Regional/global load balancer requirements.
- Frontend IP reservation and DNS.
- Firewall health-check source ranges.
- Backend health and Pod readiness.
- Client source IP preservation.
- Hybrid connectivity and routes.
- Cost labels, owner and cleanup.

## 9. Lab 7 — Ingress and Gateway API

GKE supports controller-managed HTTP(S) load balancing patterns through supported Ingress and Gateway implementations. Gateway API resources depend on installed CRDs and enabled GKE features.

```powershell
kubectl get ingressclasses
kubectl get ingress -A
kubectl get gatewayclasses
kubectl get gateways -A
kubectl get httproutes -A
```

If Gateway API resources are not installed, record Not installed. Do not infer an ingress controller is active from the presence of CRDs alone.

### HTTP(S) acceptance

1. Host/path rules and backend references correct.
2. TLS certificates and renewal ownership documented.
3. Health checks aligned with readiness behavior.
4. WAF/Cloud Armor policy reviewed if required.
5. External/internal exposure matches security requirements.
6. HTTP 5xx, latency and backend health monitored.
7. Controller compatibility and release lifecycle reviewed.

## 10. Lab 8 — NetworkPolicy, Dataplane V2 and firewall controls

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(networkPolicy,datapathProvider,networkConfig)'
kubectl get networkpolicies -A
gcloud compute firewall-rules list --project $project --format='table(name,network,direction,priority,disabled)'
```

### Enforcement layers

- Kubernetes NetworkPolicy, only when supported/enforced by the active dataplane.
- VPC firewall rules for VM/node and other VPC traffic.
- Cloud NAT/Private Google Access for required egress patterns.
- Private Service Connect and private DNS for supported services.
- IAM/Workload Identity for authorization to Google Cloud APIs.
- Application TLS and authentication.

**Expected:** policy enforcement confirmed through an approved negative/positive connectivity test; manifest existence alone is insufficient.

## 11. Lab 9 — Inspect Persistent Disk CSI and StorageClasses

```powershell
kubectl get csidrivers
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
kubectl get volumesnapshotclasses
kubectl get nodes -L topology.kubernetes.io/zone
```

### Persistent Disk design

- Block storage for supported ReadWriteOnce workloads.
- Zonal versus regional Persistent Disk.
- `WaitForFirstConsumer` and topology-aware provisioning.
- Performance, disk size, IOPS and throughput.
- Reclaim policy and volume expansion.
- Snapshot and application-consistent backup.
- CSI permissions and attachment limits.

**Expected:** storage class, binding mode, topology and data deletion risk recorded.

## 12. Lab 10 — Disposable Persistent Disk PVC test

**Staging only; creates potentially billable persistent storage.**

Save `ch088-pd.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pd-test
  namespace: ch088
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: REPLACE_WITH_APPROVED_GCE_PD_STORAGECLASS
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: pd-writer
  namespace: ch088
spec:
  containers:
    - name: writer
      image: busybox:1.36
      command:
        - /bin/sh
        - -c
        - |
          if [ ! -f /data/checkpoint ]; then
            echo gke-ch088-data > /data/checkpoint
          fi
          sleep 360000
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: pd-test
```

```powershell
kubectl apply -f .\ch088-pd.yaml
kubectl -n ch088 get pvc,pods -o wide
kubectl -n ch088 describe pvc pd-test
kubectl -n ch088 wait --for=condition=Ready pod/pd-writer --timeout=300s
kubectl -n ch088 exec pd-writer -- sha256sum /data/checkpoint
```

**Expected:** Bound PVC, Ready Pod and recorded checksum. A file checksum is not a database backup or disaster recovery test.

## 13. Lab 11 — Filestore CSI and shared filesystem evaluation

Filestore CSI supports compatible shared filesystem workloads. Compare with Persistent Disk based on access semantics, latency, throughput, quota, network design and cost.

```powershell
kubectl get csidrivers
kubectl get storageclasses
gcloud filestore instances list --project $project
```

Filestore APIs/permissions may not be enabled for the lab project. Record Not available if so.

### Evaluation

- ReadWriteMany and application locking semantics.
- NFS access and VPC connectivity.
- Performance tier, throughput and capacity.
- Availability and zone/region options.
- Backup and restore procedures.
- IAM/network controls and cost.
- Database compatibility and recovery guarantees.

**Expected:** documented rationale for block versus shared filesystem storage.

## 14. Lab 12 — Hybrid connectivity and private DNS incident tabletop

**Scenario:** an internal load balancer has a healthy backend and correct DNS entry, but an on-premises client cannot connect. A separate Pod can resolve a private Google Cloud service hostname but cannot reach it.

### Investigation

1. Verify source network, VPC, region and service frontend IP.
2. Inspect Cloud VPN/Interconnect routes and advertised prefixes.
3. Confirm VPC firewall ingress and health-check rules.
4. Check DNS forwarding, private zones and split-horizon behavior.
5. Verify Private Google Access, Cloud NAT or PSC as applicable.
6. Confirm NetworkPolicy/dataplane enforcement.
7. Separate DNS lookup success from TCP reachability.
8. Inspect Service endpoints and application readiness.
9. Record owner, change approval and recovery validation.
10. Document preventive tests and monitoring.

**Expected:** network fault tree without speculative firewall changes.

## 15. Lab 13 — Zonal disk attach incident tabletop

**Scenario:** a database Pod is rescheduled to a node in zone B, but its zonal Persistent Disk exists in zone A. The Pod remains Pending or reports a volume attachment error.

### Investigation

```powershell
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get pvc -A
kubectl get pv -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get volumeattachments
kubectl get events -A --sort-by=.lastTimestamp
```

1. Check PV node affinity and Pod scheduling constraints.
2. Confirm actual disk zone and attachment state.
3. Review StatefulSet, PDB and node pool zone coverage.
4. Avoid force-detaching a mounted database disk.
5. Use approved topology-aware recovery or restore plan.
6. Validate database consistency and application SLOs.

**Expected:** evidence that the root cause is storage topology, not DNS or CPU.

## 16. Lab 14 — Monitoring, cost and operational readiness

### Critical signals

| Domain | Signal | Runbook |
|---|---|---|
| IP capacity | Secondary range usage, Pod IP failures | Capacity and scaling |
| DNS | Lookup failures and latency | DNS diagnosis |
| Services | Empty EndpointSlices | Readiness/selector |
| Load balancing | Backend health, 5xx and latency | LB/ingress |
| Network | Firewall denies, hybrid route loss | VPC path |
| Storage | PVC Pending, CSI attach errors | Storage topology |
| Data | Restore status, integrity checks | DBRE recovery |
| Cost | LB, egress, disks, Filestore | FinOps |

### Cost worksheet

```text
Load balancer and frontend IP:
Cloud NAT and egress:
Interconnect/VPN traffic:
Cross-zone data transfer:
Persistent Disk type, size and snapshots:
Filestore tier and capacity:
Logging/Monitoring:
Unused resources:
Budget alert and owner:
```

**Expected:** dashboards, alerts, ownership and cost thresholds documented.

## 17. Production runbooks

### A. Pod networking failure

1. Capture Pod Events and node readiness.
2. Check VPC-native Pod IP allocations and autoscaler limits.
3. Inspect dataplane/network policy and VPC firewall.
4. Test DNS separately from application connectivity.
5. Review NAT/Private Google Access for egress.
6. Confirm application recovery and SLOs.

### B. Load balancer 5xx or unreachable

1. Verify Service/Ingress/Gateway configuration.
2. Check backend Pod readiness and EndpointSlices.
3. Inspect load balancer health checks and firewall rules.
4. Validate DNS and internal/external frontend reachability.
5. Review TLS, routing and controller events.
6. Confirm recovery with synthetic client tests.

### C. Persistent Disk mount failure

1. Inspect Pod, PVC, PV and VolumeAttachment Events.
2. Verify CSI driver and disk topology.
3. Check disk quota, attachment state and IAM.
4. Avoid unsafe force detach or data deletion.
5. Execute approved rescheduling or restore procedure.
6. Validate data integrity before closing incident.

## 18. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Pod IP allocation fails | Secondary range capacity | GKE IP allocation policy |
| Service resolves but fails | Empty endpoints or network | EndpointSlices, policies |
| DNS timeout | kube-dns/Cloud DNS/network | DNS logs and VPC |
| LoadBalancer Pending | IAM/quota/health | Service Events, cloud resources |
| Ingress 503 | Unhealthy backend | Readiness, LB health |
| Internal LB unreachable | Firewall/hybrid routes | VPC and Interconnect |
| PVC Pending | StorageClass/quota/topology | PVC Events |
| PD attach conflict | Disk zone mismatch | PV affinity, node zone |
| Filestore mount fails | NFS/network/permissions | CSI and VPC |
| Storage cost spike | Orphaned disks/snapshots | Billing and labels |

## 19. Cleanup and data protection

Before deleting the namespace, inspect PVC reclaim policies and backing disk ownership:

```powershell
kubectl config current-context
kubectl -n ch088 get deployments,pods,services,pvc
kubectl get pv
```

Only with approval:

```powershell
kubectl delete namespace ch088
```

PVC deletion can delete underlying Persistent Disks when reclaim policy is `Delete`. Do not delete shared VPC ranges, firewall rules, load balancers, Filestore instances, snapshots or production disks as lab cleanup.

## 20. Acceptance checklist

- [ ] Project, cluster and kubeconfig context verified.
- [ ] VPC, primary and secondary ranges inventoried.
- [ ] Pod IP growth and exhaustion risks documented.
- [ ] DNS, Services and EndpointSlices inspected.
- [ ] ClusterIP smoke test completed or marked Not run.
- [ ] Internal/external load balancing reviewed.
- [ ] Ingress/Gateway and TLS architecture assessed.
- [ ] NetworkPolicy and firewall enforcement verified.
- [ ] Persistent Disk CSI, topology and reclaim policy inspected.
- [ ] Disposable PVC checksum test completed or marked Not run.
- [ ] Filestore CSI suitability reviewed.
- [ ] Hybrid connectivity and storage incident tabletops completed.
- [ ] Monitoring, cost and on-call ownership documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 21. References

- [GKE VPC-native Clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/alias-ips)
- [GKE IP Address Management](https://cloud.google.com/kubernetes-engine/docs/concepts/about-ip-addresses)
- [GKE LoadBalancer Services](https://cloud.google.com/kubernetes-engine/docs/concepts/service-load-balancer)
- [GKE Ingress](https://cloud.google.com/kubernetes-engine/docs/concepts/ingress)
- [GKE Gateway API](https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api)
- [GKE Dataplane V2](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2)
- [GKE Persistent Volumes](https://cloud.google.com/kubernetes-engine/docs/concepts/persistent-volumes)
- [GKE Filestore CSI](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/filestore-csi-driver)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)

**Next:** Chapter 089 — GKE Security, Workload Identity Federation, IAM, Monitoring and Upgrades.
