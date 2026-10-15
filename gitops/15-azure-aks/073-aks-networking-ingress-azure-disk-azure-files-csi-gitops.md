# Chapter 073 — AKS Networking, Ingress, Azure Disk and Azure Files CSI Integration for GitOps

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 15:** Azure Kubernetes Service (AKS)  
**Chapter:** 073 / 100  
**Audience:** Platform Engineers, SREs, Kubernetes Administrators, Network Engineers, DBREs

> **Safety:** Use an isolated AKS staging environment and synthetic data. Changes to private DNS, UDRs, NSGs, CNI, ingress, StorageClasses and reclaim policies can disrupt workloads or delete data. Never delete a production PVC/PV or modify shared routing during these labs. Confirm subscription and kubeconfig context before executing changes.

## 1. Objectives

After completing this chapter, you should be able to:

1. Explain AKS Pod, Service, node and Azure VNet networking paths.
2. Compare Azure CNI Overlay and Azure CNI Pod Subnet designs.
3. Validate CoreDNS, private DNS, egress and NetworkPolicy enforcement.
4. Configure internal/external Azure Load Balancer Services and managed ingress.
5. Understand application routing through ingress controllers and Gateway API.
6. Provision encrypted Azure Disk CSI and Azure Files CSI storage.
7. Diagnose volume provisioning, AZ affinity, attachment and SMB/NFS failures.
8. Apply GitOps ownership, immutable storage decisions and safe cleanup.
9. Monitor networking/storage SLIs and execute production recovery runbooks.

## 2. Reference architecture

~~~text
Approved operator network / private DNS
                  |
            AKS private API
                  |
       Azure VNet + node subnets
                  |
       Azure CNI dataplane / Pods
           /              \
       CoreDNS           Service VIP
           |                 |
     internal DNS        Azure Load Balancer
                             |
                      ingress controller
                             |
                       application Pods
                         /       \
                    Azure Disk  Azure Files
                      CSI         CSI
                         \       /
                    snapshots / backup
                             |
             Azure Monitor + Prometheus
                             |
           GitLab -> reviewed GitOps MR -> Argo CD
~~~

**Separation of concerns:** Azure networking and identities are owned by approved infrastructure code; Kubernetes Services, Ingress/Gateway routes, PVCs and app policies may be owned by Argo CD. StorageClass ownership and reclaim behavior must be explicit.

## 3. Networking request path

A request can traverse Azure DNS, a load balancer frontend, NSGs, an ingress controller, a Kubernetes Service and an application Pod. Internal Pod-to-Service traffic generally uses cluster networking and does not necessarily traverse the external load balancer.

Trace failures hop-by-hop; avoid assuming a 502 response proves the Azure Load Balancer is defective.

## 4. AKS network modes

| Topic | Azure CNI Overlay | Azure CNI Pod Subnet |
| --- | --- | --- |
| Pod addressing | Overlay Pod CIDR | Pod addresses from Azure networking subnet model |
| Node addressing | VNet subnet | VNet subnet |
| Capacity concern | Node subnet plus overlay planning | Pod subnet allocation planning |
| Routing | Supported overlay dataplane | Supported Pod subnet dataplane |
| Operational risk | CIDR overlap, NAT/egress, policy | Subnet exhaustion, routes, policy |
| Migration | Evaluate supported cluster migration | Evaluate supported cluster migration |

Kubenet and legacy configurations have different limitations; do not assume an in-place conversion between network models. Validate Azure CNI mode and network dataplane support for the deployed AKS version.

## 5. Network inventory

~~~bash
az account show --output table
kubectl config current-context
az aks show -g rg-aks-staging -n aks-staging \
  --query '{network:networkProfile,private:apiServerAccessProfile}' -o json
az network vnet subnet list -g rg-aks-staging --vnet-name vnet-aks-staging -o table
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get services -A
kubectl get networkpolicies -A
~~~

Inspect the actual node resource group and subnet resource group; AKS-managed resources may not reside in the user-facing resource group.

## 6. CIDR planning

Example staging design:

