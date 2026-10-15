# Chapter 080 — GKE Enterprise GitOps Production Operations and Disaster Recovery Capstone

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 16:** Google Kubernetes Engine (GKE) — Final Capstone  
**Chapter:** 080 / 100  
**Audience:** SREs, Platform Engineers, DBREs, DevSecOps, Cloud Architects and Incident Commanders

> **Safety:** Run all exercises in an isolated Google Cloud staging project using synthetic data, dedicated service identities, approved quotas and budgets. Never destroy production clusters, volumes, backup archives or shared VPC resources. Disaster recovery must be demonstrated using independent recovery resources and verified backups, not assumed from Kubernetes replica counts.

## 1. Capstone mission

Build, operate, secure, upgrade and recover a production-oriented Google Kubernetes Engine platform managed through Terraform, GitLab CI/CD and Argo CD. Demonstrate end-to-end traceability from approved infrastructure changes and signed application artifacts to observable runtime behavior and independently verified data recovery.

This capstone integrates:

- Chapter 076 — GKE architecture, provisioning and platform foundations.
- Chapter 077 — Node pools, autoscaling, scheduling and capacity.
- Chapter 078 — VPC-native networking, Ingress, Gateway API and persistent storage.
- Chapter 079 — Workload Identity Federation, security, observability and upgrades.

**Required result:** A reviewer can reproduce the staging environment, deploy an approved signed image digest, test identity and admission controls, survive planned disruption, restore application-consistent data to a separate environment and verify measured SLO, RPO and RTO.

## 2. End-to-end architecture

~~~text
Google Cloud Organization / Org Policy / IAM
                      |
         Protected GitLab Terraform MR
                      |
        GCP project / VPC / Cloud DNS
                      |
    Subnet + Pod/Service secondary ranges
                      |
       Private regional GKE Standard
                /             \
         system pool         app pools
             |               /      \
          Argo CD       on-demand    Spot batch
             |               |
        GitOps sync      signed images
             |               |
         AppProjects     Artifact Registry
             |               |
        NetworkPolicy + Gateway API
                      |
          Workload Identity Federation
                      |
          Secret Manager / Google APIs
                      |
          Persistent Disk / Filestore
                      |
      application-consistent backups
                      |
      independent recovery GKE cluster
                      |
Cloud Audit Logs / Logging / Monitoring
                      |
        Managed Prometheus / SRE
~~~

Terraform owns GCP resources and GKE configuration. Argo CD owns approved Kubernetes objects. GKE-managed controllers own supported cloud load balancer, CSI and managed control-plane reconciliation. Avoid competing ownership.

## 3. Success criteria

| Domain | Required evidence |
| --- | --- |
| Landing zone | Approved project, IAM, Org Policy, budgets |
| Terraform | Reproducible reviewed plan and state |
| GKE | Regional cluster, stable system pool, resilient app pools |
| Networking | Private access, DNS, NetworkPolicy, internal Gateway |
| Identity | Least privilege and positive/negative WIF tests |
| Supply chain | Signed digest and admission denial of untrusted image |
| GitOps | Protected MR, AppProject restrictions, rollback |
| Storage | Persistent Disk and Filestore behavior, verified restore |
| Observability | Audit logs, metrics, synthetic alert |
| DR | Recovery cluster, measured RPO/RTO, data integrity |
| FinOps | Resource tagging, quota, budget, cleanup |

## 4. Recovery objectives

Set actual application-specific SLOs and RPO/RTO with the business owner. Illustrative staging exercise targets:

| Metric | Example target |
| --- | --- |
| Application ready replicas | All required replicas Ready after recovery |
| Identity | Unauthorized API calls denied |
| Ingress | Internal HTTPS endpoint healthy |
| Backup restore | Integrity and consistency verified |
| RPO | At most 15 minutes |
| RTO | At most 60 minutes |
| Audit coverage | Required control-plane and application events visible |

These are proposed targets, not guarantees. Cold cluster provisioning, DNS cutover, database restore size, image replication and region availability may exceed them. If measurements fail, redesign or revise the approved target.

## 5. Prerequisites

