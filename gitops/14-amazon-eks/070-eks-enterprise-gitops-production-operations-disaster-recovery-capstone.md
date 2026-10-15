# Chapter 070 — EKS Enterprise GitOps Production Operations and Disaster Recovery Capstone

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 14:** Amazon EKS — Final Capstone  
**Chapter:** 070 / 100  
**Audience:** EKS Platform Engineers, SREs, DBREs, DevSecOps, Incident Commanders and Cloud Architects

> **Safety and cost:** Perform every destructive exercise in an isolated staging AWS account and disposable cluster with synthetic data. Never simulate AZ outages by deleting production subnets, revoke shared IAM roles, disable critical admission policies, or destroy a live EKS cluster. Obtain approval for spending and cleanup. An EKS control-plane minor-version downgrade is generally unsupported.

## 1. Capstone mission

Design, deploy, secure, operate and recover an enterprise Amazon EKS platform managed through Terraform, GitLab CI/CD and Argo CD. This is an integrated acceptance project for Chapters 066–069.

**Required proof:** a reviewer can trace a signed image from approved GitLab source to a healthy Kubernetes workload, verify that IAM and networking are least-privileged, observe operational SLOs, restore a stateful application, and recover from simulated failures without bypassing governance.

## 2. Integrated architecture

~~~text
AWS Organizations / approved staging account
       |
Terraform protected plan and apply
       |
Multi-AZ VPC / private subnets / endpoints / NAT
       |
Amazon EKS managed control plane
       |
EKS access entries / audit logs / CloudTrail
       |
Managed On-Demand bootstrap node group
       |                          \
  CoreDNS, CNI, Argo CD       Karpenter controller
                                  |
                       NodePools / EC2NodeClasses
                                  |
                        application capacity
       |
GitLab CI: test -> build -> SBOM -> scan -> sign
       |
Protected GitOps merge request with image digest
       |
Argo CD AppProjects / Applications
       |
Admission controls -> Deployment / StatefulSet
       |                         |
   ALB/NLB ingress          EBS CSI / EFS CSI
       |                         |
   application SLOs        backup / snapshot / restore
       \                         /
         Prometheus / Grafana / CloudWatch
                      |
             SRE alerts and runbooks
~~~

**Ownership boundary:** Terraform owns EKS infrastructure and approved AWS IAM/networking; Argo CD owns selected Kubernetes controllers, policies and applications. Karpenter owns its NodeClaims. Do not let Terraform, Argo CD and Karpenter compete for the same resource.

## 3. Acceptance scope

| Domain | Control objective | Primary evidence |
| --- | --- | --- |
| Infrastructure | Multi-AZ EKS with controlled API access | Terraform plan, EKS describe |
| Identity | Least-privilege EKS and Pod access | Access entries, IAM/RBAC tests |
| Capacity | Bootstrap nodes and elastic application pools | NodePools, NodeClaims, metrics |
| Networking | DNS, Pod IPs, private ingress | CNI, CoreDNS, ALB health |
| Storage | Encrypted persistent data and recovery | PVC, snapshots, restore drill |
| Delivery | Signed digest promoted by protected GitOps MR | Pipeline, signature, Argo CD |
| Security | Admission, secrets, audit and isolation | Denial tests, CloudTrail |
| Reliability | SLO monitoring and safe disruption | Dashboards, alerts, PDB tests |
| DR | Rebuild and recover in isolated environment | RPO/RTO, recovery transcript |
| FinOps | Capacity, load balancer and storage accountability | Cost allocation report |

## 4. Service objectives

Define explicit application-specific values before beginning. Example *staging acceptance targets* (not universal production SLOs):

| Indicator | Exercise target |
| --- | --- |
| Deployment health | All required replicas Ready |
| DNS / service routing | No sustained resolution failures |
| Provisioning | Pending workload becomes schedulable within reviewed objective |
| Ingress | Target group healthy and TLS valid |
| Backup | Snapshot and application backup succeed |
| Restore | Synthetic data passes integrity verification |
| RPO | No more than 15 minutes in designed test |
| RTO | No more than 60 minutes in designed test |
| Security | All required negative authorization tests denied |