~~~text
VNet:                10.40.0.0/16
Node subnet:         10.40.0.0/20
Private endpoints:   10.40.16.0/24
Overlay Pod CIDR:    10.244.0.0/16
Service CIDR:        10.96.0.0/16
DNS Service IP:      10.96.0.10
~~~

Avoid overlap with peered VNets, VPN, ExpressRoute, on-premises networks and future disaster recovery regions. Record the maximum nodes, Pod density, ingress frontends and private endpoints.

## 7. NSGs, UDRs and outbound connectivity

Network Security Groups filter supported Azure traffic; user-defined routes control next hops. NAT Gateway, Azure Firewall or another approved egress path may be required for image pulls, identity endpoints, package mirrors and platform services.

Check effective routes and security rules rather than editing broad allow-all rules. A private cluster still needs permitted control-plane, DNS and Azure service connectivity.

## 8. Private API DNS

Private AKS API connectivity depends on correct name resolution and routing from the operator, GitLab runner and approved management environment. Validate private DNS zone links and split-horizon DNS.

~~~bash
az aks show -g rg-aks-staging -n aks-staging \
  --query '{privateFqdn:privateFqdn,fqdn:fqdn}' -o json
kubectl cluster-info
~~~

Do not publish a private cluster endpoint to the internet to bypass a DNS incident.

## 9. CoreDNS and Service discovery

~~~bash
kubectl -n kube-system get deployment coredns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get configmap coredns -o yaml
kubectl -n demo-staging get services,endpointslices
~~~

CoreDNS availability depends on replicas, node placement, upstream DNS, resource requests and network reachability. Service DNS records require correct namespaces and selectors.

## 10. NetworkPolicy enforcement

A NetworkPolicy manifest is only effective if the deployed network dataplane supports and enables policy enforcement. Azure CNI powered by Cilium and other supported AKS policy models differ in capability.

~~~yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-from-frontend
  namespace: demo-staging
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
~~~

This policy restricts ingress to selected Pods only when enforcement is active. It does not establish default-deny egress. Design DNS, metrics, health and identity egress explicitly before applying broader restrictions.

## 11. Azure Load Balancer Services

~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-api-internal
  namespace: demo-staging
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
    - name: http
      port: 80
      targetPort: 8080
~~~

Verify supported annotation behavior, frontend subnet selection, health probes and allocated internal IP. Internal does not mean automatically authorized to all network segments; NSGs and routing still matter.

## 12. Ingress controller choices

Common AKS designs include NGINX-based controllers, Azure Application Gateway-based integration, managed ingress capabilities and Gateway API implementations. Support, controller lifecycle and feature availability change; validate the selected controller's maintained release and compatibility.

Ingress objects require an installed ingress controller. The Ingress resource alone does not create routing. Prefer a dedicated IngressClass and reviewed annotations; untrusted annotation injection can create security risk.

## 13. Ingress example

~~~yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  ingressClassName: internal-nginx
  tls:
    - hosts:
        - api.staging.example.internal
      secretName: demo-api-tls
  rules:
    - host: api.staging.example.internal
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: demo-api
                port:
                  number: 80
~~~

This requires an installed controller, matching IngressClass, approved internal DNS and a valid TLS Secret or supported certificate integration. Do not commit plaintext TLS private keys to Git.

## 14. Gateway API

Gateway API separates infrastructure-owned listeners from application-owned HTTPRoutes and other route resources. Before using it, install a supported controller and CRDs and confirm its AKS integration.

Use Gateway/HTTPRoute policy boundaries to prevent applications from creating unauthorized public listeners. Gateway API support differs by controller and version.

## 15. Ingress TLS and certificate lifecycle

Use approved certificate issuance and rotation, e.g. Azure Key Vault-backed workflow or cert-manager where appropriate. Validate certificate chain, hostname, expiry, secret access and ingress reload behavior.

Certificate renewal should be monitored. TLS termination at ingress does not automatically encrypt all backend traffic; document end-to-end encryption requirements.

## 16. Azure Disk CSI fundamentals

Azure Disk CSI provisions block volumes suitable for a single-writer zonal workload under supported access modes. Azure managed disks have topology, attachment and SKU constraints.

