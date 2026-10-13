# Chapter 086 — Google GKE Architecture, Control Plane and Cluster Provisioning

**Track:** Kubernetes Administration · **Part 18 — Google Kubernetes Engine**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers and Google Cloud administrators  
**Prerequisites:** Chapters 001–015, 021–030, 061–070 and 076–085; Google Cloud CLI, gke-gcloud-auth-plugin, kubectl, Windows PowerShell; approved staging project and billing budget

## 1. Production scenario and mission

A team is preparing a Google Kubernetes Engine (GKE) environment for customer-facing APIs and stateful services. It must choose between Standard and Autopilot, determine regional availability, plan VPC-native Pod and Service IP ranges, establish IAM and workload identity, and verify access to a private control plane. An initial design review identifies overlapping secondary CIDRs, insufficient subnet capacity, broad project IAM grants and missing monitoring ownership.

**Mission:** design a secure, observable and cost-governed GKE staging cluster, review its provisioning configuration, validate access and Kubernetes primitives, and produce a production-readiness report.

**Safety:** creating GKE clusters, node pools, load balancers, disks, NAT gateways or monitoring resources can incur charges. Provision only in an approved staging Google Cloud project. Never remove the only cluster administrator or change production network/firewall policies as part of a lab.

### Learning outcomes

1. Explain the GKE control plane and shared responsibility model.
2. Compare Standard and Autopilot cluster operating models.
3. Distinguish regional and zonal cluster failure domains.
4. Design VPC-native networking with secondary Pod/Service IP ranges.
5. Plan private cluster endpoint access, Cloud DNS and egress.
6. Separate Google Cloud IAM, Kubernetes RBAC and Workload Identity Federation for GKE.
7. Prepare repeatable cluster provisioning using gcloud and IaC.
8. Validate nodes, CoreDNS, Services and CSI storage.
9. Establish logging, monitoring, security and cost controls.
10. Deliver provisioning acceptance evidence and troubleshooting runbooks.

## 2. GKE architecture and shared responsibility

```text
             Users / CI / platform engineers
                           |
                 Google Cloud IAM
                           |
                 GKE API / gcloud
                           |
               Managed control plane
           API server / scheduler / etcd
                           |
                  Kubernetes API
                           |
        +------------------+------------------+
        |                                     |
   GKE Standard                         GKE Autopilot
   Customer-configured                  Google-managed
   node pools / sizing                  node infrastructure
        |                                     |
        +------------------+------------------+
                           |
           VPC-native Pods / Services
                           |
       Ingress / Gateway / Cloud Load Balancing
                           |
       Persistent Disk CSI / Filestore CSI
                           |
    Cloud Logging / Monitoring / Audit Logs
```

Google operates the managed control plane. Customers remain responsible for workload configuration, application availability, Kubernetes permissions, data protection, network access policy, secrets and operational acceptance. Standard and Autopilot differ in the level of node-management responsibility and workload constraints.

## 3. Lab 1 — Verify tooling, identity, project and billing boundary

```powershell
$ErrorActionPreference = 'Stop'
gcloud version
kubectl version --client
gke-gcloud-auth-plugin --version
gcloud auth login
gcloud auth list
$project = 'REPLACE_WITH_APPROVED_STAGING_PROJECT_ID'
$region = 'us-central1'
$cluster = 'REPLACE_WITH_APPROVED_STAGING_GKE_CLUSTER'
gcloud config set project $project
gcloud config get-value project
gcloud projects describe $project --format='table(projectId,lifecycleState)'
gcloud billing projects describe $project
```

**Stop** if the project, principal or billing account does not match the approved charter. The `gcloud` active account and Kubernetes kubeconfig identity must both be checked.

**Expected:** verified project, principal, region and billing owner.

## 4. Lab 2 — Inventory existing GKE clusters and cluster modes

```powershell
gcloud container clusters list --project $project
gcloud container clusters describe $cluster --region $region --project $project --format='yaml(name,location,autopilot,releaseChannel,currentMasterVersion,privateClusterConfig,networkConfig,workloadIdentityConfig)'
```

Use `--zone` instead of `--region` for an existing zonal cluster; do not assume a cluster's location type from its name.

### Inventory

```text
Project / organization / folder:
Cluster mode (Standard or Autopilot):
Regional or zonal:
Release channel and version:
Control-plane endpoint policy:
VPC / subnet / Pod secondary range:
Service secondary range:
Node service account:
Workload Identity Federation:
Network policy / dataplane:
Cloud Logging / Monitoring:
Cost labels / budget:
```

## 5. Lab 3 — Standard versus Autopilot

