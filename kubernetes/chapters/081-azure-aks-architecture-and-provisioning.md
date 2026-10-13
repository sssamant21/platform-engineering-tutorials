# Chapter 081 — Azure AKS Architecture and Provisioning

**Track:** Kubernetes Administration · **Part 17 — Azure Kubernetes Service**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes platform, Azure cloud and security engineers  
**Prerequisites:** Chapters 001–015, 021–030, 036–040, 061–070, 076–080; Azure CLI, kubectl, Windows PowerShell, optional kubelogin and Terraform; approved Azure staging subscription

## 1. Production scenario and mission

A platform team is migrating a regulated application from self-managed Kubernetes to Azure Kubernetes Service (AKS). The new cluster must provide highly available worker capacity, private network access, Microsoft Entra authentication, managed identities, auditable permissions, CSI storage and repeatable provisioning. A failed provisioning attempt has already exposed three common risks: subnet IP exhaustion, missing identity permissions and inaccessible private API endpoints.

**Mission:** understand AKS architecture, design the Azure landing-zone dependencies, prepare a secure provisioning configuration, validate cluster access and node readiness, and document production acceptance criteria.

**Safety:** AKS cluster creation can incur charges for VM scale sets, disks, public IPs, NAT gateways, load balancers, monitoring and optional cluster tiers. Never run provisioning commands outside an approved staging subscription and budget. All labs distinguish read-only inspection from mutating operations.

### Learning outcomes

1. Explain AKS control plane, node pools and shared responsibilities.
2. Design Azure VNet, subnet, IP allocation and private API access.
3. Compare Azure CNI Overlay and VNet-based Pod addressing.
4. Understand managed identities, Microsoft Entra and Kubernetes/Azure RBAC.
5. Plan system and user node pools and zone distribution.
6. Provision an approved staging cluster with Azure CLI or Terraform.
7. Configure kubeconfig and kubelogin safely.
8. Validate CoreDNS, networking, ingress and CSI storage.
9. Design Azure Monitor, logging, alerting and upgrade ownership.
10. Produce an operational readiness checklist and cost-aware cleanup plan.

## 2. AKS architecture and shared responsibility

```text
Azure-managed AKS control plane
+------------------------------------------------+
| Kubernetes API server / scheduler / controllers |
| Managed etcd and control-plane infrastructure  |
+-----------------------+------------------------+
                        |
            Private/public API endpoint
                        |
Customer Azure subscription / resource group
+------------------------------------------------+
| Azure VNet / subnets / NSGs / routes / DNS      |
| VM Scale Sets / system and user node pools     |
| Azure CNI / CoreDNS / kube-proxy or dataplane  |
| Azure Disk CSI / Azure Files CSI               |
| Ingress / app workloads / stateful services    |
+------------------------------------------------+
                        |
         Entra ID / managed identity / Key Vault
                        |
          Azure Monitor / Log Analytics / Backup
```

Microsoft operates the AKS managed control plane; customers own workload security, node pool configuration, networking, identity assignments, application lifecycle, data protection, monitoring, capacity and upgrade coordination. Managed AKS does not automatically guarantee application high availability or database recovery.

### Cluster and node resource groups

An AKS cluster has a user-managed resource group containing the cluster resource and a **node resource group** containing AKS-managed infrastructure such as VM scale sets and networking resources. Avoid directly editing AKS-managed resources in the node resource group unless Azure documentation explicitly supports the change.

## 3. Lab 1 — Verify Azure identity, subscription and tools

```powershell
az version
kubectl version --client
az login
az account list --output table
$subscription = 'REPLACE_WITH_APPROVED_SUBSCRIPTION_ID'
az account set --subscription $subscription
az account show --query '{Name:name,Id:id,Tenant:tenantId}' --output json
```

For organizations using SSO or device login, follow approved authentication policies. Avoid exporting long-lived credentials into scripts.

**Stop if** the subscription or tenant is not approved. Document the signed-in principal, subscription, tenant and environment before any deployment.

## 4. Lab 2 — Inventory existing AKS clusters and networking

