# Chapter 083 — AKS Networking, Load Balancing and Storage

**Track:** Kubernetes Administration · **Part 17 — Azure Kubernetes Service**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, Azure networking and storage engineers  
**Prerequisites:** Chapters 026–030, 036–040, 081–082; Azure CLI, kubectl, Windows PowerShell; approved AKS staging cluster and subscription

## 1. Production incident scenario

An AKS application experiences intermittent 502 errors after a node pool expansion. New Pods remain Pending because the node subnet has insufficient IP capacity, an internal load balancer frontend cannot be reached from the corporate network, and a PostgreSQL StatefulSet cannot attach an Azure Disk volume after rescheduling into a different availability zone. The incident requires separating Kubernetes Service behavior, Azure network routing and CSI storage topology.

**Mission:** inventory AKS networking, validate Service and ingress paths, test isolated staging workloads and persistent volumes, diagnose Azure load balancer/CSI failures, and produce production-ready network and storage runbooks.

**Safety:** changing NSGs, UDRs, private DNS, load balancer annotations, storage classes, disk reclaim policies or Azure CNI configuration can disrupt workloads or incur charges. All mutating steps are staging-only and require approved resource ownership and budget.

### Learning outcomes

1. Explain AKS VNet, subnet, Pod, Service and egress data paths.
2. Compare Azure CNI Overlay and Pod Subnet addressing.
3. Diagnose subnet capacity, CNI and CoreDNS problems.
4. Distinguish ClusterIP, NodePort, LoadBalancer and ingress.
5. Design Azure Standard Load Balancer internal/external Services.
6. Evaluate ingress controllers, TLS and health probes.
7. Validate network policies, NSGs, routes and private endpoints.
8. Compare Azure Disk CSI and Azure Files CSI.
9. Troubleshoot PVC binding, AZ placement, attachment and mount errors.
10. Document backup, observability, cost and operational acceptance.

## 2. AKS networking and storage architecture

```text
Internet / corporate / private clients
                  |
            Azure DNS / TLS
                  |
        Azure Load Balancer / ingress
                  |
           Kubernetes Service
                  |
             EndpointSlices
                  |
               AKS Pods
                  |
         Azure CNI / node VNet
                  |
          NSGs / UDRs / NAT / DNS

Persistent data:
  Pod -> CSI driver -> Azure Managed Disk (AZ-scoped)
  Pod -> CSI driver -> Azure Files (shared filesystem)
```

AKS manages the Kubernetes control plane, but customers design VNet connectivity, IP capacity, security groups, DNS, load balancer exposure, CSI configuration, backups and disaster recovery. Azure Load Balancer is Layer 4; Layer 7 routing requires an appropriate ingress or gateway solution.

## 3. Lab 1 — Verify identity and cluster network profile

```powershell
$ErrorActionPreference = 'Stop'
$subscription = 'REPLACE_WITH_APPROVED_SUBSCRIPTION_ID'
$resourceGroup = 'REPLACE_WITH_STAGING_RESOURCE_GROUP'
$cluster = 'REPLACE_WITH_STAGING_AKS_CLUSTER'
az account set --subscription $subscription
az account show --query '{Name:name,Id:id,Tenant:tenantId}' --output json
az aks show --resource-group $resourceGroup --name $cluster --query '{Name:name,Network:networkProfile,Private:apiServerAccessProfile,NodeResourceGroup:nodeResourceGroup}' --output json
kubectl config current-context
kubectl get nodes -o wide
```

**Stop** if Azure subscription or kubeconfig context is not the approved staging environment.

**Expected:** record network plugin, plugin mode, dataplane, Pod CIDR, Service CIDR, outbound type, DNS service IP and private/public API mode.

## 4. Lab 2 — Inspect VNet, subnets, NSGs and routes

```powershell
az network vnet list --resource-group $resourceGroup --output table
az network nsg list --resource-group $resourceGroup --output table
az network route-table list --resource-group $resourceGroup --output table
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --output table
```

The AKS node subnet or associated NSGs may live in a different resource group; use the actual resource IDs from the AKS network profile and node pool configuration rather than assuming all resources are in the cluster resource group.

### Network inventory

```text
VNet and CIDR:
Node subnet and available IPs:
Pod subnet or overlay CIDR:
Service CIDR / DNS IP:
Availability zones:
NSG and route table:
NAT gateway / firewall / outbound type:
Private endpoints and DNS zones:
On-premises VPN/ExpressRoute:
Load balancer frontend IPs:
IP growth threshold and owner:
```

**Expected:** a network dependency map with subnet capacity and route ownership.