| Dimension | GKE Standard | GKE Autopilot |
|---|---|---|
| Node operations | Explicit node pool management | Google manages underlying node infrastructure |
| Scheduling | Broad node configuration flexibility | Workload-driven provisioning with platform constraints |
| Capacity control | Node pool sizing/autoscaling | Resource requests and Autopilot policies |
| Security baseline | Customer must configure more node settings | Stronger managed defaults and restrictions |
| Cost model | Cluster/node infrastructure and resources | Autopilot-specific workload and cluster pricing |
| Typical fit | Specialized node configurations | Reduced infrastructure operations |

Do not assume that every DaemonSet, privileged container, hostPath, GPU configuration or storage pattern works identically across modes. Verify current supported workloads and regional capabilities before choosing.

### Decision record

```text
Required workload types:
Privileged/host networking requirements:
GPU and specialized VM requirements:
Node-level observability agents:
Spot and batch scheduling:
Persistent storage and CSI:
Availability target:
Operational staffing:
Budget model:
Selected mode and justification:
```

## 6. Lab 4 — Regional versus zonal architecture

A regional GKE cluster provides control-plane and node placement characteristics designed for greater availability than a single-zone deployment, but application resilience still depends on replicas, zone spread, storage topology and external dependencies.

```powershell
gcloud compute zones list --filter="region:($region)" --format='table(name,status)'
gcloud container get-server-config --region $region --project $project --format='yaml(validMasterVersions,channels)'
```

### Failure-domain design

- Spread critical stateless replicas across available zones.
- Account for PodDisruptionBudgets and graceful shutdown.
- Verify persistent disk regional/zonal capabilities.
- Maintain capacity for node or zone failure.
- Review quotas per region and VM family.
- Distinguish cluster recovery from application/data recovery.

**Expected:** explicit availability and recovery targets with documented cost tradeoffs.

## 7. Lab 5 — VPC-native networking and IP capacity

GKE VPC-native clusters use alias IP addressing with Pod and Service secondary IP ranges. IP design must consider maximum Pods, node count, growth, connected networks and overlapping CIDRs.

```powershell
gcloud compute networks list --project $project
gcloud compute networks subnets list --regions $region --project $project --format='table(name,region,ipCidrRange,secondaryIpRanges)'
gcloud compute firewall-rules list --project $project --format='table(name,network,direction,disabled)'
```

### Address plan

```text
VPC and subnet:
Node primary CIDR:
Pod secondary CIDR/range name:
Service secondary CIDR/range name:
Expected max nodes and Pods:
Upgrade surge headroom:
Network policy / dataplane:
Private Service Connect / private endpoints:
Cloud NAT and egress:
VPN / Interconnect CIDR overlaps:
DNS and hybrid name resolution:
```

**Expected:** nonoverlapping CIDRs and an approved growth plan. Secondary-range sizing is a provisioning decision that should not be left to defaults without review.

## 8. Lab 6 — Private control-plane access and DNS

Private cluster networking may involve internal or DNS-based control-plane endpoints, authorized access policies and approved corporate connectivity. Exact options vary by GKE mode and current platform capabilities.

```powershell
gcloud container clusters describe $cluster --region $region --project $project --format='yaml(privateClusterConfig,controlPlaneEndpointsConfig,masterAuthorizedNetworksConfig)'
```

### Private access gates

1. Operator and CI network paths documented.
2. Control-plane DNS resolution tested from approved hosts.
3. Authorized networks/endpoints constrained appropriately.
4. Firewall and routing allow required control-plane connectivity.
5. Emergency access path is tested and audited.
6. No public endpoint exposure without explicit approval.

**Expected:** a reachable, least-exposed API endpoint design, not merely a private-cluster checkbox.

## 9. Lab 7 — IAM, Kubernetes RBAC and workload identity

Three separate layers matter:

1. **Google Cloud IAM:** controls GKE and Google Cloud API operations.
2. **Kubernetes RBAC:** controls Kubernetes API resources and namespaces.
3. **Workload Identity Federation for GKE:** lets workloads obtain scoped Google Cloud credentials without embedding service account keys.

```powershell
gcloud projects get-iam-policy $project --format='table(bindings.role,bindings.members)'
gcloud container clusters describe $cluster --region $region --project $project --format='yaml(workloadIdentityConfig,securityPostureConfig)'
kubectl get clusterrolebindings
kubectl get rolebindings -A
kubectl get serviceaccounts -A
```

These commands assume the intended kubeconfig is already configured for the cluster.

### Security acceptance

- Human users have minimum required Google Cloud IAM and Kubernetes RBAC.
- Node service accounts have no unnecessary broad project permissions.
- Workload identity principal bindings are scoped.
- Long-lived JSON service account keys are avoided.
- Audit logging covers privilege changes.
- Break-glass access is documented and tested.

## 10. Lab 8 — Provisioning plan with gcloud

**Review-only template; staging approval required before execution.**