The backup schedule, dataset size, database engine and recovery architecture must be capable of meeting the selected RPO/RTO. Do not claim compliance from an unmeasured tabletop alone.

## 5. Prerequisites and preflight

- Dedicated nonproduction AWS account, approved region and VPC CIDR.
- Healthy EKS cluster with managed node group and access entries.
- Karpenter compatible with the EKS Kubernetes version.
- VPC CNI, CoreDNS, kube-proxy, EBS CSI and AWS Load Balancer Controller.
- Approved Argo CD installation and restricted AppProjects.
- GitLab repository, protected branch, CI identity and registry.
- Signed immutable synthetic image, SBOM and provenance.
- Synthetic stateful test dataset and approved backup destination.
- CloudWatch/Prometheus/Grafana and incident alert routing.
- Terraform remote state encryption, locking and recovery.
- Security approval, cost budget and teardown plan.

~~~bash
aws sts get-caller-identity
aws eks describe-cluster --name demo-eks-staging --region us-east-1 \
  --query 'cluster.{Status:status,Version:version}'
kubectl config current-context
kubectl get nodes -o wide
kubectl -n kube-system get pods
kubectl get nodepools,nodeclaims
kubectl get storageclasses,ingressclasses
kubectl -n argocd get applications.argoproj.io
~~~

**Stop conditions:** incorrect AWS account, unknown kubeconfig context, unapproved spend, missing backup, insufficient staging isolation or unclear resource ownership.

## 6. Reference repository

~~~text
eks-enterprise-capstone/
  infra/
    modules/
      vpc/
      eks/
      iam/
      observability/
    environments/
      staging/
        backend.tf
        providers.tf
        main.tf
        variables.tf
        outputs.tf
  gitops/
    bootstrap/
      argocd/
    clusters/
      eks-staging/
        platform/
          karpenter/
          networking/
          storage/
          security/
          monitoring/
        apps/
          stateless-demo/
          stateful-demo/
    policies/
      admission/
      identity/
      ingress/
  ci/
    validate-infra.sh
    verify-image.sh
    check-gitops.sh
    generate-evidence.sh
  runbooks/
    api-access-outage.md
    node-capacity-incident.md
    networking-outage.md
    storage-recovery.md
    gitops-rollback.md
    cluster-rebuild.md
  evidence/
    acceptance-report.md
~~~

All script names represent internal implementations to build and test; they are not supplied by AWS.

## 7. Terraform governance

Use pinned, compatible Terraform, provider and module versions. Encrypt and version remote state, enable supported locking, restrict state readers, review plans and separate staging from production state. Treat plan files as potentially sensitive.

~~~bash
terraform -chdir=infra/environments/staging init
terraform -chdir=infra/environments/staging fmt -check
terraform -chdir=infra/environments/staging validate
terraform -chdir=infra/environments/staging plan -out=staging.tfplan
terraform -chdir=infra/environments/staging show staging.tfplan
~~~

Apply only after approval. A private-only EKS endpoint requires an authorized network path from the operator and CI runner.

## 8. EKS access and identity governance

Review EKS access entries, Kubernetes RBAC, IAM role trust and workload identity separately.

~~~bash
aws eks list-access-entries --cluster-name demo-eks-staging --region us-east-1
aws eks list-pod-identity-associations --cluster-name demo-eks-staging --region us-east-1
kubectl auth can-i list pods --all-namespaces
kubectl auth can-i get secrets -n demo-staging
~~~

IRSA uses a trusted Kubernetes ServiceAccount OIDC subject; EKS Pod Identity uses a cluster association and agent. Choose per controller. Avoid granting a GitLab runner cluster-admin merely to update a GitOps overlay.

## 9. Karpenter and managed node-group separation

Keep system controllers on a resilient On-Demand managed node group. Use Karpenter for workload capacity with NodePool limits, allowed instance types, Spot/On-Demand policy and conservative disruption budgets. Test EC2 quota, subnet IP capacity, AZ diversity and workload PodDisruptionBudgets.

