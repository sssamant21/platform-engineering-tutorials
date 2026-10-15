# Chapter 078 — GKE Networking, Ingress, Gateway API and Persistent Storage Integration for GitOps

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 16:** Google Kubernetes Engine (GKE)  
**Chapter:** 078 / 100  
**Audience:** Platform Engineers, SREs, DBREs, Network Engineers and Cloud Architects

> **Safety:** Use a dedicated GKE staging project, synthetic data and approved budgets. Networking, firewall, Gateway, StorageClass and PVC changes can interrupt workloads or delete data. Never delete production PVs or modify shared VPC routes during these exercises. Verify Google Cloud project, region, cluster and Kubernetes context before making changes.

## 1. Learning objectives

1. Explain GKE VPC-native Pod, Service and node networking.
2. Design nonoverlapping secondary IP ranges, private nodes and egress.
3. Troubleshoot Cloud DNS, CoreDNS, firewall and NetworkPolicy behavior.
4. Compare GKE Ingress, Service type LoadBalancer and Gateway API.
5. Implement internal TLS ingress and policy-controlled routing.
6. Provision Persistent Disk CSI block volumes and Filestore CSI shared volumes.
7. Plan storage topology, access modes, snapshots, backup and restore.
8. Establish Terraform and Argo CD resource ownership.
9. Build observability, alerting and incident response for network/storage SLOs.
10. Validate the platform with integrated failure injection.

## 2. Architecture

~~~text
GitLab protected MR -> Argo CD -> Kubernetes manifests
                               |
                     private regional GKE
                               |
                    VPC-native alias IPs
                    /                 \
                CoreDNS          internal/external LB
                    |                 |
             Service discovery   Ingress / Gateway
                    |                 |
                 ClusterIP       TLS / HTTPRoute
                     \              /
                        app Pods
                       /        \
             Persistent Disk   Filestore
                    CSI          CSI
                       \        /
                     backups / DR
                          |
             Cloud Logging / Monitoring
                          |
                    SRE response
~~~

**Responsibility boundary:** Terraform owns VPC, subnets, secondary ranges, firewall, Cloud NAT, IAM and foundational cluster configuration. Argo CD owns delegated Services, Ingress/Gateway routes, NetworkPolicy and workload PVCs. Shared GatewayClasses, StorageClasses and CSI add-ons need explicit platform ownership.

## 3. VPC-native addressing

GKE VPC-native clusters use alias IPs. Nodes consume primary subnet addresses, Pods consume the Pod secondary range, and Services consume the Service secondary range.

~~~text
Primary node subnet:  10.50.0.0/20
Pod secondary range:  10.60.0.0/16
Service range:        10.70.0.0/20
~~~

These are illustrative; avoid overlap with peered VPCs, Cloud VPN, Interconnect, on-premises and disaster recovery regions. Node Pod CIDR allocation and maximum Pods per node affect real capacity.

## 4. Inventory and preflight

~~~bash
gcloud config get-value project
kubectl config current-context
gcloud container clusters describe gke-staging \
  --region REGION --project PROJECT_ID \
  --format="yaml(network,subnetwork,ipAllocationPolicy,privateClusterConfig,networkPolicy)"
gcloud compute networks subnets list --project PROJECT_ID
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get services -A
kubectl get networkpolicies -A
~~~

Stop if the project or cluster does not match the approved change. Check whether the cluster is Standard or Autopilot before applying controller-specific guidance.

## 5. Pod IP exhaustion

Pod secondary range exhaustion can prevent node scale-up or Pod scheduling. Plan node count, maximum Pods per node, per-node alias IP allocation and spare growth. Do not treat the raw CIDR address count as directly equal to schedulable Pods.

~~~bash
kubectl describe node NODE_NAME
kubectl get events -A --sort-by=.lastTimestamp
gcloud compute networks subnets describe SUBNET_NAME \
  --region REGION --project PROJECT_ID \
  --format="yaml(secondaryIpRanges)"
~~~