- Isolated Google Cloud project with billing and cost alert.
- Approved GKE region, Kubernetes version and quotas.
- gcloud, gke-gcloud-auth-plugin, Terraform, kubectl and Helm.
- Private management connectivity and Cloud DNS.
- Regional Standard GKE system/user node pools.
- Workload Identity Federation for GKE and least-privilege IAM.
- Artifact Registry with signed synthetic images.
- GitLab protected branches, OIDC federation and CODEOWNERS.
- Argo CD with restricted AppProjects.
- Gateway API or approved ingress controller.
- Persistent Disk CSI, Filestore CSI where supported.
- Cloud Logging, Cloud Monitoring and Managed Prometheus.
- Application-consistent backup, isolated restore and recovery region plan.
- Incident commander, change approver and teardown owner.

## 6. Safety preflight

~~~bash
gcloud config get-value project
gcloud container clusters list --project PROJECT_ID
kubectl config current-context
gcloud container clusters describe gke-staging \
  --region REGION --project PROJECT_ID \
  --format="yaml(status,location,currentMasterVersion,releaseChannel)"
kubectl get nodes -o wide
kubectl get pods -A
kubectl get storageclasses,csidrivers
kubectl -n argocd get applications.argoproj.io
~~~

**Stop conditions:** wrong project or cluster, unresolved production dependencies, absent backup, unknown Terraform state owner, missing private endpoint access, insufficient recovery quota, or unapproved budget.

## 7. Reference repository

~~~text
gke-enterprise-capstone/
  terraform/
    versions.tf
    providers.tf
    backend.tf
    project-services.tf
    network.tf
    iam.tf
    gke.tf
    nodepools.tf
    observability.tf
    outputs.tf
    environments/staging.tfvars
  gitops/
    bootstrap/argocd/
    clusters/gke-staging/
      platform/
        security/
        networking/
        gateway/
        storage/
        observability/
      applications/
        stateless-demo/
        stateful-demo/
  ci/
    validate-terraform.sh
    validate-manifests.sh
    verify-signatures.sh
    check-policy.sh
    generate-evidence.sh
  runbooks/
    private-access.md
    nodepool-capacity.md
    workload-identity.md
    ingress-dns.md
    persistent-storage.md
    gitops-recovery.md
    region-dr.md
  evidence/
    acceptance-report.md
~~~

Scripts and paths are examples; implement and validate them. Never commit state, credential JSON, access tokens, secret values or privileged kubeconfigs.

## 8. Terraform state and approvals

Use a secure, versioned remote backend with least-privilege access and tested state recovery. Pin Terraform/provider versions and validate GKE resource schema before apply.

~~~bash
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan \
  -var-file=environments/staging.tfvars \
  -out=staging.tfplan
terraform -chdir=terraform show staging.tfplan
~~~

Plan files may contain sensitive values. Protect them in CI and require independent approval for deletions, IAM changes and cluster upgrades.

## 9. VPC-native networking baseline

Verify primary node subnet and Pod/Service secondary ranges. Calculate expected IP allocation using max Pods per node and regional node scale, not merely total CIDR addresses.

Review VPC firewall, Cloud DNS, Private Google Access, Cloud NAT and private control-plane endpoint. Private nodes alone do not prove that the API endpoint is private.

## 10. Regional cluster and node pool design

Use reliable system capacity for critical controllers, resilient application pools across supported zones, autoscaling bounds, PodDisruptionBudgets and topology spread.

Regional pool node counts and autoscaling bounds may be per-zone or total depending on configuration. Validate actual VM inventory, regional quota and cost.

## 11. Workload placement and scaling

~~~yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  replicas: 3
  selector:
    matchLabels: {app: demo-api}
  template:
    metadata:
      labels: {app: demo-api}
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels: {app: demo-api}
      containers:
        - name: api
          image: REGION-docker.pkg.dev/PROJECT_ID/demo/api@sha256:REPLACE_WITH_REAL_DIGEST
          resources:
            requests: {cpu: 250m, memory: 256Mi}
            limits: {memory: 512Mi}
~~~

Replace placeholders. Strict topology constraints require sufficient compatible zone capacity.

## 12. HPA and Cluster Autoscaler

HPA adjusts replicas based on supported metrics. Cluster Autoscaler adjusts node capacity for unschedulable Pods, subject to pool bounds, quota and constraints. Do not let Terraform or Argo CD continually overwrite autoscaler-managed values.