Karpenter NodePools, EC2NodeClasses and NodeClaims have version-specific APIs. Validate against installed CRDs rather than assuming older Provisioner examples apply.

## 10. Network and ingress governance

Validate VPC CNI Pod IP allocation, CoreDNS, EndpointSlices, Service routing and internal ALB/NLB target health. Require approved subnet discovery, least-privilege AWS Load Balancer Controller identity, HTTPS/TLS for applicable services and network isolation.

~~~bash
kubectl -n kube-system get daemonset aws-node
kubectl -n kube-system get deployment coredns
kubectl -n demo-staging get services,endpointslices,ingress
kubectl -n kube-system logs deployment/aws-load-balancer-controller --tail=100
~~~

NetworkPolicy only enforces traffic isolation when the installed dataplane supports and enables enforcement.

## 11. Persistent storage and DR

Use encrypted EBS CSI StorageClasses with WaitForFirstConsumer for zonal volumes; select EFS CSI only when shared filesystem semantics are needed. Document reclaim policy and GitOps prune safeguards.

For database-like workloads, pair CSI snapshots with application-consistent backup/restore. A block snapshot alone may not satisfy logical consistency or multi-AZ disaster recovery. Test restore to a **new** PVC in an isolated namespace before any cutover.

## 12. Protected delivery pipeline

~~~yaml
stages: [validate, test, build, verify, promote]

validate:
  stage: validate
  image: registry.example.internal/ci/platform-tools:PINNED_DIGEST
  script:
    - ./ci/validate-infra.sh
    - ./ci/check-gitops.sh

test:
  stage: test
  image: registry.example.internal/ci/test-tools:PINNED_DIGEST
  script:
    - ./ci/run-tests.sh

build:
  stage: build
  image: registry.example.internal/ci/builder:PINNED_DIGEST
  script:
    - ./ci/build-and-push.sh

verify:
  stage: verify
  image: registry.example.internal/ci/security-tools:PINNED_DIGEST
  script:
    - ./ci/verify-image.sh

promote:
  stage: promote
  image: registry.example.internal/ci/gitlab-tools:PINNED_DIGEST
  script:
    - ./ci/propose-protected-gitops-mr.sh
~~~

These are intentionally illustrative jobs. Implement trusted artifact passing, SBOM/scanning, signature and provenance checks, short-lived CI credentials and protected approvals. Do not claim image verification solely from an image name or registry allowlist.

## 13. Argo CD release contract

Each release must record source SHA, pipeline ID, image digest, signer identity, GitOps MR and approver, Argo CD revision, policy decision, running Pod imageID and application health.

Keep privileged platform add-ons in a dedicated AppProject. Use scoped application AppProjects for workload namespaces. Configure resource pruning carefully for persistent volumes, load balancers and security-critical resources.

## 14. Observability and alerting

At minimum, capture EKS audit/control-plane logs, CloudTrail, node Ready status, Pod Pending duration, VPC CNI IP allocation, CoreDNS errors, ALB target health, CSI attach/provisioning failures, Argo CD reconciliation and application latency/error/availability SLOs.

Use labels that identify cluster, namespace, workload and owner without exposing secret values. Confirm metric names against actual deployed controller versions.

## 15. Upgrade and change readiness

Inventory EKS, managed node, Karpenter, VPC CNI, CoreDNS, kube-proxy, CSI, ALB Controller, Argo CD and admission controller versions. Check deprecated APIs and upgrade insights. Rehearse in staging before production.

**Do not treat EKS control-plane downgrade as a rollback strategy.** Plan compatible forward repair, add-on/node rollback where supported, or replacement-cluster migration.

## 16. Lab A — Architecture and change review

1. Verify AWS account, region and EKS cluster.
2. Inspect VPC CIDR, subnet AZs, API endpoint mode and Terraform state.
3. Review IaC plan and resource ownership.
4. Confirm approved cost ceiling and teardown owner.
5. Verify emergency access path.
6. Archive redacted approval evidence.

**Pass:** no unreviewed public API exposure, conflicting resource owner or wrong account.