GKE discontiguous multi-Pod CIDR and expansion options depend on supported cluster configurations. Validate the exact migration path before modifying live IP ranges.

## 6. Private nodes and control-plane endpoints

Private nodes do not have external IP addresses. Control-plane endpoint access is configured separately. Use supported private endpoint or DNS-based access, authorized networks, Cloud DNS and approved operator connectivity.

Never expose a private control plane merely to bypass a VPN, firewall or DNS failure.

## 7. Private Google Access, Cloud NAT and egress

Private Google Access permits supported Google API access from eligible private VM interfaces; Cloud NAT may be required for other outbound destinations. Cloud NAT port exhaustion, firewall denies and DNS failures can all appear as image-pull or API timeouts.

Inspect actual routes, NAT configuration and firewall rules. Avoid broad allow-all egress changes during incidents.

## 8. Cloud DNS and CoreDNS

Cloud DNS handles approved VPC DNS zones and forwarding. CoreDNS handles Kubernetes Service discovery. Validate each dependency separately.

~~~bash
kubectl -n kube-system get deployment kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n demo-staging get service,endpointslices
~~~

GKE DNS implementations and managed components vary; inspect installed components rather than assuming identical names across every release.

## 9. NetworkPolicy enforcement

NetworkPolicy only enforces traffic when the cluster's dataplane/policy provider supports it and enforcement is enabled. GKE Dataplane V2 behavior differs from legacy policy implementations; validate feature-specific support.

~~~yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: demo-staging
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: frontend}
      ports:
        - protocol: TCP
          port: 8080
~~~

This example controls ingress to selected API Pods. It does not automatically restrict egress. Test both allowed and denied paths before rollout.

## 10. GKE Dataplane V2

GKE Dataplane V2 uses an eBPF-based networking implementation with its own policy and observability behavior. Confirm the cluster's actual dataplane before selecting diagnostic tools or policy manifests.

Review compatibility for network policy logging, IP masquerading, service routing and network troubleshooting features in the deployed GKE version.

## 11. Kubernetes Service types

ClusterIP provides internal virtual Service connectivity. NodePort exposes a port on eligible nodes. LoadBalancer integrates with Google Cloud load balancing using supported GKE controllers and annotations.

Internal and external load balancers have different frontend, firewall, routing and health-check requirements. Service creation alone does not establish an authenticated application boundary.

## 12. Internal LoadBalancer example

~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-api-internal
  namespace: demo-staging
  annotations:
    networking.gke.io/load-balancer-type: "Internal"
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
    - name: http
      port: 80
      targetPort: 8080
~~~

Validate current supported annotation behavior and controller capabilities. Internal access still depends on VPC routes, firewall rules, health checks and permitted clients.

## 13. GKE Ingress

GKE Ingress can provision Google Cloud HTTP(S) load balancer resources. Ingress controllers, ingress classes, static IPs, TLS certificate options and BackendConfig features vary by cluster mode and supported release.

Avoid mixing controller-specific annotations from NGINX, GKE Ingress and Gateway implementations. Choose one supported controller per route.

## 14. Ingress example

~~~yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: demo-api
  namespace: demo-staging
  annotations:
    kubernetes.io/ingress.class: "gce-internal"
spec:
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

This is a controller-specific illustration; GKE-managed internal Ingress prerequisites and TLS termination support must be validated against current documentation. Do not assume every Ingress controller supports identical TLS Secret behavior or annotations.

## 15. Gateway API

Gateway API provides GatewayClass, Gateway, HTTPRoute and policy attachment boundaries. It separates platform-managed listeners from application routes, supporting more explicit delegation than many legacy Ingress designs.

Confirm that the chosen GKE GatewayClass supports the desired internal/external load balancer, TLS certificate mechanism, traffic policies and cross-namespace routing.

## 16. Gateway API sample

~~~yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: internal-apps
  namespace: platform-ingress
spec:
  gatewayClassName: gke-l7-rilb
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: Same
~~~

This is a minimal HTTP-only illustration and not a production TLS configuration. The GatewayClass must exist and be supported. A route in another namespace would not attach with from: Same; use an explicitly reviewed policy for cross-namespace routes.

