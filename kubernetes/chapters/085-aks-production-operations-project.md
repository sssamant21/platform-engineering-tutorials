# Chapter 085 — AKS Production Operations Project

**Track:** Kubernetes Administration · **Part 17 — Azure Kubernetes Service (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, AKS platform, Azure networking, security and FinOps engineers  
**Prerequisites:** Chapters 081–084 and earlier Kubernetes reliability labs; Azure CLI, kubectl, Windows PowerShell, kubelogin; approved AKS staging subscription

## 1. Capstone mission and production scenario

A customer-facing application on Azure Kubernetes Service (AKS) has intermittent 5xx responses during peak batch processing. Some Pods remain Pending after autoscaling reaches a node pool limit, an internal LoadBalancer cannot be reached over ExpressRoute, and a stateful component cannot attach an Azure Disk after moving across availability zones. A security review also finds unclear Azure RBAC ownership, missing workload identity evidence, incomplete diagnostic logging and an approaching Kubernetes upgrade window.

**Mission:** operate an AKS staging cluster as a production service: establish architecture and SLO baselines, investigate network and storage failures, validate node capacity and workload identity, review monitoring and security, and deliver an evidence-based operational readiness report.

**Safety:** this is an **approved staging-only** exercise. No production node drains, firewall edits, IAM changes, forced volume detaches, destructive chaos tests or cluster upgrades. Tabletop simulations are not equivalent to tested recovery procedures.

### Capstone outcomes

1. Confirm Azure subscription, tenant, AKS cluster and kubeconfig identity.
2. Inventory AKS architecture, node pools, networking, CSI and dependencies.
3. Assess autoscaler, quota, subnet and Pod capacity.
4. Validate CNI, DNS, Service and ingress paths.
5. Test an isolated application and storage path.
6. Audit Entra ID, Azure RBAC and AKS Workload Identity.
7. Review diagnostics, monitoring, alerts and application SLOs.
8. Diagnose multi-layer incident scenarios.
9. Prepare controlled upgrade and DR readiness plans.
10. Deliver a scored operational handover with evidence and owners.

## 2. Reference production architecture

```text
                    Corporate / internet clients
                               |
                       DNS / TLS / WAF
                               |
                   App Gateway / Azure LB
                               |
                      Ingress / Service
                               |
+------------------------- AKS VNet --------------------------+
|                                                             |
|   System node pool             User node pools              |
|   CoreDNS / critical add-ons   API / batch / stateful       |
|                                                             |
|   Azure CNI Overlay or Pod Subnet / NSGs / UDRs / NAT        |
|   Azure Disk CSI / Azure Files CSI                          |
+-------------------------------------------------------------+
             |                              |
    Microsoft Entra / Key Vault      Azure Monitor / Logs
    Managed / Workload Identity      Prometheus / Grafana
             |                              |
         Azure Backup / DR       Alerts / incident response
```

Azure manages the AKS control plane. The platform team remains responsible for workload reliability, identity, VNet design, capacity, storage lifecycle, observability, application backups and recovery.

## 3. Exercise charter and stop conditions

| Role | Responsibilities |
|---|---|
| Incident commander | Severity, timeline, decisions, communications |
| Platform SRE | AKS nodes, autoscaling, add-ons |
| Network engineer | VNet, DNS, CNI, ingress and ExpressRoute |
| DBRE/storage owner | Azure Disk/Files, backups, integrity |
| Security owner | Entra, Azure RBAC, workload identity, audit |
| Application owner | Synthetic checks, SLIs, business validation |
| Observer | Evidence, timestamps, scoring and follow-ups |

### Illustrative acceptance objectives

| Objective | Example target |
|---|---|
| Application availability | 99.9% monthly SLO |
| Incident detection | Within 5 minutes |
| Staging service restoration | Within 30 minutes |
| Data integrity | Exact checksum match |
| Node readiness | No unexpected NotReady nodes |
| Pending Pods | No unexplained sustained Pending Pods |
| Unauthorized access | Denied and auditable |
| Spend | Within approved capstone budget |

These are **example targets**, not measured achievements.

### Stop conditions

- Azure subscription or Kubernetes context mismatch.
- Missing resource owner or change approval.
- Risk of production impact.
- Missing backup or data protection.
- Unknown disk/PVC reclaim policy.
- Budget or quota constraints.
- Missing security authorization for access changes.

## 4. Lab 1 — Verify Azure identity and AKS cluster baseline

```powershell
$ErrorActionPreference = 'Stop'
$subscription = 'REPLACE_WITH_APPROVED_SUBSCRIPTION_ID'
$resourceGroup = 'REPLACE_WITH_STAGING_RESOURCE_GROUP'
$cluster = 'REPLACE_WITH_STAGING_AKS_CLUSTER'
az account set --subscription $subscription
az account show --query '{Name:name,Id:id,Tenant:tenantId}' --output json
az aks show --resource-group $resourceGroup --name $cluster --query '{Name:name,Version:kubernetesVersion,Provisioning:provisioningState,NodeResourceGroup:nodeResourceGroup,Network:networkProfile,Identity:identity}' --output json
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A -o wide
```

**Expected:** verified subscription, tenant, AKS cluster, node resource group and kubeconfig context. Azure CLI identity and kubeconfig authentication identity may differ.

## 5. Lab 2 — Inventory node pools and autoscaling

```powershell
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --output table
kubectl get nodes -L agentpool,topology.kubernetes.io/zone,kubernetes.azure.com/mode
kubectl top nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get pdb -A
```

Metrics Server is required for `kubectl top`. Record Not available if absent and use approved Azure Monitor metrics instead.

### Capacity worksheet

```text
System pool count/SKU/zones:
User pool count/SKU/zones:
Autoscaler min/max:
Spot pool strategy:
CPU/memory requested and allocatable:
DaemonSet/system overhead:
Subnet free IPs / CNI mode:
VM quota and surge headroom:
Max Pods per node:
Node image/OS:
Monthly compute budget:
```

**Expected:** a specific capacity bottleneck and mitigation owner, not only average CPU utilization.

## 6. Lab 3 — Validate Azure CNI, VNet and CoreDNS

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query 'networkProfile' --output json
az network vnet list --subscription $subscription --output table
kubectl -n kube-system get deployment coredns
kubectl -n kube-system get service kube-dns
kubectl get services -A
kubectl get endpointslices -A
kubectl -n kube-system logs deployment/coredns --tail=100
```

### Network acceptance

1. Node subnet and Pod CIDR capacity documented.
2. CNI/dataplane health confirmed.
3. CoreDNS healthy and available.
4. Service endpoints reflect ready Pods.
5. NSGs/UDRs/egress ownership identified.
6. Private DNS and ExpressRoute/VPN path documented.
7. NetworkPolicy enforcement actually verified.

**Expected:** network dependency map and any connectivity gaps.

## 7. Lab 4 — Deploy a disposable staging application

Save `ch085-app.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch085
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch085
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
  namespace: ch085
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch085-app.yaml
kubectl -n ch085 rollout status deployment/web --timeout=180s
kubectl -n ch085 get pods,services,endpointslices -o wide
kubectl -n ch085 get events --sort-by=.lastTimestamp
```

**Expected:** two Ready Pods and ready Service endpoints. ClusterIP does not create an Azure load balancer.

## 8. Lab 5 — Review Azure Load Balancer and ingress

```powershell
kubectl get services -A
kubectl get ingressclasses
kubectl get ingress -A
kubectl get gatewayclasses
kubectl get gateways -A
```

Gateway API CRDs may not be installed; record Not installed rather than treating the missing resource type as a failed cluster.

### Ingress acceptance

- Internal/public exposure approved.
- Azure Load Balancer or Application Gateway ownership.
- TLS and certificate renewal.
- DNS/private DNS correctness.
- Health probes and ready endpoints.
- NSG/UDR/ExpressRoute path.
- WAF where required.
- Metrics for 4xx/5xx and unhealthy targets.
- Resource tags and cost ownership.

**Expected:** an ingress architecture and reachability checklist. No new billable load balancer is required for the capstone.

## 9. Lab 6 — Validate Azure Disk CSI and data integrity

```powershell
kubectl get csidrivers
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
kubectl get volumesnapshotclasses
```

**Approved staging only:** save `ch085-disk.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: ch085
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: REPLACE_WITH_APPROVED_AZURE_DISK_STORAGECLASS
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: data-check
  namespace: ch085
spec:
  containers:
    - name: check
      image: busybox:1.36
      command:
        - /bin/sh
        - -c
        - |
          if [ ! -f /data/checkpoint ]; then
            printf 'ch085-aks-data-checkpoint\n' > /data/checkpoint
          fi
          sleep 360000
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data
```

```powershell
kubectl apply -f .\ch085-disk.yaml
kubectl -n ch085 get pvc,pods -o wide
kubectl -n ch085 wait --for=condition=Ready pod/data-check --timeout=180s
kubectl -n ch085 exec data-check -- sha256sum /data/checkpoint
```

**Expected:** PVC Bound and checksum recorded. This is a volume smoke test, **not** a database-consistent backup. Confirm reclaim policy before cleanup.

## 10. Lab 7 — Audit Entra, Azure RBAC and workload identity

```powershell
$aksId = az aks show --resource-group $resourceGroup --name $cluster --query id --output tsv
az role assignment list --scope $aksId --output table
az aks show --resource-group $resourceGroup --name $cluster --query '{Aad:aadProfile,Identity:identity,Oidc:oidcIssuerProfile,WorkloadIdentity:securityProfile.workloadIdentity}' --output json
kubectl get clusterrolebindings
kubectl get rolebindings -A
kubectl get serviceaccounts -A
```

### Security acceptance

- Human operators use approved Entra groups.
- Azure RBAC and Kubernetes authorization model understood.
- Cluster-admin and break-glass access controlled.
- Workload Identity federation configured where required.
- Static service principal secrets minimized.
- Key Vault access least privilege.
- Audit evidence for elevated changes available.
- Pod Security and network isolation validated.

**Expected:** principal-to-role matrix and security remediation owners.

## 11. Lab 8 — Review Key Vault and secrets controls

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query 'addonProfiles.azureKeyvaultSecretsProvider' --output json
kubectl get csidrivers
kubectl get secretproviderclasses -A
```

Secrets Store CSI resources are optional. If absent, record the cluster's actual approved secret delivery pattern.

### Key Vault acceptance

1. Managed identity permissions scoped to required secrets.
2. Private endpoint and DNS connectivity validated where used.
3. Rotation and application reload behavior documented.
4. No secret material in source code or logs.
5. Access failure alerts and audit events configured.
6. Recovery owner and escalation identified.

## 12. Lab 9 — Build monitoring and incident response scorecard

```powershell
az monitor diagnostic-settings list --resource $aksId --output json
az monitor activity-log list --resource-id $aksId --max-events 20 --output json
kubectl get nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

### Observability scorecard

| Domain | Signal | Typical owner |
|---|---|---|
| Application | Error rate, latency, availability | App/SRE |
| Nodes | Ready, pressure, VMSS health | Platform |
| Scheduling | Pending duration, autoscaler limits | Platform |
| Network | CoreDNS, CNI, ingress health | Network |
| Storage | PVC Pending, CSI attach failures | DBRE |
| Identity | Authorization failures, role changes | Security |
| Cost | VMSS, disks, NAT, monitoring | FinOps |

**Expected:** each critical signal has a dashboard, alert threshold, on-call owner and runbook.

## 13. Lab 10 — Multi-layer AKS incident simulation

**Tabletop injects — no destructive changes:**

| Inject | Expected diagnosis |
|---|---|
| User pool max reached | Autoscaler bounds and quota |
| Pods Pending with free CPU | Taints, requests, topology or IP capacity |
| Internal LB unreachable | NSG, UDR, peering, ExpressRoute |
| DNS resolves but HTTP fails | Endpoint health and network path |
| Azure Disk attach fails after reschedule | Zonal disk topology |
| Pod cannot access Key Vault | Workload Identity and permissions |
| Admission webhook rejects workloads | Certificate, policy or version |
| Audit logs missing | AKS diagnostic settings |

### Incident workflow

1. Declare severity and start UTC timeline.
2. Capture customer symptoms and application SLIs.
3. Confirm Azure identity and cluster context.
4. Separate scheduling, network, storage and identity symptoms.
5. Use reversible, scoped remediations only.
6. Validate application recovery and data integrity.
7. Record RCA, contributing factors and preventive actions.

**Expected:** incident evidence and recovery decision log.

## 14. Lab 11 — AKS upgrade and maintenance readiness

```powershell
az aks show --resource-group $resourceGroup --name $cluster --query '{Version:kubernetesVersion,Provisioning:provisioningState,AutoUpgrade:autoUpgradeProfile}' --output json
az aks get-upgrades --resource-group $resourceGroup --name $cluster --output table
az aks nodepool list --resource-group $resourceGroup --cluster-name $cluster --output table
kubectl get pdb -A
kubectl get apiservices
kubectl get crds
```

### Upgrade gates

- Supported Kubernetes target and deprecated API review.
- CNI, CSI, ingress and admission webhook compatibility.
- Node pool OS/image and version strategy.
- PDB and max surge capacity.
- Azure VM quota and subnet IP headroom.
- Valid application/database backups.
- Monitoring and synthetic tests.
- Approved change window and communication plan.
- Recovery plan acknowledging control-plane downgrade limitations.

**Expected:** staged upgrade plan; no control-plane upgrade executed in this capstone.

## 15. Lab 12 — DR, backup and cost readiness

### Disaster recovery checklist

1. Confirm application-consistent backups.
2. Verify Azure Disk/Files recovery methods and retention.
3. Confirm Azure Backup or other approved backup tooling.
4. Validate cross-region Key Vault, identity and image dependencies.
5. Document VNet, private DNS and ingress recovery.
6. Define database writer fencing and cutover authority.
7. Specify RPO/RTO targets and evidence from drills.
8. Test restores in a separate approved staging environment.

### Cost worksheet

```text
AKS cluster tier/control-plane charges:
System/user VMSS compute:
Spot capacity:
Azure Disk/Files and snapshots:
Load Balancer/Application Gateway:
NAT Gateway and outbound transfer:
Azure Monitor/Log Analytics:
Key Vault/private endpoints:
Backup and DR retention:
Upgrade surge headroom:
Budget and owner:
```

**Expected:** a cost and DR readiness record with owners, not a claim that recovery was tested.

## 16. Lab 13 — Final operational handover and acceptance

### Handover template

```text
Subscription / tenant / cluster:
Resource group / node resource group:
Architecture and VNet diagram:
Node pools / autoscaler bounds:
Subnet and Pod IP capacity:
Ingress/LB and DNS ownership:
StorageClasses, PVs and backup inventory:
Entra / Azure RBAC / workload identity matrix:
Diagnostic logs and monitoring dashboards:
Application SLIs and SLO evidence:
Incident timeline and response actions:
Upgrade compatibility and maintenance plan:
DR RPO/RTO and exercise status:
Cost forecast and budget:
Known risks, owners and due dates:
On-call and escalation:
Independent technical reviewer:
Overall outcome: Pass / Fail / Not run
```

### Scoring rubric

| Domain | Weight |
|---|---:|
| Cluster identity and architecture | 10% |
| Node pools, autoscaling and capacity | 15% |
| Networking and ingress | 15% |
| Storage and data integrity | 15% |
| Identity and security | 15% |
| Monitoring and incident response | 15% |
| Upgrades, DR and cost readiness | 15% |

A score is valid only with recorded evidence. Critical data integrity or unauthorized-access failures block an overall Pass even if the weighted score is high.

## 17. Production operations runbooks

### A. Pods Pending after peak load

1. Inspect scheduler Events and Pod resource requests.
2. Check node pool autoscaler min/max and node health.
3. Review Azure VM quota and regional SKU capacity.
4. Check subnet/Pod IP headroom.
5. Review taints, affinity and PDB constraints.
6. Apply approved scaling or scheduling changes.
7. Verify SLO and cost recovery.

### B. Internal LoadBalancer unreachable

1. Confirm Service frontend IP and backend endpoints.
2. Check Azure LB probes and target health.
3. Validate NSGs, UDRs, DNS and ExpressRoute path.
4. Verify ingress/controller configuration.
5. Run approved client connectivity tests.
6. Confirm application recovery.

### C. Azure Disk attach failure

1. Inspect PVC/PV and Pod Events.
2. Confirm node/disk availability-zone topology.
3. Check CSI driver and Azure identity permissions.
4. Avoid force-detaching active stateful disks.
5. Use approved rescheduling/recovery.
6. Validate filesystem and database integrity.

### D. Key Vault authorization failure

1. Verify Pod service account and workload identity.
2. Inspect federation issuer/subject/audience.
3. Confirm managed identity and Key Vault permissions.
4. Check private endpoint/DNS/network.
5. Review audit events and CSI/provider logs.
6. Restore access using least privilege.

## 18. Troubleshooting matrix

| Symptom | Likely domain | Investigation |
|---|---|---|
| API access denied | Entra/RBAC | kubelogin, role assignments |
| Pods Pending | Scheduling/autoscaler | Events, node pools |
| Nodes NotReady | VMSS/CNI/bootstrap | Node conditions, Azure operations |
| DNS timeouts | CoreDNS/VNet | DNS logs, NSGs, routes |
| Internal LB unreachable | Network path | LB, UDR, ExpressRoute |
| PVC Pending | CSI/StorageClass | PVC Events |
| Disk attach conflict | AZ topology | PV/node zone |
| Key Vault AccessDenied | Workload identity | Federation, roles |
| Upgrade stalled | PDB/quota/webhook | AKS status, Events |
| Unexpected cost | VMSS/disks/egress/logs | Azure Cost Management |

## 19. Cleanup and safety

Before deleting lab resources, record evidence and check disk reclaim policy.

```powershell
kubectl config current-context
kubectl -n ch085 get deployments,pods,services,pvc
kubectl get pv
```

Only after approval, in the verified staging cluster:

```powershell
kubectl delete namespace ch085
```

Deleting a namespace can delete PVCs and backing disks when reclaim policy is `Delete`. Do not delete shared node pools, Azure identities, VNet resources, Key Vault, monitoring, backup infrastructure or production clusters.

## 20. Capstone acceptance checklist

- [ ] Exercise charter, owners, budget and stop conditions approved.
- [ ] Subscription, tenant, cluster and kubeconfig verified.
- [ ] Node pools and autoscaling inventory completed.
- [ ] Subnet/Pod IP capacity and quota reviewed.
- [ ] CNI, CoreDNS and Services inspected.
- [ ] Disposable application smoke test completed or marked Not run.
- [ ] Load balancer/ingress architecture reviewed.
- [ ] Azure Disk CSI checksum test completed or marked Not run.
- [ ] Entra, Azure RBAC and workload identity audited.
- [ ] Key Vault secrets delivery and rotation assessed.
- [ ] Diagnostics, dashboards, alerts and SLOs reviewed.
- [ ] Multi-layer incident tabletop documented.
- [ ] Upgrade compatibility and recovery constraints documented.
- [ ] DR readiness and cost ownership assessed.
- [ ] Handover report, score and remediation owners recorded.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Part 17 writing milestone:** Chapters 081–085 drafted. Runtime validation and independent technical review remain pending.

## 21. References

- [Azure Kubernetes Service Documentation](https://learn.microsoft.com/en-us/azure/aks/)
- [AKS Best Practices](https://learn.microsoft.com/en-us/azure/aks/best-practices)
- [AKS Node Pools](https://learn.microsoft.com/en-us/azure/aks/use-multiple-node-pools)
- [AKS Cluster Autoscaler](https://learn.microsoft.com/en-us/azure/aks/cluster-autoscaler)
- [AKS Networking](https://learn.microsoft.com/en-us/azure/aks/concepts-network)
- [AKS Internal Load Balancer](https://learn.microsoft.com/en-us/azure/aks/internal-lb)
- [AKS Storage](https://learn.microsoft.com/en-us/azure/aks/concepts-storage)
- [AKS Microsoft Entra](https://learn.microsoft.com/en-us/azure/aks/enable-authentication-microsoft-entra-id)
- [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [AKS Monitoring](https://learn.microsoft.com/en-us/azure/aks/monitor-aks)
- [AKS Upgrade](https://learn.microsoft.com/en-us/azure/aks/upgrade-aks-cluster)
- [AKS Key Vault Secrets Store CSI](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver)

**Next:** Chapter 086 — Google GKE Architecture, Control Plane and Cluster Provisioning, beginning Part 18.