## 17. Lab B — Secure EKS access

1. Inventory access entries and associated policies.
2. Create staging read-only access through approved IaC.
3. Verify allowed Pod listing.
4. Verify Secret access and cluster mutation are denied.
5. Correlate denial with Kubernetes audit logs.
6. Revoke the test principal.

**Pass:** least privilege is demonstrated.

## 18. Lab C — Workload identity isolation

1. Choose IRSA or EKS Pod Identity for a synthetic application.
2. Create narrowly scoped AWS IAM permissions.
3. Bind identity to an exact ServiceAccount.
4. Verify authorized AWS read.
5. Verify unauthorized API action fails.
6. Confirm no static credentials appear in Pod or CI configuration.

**Pass:** role use is limited to the intended workload.

## 19. Lab D — Bootstrap node availability

1. Verify managed On-Demand system node group.
2. Inspect Karpenter controller placement.
3. Reduce only disposable application NodePool capacity.
4. Confirm Argo CD, CoreDNS and Karpenter remain Ready.
5. Restore workload capacity.
6. Record recovery duration.

**Pass:** the autoscaler is not dependent solely on nodes it creates.

## 20. Lab E — Karpenter capacity burst

1. Deploy synthetic CPU-requesting workload.
2. Increase replicas to exceed current application capacity.
3. Observe Pending Pods and NodeClaims.
4. Confirm new nodes register and Pods become Ready.
5. Measure provisioning latency and instance cost.
6. Scale down and inspect safe consolidation.

**Pass:** scaling meets the documented objective and NodePool limits.

## 21. Lab F — Spot interruption resilience

1. Use disposable interruption-tolerant workload.
2. Confirm interruption handling infrastructure and alerts.
3. Simulate interruption via an approved test harness.
4. Observe drain/replacement and fallback capacity.
5. Validate retries, checkpoint behavior and readiness.
6. Record service impact.

**Pass:** application recovers without depending on a single Spot pool.

## 22. Lab G — Pod networking and DNS

1. Record subnet free IPs and VPC CNI health.
2. Deploy synthetic DNS/client Pods.
3. Verify CoreDNS and Service name resolution.
4. Test Pod-to-Service connectivity.
5. Simulate namespace-local NetworkPolicy misconfiguration.
6. Restore policy and confirm connectivity.

**Pass:** DNS, routing and enforcement are diagnosable.

## 23. Lab H — Internal ALB and TLS

1. Deploy synthetic HTTP service.
2. Provision internal ALB using approved controller.
3. Verify target type, health and security groups.
4. Configure approved ACM certificate and DNS.
5. Test HTTPS and readiness failure recovery.
6. Remove test ingress and confirm AWS cleanup.

**Pass:** no accidental public ingress or orphaned load balancer.

## 24. Lab I — Encrypted EBS persistence

1. Verify EBS CSI driver identity and StorageClass.
2. Create encrypted disposable PVC.
3. Deploy stateful synthetic application.
4. Confirm PV AZ affinity and mount.
5. Write synthetic data and verify persistence after Pod restart.
6. Document reclaim policy and cleanup.

**Pass:** encrypted storage is provisioned with known topology.

## 25. Lab J — Backup and isolated restore

1. Generate synthetic application data with a known checksum.
2. Create application-consistent backup and supported CSI snapshot.
3. Record backup timestamp and recovery point.
4. Restore into a new PVC and isolated namespace.
5. Verify checksum and application-level integrity.
6. Measure RPO/RTO and clean up test resources.

**Pass:** verified restore meets selected objectives.

## 26. Lab K — Admission and signed image enforcement

1. Build and sign synthetic OCI image by digest.
2. Record SBOM, scan and provenance.
3. Deploy compliant workload in audit mode.
4. Attempt unsigned image deployment in scoped enforcement namespace.
5. Verify denial and capture admission reason.
6. Restore approved signed digest.

**Pass:** untrusted artifact cannot be admitted.

## 27. Lab L — GitLab-to-Argo CD promotion