## 17. HTTPRoute sample

~~~yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: demo-api
  namespace: platform-ingress
spec:
  parentRefs:
    - name: internal-apps
  hostnames:
    - api.staging.example.internal
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: demo-api
          port: 80
~~~

The backend Service must be in the route namespace unless a supported cross-namespace reference is explicitly authorized. For production TLS, configure a supported HTTPS listener and certificate integration.

## 18. TLS, certificates and DNS

Use approved certificate issuance and renewal, managed certificates where supported, or a compatible cert-manager workflow. Verify hostname, trust chain, expiration, frontend certificate attachment and backend encryption requirements.

DNS propagation and health checks can delay a successful load balancer rollout. Monitor certificate expiry and load balancer target health independently.

## 19. Persistent Disk CSI

Compute Engine Persistent Disk CSI provisions block volumes for supported GKE workloads. Zonal and regional disk capabilities differ, and access mode semantics depend on disk type and driver support.

~~~bash
kubectl get csidrivers
kubectl get storageclasses
kubectl -n kube-system get pods | grep -i csi
~~~

For critical databases, prefer application replication and tested backups over assuming a single disk can move transparently across zones.

## 20. Persistent Disk StorageClass

~~~yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pd-balanced-staging
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-balanced
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
~~~

Validate encryption, topology, capacity, storage class parameter support and workload latency requirements. Retain does not replace backup.

## 21. PVC example

~~~yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-data
  namespace: demo-staging
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: pd-balanced-staging
  resources:
    requests:
      storage: 20Gi
~~~

With WaitForFirstConsumer, a PVC can remain Pending until a Pod is scheduled. Inspect scheduling and CSI events before declaring failure.

## 22. Filestore CSI

Filestore provides shared NFS storage under supported GKE/Filestore configurations. Use it for appropriate RWX workloads, not as a universal replacement for block storage or database-native replication.

Plan Filestore instance tier, region/zone, VPC connectivity, NFS permissions, performance and cost. Verify support for dynamically provisioned Filestore CSI volumes and the required API/driver.

## 23. Filestore StorageClass illustration

~~~yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: filestore-staging
provisioner: filestore.csi.storage.gke.io
parameters:
  tier: basic_hdd
reclaimPolicy: Retain
volumeBindingMode: Immediate
allowVolumeExpansion: false
~~~

Parameter support, minimum capacity and tier availability vary. This example must be adapted to the installed CSI driver and regional Filestore offering before use.

## 24. Backup, snapshots and restore

Use application-consistent backup for databases, CSI snapshots where supported, independently protected backup storage and a documented restore process. A crash-consistent snapshot does not necessarily satisfy application RPO/RTO.

Restore to a separate namespace and PVC; verify checksum or database integrity before any traffic cutover. Record encryption keys, permissions, region availability and recovery dependencies.

## 25. GitOps ownership and prune safety

~~~text
Terraform:
  VPC, subnet, DNS, firewall, Cloud NAT, IAM, GKE
Platform Argo CD:
  GatewayClass, shared Gateway, policy, StorageClass
Application Argo CD:
  Services, HTTPRoutes, Ingress, NetworkPolicy, PVC
GKE-managed controllers:
  load balancer reconciliation, CSI provisioning
~~~

Do not allow app projects to alter shared cluster-wide networking/storage resources. Protect stateful resources against unsafe Argo CD pruning, and validate rollback behavior.

## 26. Observability and SLOs

Track DNS latency/error, Pod IP exhaustion, network drops, NAT port use, load balancer health, TLS expiry, Gateway route conditions, ingress 5xx, PVC provisioning time, CSI attach/mount failures, disk latency, Filestore NFS errors and backup success.

Correlate Cloud Logging, Cloud Monitoring, GKE events, load balancer logs, CSI controller logs and application traces. Alert on sustained user impact rather than transient controller reconciliation.

## 27. Lab A — Network baseline

