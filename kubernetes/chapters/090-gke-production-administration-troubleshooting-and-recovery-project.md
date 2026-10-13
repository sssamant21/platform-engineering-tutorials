# Chapter 090 — GKE Production Administration, Troubleshooting and Recovery Project

**Track:** Kubernetes Administration · **Part 18 — Google Kubernetes Engine (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, GKE platform, networking, security, application and FinOps engineers  
**Prerequisites:** Chapters 086–089, earlier Kubernetes incident/DR labs, Google Cloud CLI, gke-gcloud-auth-plugin, kubectl and Windows PowerShell; approved GKE staging project

## 1. Capstone mission

A production-like GKE platform runs a customer-facing API, a background worker and a stateful component. During a simulated peak event, requests return HTTP 503, HPA requests additional replicas, new Pods remain Pending, a private backend is unreachable over hybrid networking, and a zonal Persistent Disk cannot attach to a replacement Pod. Meanwhile, an application identity loses Secret Manager access and an upgrade window is approaching.

**Mission:** perform a coordinated GKE operational assessment, isolate failures by domain, demonstrate safe staging recovery and deliver an evidence-based reliability acceptance report.

**Safety:** all commands are read-only unless explicitly labeled as approved staging changes. No production cluster upgrades, force drains, IAM grants, firewall edits, disk detachments, destructive chaos tests or cross-region cutovers. A tabletop does not constitute a validated recovery test.

### Learning outcomes

1. Validate Google Cloud project, GKE cluster and kubeconfig identity.
2. Review Standard/Autopilot architecture and node capacity.
3. Diagnose scheduling, HPA and autoscaling constraints.
4. Verify VPC-native Pod/Service networking and private connectivity.
5. Inspect ingress, load balancing and health checks.
6. Validate Persistent Disk/Filestore CSI and data integrity.
7. Audit IAM, Kubernetes RBAC and Workload Identity Federation.
8. Verify Cloud Logging, Monitoring, alerts and SLOs.
9. Execute controlled incident simulations and tabletop recovery.
10. Prepare upgrades, DR, cost and operational handover.

## 2. Reference architecture

```text
                   Public / corporate clients
                              |
                       DNS / TLS / WAF
                              |
                 Google Cloud Load Balancing
                              |
                  Ingress / Gateway / Service
                              |
     +---------------- GKE regional cluster ----------------+
     |                                                       |
     |  Managed control plane (Google)                       |
     |                                                       |
     |  Standard node pools OR Autopilot-managed capacity     |
     |   API replicas / workers / stateful Pods              |
     |                                                       |
     |  VPC-native Pod and Service ranges                    |
     |  kube-dns / dataplane / NetworkPolicy                 |
     |  Persistent Disk CSI / Filestore CSI                  |
     +-------------------------------------------------------+
           |                  |                    |
    VPC / Cloud NAT      Secret Manager      Cloud Monitoring
    VPN / Interconnect   Workload Identity   Logging / Audit
           |                  |                    |
      Private services      IAM/RBAC          On-call / SLO
```

GKE manages its control plane. The platform team still owns application availability, Kubernetes access, VPC and data protection configuration, cost, observability and operational recovery.

## 3. Exercise charter and safety gates

| Role | Responsibility |
|---|---|
| Incident commander | Severity, communications and decision log |
| GKE platform SRE | Cluster, nodes, scheduling and upgrades |
| Network engineer | VPC, DNS, load balancers and hybrid routes |
| DBRE/storage owner | CSI, backup and data integrity |
| Security engineer | IAM, RBAC, workload identity and audit |
| Application owner | Synthetic checks and customer SLIs |
| FinOps owner | Quotas, resource cost and budget |
| Observer | Evidence, timestamps and scoring |

### Illustrative acceptance targets

| Objective | Example target |
|---|---|
| Availability | 99.9% monthly SLO |
| Incident detection | Within 5 minutes |
| Staging restoration | Within 30 minutes |
| Data integrity | Exact checksum match |
| Node readiness | No unexplained NotReady nodes |
| Pending Pods | No unexplained sustained Pending Pods |
| Privilege | Least privilege and auditable changes |
| Cost | Within approved staging budget |

Targets are examples and must not be reported as measured achievements.

**Stop conditions:** wrong project/context, missing change approval, unexpected production risk, missing backups, unknown PVC reclaim policy, inadequate budget/quota or loss of break-glass access.

## 4. Lab 1 — Verify project, identity and cluster

```powershell
$ErrorActionPreference = 'Stop'
$project = 'REPLACE_WITH_APPROVED_STAGING_PROJECT'
$location = 'us-central1'
$cluster = 'REPLACE_WITH_APPROVED_GKE_CLUSTER'
gcloud config set project $project
gcloud auth list
gcloud config get-value project
gcloud projects describe $project --format='table(projectId,lifecycleState)'
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(name,location,autopilot,currentMasterVersion,releaseChannel,network,subnetwork,ipAllocationPolicy)'
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
```

**Expected:** verified project, identity, cluster, mode, release channel and context. Use actual regional or zonal location.

## 5. Lab 2 — Inventory Standard/Autopilot capacity

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(autopilot,autoscaling,releaseChannel)'
gcloud container node-pools list --cluster $cluster --location $location --project $project
kubectl get nodes -L cloud.google.com/gke-nodepool,topology.kubernetes.io/zone
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get pdb -A
kubectl top nodes
```

Autopilot does not expose customer-managed node pools like Standard; record Not applicable for Standard-specific operations. `kubectl top` requires a working metrics source.

### Capacity worksheet

```text
Cluster mode:
Region/zones:
Standard pool count/SKU/autoscaler bounds:
Autopilot workload classes/constraints:
Node allocatable CPU/memory:
Pod requests and limits:
Spot capacity and fallback:
VM quota and Pod secondary IP headroom:
PDB and upgrade surge headroom:
Peak traffic capacity target:
```

**Expected:** capacity risks with owners and approved mitigation paths.

## 6. Lab 3 — VPC-native networking and DNS assessment

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(network,subnetwork,ipAllocationPolicy,privateClusterConfig,networkPolicy,datapathProvider)'
gcloud compute networks subnets list --project $project --format='table(name,region,ipCidrRange,secondaryIpRanges)'
gcloud compute firewall-rules list --project $project --format='table(name,network,direction,disabled)'
kubectl -n kube-system get services
kubectl get services -A
kubectl get endpointslices -A
```

### Network acceptance

1. Node primary, Pod and Service secondary ranges documented.
2. IP capacity supports autoscaling and upgrade surge.
3. DNS and Service endpoints healthy.
4. Dataplane/NetworkPolicy enforcement understood.
5. Cloud NAT, Private Google Access and egress reviewed.
6. VPN/Interconnect and private DNS dependencies documented.
7. Private control-plane endpoint access approved and tested.

## 7. Lab 4 — Deploy an isolated staging application

Save `ch090-app.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch090
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: web
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
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch090
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web
  namespace: ch090
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```

```powershell
kubectl apply -f .\ch090-app.yaml
kubectl -n ch090 rollout status deployment/web --timeout=300s
kubectl -n ch090 get pods,services,endpointslices,pdb -o wide
kubectl -n ch090 get events --sort-by=.lastTimestamp
```

**Expected:** three Ready Pods, populated EndpointSlices and a PDB. `ScheduleAnyway` is a soft spread preference; do not claim it proves multi-zone placement.

## 8. Lab 5 — HPA and scheduling review

Save `ch090-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
  namespace: ch090
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 3
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
```

```powershell
kubectl apply -f .\ch090-hpa.yaml
kubectl -n ch090 get hpa
kubectl -n ch090 describe hpa web
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

HPA requires CPU metrics; this exercise does not generate load. The absence of scale-up is not failure.

### Scheduling incident classification

- Insufficient requested CPU/memory.
- Taints, selectors, affinity or topology constraints.
- Standard autoscaler bounds or Autopilot admission restrictions.
- VM quota, regional capacity or Pod IP exhaustion.
- Persistent Disk topology mismatch.
- ResourceQuota or LimitRange.

## 9. Lab 6 — Ingress and load balancer review

```powershell
kubectl get ingressclasses
kubectl get ingress -A
kubectl get gatewayclasses
kubectl get gateways -A
kubectl get services -A
```

Gateway API CRDs may not be installed; record Not installed if unavailable.

### Acceptance gates

- External versus internal exposure approved.
- TLS, DNS and certificate ownership documented.
- Backend health and readiness probes validated.
- Firewall and hybrid routing reviewed.
- Cloud Armor/WAF reviewed where applicable.
- 4xx/5xx and backend health dashboards available.
- No unapproved billable load balancer created for the lab.

## 10. Lab 7 — Persistent Disk CSI and integrity smoke test

```powershell
kubectl get csidrivers
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
kubectl get nodes -L topology.kubernetes.io/zone
```

**Approved staging only:** save `ch090-pd.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: ch090
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
  name: data-check
  namespace: ch090
spec:
  containers:
    - name: check
      image: busybox:1.36
      command:
        - /bin/sh
        - -c
        - |
          if [ ! -f /data/checkpoint ]; then
            echo ch090-gke-integrity > /data/checkpoint
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
kubectl apply -f .\ch090-pd.yaml
kubectl -n ch090 get pvc,pods -o wide
kubectl -n ch090 wait --for=condition=Ready pod/data-check --timeout=300s
kubectl -n ch090 exec data-check -- sha256sum /data/checkpoint
```

**Expected:** Bound PVC, Ready Pod and recorded checksum. This is not a database-consistent backup or restore validation.

## 11. Lab 8 — IAM, RBAC and Workload Identity Federation

```powershell
gcloud projects get-iam-policy $project --format=json
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(workloadIdentityConfig,securityPostureConfig)'
kubectl get clusterrolebindings
kubectl get rolebindings -A
kubectl get serviceaccounts -A
gcloud secrets list --project $project
```

### Identity acceptance

1. Human Google Cloud IAM and Kubernetes RBAC mapped.
2. Break-glass and cluster-admin access controlled.
3. Workload Identity Federation principal/namespace bindings verified.
4. Secret Manager permissions scoped to resources.
5. No long-lived service account keys embedded in Pods.
6. Audit events available for privilege changes.
7. Negative authorization tests documented.

Do not print secret values or change shared IAM bindings during the lab.

## 12. Lab 9 — Logging, monitoring and SLO baseline

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(loggingConfig,monitoringConfig)'
gcloud logging read 'resource.type="k8s_cluster"' --project $project --limit 20 --format=json
kubectl get nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

### Monitoring scorecard

| Domain | Signal | Owner |
|---|---|---|
| Application | Availability, 5xx, latency | App/SRE |
| Nodes | Ready, pressure, CPU/memory | Platform |
| Scheduling | Pending Pods, autoscaler capacity | Platform |
| Network | DNS, load balancer backend health | Network |
| Storage | PVC/CSI errors, backup freshness | DBRE |
| Security | IAM changes, access denials | Security |
| Cost | VM, disk, NAT, LB, logging | FinOps |

**Expected:** actionable alerts, dashboard links, thresholds, on-call owner and runbook per critical signal.

## 13. Lab 10 — Multi-domain incident tabletop

**Injects (no destructive changes):**

| Inject | Expected diagnosis |
|---|---|
| HPA increases desired replicas | Application load versus metrics |
| Pods Pending at capacity | Autoscaler, quota, IPs, topology |
| Internal LB unreachable | Firewall, routes, hybrid DNS |
| Service 503 | Backend readiness and EndpointSlices |
| Persistent Disk cannot attach | Zonal PV/node mismatch |
| Secret Manager AccessDenied | Workload identity/IAM |
| Admission webhook rejects Pods | Policy, TLS, compatibility |
| Node upgrade stalled | PDB, quota, surge and API changes |

### Incident command sequence

1. Declare severity and start UTC timeline.
2. Identify customer symptoms and SLO impact.
3. Verify Google Cloud project and kubeconfig context.
4. Separate network, scheduling, storage and identity failures.
5. Capture Events, cloud operations, metrics and logs.
6. Select approved reversible remediation.
7. Validate application recovery and data integrity.
8. Publish RCA, contributing factors and preventive work.

## 14. Lab 11 — GKE upgrade readiness

```powershell
gcloud container clusters describe $cluster --location $location --project $project --format='yaml(currentMasterVersion,releaseChannel,maintenancePolicy,autopilot)'
gcloud container node-pools list --cluster $cluster --location $location --project $project
kubectl get pdb -A
kubectl get apiservices
kubectl get crds
```

### Upgrade gates

- Supported target and release-channel policy.
- Deprecated API and webhook compatibility.
- Dataplane, CSI, ingress and observability agent readiness.
- Standard node pool surge/blue-green capacity as applicable.
- Autopilot workload and admission compatibility.
- VM quota and secondary IP headroom.
- PDB, StatefulSet and storage topology review.
- Backup, synthetic tests and change window.
- Recovery plan acknowledging control-plane downgrade limitations.

**Expected:** staged change plan; no upgrade executed.

## 15. Lab 12 — DR, data recovery and failure-domain tabletop

### Recovery design

1. Define application and database RPO/RTO.
2. Inventory backup tools, retention and restore owners.
3. Verify Persistent Disk snapshots and application-consistent backup methods.
4. Document zonal/regional storage recovery choices.
5. Plan replacement cluster, VPC, IAM and secret dependencies.
6. Confirm image/artifact registry availability.
7. Establish database writer fencing and cutover authority.
8. Rehearse restore in isolated approved staging.
9. Measure recovery and validate application integrity.

**Expected:** DR readiness record with Not tested clearly distinguished from Passed.

## 16. Lab 13 — Cost, quota and capacity acceptance

```text
GKE Standard or Autopilot mode:
Regional/zonal footprint:
Node VM / Autopilot workload cost:
Spot use and on-demand fallback:
Pod IP range and node headroom:
Upgrade surge capacity:
Load balancing and egress:
Persistent Disk/Filestore and snapshots:
Cloud NAT / VPN / Interconnect:
Logging, Monitoring and Prometheus:
Secret Manager and backup:
Budget threshold and owner:
```

### FinOps questions

- Are requests sized from measured usage and SLOs?
- Are Standard pools bounded and appropriately scaled?
- Are Autopilot resource constraints reflected in cost forecasts?
- Are orphaned disks, load balancers and logs reviewed?
- Is there budget headroom for zone failure and upgrades?
- Does every resource have a service and cost owner?

## 17. Lab 14 — Final operational handover

### Evidence template

```text
Google Cloud project / billing owner:
GKE cluster / location / mode:
Architecture and VPC diagram:
Node capacity / autoscaler bounds:
Pod and Service secondary ranges:
Ingress/LB and DNS:
StorageClasses, PV/PVC and backups:
IAM / Kubernetes RBAC / Workload Identity:
Secret Manager controls:
Cloud Logging / Monitoring / alerts:
Application SLIs/SLOs:
Incident timeline and fault tree:
Upgrade readiness and blockers:
DR RPO/RTO and drill evidence:
Cost forecast and budget:
Known risks, owners and deadlines:
On-call and escalation:
Independent technical reviewer:
Outcome: Pass / Fail / Not run
```

### Scoring rubric

| Domain | Weight |
|---|---:|
| Identity and architecture | 10% |
| Capacity and scheduling | 15% |
| Networking and load balancing | 15% |
| Storage and data integrity | 15% |
| Security and workload identity | 15% |
| Monitoring and incident response | 15% |
| Upgrade, DR and FinOps | 15% |

Scores require evidence. Critical data integrity, security or unauthorized-access failures block an overall Pass regardless of weighted score.

## 18. Production runbooks

### A. Pending Pods during load

1. Inspect scheduler Events and Pod requests.
2. Review HPA desired/current replicas.
3. Check Standard pool limits or Autopilot constraints.
4. Inspect VM quota, Pod IP capacity and topology.
5. Apply approved scaling or scheduling changes.
6. Confirm application SLIs and cost recovery.

### B. Internal load balancer outage

1. Confirm frontend, backend health and ready EndpointSlices.
2. Inspect VPC firewall and hybrid routes.
3. Verify private DNS and TLS configuration.
4. Check NetworkPolicy and dataplane enforcement.
5. Run approved client connectivity tests.
6. Confirm 5xx recovery.

### C. Persistent Disk attach failure

1. Inspect PVC/PV/Pod Events and VolumeAttachments.
2. Check disk/node zones and CSI driver.
3. Verify attachment limits and IAM.
4. Avoid force-detaching an active stateful volume.
5. Execute approved rescheduling or restore.
6. Validate filesystem and database consistency.

### D. Workload identity authorization failure

1. Verify namespace and Kubernetes service account.
2. Inspect Workload Identity Federation pool and IAM binding.
3. Check Secret Manager resource-level permissions.
4. Validate DNS/network path to Google APIs.
5. Review audit logs without exposing secrets.
6. Confirm restored least-privilege access.

## 19. Troubleshooting matrix

| Symptom | Domain | Evidence |
|---|---|---|
| kubectl Unauthorized/Forbidden | IAM/RBAC | gcloud identity, role bindings |
| Nodes NotReady | GKE/VM/network | Node conditions, operations |
| Pods Pending | Scheduler/autoscaler | Events, quotas, IP ranges |
| DNS timeouts | kube-dns/VPC | DNS and route evidence |
| Load balancer 503 | Backend/ingress | Health checks, endpoints |
| PVC Pending | CSI/topology | PVC Events, StorageClass |
| Disk attach conflict | Zone/attachment | PV affinity, node zone |
| Secret Manager denied | Workload identity | Principal and IAM binding |
| Upgrade blocked | PDB/API/quota | GKE operation, Events |
| Cost spike | Compute/network/storage | Billing and resource inventory |

## 20. Cleanup and safety

Before deleting lab resources:

```powershell
kubectl config current-context
kubectl -n ch090 get deployments,pods,services,hpa,pdb,pvc
kubectl get pv
```

Only with staging approval and verified reclaim policies:

```powershell
kubectl delete namespace ch090
```

Deleting PVCs may delete underlying Persistent Disks when reclaim policy is `Delete`. Do not delete shared clusters, VPCs, IAM resources, Secret Manager secrets, load balancers or backups as part of routine cleanup.

## 21. Acceptance checklist

- [ ] Charter, owners, budget and stop conditions approved.
- [ ] Project, identity, GKE cluster and kubeconfig verified.
- [ ] Standard/Autopilot and capacity inventory completed.
- [ ] VPC, secondary CIDRs and DNS inspected.
- [ ] Isolated application smoke test completed or marked Not run.
- [ ] HPA, scheduling and PDB behavior assessed.
- [ ] Ingress/load balancing architecture reviewed.
- [ ] CSI storage checksum test completed or marked Not run.
- [ ] IAM, RBAC and Workload Identity Federation audited.
- [ ] Logging, Monitoring and alert coverage reviewed.
- [ ] Multi-domain incident tabletop completed.
- [ ] Upgrade compatibility and change plan documented.
- [ ] DR dependencies and restore status recorded.
- [ ] Cost, quotas and operational owners reviewed.
- [ ] Handover report and acceptance score documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Part 18 writing milestone:** Chapters 086–090 drafted. Runtime validation and independent technical review remain pending.

## 22. References

- [GKE Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/kubernetes-engine-overview)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [GKE Standard and Autopilot](https://cloud.google.com/kubernetes-engine/docs/concepts/choose-cluster-mode)
- [GKE Cluster Autoscaler](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler)
- [GKE VPC-native Clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/alias-ips)
- [GKE Load Balancing](https://cloud.google.com/kubernetes-engine/docs/concepts/service-load-balancer)
- [GKE Persistent Storage](https://cloud.google.com/kubernetes-engine/docs/concepts/persistent-volumes)
- [GKE Workload Identity Federation](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [GKE Monitoring](https://cloud.google.com/kubernetes-engine/docs/concepts/monitoring-overview)
- [GKE Release Channels](https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels)
- [GKE Upgrades](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-upgrades)

**Next:** Chapter 091 — GitOps with Argo CD and Flux, beginning Part 19.
