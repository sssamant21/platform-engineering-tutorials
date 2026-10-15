# Chapter 068 — EKS Networking, AWS Load Balancer Controller and Storage Integration for GitOps

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 14:** Amazon EKS  
**Chapter:** 068 / 100  
**Audience:** Platform Engineers, SREs, Cloud Architects, Kubernetes Administrators and DBREs

> **Safety:** Execute labs only in an isolated, approved staging cluster. Load balancers, NAT gateways, EBS/EFS volumes and cross-AZ traffic incur costs. Do not modify shared CNI, CoreDNS, production ingress, network routes or live persistent volumes during failure injection. Protect data with verified backups before storage changes.

## 1. Learning objectives

After this chapter, you can:

1. Trace EKS Pod networking through Amazon VPC CNI, subnets, ENIs and routing.
2. Diagnose Pod IP exhaustion, DNS failures and service connectivity.
3. Configure AWS Load Balancer Controller for ALB and NLB workloads.
4. Explain Ingress, Service, target types, TLS and load-balancer security.
5. Configure EBS CSI and EFS CSI storage through declarative GitOps.
6. Design multi-AZ storage placement, snapshots and application recovery.
7. Enforce network isolation and least-privilege AWS workload identity.
8. Operate networking and storage changes through GitLab and Argo CD.
9. Perform hands-on troubleshooting and disaster-recovery acceptance.

## 2. Production architecture

~~~text
GitLab protected GitOps MR -> Argo CD
                                 |
               EKS cluster across three AZs
                                 |
  VPC private subnets / VPC CNI / Pod IP allocation
          |                   |
      CoreDNS            kube-proxy
          |                   |
      Service discovery / ClusterIP
          |
   AWS Load Balancer Controller
        /                 \
      ALB                 NLB
   HTTP / HTTPS          TCP / TLS
        \                 /
          Kubernetes Pods
             |       |
         EBS CSI   EFS CSI
         zonal     regional multi-AZ access
             |       |
        snapshots / backups / recovery
~~~

**Ownership:** AWS manages the EKS control plane. Platform teams own VPC/subnets, CNI configuration, controller IAM, ingress rules, storage classes, PVC lifecycle, application availability and disaster recovery.

## 3. Design decisions

| Domain | Staging baseline | Production review |
| --- | --- | --- |
| Pod networking | Amazon VPC CNI | Prefix delegation, IP planning |
| DNS | CoreDNS | Replicas, upstream, NodeLocal DNSCache if used |
| Service routing | kube-proxy or supported dataplane | Version-specific networking |
| Ingress | AWS Load Balancer Controller | ALB/NLB, TLS, WAF, access controls |
| NetworkPolicy | Compatible enforcing implementation | Test default-deny and exceptions |
| Block storage | EBS CSI | AZ affinity, snapshots, KMS |
| Shared filesystem | EFS CSI | Access points, performance, IAM |
| GitOps | Argo CD platform/application separation | Safe prune and CRD ordering |
| IAM | IRSA or EKS Pod Identity | Least privilege and trust |
| Recovery | Backups plus restore drills | Defined RPO/RTO |

## 4. Prerequisites

- EKS cluster and managed node group from Chapter 066.
- Karpenter/managed capacity model from Chapter 067.
- Approved AWS region, profile and network access.
- EKS VPC CNI, CoreDNS and kube-proxy in healthy state.
- EBS CSI add-on and approved AWS Load Balancer Controller release.
- Optional EFS CSI driver and staging EFS filesystem.
- Argo CD platform AppProject and protected GitLab repository.
- Approved KMS, ACM, DNS and IAM resources.

~~~bash
aws sts get-caller-identity
kubectl config current-context
kubectl -n kube-system get daemonsets,deployments,pods
kubectl get storageclasses
kubectl get ingressclasses
kubectl get csidrivers
~~~

Verify exact cluster and AWS account before changes.

## 5. Network packet path

