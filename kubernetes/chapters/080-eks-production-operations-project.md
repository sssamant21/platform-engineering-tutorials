# Chapter 080 — EKS Production Operations Project

**Track:** Kubernetes Administration · **Part 16 — Managed Kubernetes on AWS and Azure (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, cloud platform, security, networking and application engineering teams  
**Prerequisites:** Chapters 076–079; approved EKS staging cluster; AWS CLI v2, kubectl, Windows PowerShell; optional Karpenter, AWS Load Balancer Controller, EBS CSI and Prometheus

## 1. Capstone mission and scenario

A customer-facing application on Amazon EKS experiences intermittent 5xx errors during batch ingestion. Some Pods cannot schedule because of subnet IP pressure, a newly launched Karpenter node fails to become Ready, and a stateful component cannot attach an EBS volume in the wrong availability zone. Meanwhile, the team must verify IAM access, alert coverage, upgrade readiness, cost limits and disaster recovery procedures.

**Mission:** operate and troubleshoot an EKS staging cluster as a production platform: establish baselines, validate networking and storage, recover from simulated failures, enforce identity boundaries, measure SLIs, review capacity/cost, and produce an evidence-based readiness report.

**Safety:** this is an **approved staging-only** exercise. Do not disable production nodes, alter production security groups, modify live DNS, force-delete stateful Pods, revoke production IAM access, or upgrade production control planes. Tabletop simulations count as design exercises, not executed recovery tests.

### Capstone outcomes

1. Verify account, cluster, IAM and kubeconfig identity.
2. Inventory EKS control plane, managed nodes, Karpenter and add-ons.
3. Measure cluster capacity, Pod IP headroom and scheduling risk.
4. Validate CoreDNS, VPC CNI, Services and ingress health.
5. Test an isolated staging workload and persistent data path.
6. Audit access entries, RBAC and workload IAM.
7. Establish actionable alerts, logs and application SLIs.
8. Diagnose multi-layer incident injects without destructive changes.
9. Prepare safe upgrade and disaster recovery runbooks.
10. Produce an operational acceptance report with owners and evidence.

## 2. Reference architecture

```text
                    Clients / synthetic probes
                              |
                         Route 53 / TLS
                              |
                          ALB or NLB
                              |
                     Ingress / Services
                              |
+--------------------------- EKS VPC ----------------------------+
| Private subnets across availability zones                     |
|                                                                 |
| Managed node group (baseline)     Karpenter NodePool (elastic)  |
|   CoreDNS / controller Pods        Stateless app / batch Pods   |
|                                                                 |
| VPC CNI + kube-proxy + CSI drivers                              |
| EBS volumes (AZ scoped) / optional EFS shared storage          |
+-----------------------------------------------------------------+
                              |
           CloudWatch / Prometheus / Grafana / CloudTrail
                              |
                Backup repository / DR runbooks
```

The AWS-managed EKS control plane is not a substitute for workload backups, application monitoring, IAM governance or node lifecycle management.

## 3. Exercise charter, roles and exit criteria

| Role | Responsibilities |
|---|---|
| Incident commander | Severity, timeline, decisions and communications |
| Platform SRE | Cluster, nodes, autoscaling and add-ons |
| Network engineer | VPC, CNI, DNS, ALB/NLB and security groups |
| DBRE/storage owner | EBS/EFS, backups and data integrity |
| Security owner | IAM, RBAC, audit and KMS |
| Application owner | Synthetic transactions and SLO acceptance |
| Observer | Evidence, timestamps and scoring |

### Illustrative acceptance objectives

| Measure | Example target |
|---|---|
| API availability | 99.9% monthly SLO (organizational target required) |
| Staging incident detection | Within 5 minutes |
| Staging service restoration | Within 30 minutes |
| Stateful data integrity | Exact checksum match |
| Node readiness | No unexpected NotReady nodes |
| Pending Pods | No unexplained sustained Pending Pods |
| Unauthorized access | Denied and auditable |
| Cost | Within approved test budget |

These are example objectives, **not measured results**.

### Stop conditions

- Unexpected production account/context.
- Unknown owner of shared resource.
- Missing backup or data protection.
- Risk of destructive cloud or storage changes.
- Cloud spend approaching approved budget.
- Security approval missing for IAM/network modifications.

## 4. Lab 1 — Verify account, cluster and operational baseline

```powershell
$ErrorActionPreference = 'Stop'
$profile = 'REPLACE_WITH_APPROVED_AWS_PROFILE'
$region = 'us-east-1'
$cluster = 'REPLACE_WITH_APPROVED_STAGING_EKS_CLUSTER'
aws sts get-caller-identity --profile $profile
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Name:name,Status:status,Version:version,Endpoint:endpoint,Access:accessConfig,Logging:logging}' --output json
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A -o wide
```

**Expected:** account, region, kubeconfig and EKS cluster identities match the approved exercise charter. A profile name does not guarantee that kubeconfig uses the same AWS identity.

## 5. Lab 2 — Inventory managed nodes and Karpenter

```powershell
aws eks list-nodegroups --cluster-name $cluster --region $region --profile $profile
aws eks list-addons --cluster-name $cluster --region $region --profile $profile
kubectl get nodes -L eks.amazonaws.com/nodegroup,karpenter.sh/nodepool,topology.kubernetes.io/zone
kubectl get nodepools
kubectl get nodeclaims
kubectl get ec2nodeclasses
kubectl get pdb -A
```

Karpenter resources are optional; `the server doesn't have a resource type` means its CRDs are absent. Record Not installed instead of treating that as a broken cluster.

### Inventory

```text
Managed node groups and min/desired/max:
Karpenter NodePools, NodeClasses and limits:
On-Demand / Spot distribution:
Node versions and AMI:
Taints, labels and zones:
PDB-sensitive workloads:
Core add-on hosting nodes:
Instance quotas:
Owner and monthly compute budget:
```

**Expected:** identify stable baseline capacity, elastic capacity and the lifecycle owner for each node.

## 6. Lab 3 — Measure resource, scheduling and IP capacity

```powershell
kubectl top nodes
kubectl top pods -A
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl get resourcequotas -A
kubectl get limitranges -A
aws ec2 describe-subnets --region $region --profile $profile --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,FreeIPs:AvailableIpAddressCount,Vpc:VpcId}' --output table
```

Metrics Server is required for `kubectl top`. Restrict subnet results to the cluster VPC when interpreting IP headroom.

### Capacity model

```text
Peak requested CPU and memory:
Node allocatable CPU and memory:
DaemonSet/system overhead:
Pod count and IP warm pool:
Subnet free IPs by AZ:
EC2 instance/ENI limits:
Spot capacity assumptions:
Zone-failure headroom:
Karpenter NodePool limits:
Expected peak and steady-state cost:
```

**Expected:** a capacity finding with a specific binding constraint, not just average node CPU.

## 7. Lab 4 — Inspect VPC CNI, CoreDNS and service discovery

```powershell
kubectl -n kube-system get daemonset aws-node
kubectl -n kube-system get deployment coredns
kubectl -n kube-system get service kube-dns
kubectl -n kube-system get pods -o wide
kubectl get services -A
kubectl get endpointslices -A
kubectl -n kube-system logs deployment/coredns --tail=100
```

### Validation questions

1. Are Pod IPs allocated from expected subnets?
2. Does the CNI have enough ENI/IP capacity for scaling?
3. Are CoreDNS Pods spread and available?
4. Are Services backed by ready EndpointSlices?
5. Are private AWS endpoints/NAT paths available?
6. Is NetworkPolicy enforcement actually configured?

**Expected:** DNS, Service and CNI health baselines recorded.

## 8. Lab 5 — Deploy a disposable staging application

Save `ch080-app.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch080
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
  namespace: ch080
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch080-app.yaml
kubectl -n ch080 rollout status deployment/web --timeout=180s
kubectl -n ch080 get pods,services,endpointslices -o wide
kubectl -n ch080 get events --sort-by=.lastTimestamp
```

**Expected:** two Ready Pods and a Service with ready endpoints. No AWS load balancer is created by this ClusterIP test.

## 9. Lab 6 — Validate ingress and load balancer operational health

```powershell
kubectl get ingress -A
kubectl get ingressclasses
kubectl -n kube-system get deployment aws-load-balancer-controller
kubectl get services -A
kubectl get targetgroupbindings -A
```

Controller-specific resources are optional. If no staging ALB/NLB exists, run the following as a tabletop instead of creating a billable load balancer.

### ALB/NLB acceptance

- Controller reconciliation healthy.
- Expected target type (IP or instance).
- Subnet discovery and security groups reviewed.
- TLS and certificate chain valid.
- Target health check path and port correct.
- No unexpected internet-facing ingress.
- Error rate and latency visible in monitoring.
- Ownership tags and teardown plan recorded.

## 10. Lab 7 — Validate EBS CSI and data integrity

```powershell
kubectl get csidrivers
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
kubectl get volumesnapshotclasses
```

For an approved EBS CSI StorageClass, save `ch080-pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: ch080
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: REPLACE_WITH_APPROVED_EBS_STORAGECLASS
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: data-check
  namespace: ch080
spec:
  containers:
    - name: check
      image: busybox:1.36
      command:
        - /bin/sh
        - -c
        - |
          if [ ! -f /data/checkpoint ]; then
            printf 'ch080-eks-data-checkpoint\n' > /data/checkpoint
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
kubectl apply -f .\ch080-pvc.yaml
kubectl -n ch080 get pvc,pods -o wide
kubectl -n ch080 wait --for=condition=Ready pod/data-check --timeout=180s
kubectl -n ch080 exec data-check -- sha256sum /data/checkpoint
```

**Expected:** PVC Bound and checksum captured. Reclaim policy and backup method must be documented before cleanup. This is a volume smoke test, not a database-consistent backup.

## 11. Lab 8 — Audit IAM, access entries and workload identity

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.accessConfig'
aws eks list-access-entries --cluster-name $cluster --region $region --profile $profile
aws eks list-pod-identity-associations --cluster-name $cluster --region $region --profile $profile
kubectl get clusterrolebindings
kubectl get rolebindings -A
kubectl get serviceaccounts -A
```

### Security gates

- Break-glass administrator access exists and is audited.
- Routine operators use least-privilege RBAC.
- Applications do not rely on overly broad node IAM roles.
- Pod Identity/IRSA associations are explicit and scoped.
- Secrets/KMS access is least privilege.
- Network policies and Pod Security controls are validated.
- CloudTrail and EKS audit logging support investigations.

**Expected:** access matrix, remediation list and security owner sign-off.

## 12. Lab 9 — Build an actionable observability scorecard

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.logging'
aws logs describe-log-groups --log-group-name-prefix "/aws/eks/$cluster/" --region $region --profile $profile
kubectl get nodes
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

### Scorecard

| SLI or operational signal | Evidence | Owner |
|---|---|---|
| API availability and error rate | Synthetic endpoint checks | App/SRE |
| Node Ready and pressure | Kubernetes/CloudWatch metrics | Platform |
| Pending Pod duration | kube-state-metrics/Events | Platform |
| Pod IP allocation failures | VPC CNI logs/metrics | Network |
| CoreDNS errors/latency | CoreDNS metrics | Network |
| ALB/NLB unhealthy targets | CloudWatch/target groups | App/network |
| EBS CSI attach failures | CSI logs/PVC Events | DBRE/platform |
| IAM changes/auth failures | CloudTrail/EKS audit | Security |
| Cost anomaly | AWS Budgets/Cost Explorer | FinOps |

Each alert should include severity, actionable threshold, runbook, dashboard, owner and escalation.

## 13. Lab 10 — Simulate a multi-layer EKS incident

**Tabletop injects — no destructive cloud actions required:**

| Inject | Expected diagnosis |
|---|---|
| Subnet free IPs fall below scaling requirement | CNI/IP capacity investigation |
| Pending Pods after batch scale-out | Requests, taints, quotas, NodePool limits |
| Karpenter NodeClaim launched but node NotReady | Bootstrap, IAM, CNI, security groups |
| ALB targets unhealthy | Readiness, EndpointSlices, SG, health path |
| EBS PVC cannot attach after node replacement | AZ topology and VolumeAttachment |
| Workload cannot read S3 | Pod Identity/IRSA permissions |
| Audit log gap discovered | EKS logging and retention configuration |
| Upgrade reveals deprecated API | Compatibility and rollback decision |

### Incident response sequence

1. Declare severity and record UTC timeline.
2. Separate customer symptoms from underlying platform signals.
3. Identify the first failing dependency.
4. Verify cloud identity and cluster context.
5. Prefer reversible, scoped remediations.
6. Validate SLOs, data integrity and security after each action.
7. Record root cause, contributing factors and prevention owners.

**Expected:** an evidence-based incident timeline, not a generic list of possible failures.

## 14. Lab 11 — Prepare EKS upgrade and maintenance readiness

```powershell
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Version:version,Status:status,Platform:platformVersion}'
aws eks list-addons --cluster-name $cluster --region $region --profile $profile
aws eks list-nodegroups --cluster-name $cluster --region $region --profile $profile
aws eks list-updates --name $cluster --region $region --profile $profile
kubectl get pdb -A
kubectl get apiservices
kubectl get crds
```

### Upgrade gates

- Supported target Kubernetes version and API compatibility.
- Add-on, controller, Karpenter and CSI version matrix.
- Node/AMI update strategy and disruption budgets.
- Sufficient subnet IPs, spare compute and EC2 quotas.
- Valid workload and database backups.
- Observability and application acceptance checks.
- Approved change window and owner communications.
- Recovery plan acknowledging **EKS control-plane downgrades are unsupported**.

**Expected:** a staged upgrade runbook. No control-plane upgrade is performed by this chapter.

## 15. Lab 12 — Disaster recovery and cost readiness

Use Chapters 071–075 as the disaster recovery baseline.

### Recovery checklist

1. Confirm independent backup repository and access.
2. Validate PVC data backups, not only Kubernetes manifests.
3. Confirm database-native recovery and transaction-log coverage.
4. Verify cross-region IAM/KMS and image availability.
5. Inventory target VPC/subnets, CSI, CRDs and StorageClasses.
6. Document single-writer fencing and GitOps recovery.
7. Define DNS/ingress cutover authority.
8. Measure RPO/RTO during a separately approved staging DR exercise.

### Cost worksheet

```text
EKS cluster hourly cost:
Managed node group EC2 hours:
Karpenter On-Demand and Spot hours:
EBS/EFS and snapshots:
ALB/NLB capacity and hours:
NAT gateway and data transfer:
CloudWatch/Prometheus/Grafana:
Backup and DR storage:
Budget alert threshold:
Resource tags and cleanup owner:
```

**Expected:** an operationally justified platform with budget and DR ownership.

## 16. Lab 13 — Final acceptance and operational handover

### Handover package

```text
Cluster/account/region:
Change approval:
Architecture and network diagram:
Managed node group and Karpenter inventory:
Pod IP capacity and quotas:
Load balancer and ingress ownership:
EBS/EFS and backup inventory:
IAM/RBAC access matrix:
Dashboards and alert routes:
Application SLI/SLO evidence:
Incident timeline and recovery actions:
Upgrade compatibility matrix:
DR RPO/RTO targets and exercise status:
Monthly cost estimate and budget:
Known risks and remediation owners:
On-call escalation:
Independent technical reviewer:
Overall outcome: Pass / Fail / Not run
```

### Scoring rubric

| Domain | Weight |
|---|---:|
| Cluster identity and architecture | 10% |
| Compute and scheduling | 15% |
| Networking and ingress | 15% |
| Storage and data integrity | 15% |
| Security and workload identity | 15% |
| Monitoring and incident response | 15% |
| Upgrade, DR and cost readiness | 15% |

A score is meaningful only when supported by evidence. A critical data-integrity or unauthorized-access failure blocks overall Pass regardless of weighted score.

## 17. Troubleshooting matrix

| Symptom | Likely domain | Investigation |
|---|---|---|
| API unreachable | Endpoint/network/IAM | EKS endpoint, STS, kubeconfig |
| Pods Pending | Scheduling/quotas/IPs | Events, requests, NodePool |
| Nodes NotReady | Bootstrap/CNI/EC2 | Node conditions, EC2 logs |
| CoreDNS timeouts | DNS/CNI/network policy | CoreDNS, routes, Service |
| ALB target unhealthy | App/SG/ingress | EndpointSlices, target health |
| PVC Pending | CSI/StorageClass | PVC Events, driver |
| EBS attachment conflict | AZ or attachment limit | PV topology, VolumeAttachment |
| S3 AccessDenied | Pod Identity/IRSA/IAM | Association, trust, CloudTrail |
| Monitoring gaps | Exporter/log config | Targets, retention, EKS logging |
| Upgrade regression | Add-on/API/webhook incompatibility | Compatibility matrix, Events |
| Cost anomaly | EC2/NAT/LB/EBS/logs | Tagged usage, budgets |

## 18. Cleanup and cost safeguards

Before cleanup, record test evidence and inspect PVC reclaim policy.

```powershell
kubectl config current-context
kubectl -n ch080 get deployments,pods,services,pvc
kubectl get pv
```

Only after approval, in the verified staging cluster:

```powershell
kubectl delete namespace ch080
```

Deleting a namespace can delete PVCs and their underlying volumes depending on reclaim policy. Never delete shared NodePools, managed node groups, AWS load balancers, IAM roles, KMS keys, backups or production clusters as part of this tutorial.

## 19. Capstone acceptance checklist

- [ ] Exercise charter, owners, cost ceiling and stop conditions approved.
- [ ] AWS account, region and Kubernetes context verified.
- [ ] Managed node group/Karpenter inventory completed.
- [ ] Scheduling, requests and Pod IP capacity measured.
- [ ] VPC CNI, CoreDNS and Services reviewed.
- [ ] Disposable application deployed or marked Not run.
- [ ] Ingress/load balancer health validated or tabletop completed.
- [ ] EBS CSI/PVC data checksum captured or marked Not run.
- [ ] EKS access entries, RBAC and workload identity audited.
- [ ] Control-plane logs, alerts and application SLIs reviewed.
- [ ] Multi-layer incident simulation documented.
- [ ] Upgrade compatibility and maintenance runbook approved.
- [ ] Backup/DR readiness and cost ownership reviewed.
- [ ] Final handover and remediation owners documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Part 16 writing milestone:** Chapters 076–080 drafted. Runtime validation and independent technical review remain pending.

## 20. References

- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [Amazon EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Amazon VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Pod Identities](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS Control Plane Logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [EKS Update Cluster](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

**Next:** Chapter 081 — Azure AKS Architecture and Provisioning, beginning Part 17.
