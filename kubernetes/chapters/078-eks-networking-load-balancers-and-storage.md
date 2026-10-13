# Chapter 078 — EKS Networking, Load Balancers and Storage

**Track:** Kubernetes Administration · **Part 16 — Managed Kubernetes on AWS and Azure**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, AWS network and storage engineers  
**Prerequisites:** Chapters 026–030, 036–040, 076–077; AWS CLI v2, kubectl, Windows PowerShell; approved EKS staging cluster; appropriate IAM permissions

## 1. Production incident scenario

A production EKS application experiences intermittent connection failures. New Pods remain Pending because subnet IP capacity is low, an internet-facing ALB shows unhealthy targets, and a PostgreSQL Pod cannot attach its EBS volume after moving to another availability zone. The team must separate Kubernetes scheduling problems from AWS VPC, load balancer and CSI storage failures.

**Mission:** map the EKS network and storage data paths, validate AWS integrations, deploy bounded staging tests, diagnose representative failures and document production-safe recovery procedures.

**Safety:** Changing subnets, security groups, VPC CNI settings, load balancers, StorageClasses or PV reclaim policies can disrupt workloads or incur charges. All mutating exercises require an approved staging cluster, budget and rollback plan.

### Learning outcomes

1. Explain Pod, node, Service and external traffic flows in EKS.
2. Diagnose VPC CNI ENI/IP allocation and subnet exhaustion.
3. Validate CoreDNS, kube-proxy, network policy and service discovery.
4. Compare ALB and NLB integrations with AWS Load Balancer Controller.
5. Understand ingress target types, health checks, TLS and subnet discovery.
6. Provision and troubleshoot EBS CSI-backed persistent volumes.
7. Evaluate EFS CSI for shared ReadWriteMany workloads.
8. Plan storage topology, EBS availability-zone placement and backup.
9. Identify IAM, security group, KMS, quota and cost dependencies.
10. Build incident runbooks for networking, ingress and persistent storage.

## 2. EKS networking and storage architecture

```text
Internet / private clients
           |
    Route 53 / DNS / TLS
           |
       ALB or NLB
           |
       Target group
           |
    Node / Pod endpoint
           |
      Kubernetes Service
           |
         Pods
           |
       VPC CNI
           |
   ENIs / subnet IPs / SGs

Pod persistent storage
           |
       CSI driver
           |
       EBS (AZ-scoped)
       EFS (regional shared filesystem)
```

**Responsibility boundary:** AWS operates managed services such as EKS control-plane infrastructure and the underlying EBS/EFS platforms. The customer configures VPC routes, security groups, IAM, load balancer controllers, CSI add-ons, StorageClasses, Kubernetes Services, workloads and recovery procedures.

## 3. Lab 1 — Establish account, cluster and network inventory

```powershell
$profile = 'REPLACE_WITH_APPROVED_AWS_PROFILE'
$region = 'us-east-1'
$cluster = 'REPLACE_WITH_STAGING_EKS_CLUSTER'
aws sts get-caller-identity --profile $profile
aws eks describe-cluster --name $cluster --region $region --profile $profile --query 'cluster.{Name:name,Status:status,Version:version,Vpc:resourcesVpcConfig}' --output json
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide
```

**Stop** if the AWS account, region or kubeconfig context is not the approved staging environment.

### Inventory worksheet

```text
Cluster and VPC:
Region / availability zones:
Public and private subnet IDs:
Subnet free IPs:
VPC CNI version:
CoreDNS / kube-proxy versions:
Ingress controller:
ALB/NLB ownership:
EBS CSI version:
EFS CSI version:
StorageClasses and reclaim policies:
KMS keys:
Network policy implementation:
Security group / IAM owner:
```

## 4. Lab 2 — Inspect VPC, subnet and route capacity

```powershell
aws ec2 describe-vpcs --region $region --profile $profile --query 'Vpcs[].{Id:VpcId,Cidr:CidrBlock}' --output table
aws ec2 describe-subnets --region $region --profile $profile --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,FreeIPs:AvailableIpAddressCount,Vpc:VpcId}' --output table
aws ec2 describe-route-tables --region $region --profile $profile --query 'RouteTables[].{Id:RouteTableId,Vpc:VpcId}' --output table
aws ec2 describe-security-groups --region $region --profile $profile --query 'SecurityGroups[].{Id:GroupId,Name:GroupName,Vpc:VpcId}' --output table
```

These account-wide queries may return unrelated resources. Restrict scope to the cluster VPC before drawing conclusions.

### IP capacity design

- Account for EC2 node primary IPs, VPC CNI secondary IPs or prefixes, and warm allocation.
- Understand instance-type ENI and per-ENI address limits.
- Evaluate custom networking and prefix delegation only with a supported design.
- Reserve free IPs for scaling, node replacements, load balancers and zone failures.
- Watch subnet CIDR fragmentation when using prefix delegation.
- Validate route tables, NAT or VPC endpoints for private nodes.