~~~text
External client -> Route 53 DNS -> ALB/NLB
  -> target group -> node or Pod IP
  -> Kubernetes Service -> Pod
  -> application container

Pod -> CoreDNS -> upstream resolver -> AWS/VPC destination
Pod -> VPC CNI ENI/IP -> route table / NAT or VPC endpoint
~~~

ALB target type **ip** registers Pod IP targets; **instance** targets nodes and NodePorts. NLB behavior depends on Service annotations, target mode and controller implementation. Trace the actual target group before troubleshooting.

## 6. Subnet and Pod IP capacity

Plan IPs for nodes, Pods, ENIs, load balancers, control-plane networking and scale bursts. AWS VPC CNI normally assigns VPC IPs to Pods; custom networking and prefix delegation alter allocation behavior.

~~~bash
aws ec2 describe-subnets   --subnet-ids subnet-REPLACE   --query 'Subnets[*].{Id:SubnetId,Available:AvailableIpAddressCount,AZ:AvailabilityZone}'

kubectl -n kube-system get daemonset aws-node
kubectl -n kube-system logs daemonset/aws-node --tail=100
~~~

Do not infer healthy IP capacity solely from node CPU utilization. A cluster can have spare CPU but fail to schedule networked Pods because ENI/IP limits or subnet addresses are exhausted.

## 7. Prefix delegation and custom networking

VPC CNI prefix delegation can improve Pod IP density and allocation efficiency, but requires suitable subnet free contiguous address blocks, supported instance types and version compatibility. Custom networking can assign Pod addresses from alternate subnets and security-group designs.

**Change safety:** review node maxPods settings, CNI environment variables, subnet fragmentation, existing Pods and rollback. Apply to staging first; do not toggle CNI allocation mode blindly during a production incident.

## 8. Security groups and NetworkPolicies

AWS security groups operate at VPC network boundaries; Kubernetes NetworkPolicies operate on Pod traffic when enforced by a compatible dataplane. Security Groups for Pods provide additional AWS-level controls where supported.

Do not assume a NetworkPolicy is enforced simply because Kubernetes accepted its YAML. Verify the installed CNI's network policy mode and test allowed/denied connections.

## 9. CoreDNS and service discovery

~~~bash
kubectl -n kube-system get deploy coredns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get configmap coredns -o yaml
kubectl get svc kubernetes -n default
~~~

CoreDNS failures can be caused by insufficient capacity, node pressure, upstream DNS failure, network policies or CNI problems. Avoid indiscriminate restarts without capturing diagnostic evidence.

## 10. NetworkPolicy example

~~~yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: demo-web-ingress
  namespace: demo-staging
spec:
  podSelector:
    matchLabels:
      app: demo-web
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              access: frontend
      ports:
        - protocol: TCP
          port: 8080
~~~

This policy only constrains selected Pods' ingress, **if** enforcement is enabled. Test DNS, monitoring, ingress-controller and health-check traffic separately before introducing default-deny policies.

## 11. Load balancer controller architecture

AWS Load Balancer Controller watches Kubernetes Ingress and Service resources and reconciles AWS load balancers, listeners, target groups and security groups.

Use a dedicated ServiceAccount with IRSA or EKS Pod Identity and the documented least-privilege IAM policy. Verify subnet tags, cluster identity, AWS API access, controller webhook certificates and release compatibility.

~~~bash
kubectl -n kube-system get deployment aws-load-balancer-controller
kubectl -n kube-system logs deployment/aws-load-balancer-controller --tail=100
kubectl get ingressclasses
~~~

## 12. ALB ingress example

~~~yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: demo-web-internal
  namespace: demo-staging
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /readyz
spec:
  ingressClassName: alb
  rules:
    - host: demo-web.staging.example.internal
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: demo-web
                port:
                  number: 80
~~~

The DNS name is illustrative and the resource is not externally reachable without appropriate private DNS, routing and a backing Service. For HTTPS, configure approved ACM certificate, listeners and TLS/security policy. Do not rely on HTTP-only examples for production exposure.