1. Confirm GCP project, region and cluster context.
2. Inventory VPC, subnet and secondary ranges.
3. Verify private nodes and control-plane access.
4. Review firewall, Cloud NAT and Cloud DNS.
5. Record network dataplane and policy mode.
6. Archive redacted evidence.

**Pass:** network topology is documented and nonoverlapping.

## 28. Lab B — Pod IP capacity

1. Inspect Pod secondary range and maximum Pods per node.
2. Record current node and Pod counts.
3. Forecast pool scale-up requirements.
4. Simulate constrained pool capacity without exhausting production IPs.
5. Review relevant scheduler/GKE diagnostics.
6. Document expansion options.

**Pass:** address capacity is understood.

## 29. Lab C — CoreDNS and Service discovery

1. Deploy synthetic API and Service.
2. Verify EndpointSlices and DNS records.
3. Resolve Service FQDN from test Pod.
4. Test namespace-specific resolution.
5. Simulate incorrect Service name.
6. Restore and record evidence.

**Pass:** DNS and Service errors can be distinguished.

## 30. Lab D — Private egress

1. Deploy synthetic network test Pod.
2. Test approved Google API access.
3. Test approved external endpoint if required.
4. Inspect Private Google Access, NAT and firewall.
5. Simulate restricted egress in isolated environment.
6. Restore authorized path.

**Pass:** private nodes can reach only required destinations.

## 31. Lab E — NetworkPolicy isolation

1. Confirm policy enforcement is active.
2. Deploy frontend, API and unauthorized client.
3. Apply allow-only policy to API.
4. Verify frontend success and unauthorized client denial.
5. Check DNS remains functional.
6. Revert test policy.

**Pass:** positive and negative enforcement tests pass.

## 32. Lab F — Internal LoadBalancer

1. Deploy synthetic HTTP workload.
2. Create internal LoadBalancer Service.
3. Inspect frontend IP and health checks.
4. Test from approved VPC client.
5. Confirm unapproved route is inaccessible.
6. Delete disposable Service and verify cleanup.

**Pass:** private service routing is functional.

## 33. Lab G — GKE Ingress

1. Review supported controller and internal ingress prerequisites.
2. Deploy synthetic backend Service.
3. Create reviewed Ingress.
4. Verify load balancer provisioning.
5. Test host/path and TLS configuration.
6. Remove test resources safely.

**Pass:** controller-specific routing is understood.

## 34. Lab H — Gateway API

1. Confirm Gateway API CRDs and supported GatewayClass.
2. Create internal staging Gateway.
3. Attach HTTPRoute in authorized namespace.
4. Test hostname and path.
5. Attempt unauthorized cross-namespace attachment.
6. Restore policy and record conditions.

**Pass:** route delegation is enforced.

## 35. Lab I — TLS rotation

1. Deploy approved test certificate.
2. Verify chain, hostname and expiry.
3. Rotate certificate in staging.
4. Confirm load balancer/controller update.
5. Validate backend readiness.
6. Document monitoring and rollback.

**Pass:** TLS rotation does not expose plaintext secrets.

## 36. Lab J — Persistent Disk CSI

1. Verify driver and StorageClass.
2. Create disposable PVC and consuming Pod.
3. Record PV, disk type and zone.
4. Write synthetic data/checksum.
5. Restart Pod and verify persistence.
6. Record reclaim and backup behavior.

**Pass:** block storage is persistent.

## 37. Lab K — Zonal disk failure

1. Record disk and Pod zone.
2. Apply incompatible affinity in disposable workload.
3. Observe Pending scheduling/attach event.
4. Inspect CSI controller and scheduler.
5. Restore compatible placement.
6. Verify data integrity.

**Pass:** zonal storage failures are diagnosable.

## 38. Lab L — Filestore RWX

1. Confirm Filestore API and CSI driver support.
2. Provision approved staging Filestore volume.
3. Mount in two synthetic Pods.
4. Test shared read/write and NFS permissions.
5. Inspect network path and performance.
6. Clean up within approved data retention policy.