**Expected:** a documented Pod IP capacity budget and subnet growth threshold.

## 5. Lab 3 — Inspect Amazon VPC CNI and Pod networking

```powershell
aws eks describe-addon --cluster-name $cluster --addon-name vpc-cni --region $region --profile $profile
kubectl -n kube-system get daemonset aws-node
kubectl -n kube-system get pods -l k8s-app=aws-node -o wide
kubectl -n kube-system describe daemonset aws-node
kubectl get nodes -o wide
kubectl get pods -A -o wide
```

If VPC CNI is self-managed rather than an EKS add-on, the AWS describe-addon call may not return an installed add-on. Inspect the DaemonSet and installation owner instead.

### Key operational concepts

- Pod IPs generally come from VPC networking through the Amazon VPC CNI.
- The `ipamd` component manages ENI/IP allocation for supported configurations.
- Warm IP and prefix settings affect startup latency and unused IP consumption.
- Security groups for Pods are optional and require compatible setup.
- NetworkPolicy enforcement depends on the deployed CNI and enabled policy implementation; do not assume policies are enforced merely because YAML exists.

**Expected:** CNI health, Pod IP allocation model and subnet headroom are understood.

## 6. Lab 4 — Troubleshoot CoreDNS and Kubernetes Services

```powershell
kubectl -n kube-system get deployment coredns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get service kube-dns
kubectl get services -A
kubectl get endpointslices -A
kubectl -n kube-system logs deployment/coredns --tail=100
```

### DNS diagnosis sequence

1. Confirm the Service and EndpointSlices exist.
2. Check Pod DNS policy and `/etc/resolv.conf` where authorized.
3. Confirm CoreDNS readiness and resource headroom.
4. Verify Service IP routing and kube-proxy or alternate dataplane.
5. Check CNI network policy, security groups and DNS egress.
6. Review upstream resolver latency, VPC DNS and private hosted zones.

**Expected:** distinguish application DNS lookup failures from missing endpoints or network connectivity failures.

## 7. Lab 5 — Understand ALB, NLB and AWS Load Balancer Controller

| Component | Typical role | Operational consideration |
|---|---|---|
| Application Load Balancer | Layer 7 HTTP/HTTPS routing | Listener rules, target health, TLS, WAF |
| Network Load Balancer | Layer 4 TCP/UDP/TLS transport | Target mode, client IP, health checks |
| AWS Load Balancer Controller | Reconciles supported Ingress/Service resources | IAM, subnet discovery, annotations |
| Kubernetes Service | Stable internal endpoint | Selectors and EndpointSlices |
| Ingress | HTTP routing specification | Requires an ingress controller |

Do not assume every `Service type=LoadBalancer` is reconciled by the AWS Load Balancer Controller; behavior depends on annotations, controller installation and EKS mode/configuration.

```powershell
kubectl -n kube-system get deployment aws-load-balancer-controller
kubectl get ingressclasses
kubectl get ingress -A
kubectl get services -A
kubectl get targetgroupbindings -A
```

`TargetGroupBinding` CRDs exist only when the relevant controller is installed.

## 8. Lab 6 — Deploy an internal staging Service

Save `ch078-service.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch078
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch078
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
            initialDelaySeconds: 3
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
  namespace: ch078
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

```powershell
kubectl apply -f .\ch078-service.yaml
kubectl -n ch078 rollout status deployment/web --timeout=180s
kubectl -n ch078 get pods,services,endpointslices
kubectl -n ch078 describe service web
```

**Expected:** two Ready Pods and an internal ClusterIP Service with healthy endpoints. This test does not create a billable AWS load balancer.

## 9. Lab 7 — Review an ALB Ingress design

**Do not apply until an approved ingress controller, subnet tags, IAM permissions and security design are verified.** Example:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
  namespace: ch078
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
  ingressClassName: alb
  rules:
    - host: ch078.internal.example.invalid
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
```

The host is a placeholder and does not create DNS. Applying this Ingress can create a **billable ALB**.

### Review checklist

- Internal versus internet-facing scheme.
- Subnet selection and multi-AZ coverage.
- IngressClass and controller ownership.
- IP versus instance target type.
- TLS certificate and listener configuration.
- Health check path and response codes.
- Security group and WAF requirements.
- Controller service account IAM permissions.
- Load balancer cost and deletion policy.

**Expected:** a reviewed ingress manifest, not an unapproved public endpoint.

## 10. Lab 8 — Diagnose ALB/NLB target health