## 13. NLB Service example

~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-tcp-internal
  namespace: demo-staging
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: demo-tcp
  ports:
    - name: tcp
      port: 5432
      targetPort: 5432
      protocol: TCP
~~~

This illustrates a TCP Service and must **not** be used to expose a real database without security review. Annotation and loadBalancerClass behavior depend on the installed controller and EKS mode. Check for conflicts with EKS Auto Mode or legacy in-tree controllers.

## 14. ALB versus NLB

| Feature | ALB | NLB |
| --- | --- | --- |
| Layer | HTTP/HTTPS (L7) | TCP/UDP/TLS (L4) |
| Routing | Host/path rules | Port/protocol targeting |
| Common use | Web APIs | TCP services |
| Health | HTTP/HTTPS target checks | TCP/HTTP/HTTPS checks |
| TLS | ACM integration | TLS listeners where configured |
| WAF | Supported ALB integration | Different controls |
| Source IP | Depends on target and headers | Depends on target mode/settings |

Choose based on actual protocol and security needs, not solely perceived performance.

## 15. Ingress and certificate governance

- Restrict public ingress creation through policy and AppProjects.
- Prefer internal ALBs for private applications.
- Require HTTPS with approved ACM certificates for user-facing applications.
- Manage DNS through approved Route 53/external-dns workflow.
- Restrict wildcard hosts and broad security group CIDRs.
- Use WAF where appropriate for public HTTP applications.
- Monitor certificate expiry, target health and access logs.
- Avoid GitOps prune of critical load balancers without change approval.

## 16. Storage: EBS CSI

EBS CSI provisions Amazon EBS volumes for Kubernetes PersistentVolumes. EBS is AZ-scoped and generally ReadWriteOnce-style block storage; shared multi-node filesystem access requires a different design.

~~~bash
aws eks list-addons --cluster-name demo-eks-staging --region us-east-1
kubectl get csidriver ebs.csi.aws.com
kubectl -n kube-system get pods | grep ebs
~~~

Controller IAM must permit only necessary EBS operations, with KMS permissions where encryption uses a customer-managed key.

## 17. EBS StorageClass example

~~~yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted-staging
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
~~~

**Operational note:** Retain reduces accidental data loss but can leave chargeable orphaned volumes. Use inventory and approved cleanup. WaitForFirstConsumer aligns volume provisioning with the selected Pod's AZ.

## 18. EBS PVC and StatefulSet example

~~~yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-data
  namespace: demo-staging
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: gp3-encrypted-staging
  resources:
    requests:
      storage: 20Gi
~~~

Mount this PVC only to a disposable test workload with compatible scheduling. A PVC alone does not demonstrate application-consistent backup, durability or cross-AZ failover.

## 19. EBS topology and multi-AZ reliability

A Pod with an EBS volume is constrained by that volume's AZ. Multi-AZ replicas need independent volumes plus application replication, quorum and recovery design.

For PostgreSQL, Elasticsearch, MongoDB and other stateful systems, storage-level snapshots should complement database-native backup/restore and transaction consistency procedures. Do not assume copying a block snapshot alone guarantees logical consistency.

## 20. EBS snapshots and recovery

Use the AWS EBS CSI snapshot controller and VolumeSnapshot CRDs where supported. Snapshot operations require correct IAM, driver, snapshot class and volume topology.

~~~bash
kubectl get volumesnapshotclasses
kubectl get crd volumesnapshots.snapshot.storage.k8s.io
kubectl -n demo-staging get pvc,pv
~~~

Test restoration into a **new** PVC and disposable workload; never overwrite production data during a recovery drill. Define RPO/RTO and retention.

## 21. EFS CSI and shared filesystem

EFS supports regional multi-AZ shared filesystem access, subject to mount targets, network rules, access points and performance configuration. It can be appropriate for workloads needing ReadWriteMany, but it is not a drop-in replacement for low-latency database block storage.