```powershell
$location = 'eastus'
$resourceGroup = 'REPLACE_WITH_STAGING_RESOURCE_GROUP'
$cluster = 'REPLACE_WITH_STAGING_AKS_CLUSTER'
az aks list --subscription $subscription --output table
az network vnet list --subscription $subscription --output table
az network nsg list --subscription $subscription --output table
az group show --name $resourceGroup --subscription $subscription --query '{Name:name,Location:location,Id:id}' --output json
```

If the staging resource group does not yet exist, record it as Planned and do not execute `az group show` as evidence of deployment.

### Architecture worksheet

```text
Subscription and tenant:
Region / availability zones:
AKS resource group:
AKS node resource group:
VNet ID and CIDR:
Node subnet IDs and IP headroom:
Pod network mode and CIDR:
Service CIDR and DNS service IP:
API endpoint public/private:
Private DNS design:
Outbound egress method:
System node pool size and zones:
User node pool requirements:
Managed identities:
Entra/RBAC ownership:
Log Analytics workspace:
Key Vault/KMS-equivalent requirements:
Cost owner and tags:
```

## 5. Lab 3 — Design VNet, subnet and Pod IP capacity

AKS networking choices materially affect IP consumption, security and routing.

### Networking options

| Design | Pod addressing | Operational consideration |
|---|---|---|
| Azure CNI Overlay | Pods use overlay CIDR distinct from VNet | Conserves VNet subnet IPs; requires correct routing/egress design |
| Azure CNI Pod Subnet | Pods receive addresses from delegated Pod subnet | Direct VNet IP consumption; subnet sizing matters |
| Other supported Azure CNI/dataplane configurations | Varies by cluster mode | Validate current support and limitations |

Azure CNI Overlay and Azure CNI Pod Subnet are not interchangeable after deployment without migration planning. Confirm compatibility with network policies, ingress, service mesh, private endpoints and on-premises routing.

### IP planning

```text
Maximum system nodes:
Maximum user nodes:
Max Pods per node:
Node IP requirements:
Pod IP requirements by network mode:
Upgrade surge nodes:
Zone failure headroom:
Private endpoint IPs:
Load balancer/frontend IPs:
Subnet free IP reserve:
CIDR overlap with VPN/ExpressRoute:
```

```powershell
az network vnet list --resource-group $resourceGroup --output table
az network vnet subnet list --resource-group $resourceGroup --vnet-name REPLACE_WITH_VNET --output table
```

**Expected:** VNet/subnet and Pod CIDRs are approved and do not overlap with connected networks.

## 6. Lab 4 — Private cluster and API endpoint design

AKS supports private cluster configurations and controlled public API exposure. The choice changes operator connectivity, DNS requirements and CI/CD deployment paths.

### Private API acceptance

1. Private DNS resolution from approved operator networks.
2. VPN, ExpressRoute, peered VNet or approved jump-host connectivity.
3. NSG, firewall and route-table rules for required traffic.
4. Azure CLI and kubelogin access to the API.
5. Recovery path if corporate network access is unavailable.
6. Documented DNS and identity ownership.

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{Name:name,PrivateFqdn:privateFqdn,ApiServerAccessProfile:apiServerAccessProfile,NetworkProfile:networkProfile}' --output json
```

This command applies to an existing cluster. Do not assume private endpoint connectivity from an arbitrary public workstation.

## 7. Lab 5 — Understand Microsoft Entra, Azure RBAC and managed identities

### Permission layers

1. **Azure RBAC:** permission to manage Azure AKS resources, VNet, identities and disks.
2. **AKS authentication:** Microsoft Entra integration and kubeconfig token acquisition.
3. **Kubernetes authorization:** Kubernetes RBAC or Azure RBAC for Kubernetes Authorization, depending on cluster setup.
4. **Workload identity:** federated identity credentials and managed identity for Pod access to Azure APIs.

An Azure subscription Owner role does not necessarily grant all Kubernetes API permissions under every AKS authorization configuration.

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{Identity:identity,AadProfile:aadProfile,EnableRbac:enableRbac,OidcIssuer:oidcIssuerProfile,WorkloadIdentity:securityProfile.workloadIdentity}' --output json
az role assignment list --scope REPLACE_WITH_AKS_RESOURCE_ID --output table
```

### Identity design