Use measured resource requests, stable scaling behavior and capacity headroom for rollouts and AZ failures.

## 13. Gateway API and internal TLS

Use a supported GKE GatewayClass and an approved internal load balancer. Platform teams own shared Gateway listeners and certificates; application teams own restricted HTTPRoutes where allowed.

Validate hostnames, route attachment conditions, TLS certificate chain, backend health, firewall rules and DNS. Never assume a Service or Gateway is private without verifying its actual frontend.

## 14. NetworkPolicy enforcement

Apply policies only after confirming the installed GKE dataplane supports and enforces them. Test allowed frontend-to-API traffic and denied unauthorized Pod traffic. Verify required DNS, metrics and health-check paths remain functional.

## 15. Workload Identity Federation for GKE

Grant a synthetic KSA direct Google Cloud resource IAM access where supported, or use a dedicated IAM service account impersonation pattern with exact binding and annotation.

Test positive and negative API calls. Never store service account keys in Git, CI variables or Pod images.

## 16. Secret Manager and Artifact Registry

Use Workload Identity Federation to access synthetic Secret Manager data. Verify rotation, reload and audit events. Grant Artifact Registry pull permissions to the correct node identity and push permissions to protected CI identity.

Deploy immutable signed digests. Verify enforcement using an intentionally untrusted synthetic image in staging.

## 17. GitLab and Argo CD delivery chain

~~~text
Source MR -> tests -> SBOM -> scan -> sign digest
          -> protected GitOps MR -> CODEOWNERS
          -> Argo CD sync -> admission verification
          -> Pod imageID -> readiness -> SLO
~~~

GitLab should use short-lived Google Cloud federation. Argo CD AppProjects should restrict repositories, destinations and privileged resource kinds. Rollback through reviewed Git history rather than untracked imperative edits.

## 18. GitLab pipeline illustration

~~~yaml
stages: [validate, test, build, verify, promote]

validate:
  stage: validate
  image: registry.example.internal/ci/gke-tools:PINNED_DIGEST
  script:
    - ./ci/validate-terraform.sh
    - ./ci/validate-manifests.sh

test:
  stage: test
  image: registry.example.internal/ci/test-tools:PINNED_DIGEST
  script:
    - ./ci/run-tests.sh

build:
  stage: build
  image: registry.example.internal/ci/oci-builder:PINNED_DIGEST
  script:
    - ./ci/build-and-push.sh

verify:
  stage: verify
  image: registry.example.internal/ci/security-tools:PINNED_DIGEST
  script:
    - ./ci/verify-signatures.sh
    - ./ci/check-policy.sh

promote:
  stage: promote
  image: registry.example.internal/ci/gitlab-tools:PINNED_DIGEST
  script:
    - ./ci/propose-protected-gitops-mr.sh
~~~

Images and scripts are placeholders, not supplied runnable components. Implement OIDC trust restrictions and protect pipeline artifacts.

## 19. Stateful storage and recovery

Persistent Disk CSI supplies supported block storage; Filestore CSI supplies appropriate shared NFS storage. A zonal disk cannot be assumed to move seamlessly across zones.

Application-consistent backups are required for database recovery. Snapshot support and Filestore backup behavior depend on service tier and configuration. Test restore to independent PVCs and namespaces before a disaster.

## 20. Backup integrity and encryption

Document backup frequency, retention, encryption key availability, IAM permissions, immutable storage policy, restore region and application consistency.

Record source dataset checksum, backup timestamp, restore timestamp, recovered checksum and application verification. RPO is based on actual recovered data age; RTO is measured from incident declaration to validated service restoration.

## 21. Recovery architecture

A second GKE cluster alone is not a DR solution. Include recovery project, VPC, IAM, DNS, Artifact Registry, Secret Manager, quotas, encryption keys, GitOps state and backup access.

Select cold rebuild, warm standby or active-active based on measured recovery requirements and budget. Test loss of primary region dependencies.

## 22. Observability

Collect Cloud Audit Logs, GKE operational logs, Cloud Monitoring metrics, Managed Prometheus, Gateway/load balancer telemetry, CSI events and Argo CD metrics.