~~~bash
kubectl get csidrivers
kubectl get storageclasses
kubectl -n kube-system get pods | grep -i csi
~~~

Do not assume ReadWriteOnce means a disk is safely shared by multiple nodes. Review actual access mode, driver capabilities and workload semantics.

## 17. Azure Disk StorageClass

~~~yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: managed-csi-staging
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_LRS
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
~~~

StorageClass creation is illustrative. Validate encryption requirements, disk SKU, supported topology and expansion behavior. Retain protects underlying PV lifecycle only within supported semantics; it does not replace backup.

## 18. Azure Disk PVC and workload

~~~yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-data
  namespace: demo-staging
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: managed-csi-staging
  resources:
    requests:
      storage: 20Gi
~~~

A PVC remains Pending until a consuming Pod schedules when WaitForFirstConsumer is used. This is often expected, not a failure.

## 19. Azure Files CSI fundamentals

Azure Files supports shared file access scenarios, subject to SMB/NFS protocol, storage account SKU, identity and network requirements. It is not a universal substitute for Azure Disk for latency-sensitive databases.

Network path, DNS, port 445 for SMB or port 2049 for NFS, storage account firewall and private endpoints may affect mounts. Check protocol-specific requirements.

## 20. Azure Files StorageClass

~~~yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: azurefile-csi-staging
provisioner: file.csi.azure.com
parameters:
  skuName: Premium_LRS
reclaimPolicy: Retain
volumeBindingMode: Immediate
allowVolumeExpansion: true
~~~

Check the selected storage account/protocol, authentication, supported CSI parameters and Azure Files regional availability. Use explicit provisioned storage and avoid broad account-key exposure.

## 21. Azure Files shared PVC

~~~yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-shared
  namespace: demo-staging
spec:
  accessModes: [ReadWriteMany]
  storageClassName: azurefile-csi-staging
  resources:
    requests:
      storage: 100Gi
~~~

Test actual multi-node mount behavior and performance. RWX access alone does not provide application-level concurrency control.

## 22. Storage backup and restore

For stateful workloads, combine supported CSI snapshots with application-consistent backups, tested restore, encryption/key recovery and a documented cutover plan. A filesystem snapshot taken during active writes may be crash-consistent rather than application-consistent.

Test restoration to a separate PVC and namespace before replacing any live volume. Measure RPO/RTO and verify checksums or database integrity.

## 23. Storage GitOps ownership

Terraform or an approved platform Argo CD Application should own StorageClasses and CSI add-on configuration. Application GitOps repositories may own PVC templates, StatefulSets and backup policies, but not shared cluster-wide StorageClasses without review.

Set prune safeguards for stateful resources. A Git revert must not accidentally delete persistent data.

## 24. Observability and SLOs

Monitor CoreDNS latency/errors, Pod IP allocation, network drops, Service endpoints, load balancer health, ingress 4xx/5xx and TLS expiry. For storage, monitor CSI errors, PVC Pending time, attach/mount failures, disk latency/throughput, Azure Files availability, quota, backup success and restore time.

Correlate Azure Monitor, Kubernetes events, ingress/controller logs and application traces. Use workload-specific latency thresholds rather than universal defaults.

## 25. Lab A — Networking baseline

1. Confirm Azure subscription and AKS context.
2. Inventory VNet, subnet, CNI mode and Pod/Service CIDRs.
3. Review NSGs, UDRs, outbound method and DNS.
4. Check node readiness and network controllers.
5. Capture Azure Monitor baseline.
6. Record network owner and cost impact.

**Pass:** networking topology is documented without CIDR overlap.

## 26. Lab B — CoreDNS and Service discovery

1. Create synthetic frontend and API Services.
2. Verify EndpointSlices match Ready Pods.
3. Resolve short and fully qualified Service DNS names.
4. Introduce a wrong namespace in disposable test.
5. Inspect DNS errors and correct name.
6. Validate resolution after recovery.

**Pass:** DNS failures can be isolated from backend failures.

## 27. Lab C — Azure CNI Pod networking