1. Run source tests and security pipeline.
2. Propose digest change through protected GitOps MR.
3. Obtain independent approval.
4. Merge and observe Argo CD reconciliation.
5. Verify actual Pod imageID and readiness.
6. Revert through approved GitOps MR.

**Pass:** promotion and rollback are traceable without CI cluster-admin.

## 28. Lab M — AZ/node disruption drill

1. Deploy replicated synthetic application across AZs.
2. Validate PDB and topology spread.
3. Drain one disposable application node under approved procedure.
4. Observe rescheduling and ALB target health.
5. Restore capacity and check stateful volume topology.
6. Measure impact and recovery time.

**Pass:** availability stays within the exercise objective.

## 29. Lab N — EKS upgrade rehearsal

1. Inventory versions and deprecated APIs.
2. Confirm compatibility of CNI, CoreDNS, CSI, Karpenter, Argo CD and admission.
3. Verify backups and recovery access.
4. Execute approved staging upgrade sequence.
5. Validate control plane, nodes, networking, storage and GitOps.
6. Record forward recovery for unsupported downgrade scenarios.

**Pass:** staging upgrade meets readiness criteria.

## 30. Lab O — Full recovery in isolated cluster

1. Provision an isolated recovery VPC/EKS environment.
2. Restore approved Terraform and GitOps revisions.
3. Recreate IAM, workload identity, secrets access and policy controllers.
4. Restore synthetic application data from verified backup.
5. Deploy approved signed digest.
6. Validate DNS, ingress, storage, application and audit logging.
7. Measure end-to-end RPO/RTO and preserve evidence.

**Pass:** secure application service is reconstructed within documented objectives.

## 31. Lab P — FinOps and teardown

1. Inventory EC2, EKS, NAT, ALB/NLB, EBS, EFS, snapshots and CloudWatch costs.
2. Compare managed nodes and Karpenter utilization.
3. Identify orphaned resources and unused volumes.
4. Validate budget alarms and resource tags.
5. Review backup retention before cleanup.
6. Tear down only approved disposable resources.

**Pass:** no unintended chargeable test resources remain.

## 32. Lab Q — Incident command tabletop

1. Declare simulated multi-symptom outage: Pending Pods, ALB 5xx and failed PVC mount.
2. Assign incident commander, communications owner and technical leads.
3. Establish timeline from Argo CD, Kubernetes events, CloudWatch and CloudTrail.
4. Identify shared dependency versus independent causes.
5. Prioritize containment and safe recovery.
6. Produce concise RCA, corrective actions and follow-up owners.

**Pass:** responders can coordinate recovery without destructive guesswork.

## 33. Troubleshooting — twenty integrated scenarios

| # | Symptom | Primary investigation | Safe response |
| --- | --- | --- | --- |
| 1 | EKS API timeout | Endpoint DNS, routes, VPN | Restore approved connectivity |
| 2 | kubectl Unauthorized | IAM principal/access entry | Repair scoped authentication |
| 3 | kubectl Forbidden | Kubernetes RBAC | Correct RoleBinding |
| 4 | Karpenter controller Pending | Bootstrap group capacity | Restore system nodes |
| 5 | NodeClaim fails | IAM, quotas, AMI, subnets | Repair constrained provisioning |
| 6 | Spot workload outage | Interruption/fallback/PDB | Restore On-Demand floor |
| 7 | Pods Pending | Requests, taints, topology | Adjust capacity or scheduling |
| 8 | Pod IP exhaustion | VPC CNI/ENI/subnet | Restore address capacity |
| 9 | CoreDNS failure | Upstream DNS, network, replicas | Repair DNS dependency |
| 10 | Service unreachable | EndpointSlices, policies | Restore endpoint path |
| 11 | ALB missing | Controller IAM/subnet tags | Repair reconciliation |
| 12 | ALB targets unhealthy | Probes, SGs, Pod readiness | Restore target health |
| 13 | EBS PVC Pending | CSI, KMS, topology | Repair provisioning |
| 14 | EBS cannot attach | Wrong AZ/attachment limit | Schedule compatible node |
| 15 | EFS mount timeout | NFS SG, mount targets | Restore TCP/2049 path |
| 16 | ESO Secret not Ready | IAM, provider, remote key | Repair least privilege |
| 17 | Image admission denied | Signature, provenance, policy | Deploy verified digest |
| 18 | Argo CD OutOfSync | Git desired state, policy | Reconcile reviewed revision |
| 19 | Upgrade stalled | PDB, API, add-on skew | Forward repair |
| 20 | DR restore corrupt | Backup consistency/keys | Use verified recovery point |