## 5. Lab 3 — Compare Azure CNI Overlay and Pod Subnet

| Mode | Pod IP model | Primary risk |
|---|---|---|
| Azure CNI Overlay | Pods use separate overlay address space | CIDR sizing, connectivity and supported feature constraints |
| Azure CNI Pod Subnet | Pods use VNet-routable subnet IPs | Subnet IP exhaustion and Pod density |
| Other supported modes | Cluster-specific | Compatibility and migration constraints |

### IP planning exercise

```text
Max nodes per pool:
Max Pods per node:
System/DaemonSet overhead:
Upgrade surge nodes:
Availability-zone failure reserve:
Node subnet free IPs:
Pod subnet free IPs (where applicable):
Overlay CIDR capacity (where applicable):
NAT/egress capacity:
Expected 12-month growth:
```

Do not assume changing the CNI mode is a harmless in-place operation. Evaluate Azure-supported migration paths and network policy compatibility before changes.

## 6. Lab 4 — Inspect CNI, CoreDNS and Service routing

```powershell
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get deployment coredns
kubectl -n kube-system get service kube-dns
kubectl get services -A
kubectl get endpointslices -A
kubectl -n kube-system logs deployment/coredns --tail=100
```

CNI component names differ by AKS network mode and dataplane; inspect the actual cluster rather than assuming a particular DaemonSet name.

### DNS investigation

1. Verify the Service selector and ready EndpointSlices.
2. Inspect CoreDNS readiness, CPU and memory.
3. Check Pod DNS policy and cluster DNS IP.
4. Review network policy and NSG/route restrictions.
5. Confirm Azure VNet DNS and private DNS zone linkage.
6. Check upstream DNS latency and resolution of private endpoints.

**Expected:** separate missing endpoints, DNS lookup failure and actual network path failure.

## 7. Lab 5 — Deploy an isolated ClusterIP Service

Save `ch083-service.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch083
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch083
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
  namespace: ch083
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch083-service.yaml
kubectl -n ch083 rollout status deployment/web --timeout=180s
kubectl -n ch083 get pods,services,endpointslices -o wide
kubectl -n ch083 describe service web
```

**Expected:** two Ready Pods and a ClusterIP Service with ready endpoints. No billable Azure load balancer is created.

## 8. Lab 6 — Design internal and external Azure Load Balancer Services

Kubernetes `Service type=LoadBalancer` can provision Azure load balancer resources through the AKS cloud provider integration. Exact behavior depends on cluster configuration, annotations, networking and identity permissions.

### Internal load balancer example — review only

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-internal
  namespace: ch083
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
```

**Do not apply without approval.** Creating an internal load balancer can incur charges and may require subnet, frontend IP and identity configuration.

### Review gates

- Internal versus public exposure.
- Correct VNet/subnet and frontend IP allocation.
- NSG, firewall, UDR and peering connectivity.
- Load balancer SKU and health probes.
- Azure identity permissions for LB/network operations.
- Client IP and traffic policy expectations.
- Cost, tags and cleanup ownership.

## 9. Lab 7 — Review ingress and TLS architecture

An Azure Standard Load Balancer is Layer 4. HTTP host/path routing, TLS termination and application-specific health checks are typically provided by an ingress controller or gateway implementation.

### Candidate integrations

- NGINX ingress controller where supported by organizational lifecycle policy.
- Azure Application Gateway integration.
- Gateway API-compatible controllers where supported.
- Other approved service mesh or ingress implementations.

Do not assume a specific ingress controller is installed.

```powershell
kubectl get ingressclasses
kubectl get ingress -A
kubectl get gatewayclasses
kubectl get gateways -A
kubectl get services -A
```

Gateway API resources are optional CRDs. NotFound errors indicate the API may not be installed.

### Ingress acceptance

- TLS certificate and renewal owner.
- Internal/public routing intent.
- DNS records and private zone resolution.
- Controller availability and version support.
- Health checks, timeouts and connection draining.
- WAF/security controls where required.
- No unintended public endpoints.

## 10. Lab 8 — NetworkPolicy, NSG and private endpoint security

Network isolation requires understanding which enforcement mechanism is active. A NetworkPolicy manifest alone does not prove that AKS enforces it.

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{NetworkPlugin:networkProfile.networkPlugin,NetworkPolicy:networkProfile.networkPolicy,NetworkDataplane:networkProfile.networkDataplane}' --output json
kubectl get networkpolicies -A
kubectl get namespaces --show-labels
```

### Layered controls