1. Verify deployed CNI mode and dataplane.
2. Record node and Pod addresses.
3. Test Pod-to-Pod connectivity in one namespace.
4. Test across namespaces.
5. Inspect route and policy effects.
6. Verify no accidental public exposure.

**Pass:** dataplane behavior matches the approved architecture.

## 28. Lab D — NetworkPolicy enforcement

1. Confirm policy enforcement is enabled.
2. Deploy frontend, API and unauthorized test client.
3. Apply ingress allow-only policy to API.
4. Verify frontend is allowed.
5. Verify unauthorized client is denied.
6. Remove policy and document impact.

**Pass:** policy changes are proven by positive and negative tests.

## 29. Lab E — Private API and DNS

1. Resolve private AKS API from approved operator network.
2. Record DNS zone and VNet links.
3. Simulate wrong DNS forwarding in isolated resolver.
4. Observe kubectl failure.
5. Restore DNS configuration.
6. Verify access without changing API exposure.

**Pass:** private access recovery does not weaken security.

## 30. Lab F — Internal LoadBalancer Service

1. Deploy synthetic HTTP workload.
2. Create annotated internal LoadBalancer Service.
3. Inspect assigned private frontend IP.
4. Verify connectivity from approved VNet client.
5. Confirm unapproved network has no route/access.
6. Delete disposable Service and check Azure resource cleanup.

**Pass:** Service is private and healthy.

## 31. Lab G — Ingress controller and TLS

1. Install pinned approved ingress controller in staging.
2. Verify IngressClass and controller Service.
3. Deploy synthetic Ingress with internal hostname.
4. Configure valid test TLS certificate.
5. Test HTTP-to-HTTPS and backend readiness.
6. Record controller logs and rollback.

**Pass:** TLS and routing work without unintended public ingress.

## 32. Lab H — Gateway API discovery

1. Inspect installed Gateway API CRDs.
2. Verify supported controller and GatewayClass.
3. Create disposable internal Gateway/HTTPRoute using supported examples.
4. Test hostname and path routing.
5. Verify cross-namespace policy boundaries.
6. Remove test resources.

**Pass:** controller ownership and route security are documented.

## 33. Lab I — Azure Disk CSI provisioning

1. Verify disk CSI driver and identity.
2. Create staging StorageClass with Retain.
3. Create PVC and consuming Pod.
4. Verify PV, managed disk and AZ placement.
5. Write synthetic data and restart Pod.
6. Confirm data integrity.

**Pass:** encrypted block storage survives Pod restart.

## 34. Lab J — Azure Disk topology failure

1. Record PV zone and consuming Pod node AZ.
2. Create a disposable incompatible scheduling constraint.
3. Observe Pending Pod or volume scheduling failure.
4. Inspect scheduler and CSI events.
5. Restore compatible placement.
6. Verify data integrity.

**Pass:** zonal volume placement is diagnosable.

## 35. Lab K — Azure Files RWX

1. Verify file CSI driver and approved storage account model.
2. Provision RWX PVC in staging.
3. Mount into two synthetic Pods on different nodes.
4. Write and read shared test file.
5. Test file permissions and concurrent access behavior.
6. Clean up without deleting retained test data unexpectedly.

**Pass:** shared filesystem semantics are validated.

## 36. Lab L — Azure Files mount failure

1. Confirm protocol and storage account networking.
2. Simulate blocked SMB/NFS path in isolated test.
3. Observe mount failure events.
4. Inspect DNS, private endpoint and NSG.
5. Restore required network path.
6. Verify successful remount.

**Pass:** mount failure is isolated to the correct dependency.

## 37. Lab M — Backup and restore

1. Generate synthetic dataset with checksum.
2. Create supported application-consistent backup and snapshot.
3. Record recovery point.
4. Restore to new PVC in separate namespace.
5. Verify checksum/application consistency.
6. Measure recovery time.

**Pass:** backup is restorable within chosen RPO/RTO.

## 38. Lab N — GitOps storage safeguards