Alert on user-impacting error budget burn, node Ready loss, Pending Pods, DNS failures, Gateway 5xx, secret access failures, volume mount failures, backup failures and GitOps drift.

## 23. Upgrade strategy

Inventory GKE release channel, target versions, CRDs, admission webhooks, node image, CSI, Gateway controller, Argo CD and Workload Identity Federation behavior. Rehearse node upgrades with PDB and surge headroom.

GKE control-plane downgrade is not a routine rollback. Prepare supported forward remediation or replacement-cluster recovery.

## 24. Incident governance

Assign incident commander, platform lead, application owner, security lead and communications owner. Maintain timestamps, approved changes, evidence, blast radius, data-integrity decisions, RPO/RTO and corrective actions.

Avoid forcing node eviction or deleting PVCs to clear symptoms. Security boundaries and data integrity take precedence over cosmetic health indicators.

## 25. Lab A — Project and organization audit

1. Verify organization, project, region and billing.
2. Review IAM and Organization Policy.
3. Confirm approved budget, labels and quota.
4. Inventory GKE APIs and Terraform state.
5. Validate private operator connectivity.
6. Archive redacted evidence.

**Pass:** staging isolation and ownership are documented.

## 26. Lab B — Terraform reproducibility

1. Pin provider and module versions.
2. Run fmt, validate and plan.
3. Review IAM, networking and deletion impact.
4. Apply approved staging plan.
5. Verify GCP resource inventory.
6. Document state recovery and drift detection.

**Pass:** infrastructure is reproducible from reviewed code.

## 27. Lab C — Regional GKE resilience

1. Inventory system and application pools.
2. Verify zone distribution and actual VM counts.
3. Check quotas and spare capacity.
4. Simulate one-zone app capacity reduction.
5. Observe scheduler and autoscaler.
6. Restore capacity and measure SLO.

**Pass:** zone failure tolerance is evidenced.

## 28. Lab D — HPA and autoscaler interaction

1. Deploy synthetic workload with resource requests.
2. Configure CPU-based HPA.
3. Generate controlled demand.
4. Observe Pod replica scale-up.
5. Observe Cluster Autoscaler node scale-up.
6. Remove load and measure stabilization.

**Pass:** controllers scale without conflicting ownership.

## 29. Lab E — Private endpoint and egress

1. Verify private GKE control-plane access path.
2. Inspect Cloud DNS, firewall and Cloud NAT.
3. Test approved Google API access from private nodes.
4. Simulate restricted egress in isolated scope.
5. Restore approved routes.
6. Confirm no unintended public exposure.

**Pass:** management and workload connectivity are controlled.

## 30. Lab F — NetworkPolicy and DNS

1. Deploy frontend, API and unauthorized client.
2. Verify CoreDNS and Service discovery.
3. Apply reviewed ingress isolation policy.
4. Test permitted frontend traffic.
5. Test unauthorized client denial.
6. Restore baseline policy and record evidence.

**Pass:** isolation is enforced by the dataplane.

## 31. Lab G — Gateway API and TLS

1. Inspect supported GatewayClass.
2. Create internal staging Gateway.
3. Attach approved HTTPRoute.
4. Configure supported TLS certificate.
5. Test hostname, backend health and HTTPS.
6. Confirm frontend is internal and clean up.

**Pass:** private routing and TLS are functional.

## 32. Lab H — Workload Identity Federation

1. Create synthetic KSA.
2. Grant exact workload principal minimum resource IAM role.
3. Deploy workload to WIF-supported nodes.
4. Verify allowed Google API read.
5. Verify denied write and unrelated KSA.
6. Remove temporary permissions.

**Pass:** no service account key is required.

## 33. Lab I — Secret Manager rotation

1. Create synthetic secret.
2. Grant scoped workload access.
3. Mount/read through supported mechanism.
4. Rotate value.
5. Verify reload behavior and audit.
6. Confirm no secret value leaked into logs.

**Pass:** rotation and least privilege are tested.

## 34. Lab J — Artifact trust and GitOps promotion

1. Build synthetic image.
2. Generate SBOM, scan and sign digest.
3. Propose protected GitOps MR.
4. Obtain independent approval.
5. Verify Argo CD sync and Pod imageID.
6. Attempt untrusted image and confirm admission denial.

**Pass:** supply-chain policy is enforced.