1. Kubernetes NetworkPolicy for Pod-level traffic where enforced.
2. Azure NSGs for subnet/NIC-level rules.
3. Azure Firewall/UDRs for controlled egress.
4. Private endpoints for supported Azure services.
5. Private DNS zone linkage and resolver configuration.
6. Managed identities for application authorization.
7. Application TLS, authentication and audit logging.

**Expected:** a documented trust boundary and verified enforcement mechanism.

## 11. Lab 9 — Inspect Azure Disk CSI and StorageClasses

```powershell
kubectl get csidrivers
kubectl -n kube-system get pods -o wide
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
kubectl get volumesnapshotclasses
```

### Azure Disk characteristics

- Block storage generally used for ReadWriteOnce workloads.
- Zone topology matters for zonal disks and node scheduling.
- Disk size, performance tier, IOPS and throughput affect application latency.
- CSI identity/permissions and Azure resource quotas affect provisioning.
- StorageClass binding mode influences when the disk is provisioned.
- Reclaim policy `Delete` can delete the backing disk when the PV is released.

**Expected:** identify the CSI driver, default StorageClass, binding mode, reclaim policy and zone topology.

## 12. Lab 10 — Provision a disposable Azure Disk PVC

**Approved staging only; may create billable Azure Disk storage.**

Save `ch083-disk.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: disk-test
  namespace: ch083
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: REPLACE_WITH_APPROVED_AZURE_DISK_STORAGECLASS
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: disk-writer
  namespace: ch083
spec:
  containers:
    - name: writer
      image: busybox:1.36
      command:
        - /bin/sh
        - -c
        - |
          echo ch083-disk-marker > /data/marker.txt
          sleep 360000
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: disk-test
```

```powershell
kubectl apply -f .\ch083-disk.yaml
kubectl -n ch083 get pvc,pods -o wide
kubectl -n ch083 describe pvc disk-test
kubectl -n ch083 wait --for=condition=Ready pod/disk-writer --timeout=180s
kubectl -n ch083 exec disk-writer -- cat /data/marker.txt
kubectl -n ch083 exec disk-writer -- sha256sum /data/marker.txt
```

**Expected:** PVC Bound, Pod Ready and checksum captured. A checksum test is not a substitute for an application-consistent backup.

## 13. Lab 11 — Evaluate Azure Files CSI shared storage

Azure Files CSI supports shared filesystem use cases, commonly including ReadWriteMany access modes. The design must account for SMB/NFS protocol choice, access permissions, networking, throughput, cost and workload consistency.

```powershell
kubectl get csidrivers
kubectl get storageclasses
az storage account list --resource-group $resourceGroup --output table
```

Storage accounts may be managed in separate resource groups; scope inventory appropriately.

### Azure Files evaluation

- Shared file access and supported protocols.
- Private endpoint and DNS requirements.
- Storage account firewall and identity model.
- Performance tier, quota, latency and throttling.
- Backup/snapshot and restore capabilities.
- POSIX/SMB permission semantics.
- Database workload compatibility.

**Expected:** choose Azure Files only when application filesystem semantics and performance requirements fit.

## 14. Lab 12 — Network and storage incident tabletop

**Scenario:** after AKS node pool expansion, a PostgreSQL Pod cannot attach its existing Azure Disk because the new node is in a different AZ. An internal load balancer is unreachable from an on-premises client, while CoreDNS resolves its private name correctly.

### Investigation sequence

1. Confirm Azure subscription, AKS cluster and node pool context.
2. Inspect Pod Events, PVC/PV topology and node zone labels.
3. Check VolumeAttachment and Azure Disk status.
4. Validate availability-zone placement and supported recovery paths.
5. Confirm internal LB frontend IP and health probes.
6. Trace VPN/ExpressRoute, VNet peering, NSGs and UDRs.
7. Verify application readiness and EndpointSlices.
8. Review Azure CNI subnet capacity and Pod IP availability.
9. Avoid force-detaching active database volumes.
10. Validate data integrity and application SLIs after recovery.

**Expected:** separate DNS success from network reachability and storage topology failures.

## 15. Lab 13 — Observability and cost acceptance

### Operational signals

- Subnet free IPs and Pod IP allocation failures.
- CoreDNS errors, latency and restart counts.
- Service EndpointSlice readiness.
- Load balancer frontend/backend health.
- Ingress 4xx/5xx, connection failures and TLS errors.
- Azure Disk attach/provision latency and disk performance.
- Azure Files latency, throughput and throttling.
- PVC Pending duration and disk topology conflicts.
- Azure Activity Log, Kubernetes Events and CSI logs.
- Unused public IPs, disks, snapshots and load balancers.