## 34. Runbook — EKS API access outage

1. Confirm AWS account, cluster status and endpoint configuration.
2. Determine whether all clients or only one network are affected.
3. Test DNS, routes, VPN/Direct Connect and security groups.
4. Validate IAM caller, EKS access entries and Kubernetes RBAC.
5. Restore private connectivity rather than opening broad public CIDRs.
6. Verify Argo CD and operational access.
7. Record incident impact and recovery evidence.

## 35. Runbook — node and capacity incident

1. Inspect Pending Pods, scheduling events and resource requests.
2. Check managed node group health and Karpenter controller.
3. Inspect NodePool/NodeClass conditions, NodeClaims and AWS quotas.
4. Check subnet IP capacity, AMI, security groups and IAM.
5. Restore approved On-Demand capacity or safe instance diversity.
6. Validate Pod readiness, topology and SLOs.
7. Record cost and capacity forecast changes.

## 36. Runbook — networking and ingress incident

1. Identify affected AZ, namespace, Service and load balancer.
2. Inspect VPC CNI, CoreDNS, EndpointSlices and NetworkPolicy.
3. Check ALB/NLB target health, security groups, DNS and TLS.
4. Restore approved GitOps configuration or controller capacity.
5. Validate private/public exposure and application health.
6. Preserve events and AWS evidence.

## 37. Runbook — storage and database recovery

1. Freeze destructive changes and confirm PVC/PV reclaim policy.
2. Inspect CSI driver, KMS, volume AZ and attachment events.
3. Select verified application-consistent backup and snapshot.
4. Restore into a separate PVC/namespace.
5. Validate checksum, schema and application semantics.
6. Execute approved cutover with rollback path.
7. Measure RPO/RTO and archive evidence.

## 38. Runbook — compromised workload identity

1. Identify affected ServiceAccount, IAM role and cloud APIs.
2. Freeze affected promotions and contain credential access.
3. Inspect CloudTrail, EKS audit logs and role trust.
4. Revoke compromised trust or association.
5. Rotate exposed credentials and restore scoped permissions.
6. Redeploy approved workloads and validate denial tests.
7. Document incident and preventive changes.

## 39. Runbook — failed GitOps release

1. Identify source SHA, GitOps MR, Argo CD revision and image digest.
2. Determine whether failure is admission, image, secret, IAM or runtime.
3. Stop further unsafe promotions.
4. Revert GitOps revision or roll forward to verified artifact.
5. Check prune effects and protect persistent data.
6. Validate Pod imageID, ingress, readiness and SLO.
7. Record RCA and regression tests.

## 40. Runbook — failed EKS upgrade

1. Freeze concurrent add-on and application changes.
2. Inspect EKS update status and compatibility evidence.
3. Check deprecated APIs, admission webhooks and node skew.
4. Restore compatible add-ons and capacity.
5. Reconcile GitOps and verify workloads.
6. Choose supported forward repair or replacement-cluster migration.
7. Do not promise control-plane minor-version downgrade.
8. Record change review and postmortem.

## 41. Runbook — full disaster recovery

1. Declare disaster and identify RPO/RTO.
2. Establish clean recovery account/VPC/cluster.
3. Restore Terraform, EKS access, IAM and bootstrap capacity.
4. Reinstall approved add-ons and Argo CD.
5. Restore GitOps configuration, secrets trust and admission policies.
6. Restore application-consistent data to new storage.
7. Verify signed digest, DNS, ingress and application SLO.
8. Execute controlled traffic cutover and archive evidence.

## 42. Evidence template