```powershell
kubectl -n ch078 get ingress
kubectl -n ch078 describe ingress web
kubectl -n ch078 get pods -o wide
kubectl -n ch078 get endpointslices
kubectl -n kube-system logs deployment/aws-load-balancer-controller --tail=100
```

If no ALB was deployed, perform a tabletop instead.

### Unhealthy target decision tree

1. Check target group health reason and registered target IP/port.
2. Confirm readiness and EndpointSlice membership.
3. Verify Pod IP reachability from load balancer subnets.
4. Check security groups, NACLs and routes.
5. Verify health check protocol/path/port and success codes.
6. Review target type and Service port mapping.
7. Check AZ/subnet enablement and load balancer attributes.
8. Review controller logs and AWS IAM errors.

**Expected:** evidence distinguishes application readiness, AWS network path and controller reconciliation.

## 11. Lab 9 — Inspect EBS CSI and StorageClass behavior

```powershell
aws eks list-addons --cluster-name $cluster --region $region --profile $profile
kubectl get csidrivers
kubectl -n kube-system get deployments,daemonsets | Select-String 'ebs'
kubectl get storageclasses -o yaml
kubectl get pv
kubectl get pvc -A
kubectl get volumesnapshotclasses
```

### EBS characteristics

- EBS volumes are associated with an availability zone.
- A Pod requiring an existing EBS PV must be scheduled compatibly with volume topology.
- `WaitForFirstConsumer` can help new volume provisioning follow scheduling constraints.
- EBS CSI needs appropriate IAM permissions and KMS access for encrypted volumes.
- Volume attachment limits, throughput and IOPS affect scheduling and database performance.
- Reclaim policy `Delete` may delete the backing EBS volume when a PV is released.

**Expected:** EBS CSI installation, identity, StorageClasses, binding mode and reclaim policy are documented.

## 12. Lab 10 — Provision a disposable EBS-backed PVC

**Approved staging only.** Use an explicitly approved EBS CSI StorageClass. Save `ch078-ebs-pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-test
  namespace: ch078
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: REPLACE_WITH_APPROVED_EBS_STORAGECLASS
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: ebs-writer
  namespace: ch078
spec:
  containers:
    - name: writer
      image: busybox:1.36
      command:
        - /bin/sh
        - -c
        - |
          echo ch078-ebs-data > /data/marker.txt
          sleep 360000
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: ebs-test
```

```powershell
kubectl apply -f .\ch078-ebs-pvc.yaml
kubectl -n ch078 get pvc,pods -o wide
kubectl -n ch078 describe pvc ebs-test
kubectl -n ch078 wait --for=condition=Ready pod/ebs-writer --timeout=180s
kubectl -n ch078 exec ebs-writer -- cat /data/marker.txt
kubectl -n ch078 exec ebs-writer -- sha256sum /data/marker.txt
```

**Expected:** PVC Bound, Pod Ready, and data marker readable. This creates billable EBS storage; do not apply without approval.

## 13. Lab 11 — Evaluate EFS CSI for shared storage

Amazon EFS provides shared filesystem access across supported availability zones and can be used with Kubernetes ReadWriteMany PVCs through the EFS CSI driver.

```powershell
kubectl get csidrivers
kubectl -n kube-system get deployments,daemonsets | Select-String 'efs'
kubectl get storageclasses
aws efs describe-file-systems --region $region --profile $profile --query 'FileSystems[].{Id:FileSystemId,State:LifeCycleState,Encrypted:Encrypted}' --output table
```

### EFS design considerations

- Mount targets in required AZs and security group access to NFS.
- POSIX permissions, access points and identity mapping.
- Throughput/performance mode and cost.
- Shared-file locking and application consistency.
- EFS backup and replication requirements.
- Access restrictions for multi-tenant workloads.
- EFS is not interchangeable with block storage for all databases.

**Expected:** identify when EFS is appropriate for shared content and when EBS or database-native storage is preferable.

## 14. Lab 12 — Combined network/storage incident tabletop

**Scenario:** a PostgreSQL StatefulSet Pod remains Pending after node replacement. The replacement node is in a different AZ from the existing EBS PV. At the same time, an ALB target group is unhealthy because its security group cannot reach Pod target ports.

### Tasks

1. Confirm node, Pod and PV zone labels.
2. Inspect PVC/PV binding and VolumeAttachment objects.
3. Check scheduler Events for volume node affinity conflict.
4. Identify a safe same-AZ node placement or approved data migration path.
5. Inspect ALB target health and controller logs.
6. Validate security groups and health check ports.
7. Review VPC CNI Pod IP availability.
8. Confirm database integrity before restarting writes.
9. Verify application readiness and synthetic transactions.
10. Record recovery time, root cause and preventive actions.

**Expected:** separate the EBS topology problem from the ALB networking problem and avoid deleting a stateful PVC as a shortcut.

## 15. Monitoring, security and FinOps

### Operational signals