### Cost worksheet

```text
Azure Load Balancer and frontend IP:
Application Gateway/ingress:
NAT Gateway and outbound data:
Cross-zone/cross-region transfer:
Azure Managed Disk tier/size/IOPS:
Azure Files capacity and throughput:
Snapshots and backup retention:
Azure Monitor / Log Analytics:
Owner and budget alert:
```

**Expected:** dashboards, alert thresholds, on-call owners and cost controls recorded.

## 16. Production troubleshooting runbooks

### A. Pod networking failure

1. Inspect Pod Events and CNI status.
2. Confirm subnet/overlay capacity and max Pods.
3. Check node Ready state and CNI dataplane.
4. Review NSGs, routes and network policy.
5. Test DNS separately from TCP connectivity.
6. Validate application recovery and Pod readiness.

### B. Internal LoadBalancer unreachable

1. Inspect Service annotations and external/internal IP assignment.
2. Confirm frontend/backend health and probes.
3. Validate NSGs, UDRs and corporate connectivity.
4. Check application endpoints and listening ports.
5. Confirm private DNS resolves to expected IP.
6. Validate source-to-destination path and SLO recovery.

### C. Azure Disk attach or mount failure

1. Inspect PVC, PV, Pod and VolumeAttachment Events.
2. Confirm CSI driver and Azure identity permissions.
3. Check node/disk AZ compatibility.
4. Review disk attachment limits and resource state.
5. Use approved rescheduling or recovery procedure.
6. Validate filesystem and database consistency.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Pod IP allocation fails | Subnet/CNI limits | AKS network profile, node events |
| DNS timeout | CoreDNS, NSG, upstream DNS | CoreDNS and VNet DNS |
| Service has no endpoints | Selector/readiness | EndpointSlices |
| LoadBalancer IP Pending | Identity/quota/subnet | Service Events, Azure Activity Log |
| Internal LB unreachable | NSG, route, peering | Azure LB and network path |
| Ingress 502/503 | Backend health, routing | Controller logs, Pods |
| PVC Pending | CSI/StorageClass/quota | PVC Events |
| Disk multi-attach/zone conflict | Zonal disk placement | PV topology, node zone |
| Azure Files mount timeout | Firewall, DNS, protocol | CSI logs, private endpoint |
| Storage cost spike | Orphaned disks/snapshots | Cost Management and tags |

## 18. Cleanup and data protection

Before deleting the test namespace, verify PVC reclaim policy and backing disk ownership.

```powershell
kubectl config current-context
kubectl -n ch083 get deployments,pods,services,pvc
kubectl get pv
```

Only after approval:

```powershell
kubectl delete namespace ch083
```

Deleting PVCs can delete backing Azure disks under a `Delete` reclaim policy. Do not delete shared Azure Files shares, load balancers, private DNS zones, snapshots, NSGs or production storage as tutorial cleanup.

## 19. Chapter acceptance checklist

- [ ] Subscription, AKS cluster and context verified.
- [ ] VNet/subnet, CNI and IP capacity inventoried.
- [ ] CoreDNS and Service routing validated.
- [ ] ClusterIP staging Service test completed or marked Not run.
- [ ] Internal/external load balancer design reviewed.
- [ ] Ingress/TLS architecture and security gates reviewed.
- [ ] NetworkPolicy, NSG and private endpoint boundaries documented.
- [ ] Azure Disk CSI, StorageClass and reclaim policy inspected.
- [ ] Azure Disk PVC checksum test completed or marked Not run.
- [ ] Azure Files CSI suitability assessed.
- [ ] Multi-layer network/storage incident tabletop completed.
- [ ] Monitoring, runbooks and cost ownership documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [AKS Networking Concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-network)
- [Azure CNI Overlay](https://learn.microsoft.com/en-us/azure/aks/azure-cni-overlay)
- [AKS Configure Load Balancer](https://learn.microsoft.com/en-us/azure/aks/load-balancer-standard)
- [AKS Internal Load Balancer](https://learn.microsoft.com/en-us/azure/aks/internal-lb)
- [AKS Network Policy](https://learn.microsoft.com/en-us/azure/aks/use-network-policies)
- [AKS Storage Concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-storage)
- [AKS Azure Disks CSI](https://learn.microsoft.com/en-us/azure/aks/azure-disk-csi)
- [AKS Azure Files CSI](https://learn.microsoft.com/en-us/azure/aks/azure-files-csi)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)

**Next:** Chapter 084 — AKS Identity, Security, Monitoring and Upgrades.