~~~text
Capstone/change ID:
AWS account, region and cluster:
Terraform state and reviewed plan:
EKS version, endpoint mode and access entries:
IAM/IRSA/Pod Identity authorization tests:
Managed node group and Karpenter revisions:
Subnet IP capacity, CoreDNS and VPC CNI:
ALB/NLB health, TLS and exposure:
CSI driver, PVC/PV, encryption and snapshots:
GitLab pipeline, source SHA and image digest:
Signature, SBOM and provenance:
Argo CD revision and admission result:
CloudWatch/CloudTrail/Prometheus evidence:
Failure simulations and incident timeline:
Backup restore point and checksum:
Measured RPO/RTO and service SLO:
FinOps inventory and cleanup:
Independent reviewers and archive:
~~~

Never include plaintext secrets, private keys, AWS session credentials or decoded Kubernetes Secret values.

## 43. Scored enterprise readiness assessment

| Domain | Points | Required evidence |
| --- | ---: | --- |
| EKS architecture and Terraform governance | 15 | Reviewed IaC, access, AZs |
| IAM, secrets and admission security | 15 | Negative authorization tests |
| Capacity and Karpenter resilience | 15 | Scale and disruption labs |
| Networking and ingress | 10 | DNS, policy, ALB health |
| Storage and disaster recovery | 20 | Backup and measured restore |
| GitLab/Argo CD release governance | 10 | Signed digest, MR and rollback |
| Observability and incident response | 10 | Alerts and incident timeline |
| FinOps, ownership and evidence | 5 | Cost and audit report |
| **Total** | **100** | |

**Pass:** at least **85/100**, plus all critical controls: no unauthorized cluster-admin, no exposed credentials, no unreviewed public ingress, no unsigned workload admission in enforced scope, verified data restore, and measured recovery within approved RPO/RTO. Scoring cannot override a critical control failure.

## 44. Final acceptance checklist

- [ ] AWS account, region, endpoint and cluster verified.
- [ ] Terraform remote state, locking, encryption and recovery tested.
- [ ] EKS access entries, RBAC and break-glass access reviewed.
- [ ] Managed system nodes independent of Karpenter.
- [ ] NodePool capacity, disruption and Spot fallback tested.
- [ ] VPC CNI Pod IPs, CoreDNS and Service routing validated.
- [ ] NetworkPolicy enforcement and internal ingress proven.
- [ ] EBS/EFS encryption, AZ topology and reclaim policies reviewed.
- [ ] Application-consistent backup and isolated restore validated.
- [ ] IRSA/Pod Identity least-privilege tests passed.
- [ ] Signed immutable image and admission enforcement verified.
- [ ] GitLab protected GitOps promotion and rollback demonstrated.
- [ ] CloudTrail, EKS audit logs and operational alerts functioning.
- [ ] EKS upgrade and compatibility rehearsal documented.
- [ ] Seventeen labs completed with evidence.
- [ ] Eight incident runbooks reviewed.
- [ ] RPO/RTO, SLO and cost objectives accepted.
- [ ] Independent platform, security and SRE reviewers approve.

## 45. Knowledge check

1. Why must Karpenter run on independent bootstrap capacity?
2. How do EKS access entries differ from Kubernetes RBAC?
3. Why can Pod IP exhaustion block scaling even with spare CPU?
4. What is the difference between ALB ip and instance target modes?
5. Why is EBS topology relevant to stateful recovery?
6. Why are snapshots not always application-consistent?
7. How should GitLab CI and Argo CD divide deployment responsibilities?
8. Why must a signing identity be verified in addition to the image digest?
9. Why is EKS control-plane downgrade not a routine rollback plan?
10. What evidence proves a recovered EKS platform is both secure and operational?

## 46. References

- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [Karpenter](https://karpenter.sh/docs/)
- [Amazon VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)
- [EKS Control Plane Logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [EKS Cluster Upgrades](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 070 complete — Part 14 complete (Chapters 066–070).**

**Next:** Chapter 071 — Azure AKS GitOps Architecture, Cluster Provisioning and Platform Foundations, beginning Part 15: Azure AKS.