1. Create protected platform StorageClass Application.
2. Create application PVC/StatefulSet Application.
3. Review Argo CD prune behavior and ownership.
4. Simulate manifest removal in disposable namespace.
5. Confirm retained data is protected.
6. Reconcile and document restore path.

**Pass:** GitOps cleanup cannot silently destroy required data.

## 39. Lab O — Integrated network/storage incident

1. Deploy synthetic app with ingress and Azure Disk PVC.
2. Inject a namespace-local network policy error.
3. Inject a separate disposable storage scheduling mismatch.
4. Trace ingress, Service, Pod and CSI symptoms.
5. Restore reviewed GitOps configuration.
6. Measure recovery and produce incident timeline.

**Pass:** incident recovery preserves data and access controls.

## 40. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Pod network unreachable | Azure CNI/dataplane | Inspect CNI and node routes |
| 2 | Pod IP allocation failure | Subnet/Pod capacity | Review addressing and maxPods |
| 3 | Service DNS NXDOMAIN | Wrong name/namespace | Inspect CoreDNS and Service |
| 4 | DNS SERVFAIL/timeouts | CoreDNS/upstream | Repair DNS dependency |
| 5 | Private AKS API unreachable | DNS/VNet path | Restore private connectivity |
| 6 | NetworkPolicy ignored | Unsupported/disabled enforcement | Verify dataplane capability |
| 7 | NetworkPolicy blocks DNS | Missing egress allowance | Permit scoped DNS traffic |
| 8 | Internal LB Pending | Azure permissions/quota | Inspect controller events |
| 9 | Internal LB unreachable | NSG/route/frontend | Trace approved network path |
| 10 | Ingress 404 | Host/path/Class mismatch | Correct route |
| 11 | Ingress 502/503 | Backend endpoints/readiness | Restore healthy targets |
| 12 | TLS handshake fails | Certificate/hostname/secret | Restore approved cert |
| 13 | Azure Disk PVC Pending | CSI/topology/identity | Inspect provisioner |
| 14 | Disk mount/attach fails | Wrong AZ/limits | Restore compatible node |
| 15 | Azure Files mount fails | SMB/NFS/private endpoint | Repair protocol network |
| 16 | RWX permissions fail | SMB/NFS identity/ACL | Correct scoped access |
| 17 | Snapshot restore inconsistent | Missing app quiescence | Use verified backup |
| 18 | Argo CD deletes storage resource | Unsafe prune ownership | Restore and add safeguards |

## 41. Runbook — Pod networking outage

1. Identify affected namespace, nodes and AZs.
2. Inspect CNI Pod health, Pod addresses and node routes.
3. Check NSGs, UDRs, subnet capacity and NetworkPolicy.
4. Compare successful and failing network paths.
5. Restore approved dataplane configuration.
6. Validate DNS, Service connectivity and application SLO.
7. Record incident evidence and regression checks.

## 42. Runbook — private API or DNS outage

1. Confirm AKS control-plane state from Azure.
2. Test private FQDN resolution from approved management network.
3. Inspect private DNS zone links and forwarding.
4. Validate VPN/ExpressRoute/VNet routing and NSGs.
5. Restore connectivity without opening public API access.
6. Verify kubectl, GitLab runner and Argo CD.
7. Document DNS ownership and preventive monitoring.

## 43. Runbook — ingress/load balancer incident

1. Identify hostname, Service, ingress controller and frontend.
2. Inspect DNS, TLS, IngressClass/GatewayClass and routes.
3. Check backend EndpointSlices, readiness and ports.
4. Inspect Azure LB provisioning and NSGs.
5. Reconcile approved GitOps revision or restore healthy Pods.
6. Validate HTTPS and target health.
7. Preserve access logs and timeline.

## 44. Runbook — Azure Disk CSI incident

1. Identify affected PVC/PV, StorageClass, CSI driver and Azure disk.
2. Confirm node/AZ placement and volume attachment state.
3. Inspect CSI controller/node logs and Azure API errors.
4. Preserve data; do not delete PVC/PV to troubleshoot blindly.
5. Restore compatible capacity or driver/identity configuration.
6. Verify filesystem/application integrity.
7. Document backup and RPO/RTO impact.