**Pass:** RWX behavior matches workload requirements.

## 39. Lab M — Filestore network incident

1. Record Filestore IP, tier and VPC path.
2. Simulate isolated NFS connectivity failure.
3. Observe mount errors.
4. Inspect firewall, routing and DNS.
5. Restore approved access.
6. Verify shared data consistency.

**Pass:** NFS dependency failures can be isolated.

## 40. Lab N — Backup and isolated restore

1. Generate synthetic stateful dataset.
2. Perform supported backup/snapshot.
3. Record restore point and checksum.
4. Restore into separate namespace/PVC.
5. Verify data/application consistency.
6. Measure RPO/RTO.

**Pass:** storage is recoverable.

## 41. Lab O — Integrated incident capstone

1. Deploy app with Gateway/Ingress and Persistent Disk PVC.
2. Inject isolated NetworkPolicy failure.
3. Inject separate disk scheduling mismatch.
4. Correlate Cloud Monitoring, events and CSI logs.
5. Restore reviewed GitOps manifests.
6. Measure recovery and produce timeline.

**Pass:** network/storage recovery preserves data and security.

## 42. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Pods cannot schedule | Pod secondary IP shortage | Review alias IP capacity |
| 2 | Pod network unreachable | Dataplane/firewall | Inspect GKE network |
| 3 | CoreDNS NXDOMAIN | Wrong Service/namespace | Correct DNS target |
| 4 | CoreDNS timeout | Upstream/network | Restore resolver path |
| 5 | Private API inaccessible | Endpoint/DNS/routing | Restore approved access |
| 6 | Private node egress fails | NAT/Private Google Access | Repair egress |
| 7 | NetworkPolicy ineffective | Enforcement not enabled | Verify dataplane |
| 8 | NetworkPolicy blocks traffic | Missing allowed path | Fix scoped policy |
| 9 | Internal LB Pending | Controller/IAM/quota | Inspect events |
| 10 | Internal LB unreachable | Firewall/route/health | Trace frontend |
| 11 | Ingress 404 | Host/path/class mismatch | Fix route |
| 12 | Ingress 502/503 | Backend readiness | Restore endpoints |
| 13 | Gateway route unattached | ParentRefs/allowedRoutes | Correct policy |
| 14 | TLS handshake failure | Cert/hostname | Restore certificate |
| 15 | PD PVC Pending | CSI/topology | Inspect provisioner |
| 16 | PD attachment fails | Zone/attachment limit | Restore compatible node |
| 17 | Filestore mount fails | NFS/VPC/permissions | Restore network/access |
| 18 | Backup restore inconsistent | App not quiesced | Use verified backup |

## 43. Runbook — GKE Pod networking outage

1. Confirm affected namespaces, nodes and zones.
2. Inspect GKE dataplane, Pod IP allocation and node health.
3. Review VPC firewall, routes, Cloud NAT and policy.
4. Test approved Pod-to-Pod and Pod-to-Service paths.
5. Restore networking through reviewed configuration.
6. Validate DNS, ingress and application SLO.
7. Document RCA.

## 44. Runbook — private API and DNS incident

1. Verify cluster status in Google Cloud.
2. Confirm operator identity and auth plugin.
3. Inspect endpoint mode, Cloud DNS and approved routes.
4. Test from management network.
5. Restore private connectivity without public exposure.
6. Verify kubectl and Argo CD.
7. Record preventive actions.

## 45. Runbook — ingress or Gateway failure

1. Identify host, Service, Gateway/Ingress and frontend.
2. Inspect route conditions, controller and backend health.
3. Check firewall, health checks, DNS and TLS.
4. Restore approved GitOps revision.
5. Validate authorized routes and HTTPS.
6. Measure recovery time.
7. Archive logs and evidence.

## 46. Runbook — Persistent Disk CSI failure

1. Identify PVC/PV, disk type and zone.
2. Inspect CSI logs, scheduler and attachment events.
3. Preserve data; do not delete PVC/PV blindly.
4. Restore compatible node/zone or recover from backup.
5. Verify checksum and application consistency.
6. Record RPO/RTO and affected SLO.
7. Update topology safeguards.