~~~yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-staging
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-REPLACE
  directoryPerms: "750"
reclaimPolicy: Retain
volumeBindingMode: Immediate
~~~

The EFS filesystem ID is a placeholder. Verify EFS mount targets in required AZs, security groups allowing NFS TCP/2049, encryption, access point policy and driver IAM.

## 22. EBS versus EFS selection

| Requirement | EBS CSI | EFS CSI |
| --- | --- | --- |
| Typical access | Single-node block | Shared POSIX filesystem |
| AZ model | Zonal | Regional mount targets |
| Kubernetes modes | Commonly RWO | RWX supported |
| Database block I/O | Often appropriate | Requires careful validation |
| Scaling | Volume performance/capacity | Throughput mode and file operations |
| Backup | EBS snapshots + app backups | EFS backups + app backups |
| Cost | Provisioned GB, IOPS/throughput | Stored GB, throughput/access |

Validate performance with actual application I/O profiles and consider cross-AZ data transfer charges.

## 23. GitOps repository and ownership

~~~text
gitops/
  clusters/eks-staging/
    platform/
      vpc-cni/
      core-dns/
      aws-load-balancer-controller/
      ebs-csi/
      efs-csi/
      storageclasses/
      networkpolicies/
    apps/
      demo-web/
        deployment.yaml
        service.yaml
        ingress.yaml
        pvc.yaml
  policies/
    ingress-security/
    storage-retention/
  tests/
    dns/
    ingress/
    storage/
~~~

Platform controllers and CRDs should be managed by a privileged platform AppProject. Application AppProjects should have narrow destination namespaces and permitted resource kinds. Avoid overlapping Terraform and Argo CD ownership of the same add-on.

## 24. GitLab validation pipeline

~~~yaml
stages: [render, validate, policy]

render:
  stage: render
  image: registry.example.internal/ci/kustomize:PINNED_DIGEST
  script:
    - kustomize build gitops/clusters/eks-staging/apps/demo-web > rendered.yaml
  artifacts:
    paths: [rendered.yaml]
    expire_in: 1 day

validate:
  stage: validate
  image: registry.example.internal/ci/kubeconform:PINNED_DIGEST
  needs: [render]
  script:
    - kubeconform -strict -summary rendered.yaml

policy:
  stage: policy
  image: registry.example.internal/ci/policy-tools:PINNED_DIGEST
  needs: [render]
  script:
    - ./ci/check-ingress-exposure.sh rendered.yaml
    - ./ci/check-storage-retention.sh rendered.yaml
~~~

The internal scripts and pinned images are illustrative; implement them in the repository. CRDs require matching schemas, and a schema-valid manifest can still be insecure.

## 25. Observability baseline

Monitor VPC CNI IP allocation, subnet free addresses, CoreDNS error rate/latency, service endpoint readiness, ALB/NLB target health, controller reconcile errors, 4xx/5xx rates, connection resets, EBS attach/detach time, PVC Pending duration, EFS mount failures, volume capacity, storage IOPS/latency and cross-AZ transfer cost.

Metric names differ by version and provider. Validate actual telemetry before writing alerts.

## 26. Lab A — VPC subnet and Pod IP inventory

1. Identify VPC, node subnets and AZs.
2. Record free subnet IPs and EC2 ENI limits.
3. Inspect VPC CNI version and Pod allocation.
4. Estimate IP demand for planned scale-up.
5. Identify bottlenecks and remediation options.
6. Save redacted evidence.

**Pass:** capacity forecast includes Pod IPs, not only CPU/memory.

## 27. Lab B — CoreDNS and Service discovery

1. Verify CoreDNS replicas and health.
2. Deploy disposable DNS test Pod.
3. Resolve Kubernetes Service names.
4. Resolve approved external DNS names.
5. Simulate a namespace-local DNS policy error rather than restarting shared CoreDNS.
6. Restore connectivity and document failure path.

**Pass:** service discovery works and failure cause is isolated.