- Subnet free IPs, ENI allocation failures and CNI warm pool usage.
- CoreDNS query latency, errors and restarts.
- Service EndpointSlice availability.
- ALB/NLB healthy targets, latency, 4xx/5xx and connection resets.
- AWS Load Balancer Controller reconciliation errors.
- EBS volume IOPS, throughput, latency and attachment failures.
- EFS throughput, burst credits and client connection health.
- PVC Pending time and PV capacity.
- Unexpected load balancers, volumes, snapshots and data transfer.

### Security controls

- Private nodes and controlled API endpoints.
- Least-privilege controller and CSI IAM roles.
- Security groups and network policies appropriate to threat model.
- TLS and certificate lifecycle.
- KMS encryption and recovery key access.
- Audit logs for load balancer, storage and IAM changes.
- Backup and snapshot retention.

### Cost drivers

```text
ALB/NLB hours and capacity units:
EBS GB-month, provisioned IOPS and throughput:
EFS storage and throughput:
NAT gateway hourly and data processing:
Cross-AZ data transfer:
CloudWatch logs and metrics:
EBS snapshots / EFS backups:
Idle resources and cleanup owner:
```

## 16. Production incident runbooks

### A. Pods cannot obtain IP addresses

1. Inspect Pod Events and VPC CNI logs.
2. Check subnet free IPs and prefix fragmentation.
3. Verify ENI limits, instance types and warm allocation settings.
4. Review IAM and EC2 API throttling.
5. Expand approved subnet capacity or adjust CNI configuration under change control.
6. Validate Pod scheduling and network connectivity.

### B. ALB targets unhealthy

1. Check Service/EndpointSlices and Pod readiness.
2. Inspect ALB target health reason codes.
3. Verify target IP/port, SG, NACL and routes.
4. Check health check configuration and ingress annotations.
5. Review controller reconciliation logs.
6. Validate external SLOs after remediation.

### C. EBS volume attach/mount failure

1. Inspect Pod, PVC, PV and VolumeAttachment Events.
2. Check PV topology and node AZ.
3. Verify EBS CSI IAM/KMS permissions.
4. Check EC2 attachment limits and volume state.
5. Use approved data recovery or scheduling remediation.
6. Validate filesystem/database integrity after recovery.

## 17. Troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| Pod sandbox creation fails | CNI IP allocation | aws-node logs, subnet IPs |
| DNS lookup timeout | CoreDNS, network policy, upstream DNS | CoreDNS and VPC DNS |
| Service has no endpoints | Selector/readiness mismatch | EndpointSlices |
| ALB not created | Controller/IAM/subnet discovery | Controller logs, Ingress Events |
| ALB target unhealthy | SG, path/port, Pod readiness | Target health and Service |
| NLB traffic drops | Target mode, SG, health check | Target group and network |
| PVC Pending | CSI, StorageClass, quotas | PVC Events |
| EBS attach conflict | AZ mismatch or attachment limit | PV topology, VolumeAttachment |
| EFS mount timeout | Mount target, NFS SG, DNS | EFS CSI and VPC |
| Unexpected storage cost | Orphaned EBS/EFS/snapshots | Tags and AWS inventory |

## 18. Cleanup and change safeguards

**Staging only.** Confirm namespace, PV reclaim policy, cloud volume ownership and any retained snapshot before cleanup.

```powershell
kubectl config current-context
kubectl -n ch078 get deployments,pods,services,pvc
kubectl get pv
kubectl delete namespace ch078
```

Namespace deletion may delete PVCs and, under `Delete` reclaim policy, backing EBS volumes. Do not remove shared load balancers, EFS file systems, snapshots, KMS keys, security groups or production resources as part of this lab.

## 19. Acceptance checklist

- [ ] AWS account, cluster and staging context verified.
- [ ] VPC/subnet/route/IP capacity inventory completed.
- [ ] VPC CNI and Pod IP allocation reviewed.
- [ ] CoreDNS, Services and EndpointSlices inspected.
- [ ] ALB/NLB controller ownership and target modes understood.
- [ ] Internal Service staging test completed or marked Not run.
- [ ] ALB ingress design reviewed without unintended exposure.
- [ ] Target health troubleshooting evidence documented.
- [ ] EBS CSI, StorageClass, AZ topology and reclaim policy reviewed.
- [ ] EBS PVC test completed or marked Not run.
- [ ] EFS CSI and shared-storage requirements assessed.
- [ ] Combined incident tabletop completed.
- [ ] Monitoring, security and cost controls documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Amazon EKS Networking](https://docs.aws.amazon.com/eks/latest/userguide/eks-networking.html)
- [Amazon VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Amazon EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Amazon EKS EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)

**Next:** Chapter 079 — EKS Security, Identity, Monitoring and Upgrades.