- Prefer Microsoft Entra groups over individual access grants.
- Use short-lived credentials and approved Conditional Access.
- Separate cluster administration from application deployment.
- Use workload identity rather than embedding client secrets in Pods.
- Scope managed identities to required Key Vault, Storage or other resources.
- Record break-glass access and audit ownership.

## 8. Lab 6 — Plan system and user node pools

AKS distinguishes **system node pools** intended for critical system Pods and **user node pools** for application workloads.

| Node pool | Primary responsibility | Design considerations |
|---|---|---|
| System | CoreDNS and critical system services | Reliable On-Demand capacity, size and availability |
| User/general | Stateless applications | Autoscaling, AZ spread, requests |
| User/stateful | Databases and stateful workloads | Storage topology, graceful disruption |
| User/Spot | Interruption-tolerant batch | Eviction, retry and cost |
| User/GPU | ML and GPU inference | GPU drivers, quotas and taints |

```powershell
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --output table
kubectl get nodes -L agentpool,topology.kubernetes.io/zone -o wide
kubectl get pdb -A
```

**Expected:** node pool ownership, min/max bounds, VM size, zone coverage, OS image and upgrade settings are recorded.

## 9. Lab 7 — Prepare Azure CLI provisioning configuration

**Staging-only template.** The following illustrates a cluster using Azure CNI Overlay and a system node pool. Do not run without approved networking, quotas, role assignments, budget and Azure CLI version checks.

```powershell
$resourceGroup = 'rg-ch081-aks-staging'
$cluster = 'aks-ch081-staging'
$location = 'eastus'
$nodeSubnetId = 'REPLACE_WITH_APPROVED_NODE_SUBNET_RESOURCE_ID'
$kubernetesVersion = 'REPLACE_WITH_SUPPORTED_AKS_VERSION'
$sshKey = 'REPLACE_WITH_APPROVED_SSH_PUBLIC_KEY_PATH'
```

### Provisioning command template

```powershell
az aks create `
  --resource-group $resourceGroup `
  --name $cluster `
  --location $location `
  --kubernetes-version $kubernetesVersion `
  --node-count 2 `
  --node-vm-size Standard_D4s_v5 `
  --network-plugin azure `
  --network-plugin-mode overlay `
  --vnet-subnet-id $nodeSubnetId `
  --enable-managed-identity `
  --enable-aad `
  --enable-azure-rbac `
  --ssh-key-value $sshKey `
  --generate-ssh-keys
```

This is a **review template**, not a universal production command. Verify current CLI flags, supported Kubernetes versions, SSH policy, identity role assignments, private endpoint requirements, monitoring, zones, node OS, egress, service CIDR and cost before execution. The supplied SSH key path and `--generate-ssh-keys` are alternative key-management approaches; choose one approved method rather than relying on both.

### Mandatory preflight

- Resource group exists and is approved.
- VNet/subnet ID is correct.
- Cluster identity can join/manage the subnet.
- Azure provider registration and quotas are satisfied.
- Network and Service CIDRs do not overlap.
- AKS version and VM SKU are available in the region.
- Cost estimate and teardown plan are approved.
- Security and network teams sign off.

## 10. Lab 8 — Infrastructure as Code governance

Terraform, Bicep or ARM can manage AKS resources. Select one system of record per resource to avoid unmanaged drift.

### IaC review checklist

```text
Subscription/tenant/provider pinned:
Region and availability zones:
VNet/subnet and outbound design:
AKS version and SKU/tier:
Managed identities and role assignments:
System and user node pools:
Autoscaler min/max:
Private API and DNS:
Azure RBAC / Entra integration:
Workload identity / OIDC issuer:
CSI and storage classes:
Azure Monitor / Log Analytics:
Key Vault integration:
Tags, budgets and policy:
State encryption and locking:
Plan approval and rollback:
```

```powershell
terraform fmt -check
terraform validate
terraform plan -out=ch081.plan
terraform show ch081.plan
```

These commands require a real initialized Terraform project. Do not commit state files, secrets or sensitive plan output.

## 11. Lab 9 — Configure kubectl and kubelogin

For an existing approved cluster:

```powershell
az account show --query '{Name:name,Id:id}'
az aks get-credentials --resource-group $resourceGroup --name $cluster --overwrite-existing
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A
```