## 35. Lab K — GitOps rollback

1. Deploy approved healthy revision.
2. Introduce synthetic app regression.
3. Confirm alert and Argo CD Degraded.
4. Revert through reviewed MR.
5. Validate readiness and SLO.
6. Confirm persistent resources were not pruned.

**Pass:** rollback is traceable and data-safe.

## 36. Lab L — Persistent Disk CSI recovery

1. Create disposable zonal Persistent Disk PVC.
2. Write synthetic data and checksum.
3. Restart Pod and verify persistence.
4. Simulate incompatible node affinity.
5. Restore compatible placement.
6. Verify checksum and record topology.

**Pass:** storage placement is understood.

## 37. Lab M — Filestore CSI shared storage

1. Verify supported Filestore tier and CSI driver.
2. Provision disposable RWX volume.
3. Mount in two synthetic Pods.
4. Test NFS permissions and shared writes.
5. Simulate isolated NFS network denial.
6. Restore and verify data integrity.

**Pass:** shared storage failure is recoverable.

## 38. Lab N — Application-consistent backup restore

1. Generate synthetic stateful dataset.
2. Quiesce/backup using application-approved method.
3. Record backup timestamp and checksum.
4. Restore to new namespace and PVC.
5. Verify application semantics and checksum.
6. Measure recovered data age and restore time.

**Pass:** RPO/RTO and integrity are measured.

## 39. Lab O — Cloud Audit and SLO alerting

1. Confirm Cloud Audit Logs and GKE logging.
2. Verify Managed Prometheus collection.
3. Generate denied IAM/Kubernetes API operation.
4. Trigger synthetic workload availability failure.
5. Confirm alert and runbook delivery.
6. Record detection latency.

**Pass:** security and reliability failures are observable.

## 40. Lab P — Node upgrade rehearsal

1. Review GKE target version and release channel.
2. Scan deprecated APIs and webhooks.
3. Validate surge, quota and PDB.
4. Perform approved staging node upgrade.
5. Verify Gateway, CSI, WIF and SLO.
6. Record forward-repair plan.

**Pass:** maintenance meets disruption budget.

## 41. Lab Q — Independent recovery cluster

1. Select approved recovery project and region.
2. Provision isolated VPC and GKE from Terraform.
3. Recreate IAM, WIF and Secret Manager trust.
4. Bootstrap Argo CD and approved platform resources.
5. Restore synthetic application data from protected backup.
6. Validate signed images, Gateway, identity and SLO.
7. Measure RPO/RTO and document cutover.

**Pass:** service is recoverable without primary cluster.

## 42. Lab R — Integrated incident command and FinOps

1. Simulate Pod Pending, Gateway 5xx and CSI mount failure.
2. Assign incident roles and establish timeline.
3. Correlate scheduler, GKE events, Cloud Monitoring and GitOps revisions.
4. Restore capacity, routing and storage safely.
5. Verify data integrity and user SLO.
6. Review incident cost, resource cleanup and preventive controls.

**Pass:** recovery is coordinated, measured and auditable.

## 43. Troubleshooting — twenty scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | GKE provisioning fails | API/IAM/quota | Inspect GCP operation |
| 2 | Private API inaccessible | Endpoint/DNS/routing | Restore approved access |
| 3 | kubectl Forbidden | Kubernetes RBAC | Repair scoped binding |
| 4 | Node pool scale-up fails | Quota/bounds | Restore headroom |
| 5 | Pods Pending | Affinity/topology | Correct placement |
| 6 | HPA not scaling | Missing metrics/requests | Repair metrics |
| 7 | Spot Job interrupted | No retry/checkpoint | Restore batch |
| 8 | Pod IP allocation fails | Secondary range shortage | Plan supported expansion |
| 9 | CoreDNS timeout | DNS/upstream/network | Restore resolver |
| 10 | NetworkPolicy blocks app | Missing allowed path | Fix scoped policy |
| 11 | Gateway route unattached | ParentRefs/policy | Correct delegation |
| 12 | Internal HTTPS unavailable | LB/TLS/backend | Trace frontend |
| 13 | WIF token fails | Principal/pool/placement | Repair trust |
| 14 | Secret Manager denied | IAM/CSI | Restore least privilege |
| 15 | Artifact Registry pull fails | Node identity/egress | Repair pull path |
| 16 | Binary Authorization rejects | Missing attestation | Verify artifact |
| 17 | Argo CD sync fails | Project/admission | Repair reviewed manifest |
| 18 | Persistent Disk mount fails | Zone/CSI | Restore compatible node |
| 19 | Filestore NFS unavailable | VPC/firewall | Restore path |
| 20 | DR restore inconsistent | Backup semantics | Use verified recovery point |