## 28. Lab C — NetworkPolicy isolation

1. Confirm policy enforcement is enabled.
2. Deploy client, server and unauthorized test Pods.
3. Apply a scoped ingress policy.
4. Verify authorized client connects.
5. Verify unauthorized client is denied.
6. Test DNS and monitoring exceptions.

**Pass:** intended allow/deny behavior is enforced, not merely accepted by API.

## 29. Lab D — ALB ingress provisioning

1. Deploy synthetic HTTP application and ClusterIP Service.
2. Apply internal ALB Ingress.
3. Verify controller IAM and subnet discovery.
4. Inspect ALB, listeners and target groups.
5. Test private DNS and target health.
6. Remove test resources and confirm cleanup.

**Pass:** only approved private ingress is created.

## 30. Lab E — ALB target-type comparison

1. Review ip and instance target modes.
2. Create an isolated ip-mode test Ingress.
3. Inspect registered target IPs and ports.
4. Compare with approved instance-mode configuration in documentation or staging.
5. Test readiness failures and recovery.
6. Record security group and health-check behavior.

**Pass:** operators can trace target registration and diagnose unhealthy targets.

## 31. Lab F — NLB TCP Service

1. Deploy a synthetic TCP echo application, not a real database.
2. Create internal NLB Service.
3. Verify target type and listener.
4. Test private TCP connectivity.
5. Simulate target unavailability.
6. Restore and delete test NLB.

**Pass:** L4 routing and recovery are verified without public exposure.

## 32. Lab G — TLS and DNS readiness

1. Request or select approved staging ACM certificate.
2. Configure private/public DNS only as approved.
3. Validate HTTPS listener and certificate chain.
4. Test incorrect host and expired-certificate alerting using a test harness.
5. Confirm redirect and TLS policy.
6. Record renewal ownership.

**Pass:** intended hostname uses valid TLS and controlled DNS.

## 33. Lab H — EBS CSI dynamic provisioning

1. Verify EBS CSI driver and IAM.
2. Apply encrypted gp3 StorageClass.
3. Create disposable PVC and workload.
4. Confirm PV bound in correct AZ.
5. Perform basic read/write test with synthetic data.
6. Review reclaim policy and cleanup.

**Pass:** encrypted EBS volume mounts successfully.

## 34. Lab I — EBS AZ mismatch

1. Create a disposable EBS-backed PVC.
2. Identify PV node affinity.
3. Attempt incompatible Pod AZ scheduling in staging.
4. Observe scheduler events.
5. Restore compatible node placement.
6. Document multi-AZ implications.

**Pass:** AZ binding failures are diagnosed without data loss.

## 35. Lab J — EBS snapshot restore

1. Write synthetic data to disposable volume.
2. Create approved VolumeSnapshot.
3. Wait for snapshot readiness.
4. Restore to a new PVC.
5. Validate restored synthetic content.
6. Record RPO/RTO and retention.

**Pass:** independent restore succeeds; original PVC remains unchanged.

## 36. Lab K — EFS shared access

1. Configure approved EFS filesystem and mount targets.
2. Validate NFS security group access.
3. Install EFS CSI driver and StorageClass.
4. Mount shared PVC into two disposable Pods.
5. Verify shared file visibility and permissions.
6. Review performance and cleanup.

**Pass:** ReadWriteMany access functions with scoped permissions.

## 37. Lab L — CSI IAM denial

1. Remove a narrowly scoped staging EBS CSI permission.
2. Create a disposable PVC.
3. Observe provisioning failure and AWS AccessDenied.
4. Inspect driver logs and CloudTrail.
5. Restore only required permission.
6. Verify successful provisioning.

**Pass:** IAM failure is diagnosable without administrator privileges.

## 38. Lab M — GitOps ingress and storage policy

1. Propose ingress/storage changes through protected MR.
2. Run schema and security policy checks.
3. Reject an unapproved internet-facing ingress.
4. Reject unsafe storage reclaim changes without approval.
5. Merge compliant manifests.
6. Verify Argo CD sync and resource ownership.