For Entra-integrated clusters, the kubeconfig may require `kubelogin` and the appropriate Azure CLI login method:

```powershell
kubelogin --version
kubelogin convert-kubeconfig -l azurecli
kubectl auth can-i get pods --all-namespaces
```

`--overwrite-existing` can replace a kubeconfig entry. Back up kubeconfig and verify context before running. AKS local accounts may be disabled, so do not depend on `--admin` credentials as a workaround.

**Expected:** authentication and Kubernetes authorization work through approved identity, and the current context is the intended staging cluster.

## 12. Lab 10 — Validate cluster networking and add-ons

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{Network:networkProfile,Addons:addonProfiles}' --output json
kubectl -n kube-system get deployments,daemonsets
kubectl -n kube-system get service kube-dns
kubectl get services -A
kubectl get endpointslices -A
kubectl get csidrivers
kubectl get storageclasses
```

### Validation gates

1. CoreDNS Pods Ready and distributed.
2. CNI Pods/dataplane healthy.
3. Nodes have correct Pod CIDRs and zone labels.
4. ClusterIP service routing works.
5. Private DNS and egress function as designed.
6. Azure Disk/Files CSI drivers are present when required.
7. Network policy enforcement is tested, not assumed.

## 13. Lab 11 — Deploy an isolated application smoke test

Save `ch081-smoke.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch081
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch081
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
  namespace: ch081
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch081-smoke.yaml
kubectl -n ch081 rollout status deployment/web --timeout=180s
kubectl -n ch081 get pods,services,endpointslices -o wide
kubectl -n ch081 get events --sort-by=.lastTimestamp
```

**Expected:** two Ready Pods and an internal Service. No public Azure load balancer is created by this ClusterIP test.

## 14. Lab 12 — Validate storage, monitoring and security baseline

```powershell
kubectl get csidrivers
kubectl get storageclasses -o yaml
kubectl get pvc -A
kubectl get pv
kubectl get networkpolicies -A
kubectl get rolebindings -A
kubectl get clusterrolebindings
az aks show --resource-group $resourceGroup --name $cluster --query '{Monitoring:addonProfiles.omsagent,Identity:identity,Security:securityProfile}' --output json
```

### Storage design

- Azure Disk CSI for block storage and typical ReadWriteOnce workloads.
- Azure Files CSI for shared filesystem use cases.
- Disk zone topology, snapshots and encryption.
- StorageClass reclaim policies and retention.
- Database-consistent backup procedures independent of CSI snapshots.
- Appropriate Key Vault/managed identity permissions.

### Monitoring design

- Azure Monitor/Container Insights or approved Prometheus/Grafana stack.
- Node Ready, CPU/memory and Pod restart signals.
- API availability and application SLOs.
- CNI/IP capacity, CoreDNS and ingress health.
- Disk attachment and storage latency.
- Azure Activity Logs and Kubernetes audit logs.
- Azure Cost Management and budget alerts.

**Expected:** storage, identity, monitoring and audit dependencies have named owners.

## 15. Lab 13 — Provisioning failure tabletop

**Scenario:** a newly created AKS cluster has a healthy control plane, but nodes cannot join, kubectl cannot reach the private API endpoint, and an application PVC remains Pending.

### Investigation sequence

1. Verify subscription, region and cluster provisioning state.
2. Check managed identity permissions on VNet/subnet.
3. Inspect VMSS instance health and node bootstrap.
4. Validate NSGs, UDRs, NAT/firewall and outbound access.
5. Confirm private DNS zone linkage and operator network path.
6. Review node subnet free IPs and Pod IP model.
7. Inspect Kubernetes Events, CSI driver and StorageClass.
8. Verify Azure Disk topology and managed identity permissions.
9. Confirm quota, VM SKU availability and AZ restrictions.
10. Document safe remediation, rollback and cost impact.

**Expected:** distinguish identity, networking, node provisioning and storage failures without rebuilding the cluster blindly.

## 16. Production provisioning runbook

### Pre-change

1. Approve architecture, subscription, region and cost.
2. Review VNet, subnet, CIDR and private API design.
3. Confirm Entra, Azure RBAC and managed identity ownership.
4. Pin Kubernetes version, node images and add-on versions.
5. Confirm system/user node pools and autoscaling bounds.
6. Validate backup, observability and DR requirements.
7. Review IaC plan and change rollback constraints.

### Provision

1. Confirm Azure subscription and authenticated principal.
2. Apply approved IaC or Azure CLI configuration.
3. Verify cluster provisioning state and API endpoint.
4. Validate system node pool and Kubernetes add-ons.
5. Configure approved kubeconfig and kubelogin.
6. Verify workload identity, storage and network controls.
7. Run staging smoke tests and collect evidence.

### Handover

1. Record resource group, node resource group and ownership.
2. Register dashboards, alerts and on-call escalation.
3. Establish Kubernetes/AKS upgrade lifecycle review.
4. Validate data backup and disaster recovery.
5. Review cost, capacity and policy compliance.
6. Obtain application, platform and security acceptance.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| AKS creation fails | Permissions, quota, VNet | Azure Activity Log, AKS operations |
| Private API unreachable | DNS, route, VPN/ExpressRoute | Private DNS and connectivity |
| kubectl Unauthorized | Entra token/kubelogin | az account, kubeconfig |
| kubectl Forbidden | Azure RBAC/Kubernetes RBAC | Role assignments and auth checks |
| Nodes NotReady | VMSS, subnet, outbound network | Node conditions, VMSS health |
| Pods Pending | Resources, taints, Pod IP capacity | Scheduler Events |
| DNS failure | CoreDNS, CNI, VNet DNS | CoreDNS logs and routes |
| PVC Pending | CSI, StorageClass, identity | PVC Events, CSI logs |
| LoadBalancer Pending | Azure identity, subnet, quota | Service Events, Azure LB |
| Unexpected charges | VMSS, disks, NAT, logs | Cost Management and tags |

## 18. Cleanup and cost safeguards

For the approved smoke-test namespace:

```powershell
kubectl config current-context
kubectl -n ch081 get deployments,pods,services
kubectl delete namespace ch081
```

**Do not automatically delete an AKS cluster, node resource group, VNet, managed identity, disks, private DNS zones or shared resources.** A lab-owned cluster may be decommissioned only under an approved teardown plan that accounts for PV reclaim policies, retained disks, load balancers, Log Analytics, snapshots and residual charges.

## 19. Chapter acceptance checklist

- [ ] Subscription, tenant and authenticated principal verified.
- [ ] AKS control-plane and node responsibilities documented.
- [ ] Resource group and node resource group design understood.
- [ ] VNet/subnet, Pod CIDR and upgrade surge capacity planned.
- [ ] Private/public API access and DNS paths reviewed.
- [ ] Microsoft Entra, Azure RBAC and workload identity mapped.
- [ ] System/user node pool design and availability documented.
- [ ] Azure CLI provisioning plan reviewed or marked Not run.
- [ ] IaC plan and drift governance reviewed.
- [ ] kubelogin and kubeconfig access validated or marked Not run.
- [ ] CNI, CoreDNS, Services and CSI checked.
- [ ] Application smoke test completed or marked Not run.
- [ ] Storage, monitoring, security and cost controls reviewed.
- [ ] Provisioning failure tabletop completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Azure Kubernetes Service Documentation](https://learn.microsoft.com/en-us/azure/aks/)
- [AKS Concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-clusters-workloads)
- [AKS Networking Concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-network)
- [Azure CNI Overlay](https://learn.microsoft.com/en-us/azure/aks/azure-cni-overlay)
- [AKS Private Clusters](https://learn.microsoft.com/en-us/azure/aks/private-clusters)
- [AKS Managed Identities](https://learn.microsoft.com/en-us/azure/aks/use-managed-identity)
- [AKS Microsoft Entra Integration](https://learn.microsoft.com/en-us/azure/aks/enable-authentication-microsoft-entra-id)
- [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [AKS Node Pools](https://learn.microsoft.com/en-us/azure/aks/use-multiple-node-pools)
- [AKS Storage Concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-storage)
- [Azure CLI AKS Reference](https://learn.microsoft.com/en-us/cli/azure/aks)
- [kubelogin](https://azure.github.io/kubelogin/)

**Next:** Chapter 082 — AKS Node Pools and Autoscaling.