```powershell
$project = 'REPLACE_WITH_APPROVED_STAGING_PROJECT_ID'
$region = 'us-central1'
$cluster = 'gke-ch086-staging'
$network = 'REPLACE_WITH_APPROVED_VPC'
$subnet = 'REPLACE_WITH_APPROVED_SUBNET'
$podRange = 'REPLACE_WITH_POD_SECONDARY_RANGE_NAME'
$serviceRange = 'REPLACE_WITH_SERVICE_SECONDARY_RANGE_NAME'
```

### Standard regional cluster template

```powershell
gcloud container clusters create $cluster `
  --project $project `
  --region $region `
  --release-channel regular `
  --enable-ip-alias `
  --network $network `
  --subnetwork $subnet `
  --cluster-secondary-range-name $podRange `
  --services-secondary-range-name $serviceRange `
  --enable-shielded-nodes `
  --workload-pool "$project.svc.id.goog" `
  --num-nodes 1
```

**Important:** `--num-nodes 1` for a regional Standard cluster can result in one node per selected zone, not necessarily one node total. Confirm zones, VM SKU, quotas, node service account, logging, monitoring, control-plane endpoint security, maintenance policy and cost before creating anything.

For Autopilot, use the separate supported `gcloud container clusters create-auto` workflow and validate its networking/security flags; do not reuse Standard-only node pool flags.

## 11. Lab 9 — Infrastructure as Code review

Terraform or another approved IaC system should be the system of record for cluster, networking and IAM resources.

### IaC review gates

```text
Project and billing:
Provider and API versions:
VPC/subnet/secondary CIDRs:
Standard vs Autopilot:
Region, zones and release channel:
Private control-plane endpoints:
Node service account / Workload Identity:
Logging, monitoring and audit:
Network policy and security posture:
Persistent storage classes:
Upgrade and maintenance policy:
Budget labels / cleanup ownership:
State encryption and locking:
Plan review and change approval:
```

```powershell
terraform fmt -check
terraform validate
terraform plan -out=ch086.plan
terraform show ch086.plan
```

These commands require an initialized Terraform project. Never commit state files, credentials or sensitive plan artifacts.

## 12. Lab 10 — Configure kubeconfig and verify cluster access

```powershell
gcloud container clusters get-credentials $cluster --region $region --project $project
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A
kubectl auth can-i list pods --all-namespaces
```

For zonal clusters use `--zone`. The gke-gcloud-auth-plugin must be installed and available. A Forbidden result can mean authentication succeeded but RBAC denied the operation.

**Expected:** correct cluster context, successful authentication and documented Kubernetes authorization.

## 13. Lab 11 — Inspect GKE networking and CSI

```powershell
kubectl -n kube-system get deployments,daemonsets
kubectl -n kube-system get service kube-dns
kubectl get services -A
kubectl get endpointslices -A
kubectl get csidrivers
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
```

### Storage considerations

- Compute Engine Persistent Disk CSI for block storage.
- Filestore CSI for supported shared filesystem workloads.
- Zonal/regional disk topology and node scheduling.
- Volume snapshots, reclaim policy and backup ownership.
- Database-consistent recovery independent of Kubernetes manifests.
- IAM, encryption and network connectivity for storage.

**Expected:** CNI, DNS, Services and storage drivers inventoried with named owners.

## 14. Lab 12 — Deploy an isolated smoke test

Save `ch086-smoke.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch086
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch086
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
  namespace: ch086
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch086-smoke.yaml
kubectl -n ch086 rollout status deployment/web --timeout=180s
kubectl -n ch086 get pods,services,endpointslices -o wide
kubectl -n ch086 get events --sort-by=.lastTimestamp
```

**Expected:** two Ready Pods and ready Service endpoints. This ClusterIP test does not provision a Google Cloud external load balancer.

## 15. Lab 13 — Logging, monitoring and security readiness

```powershell
gcloud container clusters describe $cluster --region $region --project $project --format='yaml(loggingConfig,monitoringConfig,releaseChannel,securityPostureConfig)'
kubectl get nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl get networkpolicies -A
```

### Monitoring scorecard

| Domain | Signal | Owner |
|---|---|---|
| Control plane | API availability, audit events | Platform/security |
| Nodes | Ready, CPU/memory, pressure | Platform |
| Scheduling | Pending Pods, autoscaler constraints | Platform |
| Network | DNS, CNI, ingress errors | Network |
| Storage | PVC Pending, CSI errors | DBRE |
| Application | Error rate, latency, SLO burn | Application |
| Security | IAM/RBAC changes, suspicious access | Security |
| Cost | Nodes, disks, NAT, logging, LB | FinOps |

Each alert should have an owner, threshold, dashboard and runbook. Log ingestion and metrics retention have cost implications.

## 16. Lab 14 — Provisioning failure tabletop

**Scenario:** the GKE API reports cluster provisioning completed, but nodes are unhealthy, private API access fails from a corporate workstation, and Pods cannot reach a private Google Cloud service.

### Investigation

1. Verify active Google Cloud project and identity.
2. Inspect GKE cluster operations and node pool health.
3. Confirm VPC subnet and secondary CIDR allocations.
4. Check firewall, routes, NAT and private access configuration.
5. Validate control-plane endpoint DNS and corporate connectivity.
6. Check node service account and required IAM permissions.
7. Inspect Pod Events and CNI/CSI health.
8. Confirm private service endpoint and workload identity.
9. Evaluate quota, VM SKU and zone capacity.
10. Record safe remediation and customer-impact assessment.

**Expected:** a fault tree separating authentication, network, capacity and workload identity failures.

## 17. Production provisioning runbook

### Preflight

1. Approve project, billing budget and resource labels.
2. Select Standard or Autopilot with documented workload constraints.
3. Choose regional/zonal availability and release channel.
4. Validate VPC/subnet and secondary CIDR capacity.
5. Review private control-plane access and DNS.
6. Approve IAM, Workload Identity and node service account.
7. Configure logging, monitoring, backup and security posture.
8. Review IaC plan, quotas and expected costs.

### Deployment

1. Confirm project and authenticated principal.
2. Apply approved IaC or gcloud configuration.
3. Verify cluster provisioning and control-plane access.
4. Inspect node health and system add-ons.
5. Validate DNS, Services and persistent storage.
6. Run staging smoke tests.
7. Verify workload identity and least privilege.
8. Capture dashboards and acceptance evidence.

### Handover

1. Document on-call ownership and escalation.
2. Record version/release-channel and maintenance policy.
3. Establish upgrade and node lifecycle review.
4. Validate application and database backup procedures.
5. Set cost alerts and capacity forecasts.
6. Obtain platform, security and application sign-off.

## 18. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| gcloud denied | IAM/project mismatch | auth list, project IAM |
| kubectl Unauthorized | Auth plugin/token | gke-gcloud-auth-plugin |
| kubectl Forbidden | Kubernetes RBAC | auth can-i, role bindings |
| Private API unreachable | Endpoint/DNS/routing | cluster endpoint, network |
| Nodes NotReady | VM/network/identity | node conditions, GKE operations |
| Pods Pending | Requests, quota, autoscaling | Events, node pools |
| Pod IP exhaustion | Secondary range sizing | subnet and cluster network config |
| DNS errors | CoreDNS/kube-dns/network | DNS logs, Services |
| PVC Pending | CSI/topology/quota | PVC Events, StorageClass |
| Unexpected cost | Nodes, NAT, disks, logging | Billing reports and labels |

## 19. Cleanup and safeguards

For the isolated namespace:

```powershell
kubectl config current-context
kubectl -n ch086 get deployments,pods,services
kubectl delete namespace ch086
```

Do not automatically delete shared GKE clusters, node pools, VPCs, firewall rules, service accounts, disks, snapshots or logging resources. If a dedicated staging cluster was created, decommission it only under an approved plan that accounts for data retention and residual charges.

## 20. Acceptance checklist

- [ ] Google Cloud project, identity and billing owner verified.
- [ ] GKE Standard vs Autopilot choice justified.
- [ ] Regional/zonal architecture and availability reviewed.
- [ ] VPC-native subnet and secondary ranges sized.
- [ ] Private control-plane access and DNS designed.
- [ ] IAM, Kubernetes RBAC and Workload Identity boundaries documented.
- [ ] gcloud provisioning plan reviewed or marked Not run.
- [ ] IaC governance and rollback considerations reviewed.
- [ ] kubeconfig access validated or marked Not run.
- [ ] CNI, DNS, Services and CSI storage inspected.
- [ ] Smoke test completed or marked Not run.
- [ ] Logging, monitoring, security and cost ownership defined.
- [ ] Provisioning failure tabletop completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 21. References

- [GKE Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/kubernetes-engine-overview)
- [GKE Standard and Autopilot](https://cloud.google.com/kubernetes-engine/docs/concepts/choose-cluster-mode)
- [GKE Regional Clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/regional-clusters)
- [VPC-native Clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/alias-ips)
- [GKE Private Clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/private-cluster-concept)
- [GKE Workload Identity Federation](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [GKE Authentication](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)
- [GKE Release Channels](https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels)
- [GKE Persistent Storage](https://cloud.google.com/kubernetes-engine/docs/concepts/persistent-volumes)
- [GKE Logging and Monitoring](https://cloud.google.com/kubernetes-engine/docs/concepts/about-logs)
- [gcloud container clusters](https://cloud.google.com/sdk/gcloud/reference/container/clusters)

**Next:** Chapter 087 — GKE Standard vs Autopilot, Node Pools and Autoscaling.