## 44. Runbook — private cluster connectivity

1. Confirm project, region and GKE operation state.
2. Verify gcloud identity and auth plugin.
3. Inspect endpoint access, DNS, firewall and routing.
4. Test from approved management network.
5. Restore private access without broad public exposure.
6. Validate kubectl, Argo CD and critical services.
7. Record RCA.

## 45. Runbook — node pool and autoscaling incident

1. Identify Pending Pods, requests and scheduler events.
2. Inspect node pool Ready count, zones and autoscaler logs.
3. Check quota, pool bounds, affinity, taints and PDBs.
4. Restore approved compatible capacity.
5. Verify workload SLO and critical platform controllers.
6. Measure recovery and cost.
7. Update forecast.

## 46. Runbook — Workload Identity or Secret Manager outage

1. Identify KSA, workload pool, principal and target resource.
2. Review direct IAM binding or impersonation configuration.
3. Check node WIF support and Pod placement.
4. Restore exact trust and least-privilege role.
5. Validate secret retrieval, rotation and negative tests.
6. Preserve audit logs.
7. Document preventive controls.

## 47. Runbook — Gateway, DNS and network incident

1. Identify hostnames, routes, Services and backends.
2. Inspect Gateway conditions, TLS, LB health and DNS.
3. Check NetworkPolicy, VPC firewall and Cloud NAT.
4. Restore approved GitOps/network configuration.
5. Validate internal exposure and application SLO.
6. Record recovery timeline.
7. Update monitoring.

## 48. Runbook — persistent storage incident

1. Identify PVC/PV, CSI driver, disk/Filestore and zone.
2. Inspect CSI events, topology and NFS/network dependencies.
3. Protect data; do not delete live PVCs.
4. Restore supported mount or recover from verified backup.
5. Validate application consistency and checksum.
6. Measure RPO/RTO.
7. Record RCA.

## 49. Runbook — GitOps release failure

1. Identify GitLab pipeline, image digest and Argo CD revision.
2. Distinguish image trust, RBAC, admission, network and runtime failures.
3. Freeze unsafe promotions.
4. Revert through reviewed GitOps MR or deploy approved fix.
5. Prevent destructive pruning of stateful resources.
6. Verify SLO and data integrity.
7. Archive evidence.

## 50. Runbook — GKE upgrade stalled

1. Freeze concurrent platform changes.
2. Inspect GKE operation, version and release channel.
3. Review PDB, quota, surge and unhealthy Pods.
4. Inspect deprecated APIs, admission and CSI/Gateway compatibility.
5. Restore supported capacity/add-ons.
6. Plan forward repair or replacement-cluster recovery.
7. Validate WIF, networking, storage and SLO.
8. Record incident.

## 51. Runbook — full regional disaster recovery

1. Declare incident and approved RPO/RTO.
2. Establish recovery project, VPC, DNS, quota and private access.
3. Provision GKE and node pools from reviewed Terraform.
4. Restore IAM, WIF, Artifact Registry and Secret Manager dependencies.
5. Bootstrap Argo CD and reconcile platform before applications.
6. Restore application-consistent data to new PVCs.
7. Validate signed image, Gateway/TLS, identity and SLO.
8. Perform approved traffic cutover and preserve evidence.

## 52. Evidence template

~~~text
Capstone/change ID:
GCP organization, project, region and cluster:
Terraform state, reviewed plan and provider version:
GKE Standard/Autopilot mode, release channel:
VPC, subnet, Pod/Service ranges and private access:
System/user node pools, AZs and quota:
Autoscaler, HPA, PDB and placement:
Gateway/Ingress, DNS, TLS and firewall:
Google IAM, Kubernetes RBAC and WIF principal:
Secret Manager and Artifact Registry:
Binary Authorization / image signature:
GitLab pipeline, GitOps MR, Argo CD revision:
Persistent Disk / Filestore and backup location:
Restore checksum and measured RPO/RTO:
Cloud Audit Logs, Monitoring and Prometheus:
Incident timeline, SLO and corrective actions:
Cost report, cleanup and independent approval:
~~~