**Pass:** risky exposure and data deletion changes are blocked before deployment.

## 39. Lab N — Network and storage incident drill

1. Simulate a staging ALB target failure.
2. Simulate a separate disposable PVC attach failure.
3. Observe dashboards and alerts.
4. Diagnose independently using events, controller logs and AWS APIs.
5. Restore healthy configuration.
6. Record timeline and recovery evidence.

**Pass:** both incidents recover without broad security bypass.

## 40. Lab O — FinOps and disaster-recovery acceptance

1. Inventory ALB/NLB, NAT, EBS, EFS and cross-AZ costs.
2. Confirm encrypted backup and snapshot retention.
3. Restore a disposable workload from backup.
4. Review orphaned load balancers and volumes.
5. Measure storage performance and restore time.
6. Document production-ready improvements.

**Pass:** recovery and cost controls are validated together.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Pods cannot get IP | Subnet/ENI exhaustion | Restore IP capacity |
| 2 | CNI DaemonSet unhealthy | IAM, network or version mismatch | Inspect aws-node |
| 3 | DNS resolution times out | CoreDNS/upstream/network | Check Pods and policy |
| 4 | ClusterIP Service unreachable | Endpoint or dataplane issue | Inspect EndpointSlices |
| 5 | NetworkPolicy has no effect | Enforcement disabled | Validate CNI capability |
| 6 | NetworkPolicy blocks DNS | Missing egress allowance | Add scoped DNS rule |
| 7 | ALB not created | IAM/subnet tags/controller | Inspect controller events |
| 8 | ALB unhealthy targets | Readiness/SG/health path | Fix target reachability |
| 9 | Wrong ALB scheme | Ingress annotation/subnet | Correct reviewed config |
| 10 | TLS handshake fails | ACM/hostname/listener | Verify certificate chain |
| 11 | NLB stuck Pending | Controller/class/subnet | Verify Service ownership |
| 12 | PVC Pending | CSI IAM/StorageClass/topology | Inspect provisioning |
| 13 | EBS volume cannot attach | AZ mismatch/attachment limits | Restore compatible placement |
| 14 | EBS latency spikes | IOPS/throughput pressure | Measure and rightsize |
| 15 | Snapshot never Ready | CRDs/controller/IAM | Repair snapshot stack |
| 16 | EFS mount timeout | NFS SG/mount targets/DNS | Restore port 2049 path |
| 17 | EFS permission denied | Access point/POSIX/IAM | Correct scoped permissions |
| 18 | GitOps prunes storage | Unsafe prune/ownership | Recover from backup and policy |

## 42. Production runbook — Pod networking failure

1. Identify impacted namespaces, nodes and AZs.
2. Inspect Pod events, aws-node and subnet IP capacity.
3. Check CNI version, ENI allocation, security groups and routes.
4. Determine whether issue is IP exhaustion, IAM or dataplane.
5. Restore capacity or roll back approved CNI change.
6. Verify Pod IP allocation, DNS and application health.
7. Record blast radius and remediation.

## 43. Production runbook — ALB/NLB outage

1. Identify load balancer ARN, target group and affected Service/Ingress.
2. Inspect controller health and Kubernetes events.
3. Validate AWS target health, security groups, listeners and DNS.
4. Check Pod readiness, endpoints and network reachability.
5. Restore reviewed GitOps config or target capacity.
6. Verify TLS, traffic and application SLOs.
7. Preserve logs and incident timeline.

## 44. Production runbook — EBS provisioning/attach failure

1. Identify PVC/PV, StorageClass, CSI driver and selected AZ.
2. Inspect CSI controller/node logs and Kubernetes events.
3. Check IAM, KMS, quotas, volume state and node attachment limits.
4. Confirm volume topology matches Pod scheduling.
5. Restore compatible capacity or correct configuration.
6. Avoid deleting PV/PVC until reclaim policy and backups are reviewed.
7. Validate data integrity and application recovery.