## 45. Runbook — Azure Files mount incident

1. Identify storage account, share, protocol and affected Pods.
2. Check CSI events, identity/secret mode and DNS.
3. Validate private endpoint, NSG and SMB/NFS port path.
4. Check account firewall, quota and share permissions.
5. Restore approved connectivity and access.
6. Test read/write and multi-node semantics.
7. Record incident and security impact.

## 46. Evidence template

~~~text
Change / incident ID:
Subscription, AKS cluster and region:
CNI mode, network dataplane and Pod/Service CIDRs:
VNet, subnets, NSGs, UDRs and egress:
Private API DNS resolution:
CoreDNS and Service endpoint evidence:
NetworkPolicy positive/negative tests:
Load balancer and ingress frontend:
TLS certificate expiry and owner:
CSI driver and StorageClass:
PVC/PV, AZ, encryption and reclaim policy:
Azure Files protocol and endpoint:
Backup point, checksum, measured RPO/RTO:
GitLab and Argo CD revisions:
SLO, recovery time and approver:
~~~

## 47. Scored operational readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| CNI, VNet, DNS and routing | 20 | Connectivity and CIDR review |
| Service, ingress and TLS | 20 | Internal LB and routing tests |
| Network isolation and security | 15 | Enforced policy tests |
| Azure Disk CSI reliability | 15 | Zonal provisioning and recovery |
| Azure Files CSI reliability | 10 | RWX and mount tests |
| Backup, restore and data safety | 10 | Verified restore |
| GitOps and incident response | 10 | Reviewed changes and runbooks |
| **Total** | **100** | |

**Pass:** at least 85/100 with no critical failure: unintended public ingress, unenforced required isolation, loss of synthetic data during restore, unapproved deletion of a persistent volume, or missing private API recovery path.

## 48. Final acceptance checklist

- [ ] Azure subscription and AKS context verified.
- [ ] CNI mode, CIDRs, routes and DNS documented.
- [ ] Private API remains restricted.
- [ ] CoreDNS and Service discovery tested.
- [ ] NetworkPolicy enforcement confirmed with negative tests.
- [ ] Internal LB and ingress/TLS validated.
- [ ] Azure Disk CSI topology and encryption tested.
- [ ] Azure Files CSI RWX and protocol networking tested.
- [ ] Backup/restore integrity and RPO/RTO measured.
- [ ] GitOps prune and ownership safeguards reviewed.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five SRE runbooks validated.
- [ ] Monitoring, alerts and cost owners assigned.

## 49. Knowledge check

1. How does Azure CNI Overlay differ from Pod Subnet mode?
2. Why does a NetworkPolicy not always enforce traffic restrictions?
3. How can a private DNS issue look like an AKS API outage?
4. What is the difference between a LoadBalancer Service and an Ingress?
5. Why does an Ingress resource require a controller?
6. When is Azure Disk more appropriate than Azure Files?
7. Why does WaitForFirstConsumer help zonal disks?
8. Which Azure Files network ports matter for SMB and NFS?
9. Why is a CSI snapshot not always application-consistent?
10. How can Argo CD pruning endanger persistent data?

## 50. References

- [AKS networking concepts](https://learn.microsoft.com/azure/aks/concepts-network)
- [Azure CNI Overlay](https://learn.microsoft.com/azure/aks/azure-cni-overlay)
- [AKS private clusters](https://learn.microsoft.com/azure/aks/private-clusters)
- [AKS network policies](https://learn.microsoft.com/azure/aks/use-network-policies)
- [AKS internal load balancer](https://learn.microsoft.com/azure/aks/internal-lb)
- [AKS ingress concepts](https://learn.microsoft.com/azure/aks/concepts-network-ingress)
- [Azure Disk CSI](https://learn.microsoft.com/azure/aks/azure-disk-csi)
- [Azure Files CSI](https://learn.microsoft.com/azure/aks/azure-files-csi)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/)
- [Kubernetes CSI Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 073 complete.** Next: **Chapter 074 — AKS Security, Microsoft Entra Workload Identity, Observability and Upgrade Operations**.