## 47. Runbook — Filestore CSI and NFS outage

1. Identify Filestore instance, tier, IP and VPC.
2. Check NFS path, firewall and mount options.
3. Inspect CSI events and storage quota.
4. Restore network and access.
5. Validate shared read/write and permissions.
6. Verify data integrity and application SLO.
7. Record incident and cost impact.

## 48. Evidence template

~~~text
Change/incident ID:
GCP project, region and GKE cluster:
VPC, node subnet, Pod/Service secondary ranges:
GKE dataplane and NetworkPolicy mode:
Private endpoint, DNS and Cloud NAT:
Internal/external LB frontend and health:
Ingress/GatewayClass/HTTPRoute:
TLS certificate and owner:
Persistent Disk CSI and PVC/PV topology:
Filestore CSI tier, VPC and access:
Backup restore point, checksum and RPO/RTO:
Terraform and Argo CD revision:
Cloud Monitoring and alert evidence:
Measured recovery, owner and approval:
~~~

## 49. Scored readiness assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| VPC-native networking and private access | 20 | IP, DNS, egress tests |
| Network isolation | 15 | Positive/negative policy tests |
| Ingress, Gateway and TLS | 20 | Internal routing and certificates |
| Persistent Disk CSI | 15 | Provisioning and zonal recovery |
| Filestore CSI | 10 | RWX and NFS recovery |
| Backup and restore | 10 | Data integrity and RPO/RTO |
| GitOps, monitoring and runbooks | 10 | Evidence and recovery |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: unintended public exposure, unenforced required isolation, lost data during testing, missing backup, or unsafe GitOps pruning of stateful resources.

## 50. Final acceptance checklist

- [ ] VPC-native Pod/Service secondary ranges validated.
- [ ] Private GKE control-plane access verified.
- [ ] Private node egress and Cloud DNS tested.
- [ ] CoreDNS and Service discovery validated.
- [ ] NetworkPolicy enforcement tested positively and negatively.
- [ ] Internal LoadBalancer and Ingress verified.
- [ ] Gateway API routing and namespace delegation tested.
- [ ] TLS issuance, renewal and monitoring validated.
- [ ] Persistent Disk CSI topology and persistence verified.
- [ ] Filestore CSI RWX and NFS access tested.
- [ ] Application-consistent backup and isolated restore passed.
- [ ] Terraform and Argo CD ownership documented.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five SRE runbooks validated.
- [ ] Operational readiness signed off.

## 51. Knowledge check

1. How do GKE node, Pod and Service IP ranges differ?
2. Why does Pod secondary range size affect node autoscaling?
3. What is the difference between Cloud DNS and CoreDNS?
4. Why does a NetworkPolicy need a supported enforcing dataplane?
5. How does Gateway API delegation differ from traditional Ingress?
6. Why must internal load balancers still be protected by firewall rules?
7. What makes Persistent Disk topology important for stateful workloads?
8. When is Filestore more appropriate than Persistent Disk?
9. Why is a snapshot not always an application-consistent backup?
10. How can GitOps pruning threaten persistent data?

## 52. References

- [GKE VPC-native clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/alias-ips)
- [GKE private clusters](https://cloud.google.com/kubernetes-engine/docs/how-to/private-clusters)
- [GKE Dataplane V2](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2)
- [GKE NetworkPolicy](https://cloud.google.com/kubernetes-engine/docs/how-to/network-policy)
- [GKE internal load balancers](https://cloud.google.com/kubernetes-engine/docs/how-to/internal-load-balancing)
- [GKE Ingress](https://cloud.google.com/kubernetes-engine/docs/concepts/ingress)
- [GKE Gateway API](https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api)
- [GKE Persistent Disk CSI](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver)
- [GKE Filestore CSI](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/filestore-csi-driver)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 078 complete.** Next: **Chapter 079 — GKE Security, Workload Identity Federation, Observability and Upgrade Operations**.