## 45. Production runbook — EFS mount incident

1. Identify EFS filesystem, access point and affected Pods.
2. Check CSI driver, mount targets and NFS TCP/2049.
3. Validate DNS, security groups, POSIX permissions and IAM.
4. Restore connectivity or access policy through approved change.
5. Validate shared file consistency and application readiness.
6. Record latency, throughput and recovery evidence.

## 46. Production runbook — storage recovery

1. Freeze destructive GitOps or storage changes.
2. Confirm latest valid application-consistent backup and snapshot.
3. Restore into isolated PVC/namespace.
4. Validate data and application semantics before cutover.
5. Execute controlled workload recovery.
6. Measure RPO/RTO and reconcile GitOps state.
7. Audit orphaned volumes and retention.

## 47. Evidence template

~~~text
Change / incident ID:
AWS account, region, cluster and VPC:
CNI version, IP mode and subnet capacity:
CoreDNS health and Service reachability:
ALB/NLB ARN, target mode and TLS:
Controller IAM and workload identity:
NetworkPolicy enforcement test:
EBS CSI and EFS CSI versions:
StorageClass, PVC/PV and AZ:
Encryption, snapshot and backup evidence:
GitOps revision and approvals:
Observed application SLO:
RPO/RTO and recovery duration:
Cost and orphan resource inventory:
Evidence archive and owner:
~~~

## 48. Scored enterprise assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| VPC CNI, IP planning and DNS | 20 | Pod connectivity and capacity |
| Load balancer security and reliability | 20 | ALB/NLB and TLS validation |
| EBS/EFS storage operations | 20 | PVC and performance tests |
| Network isolation and IAM | 15 | Denial and scoped access tests |
| GitOps governance and observability | 15 | Reviewed changes and alerts |
| Backup, recovery and FinOps | 10 | Restore drill and cost review |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failures: unapproved public ingress, unencrypted sensitive storage, inability to restore data, unrestricted controller IAM, or uncontrolled destructive GitOps pruning.

## 49. Final acceptance checklist

- [ ] Pod IP and ENI capacity are forecasted.
- [ ] VPC CNI and CoreDNS are healthy and monitored.
- [ ] Service and EndpointSlice connectivity verified.
- [ ] NetworkPolicy enforcement proven by tests.
- [ ] AWS Load Balancer Controller IAM restricted.
- [ ] ALB/NLB target modes, subnet tags and health checks validated.
- [ ] TLS, DNS and public exposure controls reviewed.
- [ ] EBS CSI provisioning, AZ affinity and encryption tested.
- [ ] EFS CSI shared access and NFS security verified.
- [ ] Snapshot and application-consistent restore tested.
- [ ] Storage reclaim and GitOps prune policies approved.
- [ ] Fifteen hands-on labs have evidence.
- [ ] Five production recovery runbooks reviewed.
- [ ] Operational SLO, RPO/RTO and cost acceptance complete.

## 50. Knowledge check

1. Why can Pod IP exhaustion occur with spare node CPU?
2. What is the difference between ALB ip and instance target modes?
3. Why must NetworkPolicy enforcement be tested rather than assumed?
4. What causes CoreDNS failures besides CoreDNS itself?
5. When should ALB versus NLB be used?
6. Why does EBS constrain Pods to an Availability Zone?
7. How does WaitForFirstConsumer help zonal storage scheduling?
8. When is EFS preferable to EBS?
9. Why are EBS snapshots insufficient for some database recovery objectives?
10. What GitOps controls prevent accidental storage deletion?

## 51. References

- [Amazon VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS Networking](https://docs.aws.amazon.com/eks/latest/userguide/eks-networking.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/)
- [EBS CSI Driver](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [EFS CSI Driver](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 068 complete.** Next: **Chapter 069 — EKS Security, Workload Identity, Observability and Upgrade Operations**.