Do not archive credentials, decoded Secrets, tokens, Terraform state or privileged kubeconfigs.

## 53. Scored enterprise readiness assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| Landing zone and Terraform | 15 | Approved infrastructure |
| Regional cluster and capacity | 15 | AZ and autoscaling tests |
| Networking, Gateway and TLS | 15 | Private connectivity and policy |
| IAM, WIF and supply-chain security | 15 | Positive/negative tests |
| GitLab/Argo CD governance | 10 | Signed digest and rollback |
| Storage, backup and disaster recovery | 20 | Integrity and measured RPO/RTO |
| Observability and incident response | 5 | Synthetic alerts and runbooks |
| FinOps and evidence | 5 | Budget and approval |
| **Total** | **100** | |

**Pass:** at least 85/100 and all critical controls: correct project, private management boundary, least-privilege IAM, enforced required artifact trust, approved GitOps promotion, no unsafe storage deletion and verified backup restoration meeting accepted objectives.

## 54. Final acceptance checklist

- [ ] GCP project, IAM, quota and budget verified.
- [ ] Terraform provisioning reproducible and reviewed.
- [ ] Regional GKE capacity and AZ resilience tested.
- [ ] HPA and Cluster Autoscaler interaction validated.
- [ ] Private API, DNS, egress and NetworkPolicy tested.
- [ ] Internal Gateway, TLS and backend health verified.
- [ ] Workload Identity Federation allowed/denied tests passed.
- [ ] Secret Manager rotation and Artifact Registry access tested.
- [ ] Binary Authorization or approved image trust enforced.
- [ ] GitLab/Argo CD promotion and rollback verified.
- [ ] Persistent Disk and Filestore behavior tested.
- [ ] Application-consistent backup and isolated restore passed.
- [ ] Cloud Audit Logs and SLO alerts operational.
- [ ] GKE upgrade rehearsal completed.
- [ ] Eighteen integrated labs completed.
- [ ] Twenty troubleshooting scenarios reviewed.
- [ ] Eight production runbooks validated.
- [ ] Independent RPO/RTO, SLO and cost sign-off obtained.

## 55. Knowledge check

1. Why does regional GKE not automatically provide multi-region DR?
2. How do Terraform and Argo CD resource ownership differ?
3. Why must Cluster Autoscaler capacity account for regional node multiplicity?
4. How can a strict topology spread rule block recovery?
5. What proves a GKE control-plane endpoint is private?
6. Why are WIF principal permissions separate from Kubernetes RBAC?
7. How does Binary Authorization differ from image signing?
8. Why can a zonal Persistent Disk block Pod rescheduling?
9. What evidence proves a backup is application-consistent?
10. How should RPO and RTO be measured during recovery?

## 56. References

- [GKE documentation](https://cloud.google.com/kubernetes-engine/docs)
- [GKE baseline security](https://cloud.google.com/kubernetes-engine/docs/concepts/security-overview)
- [GKE regional clusters](https://cloud.google.com/kubernetes-engine/docs/concepts/regional-clusters)
- [GKE Cluster Autoscaler](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler)
- [GKE private clusters](https://cloud.google.com/kubernetes-engine/docs/how-to/private-clusters)
- [GKE Gateway API](https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api)
- [GKE Persistent Disk CSI](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver)
- [GKE Filestore CSI](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/filestore-csi-driver)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [Binary Authorization](https://cloud.google.com/binary-authorization/docs)
- [Cloud Audit Logs](https://cloud.google.com/logging/docs/audit)
- [GKE Observability](https://cloud.google.com/kubernetes-engine/docs/concepts/observability)
- [GKE Upgrades](https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)

---

**Chapter 080 complete — Part 16: Google Kubernetes Engine complete (Chapters 076–080).**

**Next:** Chapter 081 — Multi-Cloud and Multi-Cluster GitOps Architecture, Governance and Platform Foundations, beginning Part 17.